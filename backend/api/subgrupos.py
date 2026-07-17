from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.auth.deps import NIVEL_ADMIN, check_permission
from backend.auth.models import Subgrupo, Usuario
from backend.auth.schemas import SubgrupoCreate, SubgrupoOut
from backend.db.session import get_db

router = APIRouter()


@router.get("", response_model=list[SubgrupoOut])
def list_subgrupos(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)) -> list[Subgrupo]:
    """Público -- o formulário de registro precisa listar subgrupos antes do login existir."""
    return db.query(Subgrupo).offset(skip).limit(limit).all()


@router.post("", response_model=SubgrupoOut)
def create_subgrupo(
    subgrupo_in: SubgrupoCreate,
    db: Session = Depends(get_db),
    _current_user: Usuario = Depends(check_permission(NIVEL_ADMIN)),
) -> Subgrupo:
    existing = db.query(Subgrupo).filter(Subgrupo.nome == subgrupo_in.nome).first()
    if existing:
        raise HTTPException(status_code=400, detail="Subgrupo já existe")
    subgrupo = Subgrupo(**subgrupo_in.model_dump())
    db.add(subgrupo)
    db.commit()
    db.refresh(subgrupo)
    return subgrupo
