import logging
import re
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

import backend.scripts_path as scripts_path  # noqa: F401  (garante sys.path antes dos imports abaixo)
from backend.auth.deps import get_current_active_user
from backend.auth.models import Usuario
from backend.bitin_number import SetorInvalido, gerar_e_salvar_bitin_sql
from backend.db.mongodb import get_mongo_db
from backend.db.session import get_db
from backend.models_sql import BitinSQL

import bitin_document
import bitin_lifecycle
import bitin_model
import bitin_view
import sap_paste_parser

logger = logging.getLogger(__name__)

VBA_MAPPING_CONFIG = bitin_model.load_config(scripts_path.VBA_MAPPING_CONFIG_PATH)
DOCUMENT_CONFIG = bitin_document.load_config(scripts_path.DOCUMENT_CONFIG_PATH)
MATERIAIS_SCHEMA = bitin_model.build_materiais_schema(VBA_MAPPING_CONFIG, DOCUMENT_CONFIG)
CHECKLIST_SCHEMA = bitin_document.build_checklist_schema(DOCUMENT_CONFIG)

router = APIRouter()

STATUS_RASCUNHO = bitin_lifecycle.STATUS_RASCUNHO
STATUS_ENVIADO = bitin_lifecycle.STATUS_ENVIADO
ADMIN_LEVEL = 99


class DraftRequest(BaseModel):
    mongo_id: str | None = None
    titulo: str | None = None
    content: dict[str, Any]


class SapPasteRequest(BaseModel):
    raw_text: str


class BitinResponse(BaseModel):
    mongo_id: str
    codigo: str | None = None
    status: str
    titulo: str | None = None
    content: dict[str, Any]
    criado_por: str | None = None
    created_at: str
    updated_at: str
    # Calculado por requisição (não vem do Mongo) -- pra o frontend abrir a tela travada
    # (modo leitura) quando quem está vendo não pode editar, em vez de deixar editar e só
    # descobrir o 403 ao tentar salvar. Ver _pode_editar. Adicionado em 2026-07-14.
    pode_editar: bool = True


class EnviarResponse(BaseModel):
    ok: bool
    errors: list[dict[str, Any]] = []
    bitin: BitinResponse | None = None


def _pode_editar(doc: dict[str, Any], current_user: Usuario) -> bool:
    """Mesmo critério de _require_owner_or_admin, mas devolve bool em vez de levantar --
    usado pro frontend saber de antemão se deve abrir a tela travada (modo leitura), em vez
    de deixar editar e só descobrir com um 403 ao tentar salvar. Um BITin já enviado nunca
    pode ser editado, nem pelo dono/admin (ver bitin_lifecycle)."""
    if doc.get("status") == STATUS_ENVIADO:
        return False
    criado_por = doc.get("criado_por")
    if criado_por and criado_por != current_user.email and current_user.permission_level < ADMIN_LEVEL:
        return False
    return True


def _doc_to_response(doc: dict[str, Any], current_user: Usuario) -> BitinResponse:
    return BitinResponse(
        mongo_id=doc["_id"],
        codigo=doc.get("content", {}).get("bitin"),
        status=doc.get("status", STATUS_RASCUNHO),
        titulo=doc.get("titulo"),
        content=doc.get("content", {}),
        criado_por=doc.get("criado_por"),
        created_at=doc.get("created_at", ""),
        updated_at=doc.get("updated_at", ""),
        pode_editar=_pode_editar(doc, current_user),
    )


def _require_owner_or_admin(doc: dict[str, Any], current_user: Usuario) -> None:
    """Só quem criou o rascunho (ou um admin) pode editar/excluir. Docs sem 'criado_por'
    (nenhum registrado) não são bloqueados -- não há dono conhecido pra comparar."""
    criado_por = doc.get("criado_por")
    if criado_por and criado_por != current_user.email and current_user.permission_level < ADMIN_LEVEL:
        raise HTTPException(
            status_code=403,
            detail="Só quem criou o rascunho (ou um admin) pode editar/excluir",
        )


class ResumoUsuarioResponse(BaseModel):
    rascunhos: int
    enviados: int


@router.get("/resumo-usuario", response_model=ResumoUsuarioResponse)
async def get_resumo_usuario(
    current_user: Usuario = Depends(get_current_active_user),
    mongo_db=Depends(get_mongo_db),
):
    """Contagem de BITins do próprio usuário logado (rascunhos/enviados) -- alimenta os
    cartões de resumo da Home (ver docs/FRONTEND.md). Escopado por criado_por de propósito
    ("só os meus", não o sistema inteiro) -- decisão registrada com o usuário."""
    collection = mongo_db["bitin_contents"]
    rascunhos = await collection.count_documents(
        {"criado_por": current_user.email, "status": STATUS_RASCUNHO}
    )
    enviados = await collection.count_documents(
        {"criado_por": current_user.email, "status": STATUS_ENVIADO}
    )
    return ResumoUsuarioResponse(rascunhos=rascunhos, enviados=enviados)


@router.get("/schema/materiais")
async def get_materiais_schema(_current_user: Usuario = Depends(get_current_active_user)):
    """Colunas do grid de materiais do frontend -- fonte única de verdade (ver
    docs/BACKEND.md, 'Grid de materiais dirigido por schema'). Config já carregada em
    memória no import do módulo (mesmo config imutável usado por validate_bitin/enviar)."""
    return MATERIAIS_SCHEMA


@router.get("/schema/checklist")
async def get_checklist_schema(_current_user: Usuario = Depends(get_current_active_user)):
    """Os 22 itens fixos do checklist (id + etapa) -- fonte única de verdade pro frontend
    montar a tabela editável na tela de cadastro (ver docs/BACKEND.md)."""
    return {"items": CHECKLIST_SCHEMA}


@router.post("/parse-sap-paste")
async def parse_sap_paste_endpoint(
    paste_in: SapPasteRequest,
    _current_user: Usuario = Depends(get_current_active_user),
):
    """Colar do SAP -> materiais[] prontos (identificação + snapshot atual), pro frontend
    inserir no grid. Reaproveita sap_paste_parser.py (já testado) em vez de reimplementar
    o parser em JS."""
    materiais = sap_paste_parser.parse_sap_paste_to_materiais(paste_in.raw_text, VBA_MAPPING_CONFIG)
    return {"materiais": materiais}


@router.post("/draft", response_model=BitinResponse)
async def create_or_update_draft(
    draft_in: DraftRequest,
    current_user: Usuario = Depends(get_current_active_user),
    mongo_db=Depends(get_mongo_db),
):
    """Cria ou atualiza um rascunho -- sem validação de negócio (liberdade de edição,
    ver docs/BITIN_MODEL.md 'Ciclo de vida')."""
    collection = mongo_db["bitin_contents"]
    now = datetime.now().isoformat()

    if draft_in.mongo_id:
        existing = await collection.find_one({"_id": draft_in.mongo_id})
        if not existing:
            raise HTTPException(status_code=404, detail="Rascunho não encontrado")
        if existing.get("status") == STATUS_ENVIADO:
            raise HTTPException(status_code=400, detail="BITin já enviado — não pode ser editado")
        _require_owner_or_admin(existing, current_user)
        mongo_id = draft_in.mongo_id
        created_at = existing.get("created_at", now)
        criado_por = existing.get("criado_por")  # não muda dono numa atualização
    else:
        mongo_id = str(uuid.uuid4())
        created_at = now
        criado_por = current_user.email

    # data_solicitacao é carimbada pelo sistema (data em que o rascunho foi salvo pela
    # primeira vez), não escolhida livremente pelo engenheiro -- qualquer valor mandado pelo
    # cliente pra esse campo é ignorado. Ver docs/BITIN_MODEL.md, "Regras de campo".
    content = {**draft_in.content, "data_solicitacao": created_at[:10]}

    doc = {
        "_id": mongo_id,
        "status": STATUS_RASCUNHO,
        "titulo": draft_in.titulo or "Novo Rascunho",
        "content": content,
        "criado_por": criado_por,
        "created_at": created_at,
        "updated_at": now,
    }
    await collection.replace_one({"_id": mongo_id}, doc, upsert=True)
    return _doc_to_response(doc, current_user)


@router.get("/{mongo_id}", response_model=BitinResponse)
async def get_bitin(
    mongo_id: str,
    current_user: Usuario = Depends(get_current_active_user),
    mongo_db=Depends(get_mongo_db),
):
    collection = mongo_db["bitin_contents"]
    doc = await collection.find_one({"_id": mongo_id})
    if not doc:
        raise HTTPException(status_code=404, detail="BITin não encontrado")
    return _doc_to_response(doc, current_user)


TERMO_CAMPO_MONGO = {
    "motivo": "content.motivo",
    "solicitante": "content.solicitante",
    "codigo": "content.bitin",
}


@router.get("", response_model=list[BitinResponse])
async def list_bitins(
    status: str | None = None,
    termo: str | None = None,
    campo: str | None = None,
    limit: int = 20,
    skip: int = 0,
    current_user: Usuario = Depends(get_current_active_user),
    mongo_db=Depends(get_mongo_db),
):
    collection = mongo_db["bitin_contents"]
    # "Meus Bitins" -- mesma decisão de escopo já registrada na Home (resumo-usuario):
    # cada usuário só vê os próprios BITins, não a listagem do sistema inteiro. Admins não
    # ganham uma visão global aqui (diferente de Gestão de usuários) porque essa tela lista
    # rascunhos/conteúdo pessoal, não é uma função administrativa.
    query: dict[str, Any] = {"criado_por": current_user.email}
    if status:
        query["status"] = status
    if termo:
        # re.escape antes de virar $regex do Mongo -- sem isso, metacaracteres de regex
        # digitados pelo usuário (ex.: "(", "*") viram parte do padrão em vez de texto
        # literal, podendo causar matches inesperados ou custo de busca patológico.
        termo_escapado = re.escape(termo)
        # `campo` restringe a busca a um campo específico (Motivo/Solicitante/Código) -- sem
        # ele (ou com valor desconhecido), busca nos três de uma vez, como sempre foi.
        campo_mongo = TERMO_CAMPO_MONGO.get(campo or "")
        if campo_mongo:
            query[campo_mongo] = {"$regex": termo_escapado, "$options": "i"}
        else:
            query["$or"] = [
                {"content.motivo": {"$regex": termo_escapado, "$options": "i"}},
                {"content.solicitante": {"$regex": termo_escapado, "$options": "i"}},
                {"content.bitin": {"$regex": termo_escapado, "$options": "i"}},
            ]
    cursor = collection.find(query).sort("updated_at", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)
    return [_doc_to_response(doc, current_user) for doc in docs]


@router.delete("/{mongo_id}")
async def delete_bitin(
    mongo_id: str,
    current_user: Usuario = Depends(get_current_active_user),
    mongo_db=Depends(get_mongo_db),
):
    collection = mongo_db["bitin_contents"]
    doc = await collection.find_one({"_id": mongo_id})
    if not doc:
        raise HTTPException(status_code=404, detail="BITin não encontrado")
    if doc.get("status") == STATUS_ENVIADO:
        raise HTTPException(status_code=400, detail="BITin já enviado — não pode ser excluído")
    _require_owner_or_admin(doc, current_user)
    await collection.delete_one({"_id": mongo_id})
    return {"message": "Rascunho excluído", "mongo_id": mongo_id}


@router.get("/{mongo_id}/resumo")
async def get_resumo(
    mongo_id: str,
    _current_user: Usuario = Depends(get_current_active_user),
    mongo_db=Depends(get_mongo_db),
):
    collection = mongo_db["bitin_contents"]
    doc = await collection.find_one({"_id": mongo_id})
    if not doc:
        raise HTTPException(status_code=404, detail="BITin não encontrado")
    return bitin_view.render_bitin_summary(doc["content"], VBA_MAPPING_CONFIG, DOCUMENT_CONFIG)


@router.post("/{mongo_id}/enviar", response_model=EnviarResponse)
async def enviar_bitin_endpoint(
    mongo_id: str,
    current_user: Usuario = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    mongo_db=Depends(get_mongo_db),
):
    """O ponto-chave: roda TODA a validação (bitin_lifecycle.enviar_bitin) antes de
    travar o BITin e gerar o número. Se falhar, devolve os erros estruturados (422),
    sem tocar em nenhum banco."""
    collection = mongo_db["bitin_contents"]
    doc = await collection.find_one({"_id": mongo_id})
    if not doc:
        raise HTTPException(status_code=404, detail="BITin não encontrado")
    if doc.get("status") == STATUS_ENVIADO:
        raise HTTPException(status_code=400, detail="BITin já foi enviado anteriormente")

    content = doc["content"]
    ok, errors = bitin_lifecycle.enviar_bitin(content, VBA_MAPPING_CONFIG, DOCUMENT_CONFIG)

    if not ok:
        return EnviarResponse(ok=False, errors=errors)

    try:
        bitin_sql = gerar_e_salvar_bitin_sql(
            db, content.get("setor", ""), mongo_id, criado_por=current_user.email,
        )
    except SetorInvalido as exc:
        return EnviarResponse(ok=False, errors=[
            {"field": "setor", "code": "invalid_setor_value", "message": str(exc)}
        ])
    except RuntimeError:
        # gerar_e_salvar_bitin_sql esgotou as tentativas -- na prática, quase sempre porque
        # este mesmo mongo_id (unique em BitinSQL.mongo_document_id) já foi enviado por uma
        # requisição concorrente enquanto esta rodava (2 cliques em "Enviar", ou 2 abas
        # abertas). Antes disso o cliente via um 500 puro; agora distingue os dois casos.
        db.rollback()
        ja_enviado = (
            db.query(BitinSQL).filter(BitinSQL.mongo_document_id == mongo_id).first()
        )
        if ja_enviado is not None:
            logger.info("Envio duplicado detectado (concorrência): mongo_id=%s codigo=%s", mongo_id, ja_enviado.codigo)
            return EnviarResponse(ok=False, errors=[
                {"field": "", "code": "ja_enviado_concorrente", "message": "Este BITin já foi enviado (provavelmente em outra aba/clique duplo). Recarregue a página."}
            ])
        logger.error("Falha ao gerar número sequencial após esgotar tentativas: mongo_id=%s setor=%s", mongo_id, content.get("setor"))
        raise HTTPException(status_code=503, detail="Não foi possível gerar o número do BITin agora. Tente novamente.")

    content["bitin"] = bitin_sql.codigo
    now = datetime.now().isoformat()
    try:
        await collection.update_one(
            {"_id": mongo_id},
            {"$set": {
                "status": STATUS_ENVIADO,
                "content": content,
                "sql_ref_id": bitin_sql.id,
                "updated_at": now,
            }},
        )
    except Exception:
        # Postgres já commitou o número (bitin_sql), mas o Mongo não gravou "enviado" --
        # sem uma transação real cobrindo os 2 bancos, desfaz o lado Postgres (best-effort)
        # pra não deixar um código "fantasma" reservado apontando pra um rascunho que nunca
        # foi marcado como enviado. Se o rollback também falhar, fica logado alto e claro em
        # vez de silencioso -- precisa de reconciliação manual (ver docs/BACKEND.md).
        logger.exception(
            "Mongo update_one falhou após commit no Postgres -- desfazendo BitinSQL id=%s codigo=%s mongo_id=%s",
            bitin_sql.id, bitin_sql.codigo, mongo_id,
        )
        try:
            db.delete(bitin_sql)
            db.commit()
        except Exception:
            logger.critical(
                "INCONSISTÊNCIA NÃO RESOLVIDA: BitinSQL id=%s codigo=%s ficou órfão (mongo_id=%s "
                "continua em rascunho). Requer reconciliação manual.",
                bitin_sql.id, bitin_sql.codigo, mongo_id,
            )
        raise HTTPException(status_code=500, detail="Falha ao registrar o envio. Tente novamente.")

    updated_doc = await collection.find_one({"_id": mongo_id})
    return EnviarResponse(ok=True, errors=[], bitin=_doc_to_response(updated_doc, current_user))
