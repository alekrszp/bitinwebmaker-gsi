"""Limite de tentativas de login por e-mail -- antes disso, /auth/login não tinha nenhum
limite, então uma senha fraca só era protegida pelo custo do hash pbkdf2 (força bruta
continuava viável). Antes (até 2026-07-15), o contador vivia num dict em memória do
processo -- funcionava, mas não sobrevivia a um restart e não funcionaria com múltiplos
workers/réplicas (limitação documentada, nunca escondida). Agora é lastreado na tabela
`tentativas_login` (backend/auth/models.py::TentativaLogin), que já existe pra dar
rastreabilidade de toda tentativa de login (sucesso ou falha) -- reaproveitar essas linhas
pro rate limit evita ter duas fontes de verdade sobre "quantas tentativas recentes".
Mantém os mesmos nomes de função de propósito, só que agora recebem `db: Session` -- callers
(backend/auth/routes.py) mudam pouco."""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from backend.auth.models import TentativaLogin

JANELA_SEGUNDOS = 5 * 60
MAX_TENTATIVAS = 5


def _janela_inicio() -> datetime:
    return datetime.now(timezone.utc) - timedelta(seconds=JANELA_SEGUNDOS)


def excedeu_limite(db: Session, email: str) -> bool:
    # Um login bem-sucedido "limpa o contador" (mesmo comportamento da versão em memória) --
    # como as tentativas agora ficam gravadas pra sempre (histórico/auditoria), isso é
    # implementado contando só as FALHAS depois da tentativa de sucesso mais recente, em vez
    # de apagar linhas.
    ultimo_sucesso = (
        db.query(TentativaLogin)
        .filter(TentativaLogin.email == email, TentativaLogin.sucesso.is_(True))
        .order_by(TentativaLogin.data_tentativa.desc())
        .first()
    )
    desde = _janela_inicio()
    if ultimo_sucesso is not None:
        # SQLite não preserva tzinfo (mesmo com DateTime(timezone=True)) -- o valor lido de
        # volta vem naive, enquanto `desde` é aware (UTC). Mesmo achado/mesmo padrão de
        # normalização de backend/auth/deps.py::get_current_user (comparar naive com aware
        # estoura TypeError no SQLite dev/teste, mesmo funcionando liso num Postgres real).
        data_sucesso = ultimo_sucesso.data_tentativa
        if data_sucesso.tzinfo is None:
            data_sucesso = data_sucesso.replace(tzinfo=timezone.utc)
        if data_sucesso > desde:
            desde = data_sucesso
    count = (
        db.query(TentativaLogin)
        .filter(
            TentativaLogin.email == email,
            TentativaLogin.sucesso.is_(False),
            TentativaLogin.data_tentativa > desde,
        )
        .count()
    )
    return count >= MAX_TENTATIVAS


def registrar_tentativa(
    db: Session, email: str, sucesso: bool, ip_address: str | None = None, user_agent: str | None = None,
) -> None:
    tentativa = TentativaLogin(
        email=email, sucesso=sucesso, ip_address=ip_address, user_agent=user_agent,
    )
    db.add(tentativa)
    db.commit()
