from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.auth.deps import check_permission, get_current_active_user
from backend.auth.models import Usuario
from backend.auth.schemas import UserOut, UserUpdatePermission
from backend.db.session import get_db

router = APIRouter()


@router.get("/me", response_model=UserOut)
def read_current_user(current_user: Usuario = Depends(get_current_active_user)) -> Usuario:
    return current_user


@router.get("", response_model=list[UserOut])
def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _current_user: Usuario = Depends(check_permission(1)),  # gestor ou admin
) -> list[Usuario]:
    return db.query(Usuario).offset(skip).limit(limit).all()


@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    _current_user: Usuario = Depends(check_permission(1)),
) -> Usuario:
    user = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return user


@router.patch("/{user_id}/permission", response_model=UserOut)
def update_user_permission(
    user_id: int,
    payload: UserUpdatePermission,
    db: Session = Depends(get_db),
    _current_user: Usuario = Depends(check_permission(99)),  # só admin promove/rebaixa
) -> Usuario:
    user = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    user.permission_level = payload.permission_level
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
