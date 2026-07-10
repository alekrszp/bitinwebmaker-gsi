from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    nome: str
    password: str
    network_id: str | None = None
    sector_id: int | None = None
    # NÃO inclui permission_level de propósito -- ver backend/auth/routes.py.register_user:
    # deixar o cliente se auto-atribuir nível de permissão é a vulnerabilidade de escalonamento
    # de privilégio encontrada na revisão do GPT_Engineering_authAPI (qualquer um podia se
    # registrar como admin). Nível é sempre decidido no servidor.


class UserOut(BaseModel):
    id: int
    email: str
    nome: str
    ativo: bool
    permission_level: int
    network_id: str | None = None
    sector_id: int | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdatePermission(BaseModel):
    permission_level: int


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
