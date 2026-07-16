from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import false
from sqlalchemy.orm import Session

from backend.auth.deps import (
    NIVEL_ADMIN,
    NIVEL_GESTOR,
    check_permission,
    get_current_active_user,
)
from backend.auth.models import Usuario, usuario_setores
from backend.auth.routes import _resolve_setores
from backend.auth.schemas import (
    NIVEIS_QUE_EXIGEM_SETOR,
    AdminUserCreate,
    AdminUserCreateOut,
    UserOut,
    UserUpdatePermission,
)
from backend.auth.security import generate_temp_password, get_password_hash
from backend.db.session import get_db

router = APIRouter()


def _setor_ids_do(db: Session, user_id: int) -> list[int]:
    """Ids de Setor do usuário, direto via a tabela de associação (evita carregar o
    relationship inteiro só pra pegar ids)."""
    linhas = db.query(usuario_setores.c.setor_id).filter(usuario_setores.c.usuario_id == user_id).all()
    return [linha[0] for linha in linhas]


def _usuarios_do_mesmo_setor_query(db: Session, gestor: Usuario):
    """Base query de Usuario filtrada pra quem compartilha ao menos um Setor com `gestor`
    (2026-07-15, pedido explícito: "gestor... só ver listagem de usuários do setor que ele é
    gestor"). Um gestor sem nenhum setor não gerencia nada -- devolve uma query que não bate
    com ninguém, não a lista toda (ver comentário em list_users)."""
    setor_ids = _setor_ids_do(db, gestor.id)
    if not setor_ids:
        return db.query(Usuario).filter(false())
    ids_com_setor_em_comum = (
        db.query(usuario_setores.c.usuario_id)
        .filter(usuario_setores.c.setor_id.in_(setor_ids))
        .distinct()
    )
    return db.query(Usuario).filter(Usuario.id.in_(ids_com_setor_em_comum))


@router.get("/me", response_model=UserOut)
def read_current_user(current_user: Usuario = Depends(get_current_active_user)) -> UserOut:
    return UserOut.from_usuario(current_user)


@router.post("", response_model=AdminUserCreateOut)
def create_user_by_admin(
    user_in: AdminUserCreate,
    db: Session = Depends(get_db),
    _current_user: Usuario = Depends(check_permission(NIVEL_ADMIN)),  # só admin cadastra usuário
) -> AdminUserCreateOut:
    """Cadastro de conta nova SÓ POR ADMIN (2026-07-15, pedido explícito: "tela de cadastro de
    usuário SÓ PARA ADMIN para não ter que cadastrar no banco"). Diferente de
    /auth/register (aberto, permission_level sempre forçado a 0 no servidor), aqui
    permission_level vem do corpo -- não é a mesma vulnerabilidade de escalonamento de
    privilégio, porque check_permission(99) já garante que só um admin existente chega até
    aqui. Gera senha temporária (backend/auth/security.py::generate_temp_password),
    marca senha_temporaria=True -- o dono da conta é obrigado a trocar no primeiro login
    (RequireAuth.tsx redireciona pra /definir-senha enquanto a flag for True)."""
    email_normalizado = user_in.email.strip().lower()
    existing = db.query(Usuario).filter(Usuario.email == email_normalizado).first()
    if existing:
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")

    # Usuário/Gestor/Cadastro (66/77/88) precisam de ao menos um Setor -- 2026-07-16, revisão
    # do modelo de permissões (só Admin, 99, enxerga tudo sem escopo nenhum e por isso pode
    # ficar sem setor). Mesmo estilo de erro 400 de _resolve_setores logo abaixo.
    if user_in.permission_level in NIVEIS_QUE_EXIGEM_SETOR and not user_in.sector_ids:
        raise HTTPException(
            status_code=400,
            detail="Este nível de permissão exige ao menos um setor -- selecione um setor antes de cadastrar.",
        )

    setores = _resolve_setores(db, user_in.sector_ids)

    senha_temporaria_gerada = generate_temp_password()
    novo_usuario = Usuario(
        email=email_normalizado,
        nome=user_in.nome,
        hashed_password=get_password_hash(senha_temporaria_gerada),
        numero_eng=user_in.numero_eng,
        setores=setores,
        permission_level=user_in.permission_level,
        email_verificado=False,
        senha_temporaria=True,
    )
    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)

    return AdminUserCreateOut(
        **UserOut.from_usuario(novo_usuario).model_dump(),
        senha_temporaria_gerada=senha_temporaria_gerada,
    )


@router.get("", response_model=list[UserOut])
def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    # Gestor ou Admin -- NÃO Cadastro (2026-07-16, revisão do modelo de permissões: Cadastro
    # cadastra/edita BITins mas não gerencia usuários).
    current_user: Usuario = Depends(check_permission(NIVEL_GESTOR, NIVEL_ADMIN)),
) -> list[UserOut]:
    # Admin continua vendo todo mundo. Gestor (2026-07-15, pedido explícito: "gestor... só ver
    # listagem de usuários do setor que ele é gestor") só vê quem compartilha ao menos um Setor
    # com ele -- um gestor sem setor nenhum não vê ninguém (não cai pra "vê todo mundo" por
    # omissão, ver _usuarios_do_mesmo_setor_query).
    if current_user.permission_level >= NIVEL_ADMIN:
        query = db.query(Usuario)
    else:
        query = _usuarios_do_mesmo_setor_query(db, current_user)
    usuarios = query.offset(skip).limit(limit).all()
    return [UserOut.from_usuario(u) for u in usuarios]


@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(check_permission(NIVEL_GESTOR, NIVEL_ADMIN)),
) -> UserOut:
    if current_user.permission_level >= NIVEL_ADMIN:
        user = db.query(Usuario).filter(Usuario.id == user_id).first()
    else:
        # 404 (não 403) pra quem está fora do(s) setor(es) do gestor -- não vaza que o id
        # existe, mesmo padrão de "not found" já usado neste arquivo pra ids inexistentes.
        user = _usuarios_do_mesmo_setor_query(db, current_user).filter(Usuario.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return UserOut.from_usuario(user)


@router.patch("/{user_id}/permission", response_model=UserOut)
def update_user_permission(
    user_id: int,
    payload: UserUpdatePermission,
    db: Session = Depends(get_db),
    _current_user: Usuario = Depends(check_permission(NIVEL_ADMIN)),  # só admin promove/rebaixa
) -> UserOut:
    user = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    # Admin nunca pode ser rebaixado por essa rota (2026-07-16, proteção contra ficar sem
    # nenhum admin no sistema por engano) -- vale independente de quem está chamando, mesmo
    # outro admin. Não há rota nenhuma pra "despromover" um admin; se for realmente
    # necessário, é edição direta no banco.
    if user.permission_level == NIVEL_ADMIN:
        raise HTTPException(
            status_code=400, detail="Não é possível alterar a permissão de um administrador.",
        )
    user.permission_level = payload.permission_level
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserOut.from_usuario(user)
