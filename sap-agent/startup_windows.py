#!/usr/bin/env python3
"""Registro de "abrir com o Windows" (2026-07-23, pedido explícito) -- chave `Run` padrão do
Windows, HKCU (não HKLM, não precisa de administrador, mesmo espírito do registro do protocolo
`bitinsap://` em `instalador_logica.py`)."""

import winreg
from pathlib import Path

_CHAVE_RUN = r"Software\Microsoft\Windows\CurrentVersion\Run"
_NOME_VALOR = "AgenteSAP"


def registrar(caminho_exe: Path) -> None:
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _CHAVE_RUN) as chave:
        winreg.SetValueEx(chave, _NOME_VALOR, 0, winreg.REG_SZ, f'"{caminho_exe}"')


def remover() -> None:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _CHAVE_RUN, 0, winreg.KEY_SET_VALUE) as chave:
            winreg.DeleteValue(chave, _NOME_VALOR)
    except FileNotFoundError:
        pass


def esta_registrado() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _CHAVE_RUN) as chave:
            winreg.QueryValueEx(chave, _NOME_VALOR)
            return True
    except FileNotFoundError:
        return False
