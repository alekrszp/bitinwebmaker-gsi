"""Limite simples de tentativas de login por e-mail -- antes disso, /auth/login não tinha
nenhum limite, então uma senha fraca só era protegida pelo custo do hash pbkdf2 (força bruta
continuava viável). Em memória de propósito: é a 1ª linha de defesa pra um app de processo
único; se um dia rodar com múltiplos workers/réplicas, precisa virar um store compartilhado
(Redis etc.) -- registrado aqui, não escondido.
"""

import time

JANELA_SEGUNDOS = 5 * 60
MAX_TENTATIVAS = 5

_tentativas_por_email: dict[str, list[float]] = {}


def _tentativas_recentes(email: str, agora: float) -> list[float]:
    tentativas = _tentativas_por_email.get(email, [])
    return [t for t in tentativas if agora - t < JANELA_SEGUNDOS]


def excedeu_limite(email: str) -> bool:
    agora = time.monotonic()
    return len(_tentativas_recentes(email, agora)) >= MAX_TENTATIVAS


def registrar_falha(email: str) -> None:
    agora = time.monotonic()
    recentes = _tentativas_recentes(email, agora)
    recentes.append(agora)
    _tentativas_por_email[email] = recentes


def limpar_tentativas(email: str) -> None:
    _tentativas_por_email.pop(email, None)
