from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from backend.auth.models import Usuario
from backend.auth.schemas import TokenPayload
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
