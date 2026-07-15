"""Hashing de senha e JWT. pbkdf2_sha256 (não bcrypt) -- achado da revisão do
GPT_Engineering_authAPI: bcrypt tem um bug conhecido no Windows ("password too long" em
alguns builds); como este backend também roda em Windows, começamos direto com o que
funciona, sem repetir o problema."""

import hashlib
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt
from passlib.context import CryptContext

from backend.config import settings

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


# Política de força de senha (2026-07-15, pedido explícito do usuário: reforçar autenticação).
# Regra: mínimo 8 caracteres + pelo menos 3 dos 4 tipos de caractere (maiúscula, minúscula,
# número, especial) -- padrão NIST-adjacente, mais forte que exigir só comprimento mas sem cair
# no exagero de exigir os 4 tipos sempre. Roda SÓ contra senha em texto puro recebida em
# /auth/register e /auth/change-password (backend/auth/schemas.py::UserCreate/
# ChangePasswordRequest) -- nunca contra hash já salvo no banco (nem daria: hash não é
# reversível). Por decisão explícita do usuário, as 2 contas de exemplo intencionalmente fracas
# (proteina.exemplo@/armazenagem.exemplo@grainproteintech.com, senha "123") e o admin existente
# NÃO são tocados nem invalidados -- a regra vale só daqui pra frente, pra registro/troca novos.
def validate_password_strength(password: str) -> str:
    erros = []
    if len(password) < 8:
        erros.append("mínimo 8 caracteres")

    classes_presentes = sum(
        bool(re.search(padrao, password))
        for padrao in (r"[A-Z]", r"[a-z]", r"[0-9]", r"[^A-Za-z0-9]")
    )
    if classes_presentes < 3:
        erros.append("pelo menos 3 dos 4 tipos: maiúscula, minúscula, número, caractere especial")

    if erros:
        raise ValueError("Senha precisa ter " + " e ".join(erros))
    return password


def create_access_token(subject: Any, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode = {"exp": expire, "sub": str(subject)}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def hash_token(token: str) -> str:
    """Hash do JWT guardado em SessaoUsuario.token (backend/auth/models.py) -- nunca o token
    cru, pelo mesmo motivo de nunca guardar senha em texto puro: um vazamento do banco não
    pode virar bearer tokens válidos direto. sha256 simples (não pbkdf2) é suficiente aqui:
    o "segredo" já é um JWT de alta entropia assinado com SECRET_KEY, não uma senha de
    usuário sujeita a força bruta/dicionário."""
    return hashlib.sha256(token.encode()).hexdigest()
