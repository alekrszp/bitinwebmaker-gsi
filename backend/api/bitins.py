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

import bitin_document
import bitin_lifecycle
import bitin_model
import bitin_view
import sap_paste_parser

VBA_MAPPING_CONFIG = bitin_model.load_config(scripts_path.VBA_MAPPING_CONFIG_PATH)
DOCUMENT_CONFIG = bitin_document.load_config(scripts_path.DOCUMENT_CONFIG_PATH)
MATERIAIS_SCHEMA = bitin_model.build_materiais_schema(VBA_MAPPING_CONFIG, DOCUMENT_CONFIG)

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


class EnviarResponse(BaseModel):
    ok: bool
    errors: list[dict[str, Any]] = []
    bitin: BitinResponse | None = None


def _doc_to_response(doc: dict[str, Any]) -> BitinResponse:
    return BitinResponse(
        mongo_id=doc["_id"],
        codigo=doc.get("content", {}).get("bitin"),
        status=doc.get("status", STATUS_RASCUNHO),
        titulo=doc.get("titulo"),
        content=doc.get("content", {}),
        criado_por=doc.get("criado_por"),
        created_at=doc.get("created_at", ""),
        updated_at=doc.get("updated_at", ""),
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


@router.get("/schema/materiais")
async def get_materiais_schema(_current_user: Usuario = Depends(get_current_active_user)):
    """Colunas do grid de materiais do frontend -- fonte única de verdade (ver
    docs/BACKEND.md, 'Grid de materiais dirigido por schema'). Config já carregada em
    memória no import do módulo (mesmo config imutável usado por validate_bitin/enviar)."""
    return MATERIAIS_SCHEMA


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

    doc = {
        "_id": mongo_id,
        "status": STATUS_RASCUNHO,
        "titulo": draft_in.titulo or "Novo Rascunho",
        "content": draft_in.content,
        "criado_por": criado_por,
        "created_at": created_at,
        "updated_at": now,
    }
    await collection.replace_one({"_id": mongo_id}, doc, upsert=True)
    return _doc_to_response(doc)


@router.get("/{mongo_id}", response_model=BitinResponse)
async def get_bitin(
    mongo_id: str,
    _current_user: Usuario = Depends(get_current_active_user),
    mongo_db=Depends(get_mongo_db),
):
    collection = mongo_db["bitin_contents"]
    doc = await collection.find_one({"_id": mongo_id})
    if not doc:
        raise HTTPException(status_code=404, detail="BITin não encontrado")
    return _doc_to_response(doc)


@router.get("", response_model=list[BitinResponse])
async def list_bitins(
    status: str | None = None,
    termo: str | None = None,
    limit: int = 20,
    skip: int = 0,
    _current_user: Usuario = Depends(get_current_active_user),
    mongo_db=Depends(get_mongo_db),
):
    collection = mongo_db["bitin_contents"]
    query: dict[str, Any] = {}
    if status:
        query["status"] = status
    if termo:
        query["$or"] = [
            {"content.motivo": {"$regex": termo, "$options": "i"}},
            {"content.solicitante": {"$regex": termo, "$options": "i"}},
            {"content.bitin": {"$regex": termo, "$options": "i"}},
        ]
    cursor = collection.find(query).sort("updated_at", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)
    return [_doc_to_response(doc) for doc in docs]


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

    content["bitin"] = bitin_sql.codigo
    now = datetime.now().isoformat()
    await collection.update_one(
        {"_id": mongo_id},
        {"$set": {
            "status": STATUS_ENVIADO,
            "content": content,
            "sql_ref_id": bitin_sql.id,
            "updated_at": now,
        }},
    )
    updated_doc = await collection.find_one({"_id": mongo_id})
    return EnviarResponse(ok=True, errors=[], bitin=_doc_to_response(updated_doc))
