from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import false
from sqlalchemy.orm import Session

from backend.auth.deps import (
    NIVEL_ADMIN,
    NIVEL_GESTOR,
    check_permission,
    get_current_active_user,
)
from backend.auth.models import Usuario, usuario_subgrupos
from backend.auth.routes import _resolve_subgrupos
from backend.auth.schemas import (
    NIVEIS_QUE_EXIGEM_SUBGRUPO,
    SETORES_VALIDOS,
    AdminUserCreate,
    AdminUserCreateOut,
    CadastroEmailOut,
    UserOut,
    UserUpdatePermission,
    UserUpdateSetor,
    UserUpdateSubgrupos,
)
from backend.auth.security import generate_temp_password, get_password_hash, verify_password
from backend.db.session import get_db

router = APIRouter()


def _subgrupo_ids_do(db: Session, user_id: int) -> list[int]:
    """Ids de Subgrupo do usuário, direto via a tabela de associação (evita carregar o
    relationship inteiro só pra pegar ids). Renomeado de _setor_ids_do (2026-07-16)."""
    linhas = (
        db.query(usuario_subgrupos.c.subgrupo_id)
        .filter(usuario_subgrupos.c.usuario_id == user_id)
        .all()
    )
    return [linha[0] for linha in linhas]


def _usuarios_do_mesmo_subgrupo_query(db: Session, gestor: Usuario):
    """Base query de Usuario filtrada pra quem compartilha ao menos um Subgrupo com `gestor`
    (2026-07-15, pedido explícito: "gestor... só ver listagem de usuários do setor que ele é
    gestor"). Um gestor sem nenhum subgrupo não gerencia nada -- devolve uma query que não bate
    com ninguém, não a lista toda (ver comentário em list_users). Renomeado de
    _usuarios_do_mesmo_setor_query (2026-07-16) junto com a rename geral Setor -> Subgrupo."""
    subgrupo_ids = _subgrupo_ids_do(db, gestor.id)
    if not subgrupo_ids:
        return db.query(Usuario).filter(false())
    ids_com_subgrupo_em_comum = (
        db.query(usuario_subgrupos.c.usuario_id)
        .filter(usuario_subgrupos.c.subgrupo_id.in_(subgrupo_ids))
        .distinct()
    )
    return db.query(Usuario).filter(Usuario.id.in_(ids_com_subgrupo_em_comum))


@router.get("/me", response_model=UserOut)
def read_current_user(current_user: Usuario = Depends(get_current_active_user)) -> UserOut:
    return UserOut.from_usuario(current_user)


@router.get("/cadastro-emails", response_model=list[CadastroEmailOut])
def list_cadastro_emails(
    db: Session = Depends(get_db),
    _current_user: Usuario = Depends(get_current_active_user),
) -> list[CadastroEmailOut]:
    """Lista nome+email de todo usuário com Usuario.setor == 'cadastro' (2026-07-16) --
    QUALQUER usuário autenticado pode chamar (sem check_permission), porque qualquer
    engenheiro precisa saber pra quem mandar um BITin pra cadastro. `setor` aqui é só o
    rótulo descritivo de cargo (ver backend/auth/models.py::Usuario.setor), não tem relação
    nenhuma com permission_level nem com Subgrupo (Proteína Animal/Armazenagem de Grãos)."""
    usuarios = db.query(Usuario).filter(Usuario.setor == "cadastro").all()
    return [CadastroEmailOut(nome=u.nome, email=u.email) for u in usuarios]


@router.post("", response_model=AdminUserCreateOut)
def create_user_by_admin(
    user_in: AdminUserCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(check_permission(NIVEL_ADMIN)),  # só admin cadastra usuário
) -> AdminUserCreateOut:
    """Cadastro de conta nova SÓ POR ADMIN (2026-07-15, pedido explícito: "tela de cadastro de
    usuário SÓ PARA ADMIN para não ter que cadastrar no banco"). Diferente de
    /auth/register (aberto, permission_level sempre forçado a 0 no servidor), aqui
    permission_level vem do corpo -- não é a mesma vulnerabilidade de escalonamento de
    privilégio, porque check_permission(99) já garante que só um admin existente chega até
    aqui. Gera senha temporária (backend/auth/security.py::generate_temp_password),
    marca senha_temporaria=True -- o dono da conta é obrigado a trocar no primeiro login
    (RequireAuth.tsx redireciona pra /definir-senha enquanto a flag for True).

    Reconfirmação de senha do admin (2026-07-16, pedido explícito) -- senha_admin precisa
    bater com a senha ATUAL de quem está chamando antes de qualquer escrita no banco, mesma
    checagem (verify_password) usada em backend/auth/routes.py::change_password."""
    if not verify_password(user_in.senha_admin, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Senha incorreta.")

    email_normalizado = user_in.email.strip().lower()
    existing = db.query(Usuario).filter(Usuario.email == email_normalizado).first()
    if existing:
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")

    # Usuário/Gestor/Cadastro (66/77/88) precisam de ao menos um Subgrupo -- 2026-07-16, revisão
    # do modelo de permissões (só Admin, 99, enxerga tudo sem escopo nenhum e por isso pode
    # ficar sem subgrupo). Mesmo estilo de erro 400 de _resolve_subgrupos logo abaixo.
    if user_in.permission_level in NIVEIS_QUE_EXIGEM_SUBGRUPO and not user_in.subgrupo_ids:
        raise HTTPException(
            status_code=400,
            detail="Este nível de permissão exige ao menos um subgrupo -- selecione um subgrupo antes de cadastrar.",
        )

    subgrupos = _resolve_subgrupos(db, user_in.subgrupo_ids)

    senha_temporaria_gerada = generate_temp_password()
    novo_usuario = Usuario(
        email=email_normalizado,
        nome=user_in.nome,
        hashed_password=get_password_hash(senha_temporaria_gerada),
        numero_eng=user_in.numero_eng,
        subgrupos=subgrupos,
        setor=user_in.setor,
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
    # SÓ ADMIN (2026-07-16, pedido explícito do usuário: "em hipótese alguma 88, 77, 66 podem
    # ver permissões e usuários que existem. gestão de usuários é só admin"). Antes permitia
    # Gestor também -- revogado.
    current_user: Usuario = Depends(check_permission(NIVEL_ADMIN)),
) -> list[UserOut]:
    # Usuário "excluído" (ativo=False, ver delete_user abaixo) some da listagem -- é soft-delete,
    # não fica visível como se ainda estivesse cadastrado (2026-07-17).
    usuarios = db.query(Usuario).filter(Usuario.ativo.is_(True)).offset(skip).limit(limit).all()
    return [UserOut.from_usuario(u) for u in usuarios]


@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    # SÓ ADMIN -- mesma revogação de list_users acima (2026-07-16).
    current_user: Usuario = Depends(check_permission(NIVEL_ADMIN)),
) -> UserOut:
    user = db.query(Usuario).filter(Usuario.id == user_id).first()
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


@router.patch("/{user_id}/subgrupos", response_model=UserOut)
def update_user_subgrupos(
    user_id: int,
    payload: UserUpdateSubgrupos,
    db: Session = Depends(get_db),
    _current_user: Usuario = Depends(check_permission(NIVEL_ADMIN)),  # só admin reatribui subgrupo
) -> UserOut:
    """Reatribuição de subgrupo(s) de um usuário JÁ cadastrado (2026-07-16, pedido explícito do
    admin) -- endpoint dedicado, à parte de /permission e /setor, mesmo espírito de "uma rota
    PATCH por aspecto" já usado nesse arquivo. Mesma regra de NIVEIS_QUE_EXIGEM_SUBGRUPO de
    create_user_by_admin acima: Usuário/Gestor/Cadastro (66/77/88) não podem ficar sem
    nenhum subgrupo; Admin (99) não é afetado por essa regra (pode ficar sem subgrupo).
    Renomeado de update_user_sectors / PATCH /sectors (2026-07-16)."""
    user = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    if user.permission_level in NIVEIS_QUE_EXIGEM_SUBGRUPO and not payload.subgrupo_ids:
        raise HTTPException(
            status_code=400,
            detail="Este nível de permissão exige ao menos um subgrupo -- selecione um subgrupo antes de salvar.",
        )

    user.subgrupos = _resolve_subgrupos(db, payload.subgrupo_ids)
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserOut.from_usuario(user)


@router.patch("/{user_id}/setor", response_model=UserOut)
def update_user_setor(
    user_id: int,
    payload: UserUpdateSetor,
    db: Session = Depends(get_db),
    _current_user: Usuario = Depends(check_permission(NIVEL_ADMIN)),  # só admin troca o rótulo
) -> UserOut:
    """Troca do rótulo de cargo (cadastro/gestor/usuario) de um usuário já existente
    (2026-07-16). `setor` é só um rótulo descritivo do cargo da pessoa -- NÃO controla
    nenhuma regra de acesso, isso continua sendo só `permission_level` (ver
    backend/auth/models.py::Usuario.setor). Validação contra SETORES_VALIDOS já acontece no
    pydantic validator de UserUpdateSetor; a checagem aqui é defensiva/redundante."""
    if payload.setor not in SETORES_VALIDOS:
        raise HTTPException(
            status_code=400,
            detail=f"Setor inválido: '{payload.setor}'. Valores aceitos: {sorted(SETORES_VALIDOS)}.",
        )
    user = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    user.setor = payload.setor
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserOut.from_usuario(user)


@router.delete("/{user_id}", response_model=UserOut)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(check_permission(NIVEL_ADMIN)),  # só admin exclui
) -> UserOut:
    """"Excluir" usuário = soft-delete (`ativo=False`), não DELETE físico da linha (2026-07-17,
    pedido explícito: botão de excluir em Gestão de usuários, decidido junto com o usuário
    depois de expor o trade-off). Motivos: (1) `ativo=False` já é checado em todo request
    autenticado (`get_current_active_user`, backend/auth/deps.py) e no login
    (backend/auth/routes.py) -- a conta já para de funcionar imediatamente, sem precisar
    revogar sessões à parte; (2) BITins não têm FK pro usuário (dono é só um campo solto no
    doc do Mongo), mas `SessaoUsuario` tem, e um DELETE físico teria que lidar com essa
    cascata; (3) soft-delete é reversível (reativar = só virar `ativo=True` de novo, hoje só
    via banco -- reativação pela UI não foi pedida). Mesmas proteções de
    update_user_permission acima: ninguém pode se auto-excluir nem excluir um admin (99)."""
    user = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Você não pode excluir a si mesmo.")
    if user.permission_level == NIVEL_ADMIN:
        raise HTTPException(status_code=400, detail="Não é possível excluir um administrador.")
    user.ativo = False
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserOut.from_usuario(user)
