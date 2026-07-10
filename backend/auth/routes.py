"""Rotas de autenticação. Corrige a vulnerabilidade de escalonamento de privilégio
encontrada na revisão do GPT_Engineering_authAPI: lá, /auth/register aceitava
'permission_level' direto do corpo da requisição -- qualquer um podia se registrar como
admin (99). Aqui, permission_level nunca vem do cliente: é sempre 0, exceto o "usuário
zero" (bootstrap -- primeiro registro do sistema, quando a tabela usuarios está vazia),
que vira admin automaticamente para não deixar o sistema sem nenhum admin no dia 1.
Promoções depois disso só via PATCH /users/{id}/permission (check_permission(99))."""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from backend.auth.models import Usuario
from backend.auth.schemas import Token, UserCreate, UserOut
from backend.auth.security import create_access_token, get_password_hash, verify_password
from backend.config import settings
from backend.db.session import get_db

router = APIRouter()

ADMIN_LEVEL = 99


@router.post("/register", response_model=UserOut)
def register_user(user_in: UserCreate, db: Session = Depends(get_db)) -> Usuario:
    existing = db.query(Usuario).filter(Usuario.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")

    is_first_user = db.query(Usuario).count() == 0
    novo_usuario = Usuario(
        email=user_in.email,
        nome=user_in.nome,
        hashed_password=get_password_hash(user_in.password),
        network_id=user_in.network_id,
        sector_id=user_in.sector_id,
        permission_level=ADMIN_LEVEL if is_first_user else 0,
    )
    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)
    return novo_usuario


@router.post("/login", response_model=Token)
def login(db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()) -> Token:
    usuario = db.query(Usuario).filter(Usuario.email == form_data.username).first()
    if not usuario or not verify_password(form_data.password, usuario.hashed_password):
        raise HTTPException(status_code=400, detail="E-mail ou senha incorretos")
    if not usuario.ativo:
        raise HTTPException(status_code=400, detail="Usuário inativo")

    access_token = create_access_token(
        usuario.id, expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return Token(access_token=access_token)
