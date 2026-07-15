from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator

from backend.auth.security import validate_password_strength


class UserCreate(BaseModel):
    email: EmailStr
    nome: str
    password: str
    network_id: str | None = None
    sector_id: int | None = None
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
    sector_id: int | None = None
    numero_eng: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdatePermission(BaseModel):
    permission_level: int


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
