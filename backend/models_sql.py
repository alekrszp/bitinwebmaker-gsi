from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.sql import func

from backend.db.session import Base


class BitinSQL(Base):
    """Só existe uma linha por BITin ENVIADO -- rascunhos vivem só no MongoDB
    (ver docs/BACKEND.md, "Modelo de dados")."""

    __tablename__ = "bitins"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String, unique=True, nullable=False, index=True)  # ex: "P6601/26"
    prefixo = Column(String(1), nullable=False)  # "P" ou "A"
    ano = Column(Integer, nullable=False)
    sequencial = Column(Integer, nullable=False)
    mongo_document_id = Column(String, nullable=False, unique=True)
    # Nullable até existir autenticação de verdade -- preparado agora pra não exigir
    # migração de schema quando o login for ligado (ver docs/BACKEND.md).
    criado_por = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
