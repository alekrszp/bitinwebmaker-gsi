from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator

from backend.auth.security import validate_password_strength

# Níveis que exigem ao menos um Subgrupo (2026-07-16, revisão do modelo de permissões) -- só
# Admin (99) pode ficar sem subgrupo. A checagem em si fica em
# backend/api/users.py::create_user_by_admin (não aqui via pydantic validator) pra devolver
# 400 com a mesma "voz" de erro de _resolve_subgrupos, em vez do 422 genérico que um
# field_validator/model_validator do pydantic geraria.
# Renomeado de NIVEIS_QUE_EXIGEM_SETOR (2026-07-16) -- mesmo conjunto de valores, só o nome
# mudou junto com a rename geral Setor -> Subgrupo (ver backend/auth/models.py).
NIVEIS_QUE_EXIGEM_SUBGRUPO = {66, 77, 88}

# Valores válidos do NOVO campo Usuario.setor (2026-07-16) -- rótulo descritivo do cargo da
# pessoa (cadastro/gestor/usuario), CONCEITO DIFERENTE do Subgrupo (Proteína Animal/
# Armazenagem de Grãos) renomeado acima. "`setor` é só um rótulo descritivo do cargo da
# pessoa (2026-07-16, decisão explícita do usuário) -- NÃO controla nenhuma regra de acesso,
# isso continua sendo só `permission_level`." Validado a nível de aplicação (Pydantic aqui +
# reforçado em backend/api/users.py), não via CHECK constraint no banco.
SETORES_VALIDOS = {"cadastro", "gestor", "usuario"}


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
        }
        return cls.model_validate(data)


class UserUpdatePermission(BaseModel):
    permission_level: int


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


class CadastroEmailOut(BaseModel):
    """Resposta de GET /users/cadastro-emails (backend/api/users.py) -- lista mínima (nome +
    email) de todo usuário com Usuario.setor == 'cadastro', pra qualquer engenheiro autenticado
    poder escolher pra quem enviar um BITin. De propósito NÃO inclui permission_level,
    subgrupo_ids ou qualquer outro campo de UserOut -- essa rota é aberta a QUALQUER usuário
    autenticado (sem check_permission), então só expõe o mínimo necessário."""

    nome: str
    email: str

    class Config:
        from_attributes = True
