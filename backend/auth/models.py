from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import DateTime

from backend.db.session import Base

# Tabela de associação pura (sem colunas extras) pro many-to-many Usuario<->Subgrupo (2026-07-15,
# pedido explícito: "um usuário poder ser tanto armazenagem tanto quanto proteina"). Antes disso
# Usuario.sector_id era uma FK única nullable -- trocada por esta tabela + Usuario.subgrupos
# (ver migração usuario_setores_many_to_many). `Table()` simples é o padrão SQLAlchemy pra
# many-to-many sem payload próprio (não precisa de uma classe/model dedicada como SessaoUsuario,
# que carrega colunas além das duas FKs).
# Renomeado de Setor/usuario_setores -> Subgrupo/usuario_subgrupos (2026-07-16): o nome "Setor"
# colidia com o novo campo Usuario.setor (rótulo de cargo cadastro/gestor/usuario, ver abaixo) --
# são dois conceitos totalmente diferentes e precisavam de nomes diferentes. Este continua sendo
# o conceito de Proteína Animal/Armazenagem de Grãos.
usuario_subgrupos = Table(
    "usuario_subgrupos",
    Base.metadata,
    Column("usuario_id", Integer, ForeignKey("usuarios.id"), primary_key=True),
    Column("subgrupo_id", Integer, ForeignKey("subgrupos.id"), primary_key=True),
)

# NOTA (2026-07-15): o ER diagram de referência (Fluxo.md) traz `password_salt` e
# `algorithm_hash` como colunas separadas em usuario_auth. NÃO copiamos isso -- o hash de
# senha aqui (backend/auth/security.py, pbkdf2_sha256 via passlib) já embute o algoritmo E
# um salt aleatório dentro da própria string de `hashed_password` (é assim que o formato de
# hash do passlib funciona, mesma razão pela qual bcrypt/argon2 são "self-contained").
# Colunas separadas seriam uma segunda fonte de verdade pra algo que já é atômico -- um
# footgun de manutenção, não uma melhoria de segurança. `hashed_password` continua sendo a
# única coluna.


class Subgrupo(Base):
    """Departamento/área da empresa a que um Usuario pertence (Engenharia, RH, TI, ...) --
    conceito diferente do 'setor' do BITin em si (Proteína Animal/Armazenagem de Grãos, que
    define o prefixo P/A do número, ver backend/bitin_number.py). Renomeado de Setor ->
    Subgrupo (2026-07-16) porque o nome "Setor" passou a colidir com o novo campo
    Usuario.setor (rótulo de cargo cadastro/gestor/usuario) -- são conceitos diferentes."""

    __tablename__ = "subgrupos"

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
    # 66 = usuário, 77 = gestor, 88 = cadastro, 99 = admin (2026-07-16, revisão do modelo de
    # permissões -- era 0/1/99; ver backend/auth/deps.py NIVEL_* / check_permission).
    permission_level = Column(Integer, nullable=False, default=66)
    network_id = Column(String, nullable=True)
    # Many-to-many desde 2026-07-15 (era sector_id, FK única nullable) -- um usuário agora pode
    # pertencer a mais de um Subgrupo ao mesmo tempo (ex.: gestor de Proteína Animal E Armazenagem
    # de Grãos). Usado tanto pra escopar GET /users (gestor só vê usuários com subgrupo em comum)
    # quanto GET /bitins (gestor só vê BITins de quem tem subgrupo em comum) -- ver
    # backend/api/users.py e backend/api/bitins.py. Renomeado de Setor/setores -> Subgrupo/
    # subgrupos (2026-07-16), ver comentário na classe Subgrupo acima.
    subgrupos = relationship("Subgrupo", secondary=usuario_subgrupos, backref="usuarios")
    # Rótulo descritivo do CARGO da pessoa -- 'cadastro'/'gestor'/'usuario' (2026-07-16, decisão
    # explícita do usuário). "`setor` é só um rótulo descritivo do cargo da pessoa, NÃO controla
    # nenhuma regra de acesso, isso continua sendo só `permission_level`" -- todo controle de
    # acesso (check_permission, NIVEL_*) usa exclusivamente permission_level; este campo é usado
    # apenas pra popular GET /users/cadastro-emails (lista de gente que recebe BITins pra
    # cadastro) e exibição no frontend. Validado em backend/auth/schemas.py contra
    # SETORES_VALIDOS a nível de aplicação, não via CHECK constraint no banco.
    setor = Column(String, nullable=False)
    # Só relevante pra contas de engenheiro (diagram: "Apenas engenheiros") -- outros papéis
    # deixam nulo, não é obrigatório pro sistema todo.
    numero_eng = Column(String, nullable=True)
    email_verificado = Column(Boolean, nullable=False, default=False)
    # Fluxo "cadastro só por admin" (2026-07-15, pedido explícito do usuário: "tela de cadastro
    # de usuário SÓ PARA ADMIN"). True quando a senha atual foi gerada pelo backend em
    # POST /users (backend/api/users.py::create_user_by_admin) e ainda não foi trocada pela
    # senha de verdade do dono da conta -- POST /auth/change-password zera de volta pra False
    # ao trocar com sucesso (backend/auth/routes.py::change_password). Login continua
    # funcionando normalmente com a senha temporária; é o FRONTEND (RequireAuth.tsx) quem lê
    # essa flag via GET /users/me e força a rota /definir-senha antes de liberar o resto do
    # app -- não há bloqueio de outros endpoints no servidor por essa flag, decisão deliberada
    # pra não precisar tocar em toda rota autenticada.
    senha_temporaria = Column(Boolean, nullable=False, default=False)

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
