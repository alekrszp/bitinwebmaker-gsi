#!/usr/bin/env python3
"""Estado em memória compartilhado entre o servidor Flask e a janela Tkinter (mesmo processo,
threads diferentes) -- hoje só guarda quem está logado no sistema web (2026-07-23, pedido
explícito: "com o agente aberto ele vai validar com o sistema... pegar a conta logada"), pra
exibir na janela do agente. NÃO é autenticação de verdade -- o sistema web manda essa
informação assim que detecta o agente conectado (ver `POST /identificar-usuario`,
`frontend/src/lib/sapAgent.ts::identificarUsuarioNoAgente`); qualquer processo rodando em
`localhost:39217` já é implicitamente confiável nesta máquina, mesmo modelo de confiança do
resto do agente."""

import threading
from typing import Any

_lock = threading.Lock()
_usuario_atual: dict[str, Any] | None = None


def definir_usuario(usuario: dict[str, Any]) -> None:
    global _usuario_atual
    with _lock:
        _usuario_atual = usuario


def obter_usuario() -> dict[str, Any] | None:
    with _lock:
        return _usuario_atual


def limpar_usuario() -> None:
    """Chamado quando o servidor é desativado (ver servidor.ServidorAgente.parar) -- não faz
    sentido continuar mostrando "conectado como fulano" na janela se o servidor nem está mais
    respondendo ao BITin."""
    global _usuario_atual
    with _lock:
        _usuario_atual = None
