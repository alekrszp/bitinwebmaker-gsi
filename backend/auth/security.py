"""Hashing de senha e JWT. pbkdf2_sha256 (não bcrypt) -- achado da revisão do
GPT_Engineering_authAPI: bcrypt tem um bug conhecido no Windows ("password too long" em
alguns builds); como este backend também roda em Windows, começamos direto com o que
funciona, sem repetir o problema."""

import hashlib
import re
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt
from passlib.context import CryptContext

from backend.config import settings

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# Contas de super-admin fixas em código (2026-07-17, ver backend/auth/deps.py::eh_super_admin
# -- movido pra cá em 2026-07-20 pra poder ser usado também em UserOut.from_usuario sem
# import circular: schemas.py <- deps.py, então deps.py não pode ser importado de volta por
# schemas.py). Checa por e-mail, não por Usuario inteiro, justamente pra não puxar
# backend.auth.models aqui.
CONTAS_SUPER_ADMIN = {"alessandro.pereiradarosafilho@grainproteintech.com"}


def eh_super_admin_email(email: str) -> bool:
    return email in CONTAS_SUPER_ADMIN


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


# Senha temporária gerada pelo admin (2026-07-15, backend/api/users.py::create_user_by_admin)
# -- precisa satisfazer validate_password_strength() acima COM CERTEZA, não por sorte.
# secrets.token_urlsafe() sozinho poderia até passar (seu alfabeto A-Za-z0-9-_ casa com
# "maiúscula"/"minúscula"/"número"/"[^A-Za-z0-9]" via -/_), mas depender de sorte não é
# aceitável pra algo que vira a senha real de alguém no primeiro login. Em vez disso, garante
# 1 caractere de cada uma das 4 classes de propósito, completa até 12 com o alfabeto
# combinado e embaralha -- sempre determinístico quanto a satisfazer a regra, só o CONTEÚDO é
# aleatório (secrets, não random: mesmo padrão de segurança do resto deste módulo).
_TEMP_PWD_LEN = 12
_MAIUSCULAS = string.ascii_uppercase
_MINUSCULAS = string.ascii_lowercase
_NUMEROS = string.digits
_ESPECIAIS = "!@#$%^&*-_"


def generate_temp_password() -> str:
    obrigatorios = [
        secrets.choice(_MAIUSCULAS),
        secrets.choice(_MINUSCULAS),
        secrets.choice(_NUMEROS),
        secrets.choice(_ESPECIAIS),
    ]
    alfabeto_completo = _MAIUSCULAS + _MINUSCULAS + _NUMEROS + _ESPECIAIS
    resto = [secrets.choice(alfabeto_completo) for _ in range(_TEMP_PWD_LEN - len(obrigatorios))]
    caracteres = obrigatorios + resto
    # secrets não tem shuffle próprio -- usa o Random do módulo `random` mas trocando a fonte
    # de aleatoriedade por SystemRandom (CSPRNG do SO), não o gerador determinístico padrão.
    secrets.SystemRandom().shuffle(caracteres)
    senha = "".join(caracteres)
    # Defensivo, não devia nunca falhar dado o construído acima -- mas se falhar, é bug real
    # (ex.: alguém mudou _TEMP_PWD_LEN pra menor que 4 classes) e precisa estourar alto em
    # dev/teste, não ser engolido silenciosamente.
    validate_password_strength(senha)
    return senha


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
