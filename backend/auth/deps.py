from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from backend.auth.models import SessaoUsuario, Usuario
from backend.auth.schemas import TokenPayload
from backend.auth.security import eh_super_admin_email, hash_token
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


# Níveis nomeados de permission_level (2026-07-20, 2ª revisão do modelo de permissões --
# substitui o esquema anterior de 4 números fixos por setor -- 66 Usuário/77 Gestor/88
# Cadastro/89 Processos -- por um esquema de RANK cruzado com `Usuario.setor` (pedido
# explícito: "99 = ADMIN APENAS EU. 88 = GESTOR: pode existir gestor de cadastro, processos e
# engenharia. 77 = cadastro, processos, engenheiro."). Agora só existem 3 ranks:
#   - NIVEL_INDIVIDUAL (77): membro comum de QUALQUER setor (cadastro/processos/engenharia) --
#     substitui o antigo NIVEL_USUARIO(66) E os antigos NIVEL_CADASTRO(88)/NIVEL_PROCESSOS(89)
#     "sem gestor".
#   - NIVEL_GESTOR (88): gestor de QUALQUER setor -- substitui o antigo NIVEL_GESTOR(77,
#     só engenharia) generalizado pros 3 setores. Único poder extra confirmado (2026-07-20):
#     um painel de acompanhamento a mais (ver backend/api/bitins.py::list_bitins), a fila de
#     trabalho em si é idêntica à de NIVEL_INDIVIDUAL do mesmo setor.
#   - NIVEL_ADMIN (99): inalterado -- vê/faz tudo, sem escopo de setor/subgrupo.
# QUAL setor (cadastro/processos/engenharia) não é mais outro número de permission_level --
# vem de `Usuario.setor` (ver SETOR_CADASTRO/SETOR_PROCESSOS/SETOR_ENGENHARIA em
# backend/auth/schemas.py). Use eh_do_setor()/check_setor() abaixo pra checagens
# (rank, setor) combinadas -- check_permission() continua servindo pra checagens só de rank
# (ex.: NIVEL_ADMIN puro).
NIVEL_INDIVIDUAL = 77
NIVEL_GESTOR = 88
NIVEL_ADMIN = 99

# Super-admin oculto (2026-07-17, pedido explícito: "me coloca como admin TOTAL... isso vai
# ser uma permissão escondida no front que só existe no back") -- essa conta específica ignora
# as proteções "admin nunca pode ser rebaixado/excluído por OUTRO admin" (ver
# backend/api/users.py::update_user_permission / delete_user). Constante em si mora em
# backend/auth/security.py (2026-07-20, movida de propósito pra lá pra evitar import
# circular -- schemas.py precisa dela em UserOut.from_usuario, e schemas.py <- deps.py).
#
# Ganhou um sinal no frontend em 2026-07-20 (UserOut.eh_super_admin, ver schemas.py) --
# pedido explícito: "GESTÃO DE USUÁRIOS SÓ PARA ADMIN TOTAL (EU)", a tela some do menu pra
# quem é admin (99) mas não é esta conta. NÃO é bypass de autoproteção: mesmo esta conta
# continua sem poder se auto-rebaixar/auto-excluir (checagem de "não pode mexer em si mesmo"
# continua valendo igual pra todo mundo, inclusive ela).
def eh_super_admin(user: Usuario) -> bool:
    return eh_super_admin_email(user.email)


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


def eh_do_setor(user: Usuario, *setores: str) -> bool:
    """(rank, setor) combinados (2026-07-20) -- substitui os antigos checks só de nível
    (`permission_level == NIVEL_CADASTRO`) agora que Cadastro/Processos/Engenharia não são
    mais números de permission_level, são valores de `Usuario.setor` (ver
    backend/auth/schemas.py::SETOR_CADASTRO etc). Rank precisa ser INDIVIDUAL ou GESTOR --
    Admin não "é" de setor nenhum pra fins de permissão, mesmo que `user.setor` tenha um
    valor (só decide a aba de trabalho própria dele no frontend, ver Home.tsx/Sidebar.tsx).
    Use check_setor() abaixo como dependency; esta função é o núcleo reaproveitado onde uma
    dependency não serve (ex.: dentro de list_bitins, que precisa ramificar por vários
    critérios, não só permitir/negar)."""
    return user.permission_level in (NIVEL_INDIVIDUAL, NIVEL_GESTOR) and user.setor in setores


def check_setor(*setores_permitidos: str):
    """Dependency pras rotas de fila de um setor (encaminhar-roteiro, atualizar-processos,
    etc, ver backend/api/bitins.py) -- substitui `check_permission(NIVEL_CADASTRO,
    NIVEL_ADMIN)` / `check_permission(NIVEL_PROCESSOS, NIVEL_ADMIN)` de antes de 2026-07-20.
    Admin sempre passa (bypass total, mesmo padrão de sempre); INDIVIDUAL/GESTOR passam só se
    `user.setor` bater com um dos setores permitidos -- Gestor não tem nenhum poder extra
    aqui de propósito (pedido explícito, 2026-07-20: "só ganha o painel de oversight, fila de
    trabalho continua igual"), a única diferença dele é ganhar telas de acompanhamento à
    parte, não mais acesso na fila em si."""
    def _dependency(user: Usuario = Depends(get_current_active_user)) -> Usuario:
        if user.permission_level >= NIVEL_ADMIN:
            return user
        if eh_do_setor(user, *setores_permitidos):
            return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Privilégio insuficiente para esta operação",
        )
    return _dependency
