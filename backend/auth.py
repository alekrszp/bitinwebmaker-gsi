"""Integração com o serviço de autenticação separado (GPT_Engineering_authAPI, ver
docs/BACKEND.md seção "Autenticação"). Decisão registrada: autenticação roda como serviço
independente, não dentro deste backend -- este backend não tem acesso à tabela de usuários,
só sabe validar a ASSINATURA e a EXPIRAÇÃO do JWT emitido por aquele serviço, usando a mesma
SECRET_KEY/ALGORITHM (compartilhada via variável de ambiente, ver `backend/config.py`).

Isso dá o suficiente pra saber "existe um usuário autenticado com esse id" (usado como trava
mínima em todos os endpoints e pra preencher `criado_por`), sem exigir que este backend bata
no serviço de auth a cada requisição nem compartilhe banco com ele. Resolver o id pra um nome
legível (ex.: "criado por Fulano" na tela) fica pro frontend, que já tem acesso ao serviço de
auth pra login -- não duplicado aqui.

Deliberadamente NÃO implementado ainda (registrado como pendência, não esquecido): checagem de
RBAC (permission_level) e reforço de "só o dono ou admin edita/exclui o rascunho" -- ambos
exigiriam buscar o perfil completo do usuário (GET /users/me no serviço de auth), o que este
módulo evita por enquanto para não acoplar uma chamada de rede a cada requisição. Revisitar
quando essas regras forem realmente necessárias.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from backend.config import settings

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.AUTH_API_URL}/auth/login", auto_error=False,
)


def get_current_user_id(token: str | None = Depends(oauth2_scheme)) -> int:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autenticado")
    try:
        payload = jwt.decode(token, settings.AUTH_SECRET_KEY, algorithms=[settings.AUTH_ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido ou expirado",
        )
    sub = payload.get("sub")
    if sub is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token sem 'sub'")
    try:
        return int(sub)
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token com 'sub' inválido")
