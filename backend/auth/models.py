from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.sql import func
from sqlalchemy.types import DateTime

from backend.db.session import Base


class Setor(Base):
    """Departamento/área da empresa a que um Usuario pertence (Engenharia, RH, TI, ...) --
    conceito diferente do 'setor' do BITin em si (Proteína Animal/Armazenagem de Grãos, que
    define o prefixo P/A do número, ver backend/bitin_number.py)."""

    __tablename__ = "setores"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True, nullable=False)
    descricao = Column(String, nullable=True)


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    nome = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    ativo = Column(Boolean, nullable=False, default=True)
    # 0 = usuário comum, 1 = gestor, 99 = admin (ver backend/auth/deps.py check_permission).
    permission_level = Column(Integer, nullable=False, default=0)
    network_id = Column(String, nullable=True)
    sector_id = Column(Integer, ForeignKey("setores.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
