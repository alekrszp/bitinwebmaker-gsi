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


# Níveis nomeados de permission_level (2026-07-16, substitui o esquema antigo 0/1/99 --
# revisão do modelo de permissões trouxe um 4º nível intermediário, "Cadastro", entre
# Gestor e Admin). Usado em todo o backend em vez de números mágicos -- ver
# backend/api/users.py, backend/api/sectors.py, backend/api/bitins.py.
NIVEL_USUARIO = 66
NIVEL_GESTOR = 77
NIVEL_CADASTRO = 88
NIVEL_ADMIN = 99

# Super-admin oculto (2026-07-17, pedido explícito: "me coloca como admin TOTAL... isso vai
# ser uma permissão escondida no front que só existe no back") -- essa conta específica ignora
# as proteções "admin nunca pode ser rebaixado/excluído por OUTRO admin" (ver
# backend/api/users.py::update_user_permission / delete_user). De propósito não existe campo
# nenhum em UserOut nem qualquer sinal no frontend indicando isso -- é só uma checagem de
# e-mail no servidor, sem UI própria. NÃO é bypass de autoproteção: mesmo esta conta continua
# sem poder se auto-rebaixar/auto-excluir (checagem de "não pode mexer em si mesmo" continua
# valendo igual pra todo mundo, inclusive ela).
CONTAS_SUPER_ADMIN = {"alessandro.pereiradarosafilho@grainproteintech.com"}


def eh_super_admin(user: Usuario) -> bool:
    return user.email in CONTAS_SUPER_ADMIN


def check_permission(*allowed_levels: int):
    """Assinatura trocada de threshold numérico (`level: int`, checava `< level`) pra um
    conjunto explícito de níveis permitidos (2026-07-16) -- com 4 níveis não-hierárquicos
    entre si em alguns pontos (ex.: um nível "no meio" numericamente, como Cadastro/88, pode
    não ter o mesmo acesso que um nível abaixo dele), um único threshold não consegue
    expressar corretamente quem pode chamar cada rota. Assinatura variádica
    (`*allowed_levels: int`) pra suportar isso -- `user.permission_level in allowed_levels`.

    NOTA (2026-07-17, achado de auditoria): o exemplo original deste comentário era
    `check_permission(NIVEL_GESTOR, NIVEL_ADMIN)` em `GET /users`, mas esse acesso foi
    revogado de Gestor em 2026-07-16 (ver docs/BACKEND.md, "Revisão do modelo de
    permissões": "em hipótese alguma 88, 77, 66 podem ver... gestão de usuários é só
    admin"). Hoje TODO call site de `check_permission` no backend passa um único nível
    (`NIVEL_ADMIN`, ver backend/api/users.py e backend/api/subgrupos.py) -- o suporte a
    múltiplos níveis continua existindo na assinatura, só não tem nenhum uso real no
    momento. `GET /bitins` faz um tipo de checagem por nível parecida, mas via comparação
    inline (`permission_level >= NIVEL_X`), não `check_permission` -- padrão diferente,
    não um exemplo de call site multi-nível."""
    def _dependency(user: Usuario = Depends(get_current_active_user)) -> Usuario:
        if user.permission_level not in allowed_levels:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Privilégio insuficiente para esta operação",
            )
        return user
    return _dependency
