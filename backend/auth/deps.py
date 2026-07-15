from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from backend.auth.models import SessaoUsuario, Usuario
from backend.auth.schemas import TokenPayload
from backend.auth.security import hash_token
from backend.config import settings
from backend.db.session import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> Usuario:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_data = TokenPayload(**payload)
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido ou expirado",
        )
    user = db.query(Usuario).filter(Usuario.id == token_data.sub).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado")

    # Checagem de revogação (adicionado em 2026-07-15, junto com POST /auth/logout): sem
    # isso, um JWT continua "válido" (assinatura + exp OK) até expirar sozinho, mesmo depois
    # de logout -- stateless de propósito, mas isso também significa que logout não fazia
    # nada de verdade. Só bloqueia quando existe uma SessaoUsuario correspondente E ela foi
    # revogada -- tokens que nunca passaram por /auth/login (criados direto via
    # create_access_token, ex.: helpers de teste que não passam pelo fluxo de login completo)
    # não têm sessão nenhuma pra checar, então continuam funcionando normalmente; é só
    # revogação que precisa de uma sessão real pra existir.
    sessao = db.query(SessaoUsuario).filter(SessaoUsuario.token == hash_token(token)).first()
    if sessao is not None and sessao.revogada:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessão encerrada (logout)",
        )
    if sessao is not None:
        # SQLite não preserva tzinfo (mesmo com DateTime(timezone=True)) -- o valor lido de
        # volta vem naive. Normaliza os dois lados pra naive-UTC antes de comparar, senão
        # comparar naive com aware estoura TypeError (SQLite dev/teste) mesmo que funcione
        # liso num Postgres real (que preserva tzinfo).
        agora = datetime.now(timezone.utc).replace(tzinfo=None)
        expira_em = sessao.expires_at.replace(tzinfo=None) if sessao.expires_at.tzinfo else sessao.expires_at
        if expira_em < agora:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido ou expirado",
            )
    return user


def get_current_active_user(current_user: Usuario = Depends(get_current_user)) -> Usuario:
    if not current_user.ativo:
        raise HTTPException(status_code=400, detail="Usuário inativo")
    return current_user


def check_permission(level: int):
    def _dependency(user: Usuario = Depends(get_current_active_user)) -> Usuario:
        if user.permission_level < level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Privilégio insuficiente para esta operação",
            )
        return user
    return _dependency
