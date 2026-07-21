from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator

from backend.auth.security import eh_super_admin_email, validate_password_strength

# Valores válidos do campo Usuario.setor (2026-07-20, 2ª revisão do modelo de permissões --
# `setor` DEIXOU de ser um rótulo puramente descritivo: agora é o domínio de trabalho da
# pessoa, cruzado com o rank em permission_level (ver backend/auth/deps.py::NIVEL_INDIVIDUAL/
# NIVEL_GESTOR/NIVEL_ADMIN). Pedido explícito: "77 = cadastro, processos, engenheiro" / "88 =
# GESTOR: pode existir gestor de cadastro, processos e engenharia" -- ou seja, TODO usuário
# 77/88 tem um setor entre esses 3; admin (99) também tem um (decide qual aba de trabalho
# própria ele vê, ver Sidebar.tsx/Home.tsx no frontend, "como eu sou de cadastro vou ter a
# tela de cadastro normal"). Substitui os antigos valores "gestor"/"usuario" (eram só rótulo,
# sem função) -- SETOR_ENGENHARIA cobre os dois papéis antigos (Usuário 66 e Gestor 77 velhos
# viram, respectivamente, NIVEL_INDIVIDUAL/NIVEL_GESTOR com setor=SETOR_ENGENHARIA).
SETOR_CADASTRO = "cadastro"
SETOR_PROCESSOS = "processos"
SETOR_ENGENHARIA = "engenharia"
SETORES_VALIDOS = {SETOR_CADASTRO, SETOR_PROCESSOS, SETOR_ENGENHARIA}

# Subgrupo (Proteína Animal/Armazenagem de Grãos) só faz sentido pra quem é de Engenharia
# (2026-07-20, pedido explícito: "apenas engenheiros devem ter subgrupos") -- Cadastro e
# Processos são times centrais (recebem BITins de QUALQUER subgrupo, não fazem sentido presos
# a um subgrupo específico, mesmo raciocínio de antes só que agora pelo setor em vez do nível
# numérico). Admin (99) nunca precisou, mesmo quando setor="engenharia". Usado em
# backend/api/users.py::create_user_by_admin/update_user_subgrupos.
def exige_subgrupo(setor: str, permission_level: int) -> bool:
    from backend.auth.deps import NIVEL_ADMIN  # import local -- evita ciclo (deps.py <- schemas.py)

    return setor == SETOR_ENGENHARIA and permission_level != NIVEL_ADMIN


# Só existem 3 ranks válidos agora (2026-07-20, ver backend/auth/deps.py) -- validado aqui
# (não só documentado) porque `permission_level` chega direto do corpo em AdminUserCreate/
# UserUpdatePermission (admin escolhe o número), diferente de UserCreate (auto-registro, nunca
# vem do cliente). 77/88/99 hardcoded em vez de importar as constantes de deps.py de propósito
# -- mesmo motivo do import local em exige_subgrupo acima (evita ciclo deps.py <- schemas.py).
NIVEIS_VALIDOS = {77, 88, 99}


def _valida_permission_level(v: int) -> int:
    if v not in NIVEIS_VALIDOS:
        raise ValueError(f"Nível de permissão inválido: {v}. Valores aceitos: {sorted(NIVEIS_VALIDOS)}.")
    return v


def _valida_setor(v: str) -> str:
    if v not in SETORES_VALIDOS:
        raise ValueError(
            f"Setor inválido: '{v}'. Valores aceitos: {sorted(SETORES_VALIDOS)}."
        )
    return v


class UserCreate(BaseModel):
    email: EmailStr
    nome: str
    password: str
    network_id: str | None = None
    # Lista de ids de Subgrupo (2026-07-15, era sector_id único -- "um usuário poder ser tanto
    # armazenagem tanto quanto proteina"). Default [] -- registro sem subgrupo nenhum continua
    # válido, mesma permissividade que sector_id=None tinha antes. Renomeado de sector_ids
    # (2026-07-16) junto com a rename geral Setor -> Subgrupo.
    subgrupo_ids: list[int] = []
    numero_eng: str | None = None
    # Rótulo de cargo (cadastro/gestor/usuario) -- NÃO afeta controle de acesso, ver
    # SETORES_VALIDOS acima e comentário em backend/auth/models.py::Usuario.setor.
    setor: str
    # NÃO inclui permission_level de propósito -- ver backend/auth/routes.py.register_user:
    # deixar o cliente se auto-atribuir nível de permissão é a vulnerabilidade de escalonamento
    # de privilégio encontrada na revisão do GPT_Engineering_authAPI (qualquer um podia se
    # registrar como admin). Nível é sempre decidido no servidor.
    # Pelo mesmo motivo, também NÃO inclui email_verificado -- ver Usuario.email_verificado
    # em backend/auth/models.py.

    @field_validator("password")
    @classmethod
    def _valida_forca_senha(cls, v: str) -> str:
        # Regra e motivação: backend/auth/security.py::validate_password_strength. Só se aplica
        # a registro novo -- contas já existentes (incl. as 2 de exemplo com senha "123") não
        # são tocadas.
        return validate_password_strength(v)

    @field_validator("setor")
    @classmethod
    def _valida_setor_campo(cls, v: str) -> str:
        return _valida_setor(v)


class UserOut(BaseModel):
    id: int
    email: str
    nome: str
    ativo: bool
    permission_level: int
    network_id: str | None = None
    # Derivado de Usuario.subgrupos (relationship), não mais uma coluna direta -- ver
    # backend/auth/models.py. Pydantic (from_attributes) resolve isso lendo o relationship e
    # devolvendo os ids; ver conversão explícita em backend/api/users.py::_user_out onde
    # necessário. Renomeado de sector_ids (2026-07-16).
    subgrupo_ids: list[int] = []
    numero_eng: str | None = None
    # Rótulo de cargo -- ver SETORES_VALIDOS acima. Puramente descritivo, não controla acesso.
    setor: str
    created_at: datetime
    # Espelha Usuario.senha_temporaria (backend/auth/models.py) -- exposto aqui pra o
    # frontend (GET /users/me, AuthContext.tsx) saber quando precisa forçar a rota
    # /definir-senha antes de liberar o resto do app (RequireAuth.tsx).
    senha_temporaria: bool
    # Sinal pro frontend esconder "Gestão de usuários" pra quem é admin (99) mas não é a conta
    # fixa (2026-07-20, pedido explícito: "GESTÃO DE USUÁRIOS SÓ PARA ADMIN TOTAL (EU)") --
    # ver backend/auth/security.py::CONTAS_SUPER_ADMIN. Só informativo, a checagem real fica
    # no backend (backend/api/users.py::_exigir_super_admin), este campo não protege nada
    # sozinho.
    eh_super_admin: bool = False

    class Config:
        from_attributes = True

    @classmethod
    def from_usuario(cls, user) -> "UserOut":
        """Usuario.subgrupos (relationship, ver backend/auth/models.py) é uma lista de objetos
        Subgrupo, não de ints -- model_validate(user) direto quebraria tentando coagir Subgrupo
        pra int em subgrupo_ids: list[int]. Todo endpoint que devolve UserOut/AdminUserCreateOut
        a partir de um Usuario de verdade deve passar por aqui em vez de model_validate cru."""
        data = {
            "id": user.id,
            "email": user.email,
            "nome": user.nome,
            "ativo": user.ativo,
            "permission_level": user.permission_level,
            "network_id": user.network_id,
            "subgrupo_ids": [s.id for s in user.subgrupos],
            "numero_eng": user.numero_eng,
            "setor": user.setor,
            "created_at": user.created_at,
            "senha_temporaria": user.senha_temporaria,
            "eh_super_admin": eh_super_admin_email(user.email),
        }
        return cls.model_validate(data)


class UserUpdatePermission(BaseModel):
    permission_level: int
    # Reconfirmação de senha do PRÓPRIO admin (2026-07-17, pedido explícito: "quando eu trocar
    # permissão de usuário já cadastrado sempre pedir a minha senha para confirmar") -- mesmo
    # padrão de AdminUserCreate.senha_admin (create_user_by_admin), verificada contra o hash
    # de quem está chamando antes de qualquer escrita (backend/api/users.py::
    # update_user_permission).
    senha_admin: str

    @field_validator("permission_level")
    @classmethod
    def _permission_level_valido(cls, v: int) -> int:
        return _valida_permission_level(v)


class UserUpdateSubgrupos(BaseModel):
    """Corpo de PATCH /users/{id}/subgrupos (backend/api/users.py) -- endpoint dedicado, à
    parte de /permission e /setor, seguindo o mesmo padrão de "uma rota PATCH por aspecto" já
    usado aqui em vez de sobrecarregar um único corpo com campos opcionais misturados.
    Reatribuição de subgrupo(s) de um usuário JÁ existente (2026-07-16, pedido explícito do
    admin: "reassign de setor de um usuário já cadastrado"). Renomeado de UserUpdateSectors."""

    subgrupo_ids: list[int]


class UserUpdateSetor(BaseModel):
    """Corpo de PATCH /users/{id}/setor (backend/api/users.py) -- troca do rótulo de cargo de
    um usuário já existente. Mesmo padrão de "uma rota PATCH por aspecto" de
    UserUpdatePermission/UserUpdateSubgrupos. NÃO afeta controle de acesso, ver
    SETORES_VALIDOS acima."""

    setor: str

    @field_validator("setor")
    @classmethod
    def _valida_setor_campo(cls, v: str) -> str:
        return _valida_setor(v)


class UserReactivate(BaseModel):
    """Corpo de POST /users/{id}/reativar (backend/api/users.py) -- 2026-07-17, pedido
    explícito: "quando eu reativo [um usuário excluído] aparece de novo com uma nova senha do
    0 e novo email". Diferente de UserUpdateSetor/Subgrupos/Permission (que só trocam UM
    campo), reativar sempre pede um e-mail (pode repetir o antigo ou ser outro -- ex.: pessoa
    saiu e voltou com e-mail corporativo diferente) e sempre gera senha temporária nova no
    servidor (não vem no corpo, mesmo padrão de AdminUserCreate)."""

    email: EmailStr


class AdminUserCreate(BaseModel):
    """Corpo de POST /users (backend/api/users.py::create_user_by_admin) -- cadastro de conta
    nova SÓ PELO ADMIN (2026-07-15, pedido explícito do usuário: "tela de cadastro de usuário
    SÓ PARA ADMIN para não ter que cadastrar no banco"). Ao contrário de UserCreate (registro
    aberto em /auth/register), aqui permission_level VEM do corpo de propósito -- isso não é
    a mesma vulnerabilidade de escalonamento de privilégio documentada lá em cima: esta rota
    já exige check_permission(99) (backend/auth/deps.py), ou seja, só quem já É admin pode
    chamá-la. Não tem campo de senha -- é gerada no servidor (ver
    backend/auth/security.py::generate_temp_password), nunca escolhida pelo admin nem pelo
    cliente."""

    email: EmailStr
    nome: str
    numero_eng: str | None = None
    subgrupo_ids: list[int] = []
    # Rótulo de cargo, obrigatório no cadastro -- ver SETORES_VALIDOS acima.
    setor: str
    permission_level: int
    # Senha do PRÓPRIO admin que está cadastrando, não do usuário novo (2026-07-16, pedido
    # explícito: reconfirmar identidade antes de criar conta -- mesma ideia de "digite sua
    # senha para confirmar" usada em ações sensíveis). Verificada em
    # backend/api/users.py::create_user_by_admin contra current_user.hashed_password via
    # verify_password, ANTES de qualquer escrita no banco.
    senha_admin: str

    @field_validator("setor")
    @classmethod
    def _valida_setor_campo(cls, v: str) -> str:
        return _valida_setor(v)

    @field_validator("permission_level")
    @classmethod
    def _permission_level_valido(cls, v: int) -> int:
        return _valida_permission_level(v)


class AdminUserCreateOut(UserOut):
    """Resposta de POST /users -- tudo de UserOut mais a senha temporária em texto puro,
    devolvida UMA ÚNICA VEZ nesta resposta (não fica recuperável depois: só o hash é salvo,
    igual qualquer outra senha). O admin precisa copiar e repassar pra pessoa fora do sistema
    (chat, verbalmente) antes de sair da tela -- ver frontend/src/pages/Settings.tsx."""

    senha_temporaria_gerada: str


class ChangePasswordRequest(BaseModel):
    """Corpo de POST /auth/change-password (backend/auth/routes.py) -- fluxo de autoatendimento
    que não existia antes (2026-07-15): sem isso, ninguém conseguia trocar a própria senha sem
    edição direta no banco."""

    senha_atual: str
    senha_nova: str

    @field_validator("senha_nova")
    @classmethod
    def _valida_forca_senha_nova(cls, v: str) -> str:
        return validate_password_strength(v)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: int | None = None


class SubgrupoCreate(BaseModel):
    nome: str
    descricao: str | None = None


class SubgrupoOut(BaseModel):
    id: int
    nome: str
    descricao: str | None = None

    class Config:
        from_attributes = True


