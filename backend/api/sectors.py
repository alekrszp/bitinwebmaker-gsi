from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.auth.deps import check_permission
from backend.auth.models import Setor, Usuario
from backend.auth.schemas import SectorCreate, SectorOut
from backend.db.session import get_db

router = APIRouter()


@router.get("", response_model=list[SectorOut])
def list_sectors(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)) -> list[Setor]:
    """Público -- o formulário de registro precisa listar setores antes do login existir."""
    return db.query(Setor).offset(skip).limit(limit).all()


@router.post("", response_model=SectorOut)
def create_sector(
    sector_in: SectorCreate,
    db: Session = Depends(get_db),
    _current_user: Usuario = Depends(check_permission(99)),
) -> Setor:
    existing = db.query(Setor).filter(Setor.nome == sector_in.nome).first()
    if existing:
        raise HTTPException(status_code=400, detail="Setor já existe")
    setor = Setor(**sector_in.model_dump())
    db.add(setor)
    db.commit()
    db.refresh(setor)
    return setor
