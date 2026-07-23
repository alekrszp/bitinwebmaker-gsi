"""Teste real contra o registro do Windows (HKCU, sem admin) -- limpa a chave de teste no
final pra não deixar lixo nem sobrescrever um registro real que já existisse."""

import sys
import winreg
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import startup_windows


def _limpar():
    startup_windows.remover()


def test_registrar_e_esta_registrado():
    _limpar()
    try:
        assert startup_windows.esta_registrado() is False
        startup_windows.registrar(Path(r"C:\algum\lugar\AgenteSAP.exe"))
        assert startup_windows.esta_registrado() is True
    finally:
        _limpar()


def test_registrar_grava_caminho_correto():
    _limpar()
    try:
        startup_windows.registrar(Path(r"C:\algum\lugar\AgenteSAP.exe"))
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as chave:
            valor, _ = winreg.QueryValueEx(chave, "AgenteSAP")
        assert r"C:\algum\lugar\AgenteSAP.exe" in valor
    finally:
        _limpar()


def test_remover_sem_ter_registrado_nao_da_erro():
    _limpar()
    startup_windows.remover()  # não deve levantar exceção mesmo sem nada registrado
