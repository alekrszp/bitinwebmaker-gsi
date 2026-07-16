from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator

from backend.auth.security import validate_password_strength

# Níveis que exigem ao menos um Setor (2026-07-16, revisão do modelo de permissões) -- só
# Admin (99) pode ficar sem setor. A checagem em si fica em
# backend/api/users.py::create_user_by_admin (não aqui via pydantic validator) pra devolver
# 400 com a mesma "voz" de erro de _resolve_setores, em vez do 422 genérico que um
# field_validator/model_validator do pydantic geraria.
NIVEIS_QUE_EXIGEM_SETOR = {66, 77, 88}


class UserCreate(BaseModel):
    email: EmailStr
    nome: str
    password: str
    network_id: str | None = None
    # Lista de ids de Setor (2026-07-15, era sector_id único -- "um usuário poder ser tanto
    # armazenagem tanto quanto proteina"). Default [] -- registro sem setor nenhum continua
    # válido, mesma permissividade que sector_id=None tinha antes.
    sector_ids: list[int] = []
    numero_eng: str | None = None
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


class UserOut(BaseModel):
    id: int
    email: str
    nome: str
    ativo: bool
    permission_level: int
    network_id: str | None = None
    # Derivado de Usuario.setores (relationship), não mais uma coluna direta -- ver
    # backend/auth/models.py. Pydantic (from_attributes) resolve isso lendo o relationship e
    # devolvendo os ids; ver conversão explícita em backend/api/users.py::_user_out onde
    # necessário.
    sector_ids: list[int] = []
    numero_eng: str | None = None
    created_at: datetime
    # Espelha Usuario.senha_temporaria (backend/auth/models.py) -- exposto aqui pra o
    # frontend (GET /users/me, AuthContext.tsx) saber quando precisa forçar a rota
    # /definir-senha antes de liberar o resto do app (RequireAuth.tsx).
    senha_temporaria: bool

    class Config:
        from_attributes = True

    @classmethod
    def from_usuario(cls, user) -> "UserOut":
        """Usuario.setores (relationship, ver backend/auth/models.py) é uma lista de objetos
        Setor, não de ints -- model_validate(user) direto quebraria tentando coagir Setor pra
        int em sector_ids: list[int]. Todo endpoint que devolve UserOut/AdminUserCreateOut a
        partir de um Usuario de verdade deve passar por aqui em vez de model_validate cru."""
        data = {
            "id": user.id,
            "email": user.email,
            "nome": user.nome,
            "ativo": user.ativo,
            "permission_level": user.permission_level,
            "network_id": user.network_id,
            "sector_ids": [s.id for s in user.setores],
            "numero_eng": user.numero_eng,
            "created_at": user.created_at,
            "senha_temporaria": user.senha_temporaria,
        }
        return cls.model_validate(data)


class UserUpdatePermission(BaseModel):
    permission_level: int


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
    sector_ids: list[int] = []
    permission_level: int


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


class SectorCreate(BaseModel):
    nome: str
    descricao: str | None = None


class SectorOut(BaseModel):
    id: int
    nome: str
    descricao: str | None = None

    class Config:
        from_attributes = True
