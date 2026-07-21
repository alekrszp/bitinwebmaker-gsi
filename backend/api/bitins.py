import logging
import re
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

import backend.scripts_path as scripts_path  # noqa: F401  (garante sys.path antes dos imports abaixo)
from backend.api.users import _usuarios_do_mesmo_subgrupo_query
from backend.auth.deps import (
    NIVEL_ADMIN,
    NIVEL_GESTOR,
    check_permission,
    check_setor,
    eh_do_setor,
    get_current_active_user,
)
from backend.auth.models import Usuario
from backend.auth.schemas import SETOR_CADASTRO, SETOR_ENGENHARIA, SETOR_PROCESSOS
from backend.bitin_number import SetorInvalido, gerar_e_salvar_bitin_sql
from backend.db.mongodb import get_mongo_db
from backend.db.session import get_db
from backend.models_sql import BitinSQL

# Estes imports de scripts/ precisam vir DEPOIS de backend.scripts_path acima, que injeta
# scripts/ em sys.path; ruff/isort alfabetizaria pra antes se deixado como um bloco só (achado
# ao rodar `ruff check --fix`, revertido manualmente).
# isort: off
import bitin_document
import bitin_lifecycle
import bitin_model
import bitin_pdf
import bitin_view
import sap_paste_parser
# isort: on

logger = logging.getLogger(__name__)

VBA_MAPPING_CONFIG = bitin_model.load_config(scripts_path.VBA_MAPPING_CONFIG_PATH)
DOCUMENT_CONFIG = bitin_document.load_config(scripts_path.DOCUMENT_CONFIG_PATH)
MATERIAIS_SCHEMA = bitin_model.build_materiais_schema(VBA_MAPPING_CONFIG, DOCUMENT_CONFIG)
CHECKLIST_SCHEMA = bitin_document.build_checklist_schema(DOCUMENT_CONFIG)

router = APIRouter()

STATUS_RASCUNHO = bitin_lifecycle.STATUS_RASCUNHO
STATUS_ENVIADO = bitin_lifecycle.STATUS_ENVIADO


class DraftRequest(BaseModel):
    mongo_id: str | None = None
    titulo: str | None = None
    content: dict[str, Any]


class SapPasteRequest(BaseModel):
    raw_text: str


class PreviewResumoRequest(BaseModel):
    content: dict[str, Any]


class AtualizarProcessosRequest(BaseModel):
    content: dict[str, Any]


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
    # Fila do setor Cadastro (2026-07-17, substitui o e-mail automático do Módulo12.bas) --
    # só passa a ter sentido depois de status==enviado, ver bitin_lifecycle.encaminhar_para_roteiro.
    encaminhado_roteiro: bool = False
    data_encaminhado_roteiro: str | None = None
    # Setor Processos (2026-07-17) -- ver bitin_lifecycle.concluir_processamento.
    processos_concluido: bool = False
    data_processos_concluido: str | None = None
    sem_necessidade_roteiro: bool = False
    # Calculado por requisição (não vem do Mongo, ver bitin_document.precisa_roteiro) -- true
    # se algum material tem Alt em {"D/P","D/-","-/P"}. Decide se a CadastroPage.tsx mostra
    # "Encaminhar para roteiro" ou "Não precisa de roteiro" na aba "Recebidos".
    precisa_roteiro: bool = False
    # Penúltimo passo (2026-07-20) -- ver bitin_lifecycle.concluir_bitin. Só depois disso o
    # PDF fica disponível na aba "Pendência de envio" de CadastroPage.tsx.
    bitin_cadastrado: bool = False
    data_cadastrado: str | None = None
    # Último passo de todos (2026-07-20) -- ver bitin_lifecycle.enviar_windchill.
    windchill_enviado: bool = False
    data_windchill_enviado: str | None = None


class EnviarResponse(BaseModel):
    ok: bool
    errors: list[dict[str, Any]] = []
    bitin: BitinResponse | None = None


def _bitin_liberado_para_processos(doc: dict[str, Any], current_user: Usuario) -> bool:
    """Única exceção à regra "enviado é travado pra sempre" (2026-07-17) -- Processos/Admin
    podem reeditar um BITin já enviado ENQUANTO ele estiver na fila do Cadastro
    (`encaminhado_roteiro=True`) e ainda não tiver sido concluído
    (`processos_concluido`). Ver bitin_lifecycle.concluir_processamento."""
    return (
        (eh_do_setor(current_user, SETOR_PROCESSOS) or current_user.permission_level >= NIVEL_ADMIN)
        and doc.get("encaminhado_roteiro", False)
        and not doc.get("processos_concluido", False)
    )


def _pode_editar(doc: dict[str, Any], current_user: Usuario) -> bool:
    """Mesmo critério de _require_owner_or_admin, mas devolve bool em vez de levantar --
    usado pro frontend saber de antemão se deve abrir a tela travada (modo leitura), em vez
    de deixar editar e só descobrir com um 403 ao tentar salvar. Um BITin já enviado é travado
    pra todo mundo (nem dono/admin edita), EXCETO a janela de reedição do Processos, ver
    _bitin_liberado_para_processos."""
    if doc.get("status") == STATUS_ENVIADO:
        return _bitin_liberado_para_processos(doc, current_user)
    criado_por = doc.get("criado_por")
    if criado_por and criado_por != current_user.email and current_user.permission_level < NIVEL_ADMIN:
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
        encaminhado_roteiro=doc.get("encaminhado_roteiro", False),
        data_encaminhado_roteiro=doc.get("data_encaminhado_roteiro"),
        processos_concluido=doc.get("processos_concluido", False),
        data_processos_concluido=doc.get("data_processos_concluido"),
        sem_necessidade_roteiro=doc.get("sem_necessidade_roteiro", False),
        precisa_roteiro=bitin_document.precisa_roteiro(doc.get("content", {})),
        bitin_cadastrado=doc.get("bitin_cadastrado", False),
        data_cadastrado=doc.get("data_cadastrado"),
        windchill_enviado=doc.get("windchill_enviado", False),
        data_windchill_enviado=doc.get("data_windchill_enviado"),
    )


def _require_owner_or_admin(doc: dict[str, Any], current_user: Usuario) -> None:
    """Só quem criou o rascunho (ou um admin) pode editar/excluir. Docs sem 'criado_por'
    (nenhum registrado) não são bloqueados -- não há dono conhecido pra comparar."""
    criado_por = doc.get("criado_por")
    if criado_por and criado_por != current_user.email and current_user.permission_level < NIVEL_ADMIN:
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


class ResumoPainelResponse(BaseModel):
    cadastro_aguardando: int
    cadastro_cadastrados: int
    processos_pendentes: int
    processos_concluidos: int
    geral_rascunhos: int
    geral_enviados: int


@router.get("/resumo-painel", response_model=ResumoPainelResponse)
async def get_resumo_painel(
    current_user: Usuario = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    mongo_db=Depends(get_mongo_db),
):
    """Contadores do dashboard (Home.tsx) num ÚNICO round-trip ao Mongo, via `$facet`
    (2026-07-20, pedido explícito: "otimiza velocidade de carregamento... tá muito lento") --
    antes, Home.tsx buscava até 7 listas COMPLETAS de BITins (`GET /bitins?limit=200/500` x7,
    incluindo `content` inteiro de cada um só pra contar `.length` no cliente) em paralelo.
    Além de 7 round-trips simultâneos, cada resposta carregava dados que nunca eram usados
    (motivo, materiais, checklist...) só pra virar um número. `$facet` roda os 6 `count`
    dentro do banco, numa passada só, devolvendo só os números -- mesmo escopo de
    visibilidade de sempre (ver _condicoes_escopo, definida mais abaixo -- lookup só
    acontece na hora da chamada, ordem de definição no arquivo não importa aqui).

    Registrada ANTES de GET /{mongo_id} de propósito (mesmo motivo de /resumo-usuario,
    /schema/*, /parse-sap-paste acima) -- rotas estáticas precisam vir antes da rota
    dinâmica /{mongo_id}, senão o FastAPI tentaria casar "resumo-painel" como um mongo_id."""
    collection = mongo_db["bitin_contents"]
    escopo = _condicoes_escopo(current_user, db)

    def com_escopo(*extra: dict[str, Any]) -> dict[str, Any]:
        condicoes = [*escopo, *extra]
        return {"$and": condicoes} if condicoes else {}

    pipeline = [
        {
            "$facet": {
                "cadastro_aguardando": [
                    {"$match": com_escopo({"status": STATUS_ENVIADO}, {"processos_concluido": True}, {"bitin_cadastrado": {"$ne": True}})},
                    {"$count": "n"},
                ],
                "cadastro_cadastrados": [
                    # Exclui quem já foi mandado pro Windchill (2026-07-20, nova etapa final)
                    # -- mesmo filtro da aba "Pendência de envio" de CadastroPage.tsx, que também não
                    # inclui mais quem já virou "Concluído".
                    {"$match": com_escopo({"status": STATUS_ENVIADO}, {"bitin_cadastrado": True}, {"windchill_enviado": {"$ne": True}})},
                    {"$count": "n"},
                ],
                "processos_pendentes": [
                    {"$match": com_escopo(
                        {"status": STATUS_ENVIADO}, {"encaminhado_roteiro": True},
                        {"processos_concluido": {"$ne": True}}, {"sem_necessidade_roteiro": {"$ne": True}},
                    )},
                    {"$count": "n"},
                ],
                "processos_concluidos": [
                    # Exclui quem nunca passou pelo Processos de verdade (2026-07-21, achado
                    # ao investigar BITins de troca de fornecedor -/F aparecendo aqui --
                    # concluir_sem_roteiro também seta processos_concluido=True como atalho,
                    # ver ProcessosPage.tsx e bitin_lifecycle.py::concluir_sem_roteiro).
                    {"$match": com_escopo(
                        {"status": STATUS_ENVIADO}, {"processos_concluido": True},
                        {"sem_necessidade_roteiro": {"$ne": True}},
                    )},
                    {"$count": "n"},
                ],
                "geral_rascunhos": [
                    {"$match": com_escopo({"status": STATUS_RASCUNHO})},
                    {"$count": "n"},
                ],
                "geral_enviados": [
                    {"$match": com_escopo({"status": STATUS_ENVIADO})},
                    {"$count": "n"},
                ],
            }
        }
    ]
    resultado = await collection.aggregate(pipeline).to_list(length=1)
    fatos = resultado[0] if resultado else {}
    return ResumoPainelResponse(**{
        chave: (fatos.get(chave, [{"n": 0}]) or [{"n": 0}])[0].get("n", 0)
        for chave in (
            "cadastro_aguardando", "cadastro_cadastrados", "processos_pendentes",
            "processos_concluidos", "geral_rascunhos", "geral_enviados",
        )
    })


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

    # Cadastro e Processos não usam esta rota (2026-07-20, pedido explícito: "usuário de
    # cadastro tem somente a tela cadastro, igual processos. não pode criar novo bitin nem
    # alterá-lo") -- os dois trabalham só pelas rotas dedicadas de cada fila
    # (encaminhar-roteiro/concluir-sem-roteiro/concluir-bitin pro Cadastro,
    # atualizar-processos/concluir-processos pro Processos), nunca por aqui. Bloqueia tanto
    # criar (sem mongo_id) quanto atualizar (com mongo_id) -- diferente do bloqueio anterior
    # do Processos, que só cobria criação. Admin continua liberado (não é nível operacional
    # restrito, mesmo padrão dos outros gates). Checado por SETOR agora (2026-07-20, 2ª
    # revisão do modelo de permissões), não mais por nível fixo -- vale pra Gestor de
    # Cadastro/Processos igual pra membro comum, só Engenharia (qualquer rank) cria BITin.
    if eh_do_setor(current_user, SETOR_CADASTRO, SETOR_PROCESSOS):
        raise HTTPException(
            status_code=403,
            detail="Este setor não cria nem edita BITins pelo rascunho -- só pela fila própria.",
        )

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
        # "Solicitante vira automático (nome de quem está logado)." (decisão do usuário,
        # 2026-07-16) -- numa atualização preserva o solicitante ORIGINAL do rascunho, não
        # importa quem esteja salvando agora (ex.: admin editando o rascunho de outra pessoa)
        # nem o que vier no payload. Isso é reforçado aqui no backend -- a barreira real de
        # segurança/integridade de dado é esta, não só a omissão do campo no formulário do
        # frontend, que qualquer requisição manual poderia contornar.
        solicitante = existing.get("content", {}).get("solicitante")
    else:
        mongo_id = str(uuid.uuid4())
        created_at = now
        criado_por = current_user.email
        # Idem ao comentário acima: na criação, o solicitante é sempre o nome de quem está
        # logado -- qualquer valor mandado pelo cliente pra esse campo é ignorado.
        solicitante = current_user.nome

    # data_solicitacao é carimbada pelo sistema (data em que o rascunho foi salvo pela
    # primeira vez), não escolhida livremente pelo engenheiro -- qualquer valor mandado pelo
    # cliente pra esse campo é ignorado. Ver docs/BITIN_MODEL.md, "Regras de campo".
    content = {**draft_in.content, "data_solicitacao": created_at[:10], "solicitante": solicitante}

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


@router.get("/{mongo_id}/pdf")
async def get_bitin_pdf(
    mongo_id: str,
    _current_user: Usuario = Depends(get_current_active_user),
    mongo_db=Depends(get_mongo_db),
):
    """Exporta o BITin em PDF (relatório interno). Mesma checagem de acesso que GET
    /bitins/{mongo_id} acima (só exige estar autenticado + o doc existir -- essa rota não
    tem restrição de visibilidade por dono/setor, ver _doc_to_response/list_bitins pra onde
    isso é aplicado de fato, no /bitins sem id)."""
    collection = mongo_db["bitin_contents"]
    doc = await collection.find_one({"_id": mongo_id})
    if not doc:
        raise HTTPException(status_code=404, detail="BITin não encontrado")
    pdf_bytes = bitin_pdf.build_bitin_pdf(doc.get("content", {}))
    codigo = doc.get("content", {}).get("bitin") or mongo_id
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="BITin-{codigo}.pdf"'},
    )


TERMO_CAMPO_MONGO = {
    "motivo": "content.motivo",
    "solicitante": "content.solicitante",
    "codigo": "content.bitin",
}

# `criado_por` é o e-mail de quem criou o BITin (campo top-level do doc, não content.*) --
# fora do TERMO_CAMPO_MONGO/campo_mongo acima de propósito, porque tem seu próprio parâmetro
# dedicado (ver `list_bitins`) usado pelo filtro "Usuário" do Painel geral, que precisa
# combinar com os outros filtros (status/etapa/setor) sem herdar o "$or" de motivo/
# solicitante/código.


def _condicoes_escopo(current_user: Usuario, db: Session) -> list[dict[str, Any]]:
    """Escopo por (rank, setor) -- 2ª revisão do modelo de permissões (2026-07-20): Cadastro/
    Processos/Engenharia não são mais níveis fixos, são valores de `Usuario.setor`, cruzados
    com o rank (NIVEL_INDIVIDUAL/NIVEL_GESTOR/NIVEL_ADMIN, ver backend/auth/deps.py).
    - setor=cadastro (INDIVIDUAL ou GESTOR): time central que recebe TODO BITin enviado por
      QUALQUER pessoa, de qualquer Subgrupo. Vê também os PRÓPRIOS BITins em qualquer status
      (incl. rascunho) -- só rascunho ALHEIO continua privado. Gestor de Cadastro NÃO tem
      escopo mais amplo que um Cadastro comum aqui de propósito (2026-07-20, pedido
      explícito: "só ganha o painel de oversight, fila de trabalho continua igual").
    - setor=processos (INDIVIDUAL ou GESTOR): mesmo raciocínio de "time central", mas pela
      fila encaminhada (encaminhado_roteiro=True) em vez de "todo enviado".
    - setor=engenharia + GESTOR: BITins de qualquer um que compartilhe ao menos um Subgrupo
      com ele (mesma consulta SQL de backend/api/users.py::
      _usuarios_do_mesmo_subgrupo_query). Gestor sem subgrupo nenhum não ganha acesso a mais
      ninguém -- cai pra "só os próprios".
    - setor=engenharia + INDIVIDUAL: só os próprios BITins (criado_por == e-mail).
    - Admin (99): sem restrição nenhuma -- vê o sistema inteiro, independente do setor.

    Extraído de list_bitins (2026-07-20) pra ser reaproveitado por GET /bitins/resumo-painel
    (contadores do dashboard, ver Home.tsx) sem duplicar a regra de visibilidade."""
    if current_user.permission_level >= NIVEL_ADMIN:
        return []  # sem restrição -- nenhuma condição de escopo
    if eh_do_setor(current_user, SETOR_CADASTRO):
        return [{"$or": [{"criado_por": current_user.email}, {"status": STATUS_ENVIADO}]}]
    if eh_do_setor(current_user, SETOR_PROCESSOS):
        return [{"$or": [{"criado_por": current_user.email}, {"encaminhado_roteiro": True}]}]
    if eh_do_setor(current_user, SETOR_ENGENHARIA) and current_user.permission_level >= NIVEL_GESTOR:
        colegas = _usuarios_do_mesmo_subgrupo_query(db, current_user).all()
        emails = [u.email for u in colegas]
        if emails:
            return [{"criado_por": {"$in": emails}}]
        return [{"criado_por": current_user.email}]
    return [{"criado_por": current_user.email}]


@router.get("", response_model=list[BitinResponse])
async def list_bitins(
    status: str | None = None,
    termo: str | None = None,
    campo: str | None = None,
    encaminhado_roteiro: bool | None = None,
    processos_concluido: bool | None = None,
    bitin_cadastrado: bool | None = None,
    windchill_enviado: bool | None = None,
    sem_necessidade_roteiro: bool | None = None,
    criado_por: str | None = None,
    limit: int = 20,
    skip: int = 0,
    current_user: Usuario = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    mongo_db=Depends(get_mongo_db),
):
    collection = mongo_db["bitin_contents"]
    # Construído como uma lista de condições combinadas com $and (em vez de ir setando chaves
    # direto num dict só) porque o escopo de Cadastro/Processos E o filtro de termo (abaixo)
    # precisam cada um do seu próprio "$or" -- setar os dois na mesma chave "$or" faria o
    # segundo sobrescrever o primeiro.
    condicoes: list[dict[str, Any]] = _condicoes_escopo(current_user, db)
    if status:
        condicoes.append({"status": status})
    if encaminhado_roteiro is not None:
        # Só faz sentido combinado com status=enviado (a fila do Cadastro sempre manda os
        # dois juntos) -- sem filtro de status, filtra em qualquer status mesmo assim, sem
        # erro (rascunhos nunca têm esse campo == True, então o resultado natural é vazio).
        # BITins enviados ANTES deste campo existir não têm a chave no Mongo -- "$ne: True"
        # (em vez de "== False") trata "campo ausente" como "ainda não encaminhado", senão
        # eles ficariam invisíveis pras duas abas da fila do Cadastro.
        condicoes.append({
            "encaminhado_roteiro": {"$ne": True} if not encaminhado_roteiro else True
        })
    if processos_concluido is not None:
        # Mesmo raciocínio de encaminhado_roteiro acima -- alimenta a aba "Aguardando
        # cadastro" da CadastroPage (2026-07-17): Processos concluiu (ou o Cadastro decidiu
        # que não precisava de roteiro) e devolveu pro Cadastro.
        condicoes.append({
            "processos_concluido": {"$ne": True} if not processos_concluido else True
        })
    if bitin_cadastrado is not None:
        # Mesmo raciocínio -- alimenta a aba "Pendência de envio" (2026-07-20, penúltimo passo do
        # fluxo, ver bitin_lifecycle.concluir_bitin): só depois disso o PDF é liberado.
        condicoes.append({
            "bitin_cadastrado": {"$ne": True} if not bitin_cadastrado else True
        })
    if windchill_enviado is not None:
        # Mesmo raciocínio -- alimenta a aba "Concluídos" (2026-07-20, último passo de todos,
        # ver bitin_lifecycle.enviar_windchill).
        condicoes.append({
            "windchill_enviado": {"$ne": True} if not windchill_enviado else True
        })
    if sem_necessidade_roteiro is not None:
        # 2026-07-21 -- ProcessosPage.tsx usa `sem_necessidade_roteiro: False` pra excluir da
        # fila do Processos os BITins que nunca passaram por lá de verdade (concluídos direto
        # via concluir_sem_roteiro, ver bitin_lifecycle.py). `processos_concluido=True`
        # sozinho não distingue os dois caminhos.
        condicoes.append({
            "sem_necessidade_roteiro": {"$ne": True} if not sem_necessidade_roteiro else True
        })
    if criado_por:
        # Filtro "Usuário" do Painel geral (2026-07-21, paginação real -- antes buscava até
        # 5000 BITins e filtrava por criado_por no cliente). Substring/case-insensitive (não
        # exact-match) -- mais fácil de digitar um pedaço do e-mail do que ter que saber o
        # endereço completo.
        condicoes.append({"criado_por": {"$regex": re.escape(criado_por), "$options": "i"}})
    if termo:
        # re.escape antes de virar $regex do Mongo -- sem isso, metacaracteres de regex
        # digitados pelo usuário (ex.: "(", "*") viram parte do padrão em vez de texto
        # literal, podendo causar matches inesperados ou custo de busca patológico.
        termo_escapado = re.escape(termo)
        # `campo` restringe a busca a um campo específico (Motivo/Solicitante/Código) -- sem
        # ele (ou com valor desconhecido), busca nos três de uma vez, como sempre foi.
        campo_mongo = TERMO_CAMPO_MONGO.get(campo or "")
        if campo_mongo:
            condicoes.append({campo_mongo: {"$regex": termo_escapado, "$options": "i"}})
        else:
            condicoes.append({
                "$or": [
                    {"content.motivo": {"$regex": termo_escapado, "$options": "i"}},
                    {"content.solicitante": {"$regex": termo_escapado, "$options": "i"}},
                    {"content.bitin": {"$regex": termo_escapado, "$options": "i"}},
                ]
            })
    query: dict[str, Any] = {"$and": condicoes} if condicoes else {}
    cursor = collection.find(query).sort("updated_at", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)
    return [_doc_to_response(doc, current_user) for doc in docs]


@router.delete("/{mongo_id}")
async def delete_bitin(
    mongo_id: str,
    current_user: Usuario = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    mongo_db=Depends(get_mongo_db),
):
    """Rascunho: qualquer dono/admin pode excluir, como sempre. BITin já enviado: só admin
    (permission_level >= NIVEL_ADMIN) pode excluir -- pra não-admin (mesmo o dono original) o
    envio continua definitivo, sem mudança nenhuma aí (decisão do usuário, 2026-07-16).

    Um BITin enviado tem uma linha real em `BitinSQL` (código sequencial gerado em /enviar) --
    deletar só o documento Mongo deixaria essa linha órfã, quebrando a sequência/histórico (o
    código nunca mais apareceria em nenhum lugar, mas o número continuaria "gasto"). Por isso
    o admin apaga os dois na mesma operação, buscando por `mongo_document_id` (mesmo campo
    usado em /enviar pra detectar envio duplicado concorrente).

    Mesma ressalva já documentada pro dual-write de /enviar (ver docs/BACKEND.md): não há uma
    transação real cobrindo Mongo+Postgres aqui. Apaga primeiro o Postgres (BitinSQL) e só
    depois o Mongo -- se a 2ª etapa falhar, o BitinSQL já foi removido mas o documento Mongo
    ainda existe (não fica número "fantasma" reservado apontando pra um documento apagado, que
    seria pior; na pior hipótese sobra um doc Mongo "enviado" sem BitinSQL correspondente,
    facilmente detectável e resolvido numa nova tentativa de exclusão)."""
    collection = mongo_db["bitin_contents"]
    doc = await collection.find_one({"_id": mongo_id})
    if not doc:
        raise HTTPException(status_code=404, detail="BITin não encontrado")
    if doc.get("status") == STATUS_ENVIADO:
        if current_user.permission_level < NIVEL_ADMIN:
            raise HTTPException(status_code=400, detail="BITin já enviado — não pode ser excluído")
        bitin_sql = db.query(BitinSQL).filter(BitinSQL.mongo_document_id == mongo_id).first()
        if bitin_sql is not None:
            db.delete(bitin_sql)
            db.commit()
    else:
        _require_owner_or_admin(doc, current_user)
    await collection.delete_one({"_id": mongo_id})
    return {"message": "BITin excluído", "mongo_id": mongo_id}


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


@router.post("/preview-resumo")
def preview_resumo(
    payload: PreviewResumoRequest,
    _current_user: Usuario = Depends(get_current_active_user),
):
    """Mesmo cálculo de GET /{mongo_id}/resumo (checklist com sugestão automática, setores
    acionados), mas a partir do `content` que está NA TELA agora -- sem salvar nada, sem
    Mongo/mongo_id nenhum envolvido (2026-07-17, pedido explícito: "eu quero que marque ao
    vivo igual com os setores afetados" -- checklist/setores só recarregavam depois de um
    Salvar; esta rota deixa o frontend chamar em background, com um pequeno debounce, sem
    persistir rascunho nenhum, então não interfere com o aviso de "alterações não salvas"
    (BitinDetail.tsx) nem precisa de autosave de verdade. `render_bitin_summary` já usa
    `.get(...)` com default em tudo (ver scripts/bitin_view.py), então um `content` parcial
    (sem `status`/`data_envio`, que só existem no doc persistido) funciona sem erro."""
    return bitin_view.render_bitin_summary(payload.content, VBA_MAPPING_CONFIG, DOCUMENT_CONFIG)


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
    campos_topo: dict[str, Any] = {
        "status": STATUS_ENVIADO,
        "content": content,
        "sql_ref_id": bitin_sql.id,
        "updated_at": now,
    }
    # Roteamento automático (2026-07-20, ver bitin_lifecycle.enviar_bitin) -- o envio já
    # decide sozinho se precisa de roteiro (encaminhar_para_roteiro) ou não
    # (concluir_sem_roteiro), mutando `content` com os campos de cada um. Espelha pro
    # TOP-LEVEL do doc (mesmo padrão dual usado em todo o resto deste arquivo) -- é o que
    # _doc_to_response/list_bitins realmente leem, não o `content` aninhado.
    if "encaminhado_roteiro" in content:
        campos_topo["encaminhado_roteiro"] = content["encaminhado_roteiro"]
        campos_topo["data_encaminhado_roteiro"] = content["data_encaminhado_roteiro"]
    if "processos_concluido" in content:
        campos_topo["processos_concluido"] = content["processos_concluido"]
        campos_topo["data_processos_concluido"] = content["data_processos_concluido"]
    if "sem_necessidade_roteiro" in content:
        campos_topo["sem_necessidade_roteiro"] = content["sem_necessidade_roteiro"]
    try:
        await collection.update_one({"_id": mongo_id}, {"$set": campos_topo})
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


@router.post("/{mongo_id}/encaminhar-roteiro", response_model=BitinResponse)
async def encaminhar_roteiro_endpoint(
    mongo_id: str,
    current_user: Usuario = Depends(check_setor(SETOR_CADASTRO)),
    mongo_db=Depends(get_mongo_db),
):
    """Substitui o e-mail automático do Módulo12.bas: quem é do Cadastro (ou admin) marca
    aqui que terminou de processar o BITin e encaminhou pro setor Roteiro -- alimenta a fila
    em CadastroPage.tsx (aba "Enviados para roteiro"). Ver bitin_lifecycle.encaminhar_para_roteiro."""
    collection = mongo_db["bitin_contents"]
    doc = await collection.find_one({"_id": mongo_id})
    if not doc:
        raise HTTPException(status_code=404, detail="BITin não encontrado")

    content = doc.get("content", {})
    try:
        bitin_lifecycle.encaminhar_para_roteiro(content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await collection.update_one(
        {"_id": mongo_id},
        {"$set": {
            "content": content,
            "encaminhado_roteiro": True,
            "data_encaminhado_roteiro": content["data_encaminhado_roteiro"],
            "updated_at": datetime.now().isoformat(),
        }},
    )
    updated_doc = await collection.find_one({"_id": mongo_id})
    return _doc_to_response(updated_doc, current_user)


@router.post("/{mongo_id}/concluir-sem-roteiro", response_model=BitinResponse)
async def concluir_sem_roteiro_endpoint(
    mongo_id: str,
    current_user: Usuario = Depends(check_setor(SETOR_CADASTRO)),
    mongo_db=Depends(get_mongo_db),
):
    """Alternativa a /encaminhar-roteiro quando o BITin não precisa passar pelo Processos
    (2026-07-17, ver bitin_document.precisa_roteiro) -- chega direto no estado final (PDF
    liberado, aba "Retornados de roteiro" em CadastroPage.tsx), sem abrir a janela de
    reedição do Processos. Reforça a regra no servidor (não confia só no frontend esconder o
    botão errado): 400 se o BITin na verdade precisa de roteiro."""
    collection = mongo_db["bitin_contents"]
    doc = await collection.find_one({"_id": mongo_id})
    if not doc:
        raise HTTPException(status_code=404, detail="BITin não encontrado")

    content = doc.get("content", {})
    if bitin_document.precisa_roteiro(content):
        raise HTTPException(
            status_code=400,
            detail="Este BITin tem alteração de Alt que exige revisão de roteiro -- use Encaminhar para roteiro.",
        )
    try:
        bitin_lifecycle.concluir_sem_roteiro(content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await collection.update_one(
        {"_id": mongo_id},
        {"$set": {
            "content": content,
            "encaminhado_roteiro": True,
            "data_encaminhado_roteiro": content["data_encaminhado_roteiro"],
            "processos_concluido": True,
            "data_processos_concluido": content["data_processos_concluido"],
            "sem_necessidade_roteiro": True,
            "updated_at": datetime.now().isoformat(),
        }},
    )
    updated_doc = await collection.find_one({"_id": mongo_id})
    return _doc_to_response(updated_doc, current_user)


@router.post("/{mongo_id}/atualizar-processos", response_model=BitinResponse)
async def atualizar_processos_endpoint(
    mongo_id: str,
    payload: AtualizarProcessosRequest,
    current_user: Usuario = Depends(check_setor(SETOR_PROCESSOS)),
    mongo_db=Depends(get_mongo_db),
):
    """Única forma de editar um BITin já enviado -- NÃO reaproveita POST /draft de propósito:
    o caminho de atualização de /draft faz um replace_one com status=rascunho HARDCODED (ver
    create_or_update_draft), que reverteria este BITin pra rascunho e apagaria sql_ref_id/
    data_envio/encaminhado_roteiro se o bloqueio de lá fosse simplesmente relaxado. Aqui o
    $set toca SÓ o campo content -- status/número/histórico do envio ficam intactos."""
    collection = mongo_db["bitin_contents"]
    doc = await collection.find_one({"_id": mongo_id})
    if not doc:
        raise HTTPException(status_code=404, detail="BITin não encontrado")
    if not _bitin_liberado_para_processos(doc, current_user):
        raise HTTPException(
            status_code=400,
            detail="Este BITin não está liberado para edição pelo Processos no momento.",
        )

    # Campos administrados pelo SISTEMA dentro de `content` (não só "bitin") são reforçados
    # aqui no servidor, nunca confiados ao payload -- mesmo raciocínio de "solicitante" em
    # create_or_update_draft. Achado real (2026-07-20, testes de ponta a ponta em
    # tests/test_bitin_workflow_e2e.py): `encaminhar_para_roteiro`/`concluir_processamento`
    # espelham seu estado DENTRO de `content` (não só no doc top-level) -- um payload montado
    # do zero (sem vir de `...conteudoExistente` como o frontend sempre faz, ver
    # BitinDetail.tsx::montarConteudo) apagava esse espelho e quebrava
    # concluir_processamento logo em seguida ("ainda não foi encaminhado"), mesmo o BITin
    # estando de fato encaminhado no doc.
    campos_do_sistema = (
        "bitin", "status", "data_envio", "encaminhado_roteiro", "data_encaminhado_roteiro",
        "processos_concluido", "data_processos_concluido", "sem_necessidade_roteiro",
        "data_solicitacao", "solicitante",
    )
    doc_content = doc.get("content", {})
    content = {
        **payload.content,
        **{campo: doc_content[campo] for campo in campos_do_sistema if campo in doc_content},
    }
    await collection.update_one(
        {"_id": mongo_id},
        {"$set": {"content": content, "updated_at": datetime.now().isoformat()}},
    )
    updated_doc = await collection.find_one({"_id": mongo_id})
    return _doc_to_response(updated_doc, current_user)


@router.post("/{mongo_id}/concluir-processos", response_model=BitinResponse)
async def concluir_processos_endpoint(
    mongo_id: str,
    current_user: Usuario = Depends(check_setor(SETOR_PROCESSOS)),
    mongo_db=Depends(get_mongo_db),
):
    """Fecha a janela de reedição aberta por /encaminhar-roteiro -- depois disso o BITin
    volta a ficar travado pra todo mundo, inclusive Processos. Ver
    bitin_lifecycle.concluir_processamento."""
    collection = mongo_db["bitin_contents"]
    doc = await collection.find_one({"_id": mongo_id})
    if not doc:
        raise HTTPException(status_code=404, detail="BITin não encontrado")

    content = doc.get("content", {})
    try:
        bitin_lifecycle.concluir_processamento(content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await collection.update_one(
        {"_id": mongo_id},
        {"$set": {
            "content": content,
            "processos_concluido": True,
            "data_processos_concluido": content["data_processos_concluido"],
            "updated_at": datetime.now().isoformat(),
        }},
    )
    updated_doc = await collection.find_one({"_id": mongo_id})
    return _doc_to_response(updated_doc, current_user)


@router.post("/{mongo_id}/concluir-bitin", response_model=BitinResponse)
async def concluir_bitin_endpoint(
    mongo_id: str,
    current_user: Usuario = Depends(check_setor(SETOR_CADASTRO)),
    mongo_db=Depends(get_mongo_db),
):
    """Penúltimo passo do fluxo (2026-07-20): o Cadastro marca aqui que já fez o
    cadastro/liberação de verdade no SAP -- move o BITin da aba "Aguardando cadastro" pra
    "Cadastrados" em CadastroPage.tsx, e só a partir daqui o PDF fica disponível pra baixar.
    Ver bitin_lifecycle.concluir_bitin."""
    collection = mongo_db["bitin_contents"]
    doc = await collection.find_one({"_id": mongo_id})
    if not doc:
        raise HTTPException(status_code=404, detail="BITin não encontrado")

    content = doc.get("content", {})
    try:
        bitin_lifecycle.concluir_bitin(content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await collection.update_one(
        {"_id": mongo_id},
        {"$set": {
            "content": content,
            "bitin_cadastrado": True,
            "data_cadastrado": content["data_cadastrado"],
            "updated_at": datetime.now().isoformat(),
        }},
    )
    updated_doc = await collection.find_one({"_id": mongo_id})
    return _doc_to_response(updated_doc, current_user)


@router.post("/{mongo_id}/enviar-windchill", response_model=BitinResponse)
async def enviar_windchill_endpoint(
    mongo_id: str,
    current_user: Usuario = Depends(check_setor(SETOR_CADASTRO)),
    mongo_db=Depends(get_mongo_db),
):
    """Última etapa de todas (2026-07-20, pedido explícito: "coloca uma ultima etapa na
    parte de cadastro que é: enviado pro windchill") -- o Cadastro confirma que já baixou o
    PDF (liberado por /concluir-bitin) e mandou pro Windchill de verdade. Move da aba
    "Cadastrados" pra "Concluídos" em CadastroPage.tsx. Ver bitin_lifecycle.enviar_windchill."""
    collection = mongo_db["bitin_contents"]
    doc = await collection.find_one({"_id": mongo_id})
    if not doc:
        raise HTTPException(status_code=404, detail="BITin não encontrado")

    content = doc.get("content", {})
    try:
        bitin_lifecycle.enviar_windchill(content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await collection.update_one(
        {"_id": mongo_id},
        {"$set": {
            "content": content,
            "windchill_enviado": True,
            "data_windchill_enviado": content["data_windchill_enviado"],
            "updated_at": datetime.now().isoformat(),
        }},
    )
    updated_doc = await collection.find_one({"_id": mongo_id})
    return _doc_to_response(updated_doc, current_user)


@router.post("/{mongo_id}/reverter-windchill", response_model=BitinResponse)
async def reverter_windchill_endpoint(
    mongo_id: str,
    current_user: Usuario = Depends(check_permission(NIVEL_ADMIN)),
    mongo_db=Depends(get_mongo_db),
):
    """"Voltar BITin" (2026-07-20, pedido explícito: "faz isso numa aba lá em configurações
    só do admin... lista dos bitins concluidos com opções de voltar bitin etc.") -- desfaz
    /enviar-windchill, único jeito de sair da pasta de Bitins Concluídos (ver
    scripts/bitin_lifecycle.py::reverter_windchill). `check_permission(NIVEL_ADMIN)` de
    propósito -- não `check_setor`, nem Cadastro (Individual ou Gestor) chama isso, só admin
    de verdade (mesmo espírito de "essa pasta vai ficar exposta só para o admin" de antes,
    agora estendido pra reversão também)."""
    collection = mongo_db["bitin_contents"]
    doc = await collection.find_one({"_id": mongo_id})
    if not doc:
        raise HTTPException(status_code=404, detail="BITin não encontrado")

    content = doc.get("content", {})
    try:
        bitin_lifecycle.reverter_windchill(content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await collection.update_one(
        {"_id": mongo_id},
        {"$set": {
            "content": content,
            "windchill_enviado": False,
            "data_windchill_enviado": None,
            "updated_at": datetime.now().isoformat(),
        }},
    )
    updated_doc = await collection.find_one({"_id": mongo_id})
    return _doc_to_response(updated_doc, current_user)
