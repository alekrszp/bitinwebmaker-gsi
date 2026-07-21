"""Rotas de autenticação. Corrige a vulnerabilidade de escalonamento de privilégio
encontrada na revisão do GPT_Engineering_authAPI: lá, /auth/register aceitava
'permission_level' direto do corpo da requisição -- qualquer um podia se registrar como
admin (99). Aqui, permission_level nunca vem do cliente: é sempre 0, exceto o "usuário
zero" (bootstrap -- primeiro registro do sistema, quando a tabela usuarios está vazia),
que vira admin automaticamente para não deixar o sistema sem nenhum admin no dia 1.
Promoções depois disso só via PATCH /users/{id}/permission (check_permission(99))."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from backend.auth import rate_limit
from backend.auth.deps import (
    NIVEL_ADMIN,
    NIVEL_INDIVIDUAL,
    get_current_active_user,
    get_current_user,
    oauth2_scheme,
)
from backend.auth.models import SessaoUsuario, Subgrupo, Usuario
from backend.auth.schemas import ChangePasswordRequest, Token, UserCreate, UserOut
from backend.auth.security import create_access_token, get_password_hash, hash_token, verify_password
from backend.config import settings
from backend.db.session import get_db

router = APIRouter()


def _resolve_subgrupos(db: Session, subgrupo_ids: list[int]) -> list[Subgrupo]:
    """Valida que todo id em subgrupo_ids corresponde a um Subgrupo real -- 400 se algum não
    existir, mesmo estilo de validação de e-mail duplicado logo acima/abaixo neste arquivo.
    Renomeado de _resolve_setores (2026-07-16) junto com a rename geral Setor -> Subgrupo."""
    if not subgrupo_ids:
        return []
    subgrupos = db.query(Subgrupo).filter(Subgrupo.id.in_(subgrupo_ids)).all()
    encontrados = {s.id for s in subgrupos}
    faltando = set(subgrupo_ids) - encontrados
    if faltando:
        raise HTTPException(status_code=400, detail=f"Subgrupo(s) inexistente(s): {sorted(faltando)}")
    return subgrupos


@router.post("/register", response_model=UserOut)
def register_user(user_in: UserCreate, db: Session = Depends(get_db)) -> UserOut:
    # E-mail sempre normalizado pra minúsculo (achado real: login falhava pra um e-mail
    # cadastrado com maiúsculas porque a comparação no banco é case-sensitive) -- registro e
    # login sempre comparam/gravam a mesma forma normalizada, então digitar o e-mail com
    # capitalização diferente da hora do cadastro nunca mais impede o login.
    email_normalizado = user_in.email.strip().lower()
    existing = db.query(Usuario).filter(Usuario.email == email_normalizado).first()
    if existing:
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")

    subgrupos = _resolve_subgrupos(db, user_in.subgrupo_ids)

    is_first_user = db.query(Usuario).count() == 0
    novo_usuario = Usuario(
        email=email_normalizado,
        nome=user_in.nome,
        hashed_password=get_password_hash(user_in.password),
        network_id=user_in.network_id,
        subgrupos=subgrupos,
        numero_eng=user_in.numero_eng,
        setor=user_in.setor,
        permission_level=NIVEL_ADMIN if is_first_user else NIVEL_INDIVIDUAL,
        # email_verificado NUNCA vem do cliente -- mesma lição de permission_level acima.
        # Fica False no registro; não há fluxo de verificação de e-mail construído ainda,
        # só a coluna.
        email_verificado=False,
    )
    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)
    return UserOut.from_usuario(novo_usuario)


@router.post("/login", response_model=Token)
def login(
    request: Request, db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends(),
) -> Token:
    # Mesma normalização do registro (ver comentário lá) -- sem isso, "Fulano@..." no cadastro
    # e "fulano@..." na hora de logar seriam tratados como e-mails diferentes.
    email = form_data.username.strip().lower()
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    if rate_limit.excedeu_limite(db, email):
        raise HTTPException(
            status_code=429,
            detail="Muitas tentativas de login pra este e-mail. Aguarde alguns minutos e tente de novo.",
        )

    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario or not verify_password(form_data.password, usuario.hashed_password):
        rate_limit.registrar_tentativa(db, email, sucesso=False, ip_address=ip_address, user_agent=user_agent)
        raise HTTPException(status_code=400, detail="E-mail ou senha incorretos")
    if not usuario.ativo:
        # Registra igual às outras duas saídas desta função (2026-07-17, achado de auditoria)
        # -- antes esse branch não chamava registrar_tentativa, deixando um buraco silencioso
        # na auditoria de login (senha certa contra conta desativada não ficava rastreado) e
        # essas tentativas nunca contavam pro rate limit (alguém com a senha certa de uma
        # conta excluída podia tentar infinitamente sem travar).
        rate_limit.registrar_tentativa(db, email, sucesso=False, ip_address=ip_address, user_agent=user_agent)
        raise HTTPException(status_code=400, detail="Usuário inativo")

    rate_limit.registrar_tentativa(db, email, sucesso=True, ip_address=ip_address, user_agent=user_agent)

    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(usuario.id, expires_delta=expires_delta)

    usuario.ultimo_acesso = datetime.now(timezone.utc)
    db.add(
        SessaoUsuario(
            usuario_id=usuario.id,
            token=hash_token(access_token),
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=datetime.now(timezone.utc) + expires_delta,
            revogada=False,
        )
    )
    db.commit()
    return Token(access_token=access_token)


@router.post("/logout")
def logout(
    token: str = Depends(oauth2_scheme),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Não existia nenhum jeito de invalidar um token antes disso -- JWT sozinho é stateless
    e continua válido até expirar naturalmente. Marca a SessaoUsuario correspondente (achada
    pelo hash do token atual) como revogada; backend/auth/deps.py::get_current_user passa a
    checar isso a cada requisição autenticada."""
    hashed = hash_token(token)
    sessao = (
        db.query(SessaoUsuario)
        .filter(SessaoUsuario.token == hashed, SessaoUsuario.usuario_id == current_user.id)
        .first()
    )
    if sessao is not None:
        sessao.revogada = True
        db.commit()
    return {"detail": "Logout efetuado"}


@router.post("/change-password")
def change_password(
    body: ChangePasswordRequest,
    token: str = Depends(oauth2_scheme),
    current_user: Usuario = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict:
    """Autoatendimento de troca de senha (2026-07-15, pedido explícito do usuário) -- antes
    disso não existia nenhum jeito de um usuário trocar a própria senha sem edição direta no
    banco. senha_nova passa pela mesma validação de força de UserCreate.password (ver
    backend/auth/schemas.py::ChangePasswordRequest / backend/auth/security.py::
    validate_password_strength) -- só daqui pra frente, não retroativo.

    Ao trocar, revoga todas as OUTRAS sessões ativas do usuário (mesmo padrão de
    revogação de logout, acima) -- se a senha vazou/foi comprometida, trocar deveria
    derrubar qualquer sessão em outro dispositivo/navegador. A sessão atual (a que fez essa
    própria requisição) fica de fora de propósito: trocar a própria senha não deveria
    deslogar quem acabou de fazer a troca no meio da requisição."""
    if not verify_password(body.senha_atual, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Senha atual incorreta")

    current_user.hashed_password = get_password_hash(body.senha_nova)
    # Reusa esta MESMA rota pro fluxo "primeiro login com senha temporária" (2026-07-15,
    # POST /users em backend/api/users.py cria a conta com senha_temporaria=True) -- não
    # existe endpoint separado pra isso, a senha temporária já É a senha_atual dessa primeira
    # chamada. Zera a flag sempre que a troca dá certo; pra conta que já não era temporária
    # (imensa maioria), fica False -> False, sem efeito nenhum.
    current_user.senha_temporaria = False

    hashed_atual = hash_token(token)
    (
        db.query(SessaoUsuario)
        .filter(
            SessaoUsuario.usuario_id == current_user.id,
            SessaoUsuario.token != hashed_atual,
            SessaoUsuario.revogada.is_(False),
        )
        .update({"revogada": True})
    )
    db.commit()
    return {"detail": "Senha alterada com sucesso"}
