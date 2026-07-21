from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import false
from sqlalchemy.orm import Session

from backend.auth.deps import (
    NIVEL_ADMIN,
    check_permission,
    eh_super_admin,
    get_current_active_user,
)
from backend.auth.models import Usuario, usuario_subgrupos
from backend.auth.routes import _resolve_subgrupos
from backend.auth.schemas import (
    SETOR_ENGENHARIA,
    SETORES_VALIDOS,
    AdminUserCreate,
    AdminUserCreateOut,
    UserOut,
    UserReactivate,
    UserUpdatePermission,
    UserUpdateSetor,
    UserUpdateSubgrupos,
    exige_subgrupo,
)
from backend.auth.security import generate_temp_password, get_password_hash, verify_password
from backend.db.session import get_db

router = APIRouter()


def _exigir_super_admin(current_user: Usuario) -> None:
    """Gestão de usuários inteira reservada à conta fixa em deps.CONTAS_SUPER_ADMIN, não a
    todo permission_level 99 (2026-07-20, pedido explícito: "GESTÃO DE USUÁRIOS SÓ PARA ADMIN
    TOTAL (EU)" -- outro admin 99 que surgir no futuro continua vendo o resto do menu de admin
    (ex.: Painel geral), só esta tela fica de fora). `check_permission(NIVEL_ADMIN)` continua
    sendo a 1ª barreira em cada rota; esta função é a 2ª, mais estreita."""
    if not eh_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Só o administrador principal pode gerenciar usuários.")


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
    _exigir_super_admin(current_user)
    if not verify_password(user_in.senha_admin, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Senha incorreta.")

    email_normalizado = user_in.email.strip().lower()
    existing = db.query(Usuario).filter(Usuario.email == email_normalizado).first()
    # E-mail é UNIQUE na tabela -- um usuário excluído (soft-delete, ativo=False, ver delete_user
    # abaixo) continua ocupando a linha, então cadastrar de novo com o mesmo e-mail precisa
    # REATIVAR essa linha em vez de tentar inserir outra (2026-07-17, pedido explícito: "quando
    # um usuário é excluído... e eu tento cadastrar ele de novo, deve permitir"). Só bloqueia de
    # verdade quando o e-mail já pertence a alguém ATIVO.
    if existing and existing.ativo:
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")

    # Só Engenharia precisa de ao menos um Subgrupo (2026-07-20, 2ª revisão do modelo de
    # permissões -- ver backend/auth/schemas.py::exige_subgrupo) -- Cadastro/Processos são
    # times centrais, não presos a um Subgrupo específico; Admin (99) sempre ficou de fora
    # mesmo quando setor="engenharia". Mesmo estilo de erro 400 de _resolve_subgrupos abaixo.
    if exige_subgrupo(user_in.setor, user_in.permission_level) and not user_in.subgrupo_ids:
        raise HTTPException(
            status_code=400,
            detail="Este nível de permissão exige ao menos um subgrupo -- selecione um subgrupo antes de cadastrar.",
        )

    subgrupos = _resolve_subgrupos(db, user_in.subgrupo_ids)
    senha_temporaria_gerada = generate_temp_password()

    if existing:
        # Reativação (ativo era False) -- reescreve a linha inteira com os dados do formulário
        # de novo, como se fosse um cadastro do zero (mesma senha temporária gerada, mesmo
        # obrigo de trocar no primeiro login), só que sem violar o UNIQUE de email.
        existing.nome = user_in.nome
        existing.hashed_password = get_password_hash(senha_temporaria_gerada)
        existing.numero_eng = user_in.numero_eng
        existing.subgrupos = subgrupos
        existing.setor = user_in.setor
        existing.permission_level = user_in.permission_level
        existing.email_verificado = False
        existing.senha_temporaria = True
        existing.ativo = True
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return AdminUserCreateOut(
            **UserOut.from_usuario(existing).model_dump(),
            senha_temporaria_gerada=senha_temporaria_gerada,
        )

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
    _exigir_super_admin(current_user)
    # Volta a devolver ativos E excluídos juntos (2026-07-17, era só ativo=True) -- a tela de
    # Gestão de usuários agora tem um filtro Ativados/Desativados (GestaoUsuarios.tsx), então
    # precisa dos dois pra filtrar no cliente. `UserOut.ativo` já existia pra distinguir.
    usuarios = db.query(Usuario).offset(skip).limit(limit).all()
    return [UserOut.from_usuario(u) for u in usuarios]


@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    # SÓ ADMIN -- mesma revogação de list_users acima (2026-07-16).
    current_user: Usuario = Depends(check_permission(NIVEL_ADMIN)),
) -> UserOut:
    _exigir_super_admin(current_user)
    user = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return UserOut.from_usuario(user)


@router.patch("/{user_id}/permission", response_model=UserOut)
def update_user_permission(
    user_id: int,
    payload: UserUpdatePermission,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(check_permission(NIVEL_ADMIN)),  # só admin promove/rebaixa
) -> UserOut:
    _exigir_super_admin(current_user)
    # Reconfirmação de senha do admin (2026-07-17, pedido explícito) -- checada ANTES de
    # qualquer outra validação/escrita, mesmo padrão de create_user_by_admin.
    if not verify_password(payload.senha_admin, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Senha incorreta.")

    user = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    # Ninguém mexe na própria permissão por essa rota, nem o super-admin (2026-07-17) --
    # autoproteção continua valendo pra todo mundo igual, só a proteção contra MEXER EM OUTRO
    # admin é que tem bypass (ver deps.eh_super_admin).
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Você não pode alterar o próprio nível.")
    # Admin nunca pode ser rebaixado por essa rota (2026-07-16, proteção contra ficar sem
    # nenhum admin no sistema por engano) -- vale independente de quem está chamando, mesmo
    # outro admin, EXCETO o super-admin oculto (2026-07-17, ver backend/auth/deps.py::
    # eh_super_admin) -- essa conta específica pode rebaixar qualquer admin, de propósito.
    if user.permission_level == NIVEL_ADMIN and not eh_super_admin(current_user):
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
    current_user: Usuario = Depends(check_permission(NIVEL_ADMIN)),  # só admin reatribui subgrupo
) -> UserOut:
    """Reatribuição de subgrupo(s) de um usuário JÁ cadastrado (2026-07-16, pedido explícito do
    admin) -- endpoint dedicado, à parte de /permission e /setor, mesmo espírito de "uma rota
    PATCH por aspecto" já usado nesse arquivo. Mesma regra de exige_subgrupo de
    create_user_by_admin acima: só Engenharia precisa de ao menos um subgrupo; Cadastro/
    Processos e Admin (99) não são afetados por essa regra (podem ficar sem subgrupo)."""
    _exigir_super_admin(current_user)
    user = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    if exige_subgrupo(user.setor, user.permission_level) and not payload.subgrupo_ids:
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
    current_user: Usuario = Depends(check_permission(NIVEL_ADMIN)),  # só admin troca o rótulo
) -> UserOut:
    """Troca do rótulo de cargo (cadastro/gestor/usuario) de um usuário já existente
    (2026-07-16). `setor` é só um rótulo descritivo do cargo da pessoa -- NÃO controla
    nenhuma regra de acesso, isso continua sendo só `permission_level` (ver
    backend/auth/models.py::Usuario.setor). Validação contra SETORES_VALIDOS já acontece no
    pydantic validator de UserUpdateSetor; a checagem aqui é defensiva/redundante."""
    _exigir_super_admin(current_user)
    if payload.setor not in SETORES_VALIDOS:
        raise HTTPException(
            status_code=400,
            detail=f"Setor inválido: '{payload.setor}'. Valores aceitos: {sorted(SETORES_VALIDOS)}.",
        )
    user = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    user.setor = payload.setor
    # Limpa subgrupo(s) ao sair de Engenharia (2026-07-21, pedido explícito) -- Cadastro/
    # Processos não usam subgrupo (nem mais aparece na UI, ver GestaoUsuarios.tsx), então
    # deixar subgrupo_ids "órfão" no banco depois da troca de setor seria só lixo de dado.
    if payload.setor != SETOR_ENGENHARIA:
        user.subgrupos = []
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
    cascata; (3) soft-delete é reversível -- ver reactivate_user abaixo (2026-07-17, reativação
    pela UI foi pedida depois desta rota já existir). Mesmas proteções de
    update_user_permission acima: ninguém pode se auto-excluir nem excluir um admin (99),
    EXCETO o super-admin oculto (2026-07-17, ver backend/auth/deps.py::eh_super_admin) pra
    excluir OUTRO admin -- autoproteção (não pode se auto-excluir) continua valendo igual pra
    ele também."""
    _exigir_super_admin(current_user)
    user = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Você não pode excluir a si mesmo.")
    if user.permission_level == NIVEL_ADMIN and not eh_super_admin(current_user):
        raise HTTPException(status_code=400, detail="Não é possível excluir um administrador.")
    user.ativo = False
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserOut.from_usuario(user)


@router.post("/{user_id}/reativar", response_model=AdminUserCreateOut)
def reactivate_user(
    user_id: int,
    payload: UserReactivate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(check_permission(NIVEL_ADMIN)),  # só admin reativa
) -> AdminUserCreateOut:
    """Reverte o soft-delete de delete_user -- 2026-07-17, pedido explícito: "quando eu
    reativo aparece de novo com uma nova senha do 0 e novo email". Diferente da primeira
    versão desta rota (só virava ativo=True mantendo tudo igual), agora reativar é quase um
    recadastro: sempre pede um e-mail (repetir o antigo é válido -- ver checagem abaixo) e
    sempre gera senha temporária nova (mesmo padrão de create_user_by_admin, incluindo
    devolver a senha em texto puro UMA ÚNICA VEZ e marcar senha_temporaria=True pra forçar
    troca no próximo login). Sem confirmação de senha do admin (diferente de
    create_user_by_admin) -- não é criação de conta nova nem escalonamento de privilégio,
    só destrava uma conta que o próprio admin acabou de excluir."""
    _exigir_super_admin(current_user)
    user = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    email_normalizado = payload.email.strip().lower()
    if email_normalizado != user.email:
        conflito = db.query(Usuario).filter(Usuario.email == email_normalizado).first()
        if conflito:
            raise HTTPException(status_code=400, detail="E-mail já em uso por outro usuário.")
        user.email = email_normalizado

    senha_temporaria_gerada = generate_temp_password()
    user.hashed_password = get_password_hash(senha_temporaria_gerada)
    user.senha_temporaria = True
    user.ativo = True
    db.add(user)
    db.commit()
    db.refresh(user)
    return AdminUserCreateOut(
        **UserOut.from_usuario(user).model_dump(),
        senha_temporaria_gerada=senha_temporaria_gerada,
    )


@router.post("/{user_id}/resetar-senha", response_model=AdminUserCreateOut)
def reset_user_password(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(check_permission(NIVEL_ADMIN)),
) -> AdminUserCreateOut:
    """"Esqueci minha senha" (2026-07-21, pedido explícito) -- sem SMTP configurado no
    backend (nenhum envio de e-mail real acontece hoje, nem pra usuário nem pra admin), um
    fluxo self-service de reset por link não teria como entregar nada de verdade. Decisão do
    usuário: em vez disso, uma opção dentro de Gestão de usuários pro admin resetar a senha de
    qualquer conta na hora -- mesmo padrão de `reactivate_user` (gera senha temporária nova,
    devolve em texto puro UMA ÚNICA VEZ, marca `senha_temporaria=True` pra forçar troca no
    próximo login), mas sem mexer em email/ativo -- só a senha muda."""
    _exigir_super_admin(current_user)
    user = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if not user.ativo:
        raise HTTPException(status_code=400, detail="Usuário está excluído -- reative a conta em vez de resetar a senha.")

    senha_temporaria_gerada = generate_temp_password()
    user.hashed_password = get_password_hash(senha_temporaria_gerada)
    user.senha_temporaria = True
    db.add(user)
    db.commit()
    db.refresh(user)
    return AdminUserCreateOut(
        **UserOut.from_usuario(user).model_dump(),
        senha_temporaria_gerada=senha_temporaria_gerada,
    )
