#!/usr/bin/env python3
"""Garante só 1 instância do agente rodando por vez nesta máquina (2026-07-23, pedido
explícito: "coloca validação de poder abrir somente 1 agente no pc" + "não consegue abrir mais
de 1 da notificação de agente já aberto"). Sem isso, cada clique em `bitinsap://abrir` (ou
abrir o atalho do Menu Iniciar de novo com o agente já rodando) lançava um processo NOVO --
várias janelas, vários ícones na bandeja, e pior: a 2ª tentativa de abrir a porta HTTP
(39217, ver servidor.py) sempre falhando silenciosamente por trás.

Mutex nomeado do Windows (`CreateMutex`) -- o próprio SO libera o mutex quando o processo
termina (mesmo em crash), então nunca existe um "mutex travado pra sempre" precisando de
limpeza manual."""

import win32api
import win32con
import win32event
import win32gui
import win32process
import winerror
import pywintypes

_MUTEX_NOME = "Global\\BitinAgenteSAP_Singleton"

# Mesmo título usado em `root.title(...)` (agente_app.py) -- `mostrar_instancia_existente`
# encontra a janela pelo texto, então os dois precisam ser exatamente o mesmo valor (fonte
# única aqui, agente_app.py importa em vez de duplicar a string).
NOME_JANELA = "Agente SAP — BITin"

# Guardado em módulo (não dentro de uma função) -- se o handle do mutex fosse coletado pelo GC,
# o Windows liberaria o mutex mesmo com o processo ainda rodando, quebrando a garantia de
# instância única. Precisa viver até o processo terminar (o SO libera sozinho na saída).
_mutex_handle = None


def adquirir() -> bool:
    """Tenta virar a instância "dona" do agente nesta máquina. Devolve `True` se conseguiu (1ª
    instância, pode prosseguir normalmente); `False` se já existe outra rodando (o chamador
    deve encerrar sem criar janela/bandeja/servidor novos, ver `mostrar_instancia_existente`)."""
    global _mutex_handle
    _mutex_handle = win32event.CreateMutex(None, False, _MUTEX_NOME)
    return win32api.GetLastError() != winerror.ERROR_ALREADY_EXISTS


def mostrar_instancia_existente() -> bool:
    """Traz a janela da instância já rodando pra frente -- via API de janela do Windows, não
    HTTP (o servidor Flask pode estar desligado, checkbox "Agente ativo" desmarcado, mesmo com
    o processo/janela ainda vivos e escondidos na bandeja). Devolve `True` se achou a janela."""
    hwnd = win32gui.FindWindow(None, NOME_JANELA)
    if not hwnd:
        return False
    if win32gui.IsIconic(hwnd):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    else:
        win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
    _forcar_foreground(hwnd)
    return True


def _forcar_foreground(hwnd: int) -> None:
    """`SetForegroundWindow` sozinho FALHA (`pywintypes.error`, achado real testando com o
    `.exe` de verdade -- não aparecia rodando via `python agente_app.py` direto, só no `.exe`
    empacotado, onde a 2ª tentativa não tinha foco algum pra doar) sempre que quem chama não é
    o processo com foco atual -- restrição de segurança do próprio Windows contra qualquer
    processo roubar o foco sem interação do usuário. Truque padrão do Win32: "anexar"
    temporariamente a fila de input da thread de quem chama à thread da janela alvo -- isso
    autoriza o `SetForegroundWindow` a valer -- sempre desanexando depois, mesmo se algo falhar
    no meio. Nunca deixa a exceção subir -- pior caso aceitável é a janela aparecer sem roubar o
    foco, não travar a tentativa inteira de abrir o agente (achado real: o `.exe` mostrava
    "Unhandled exception in script" pro engenheiro em vez de simplesmente mostrar a janela)."""
    thread_atual = win32api.GetCurrentThreadId()
    thread_alvo, _ = win32process.GetWindowThreadProcessId(hwnd)
    anexado = False
    try:
        if thread_atual != thread_alvo:
            win32process.AttachThreadInput(thread_atual, thread_alvo, True)
            anexado = True
        win32gui.SetForegroundWindow(hwnd)
    except pywintypes.error:
        pass
    finally:
        if anexado:
            win32process.AttachThreadInput(thread_atual, thread_alvo, False)
