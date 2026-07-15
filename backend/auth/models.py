from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.sql import func
from sqlalchemy.types import DateTime

from backend.db.session import Base

# NOTA (2026-07-15): o ER diagram de referência (Fluxo.md) traz `password_salt` e
# `algorithm_hash` como colunas separadas em usuario_auth. NÃO copiamos isso -- o hash de
# senha aqui (backend/auth/security.py, pbkdf2_sha256 via passlib) já embute o algoritmo E
# um salt aleatório dentro da própria string de `hashed_password` (é assim que o formato de
# hash do passlib funciona, mesma razão pela qual bcrypt/argon2 são "self-contained").
# Colunas separadas seriam uma segunda fonte de verdade pra algo que já é atômico -- um
# footgun de manutenção, não uma melhoria de segurança. `hashed_password` continua sendo a
# única coluna.


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
    # Só relevante pra contas de engenheiro (diagram: "Apenas engenheiros") -- outros papéis
    # deixam nulo, não é obrigatório pro sistema todo.
    numero_eng = Column(String, nullable=True)
    email_verificado = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    # Preenchido em backend/auth/routes.py::login a cada login bem-sucedido.
    ultimo_acesso = Column(DateTime(timezone=True), nullable=True)


class SessaoUsuario(Base):
    """Sessões de login, criadas em backend/auth/routes.py::login e revogadas em
    backend/auth/routes.py::logout -- torna o JWT (que sozinho é stateless e válido até
    expirar) revogável de verdade. `token` guarda o HASH do JWT (sha256, ver
    backend/auth/security.py::hash_token), nunca o token cru: um vazamento do banco não pode
    virar bearer tokens válidos direto."""

    __tablename__ = "sessoes_usuario"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    token = Column(String, unique=True, nullable=False, index=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    revogada = Column(Boolean, nullable=False, default=False)


class TentativaLogin(Base):
    """Registro de toda tentativa de login (sucesso ou falha) -- substitui o dict em memória
    de backend/auth/rate_limit.py (achado: em memória não sobrevive a um restart do processo
    nem funciona com múltiplos workers/réplicas). `email` fica solto (não FK) de propósito --
    tentativa com e-mail inexistente também precisa ser registrada/limitada."""

    __tablename__ = "tentativas_login"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False, index=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    sucesso = Column(Boolean, nullable=False, default=False)
    data_tentativa = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
