"""Testes de `instalador_logica.py` -- nunca abre janela (Tkinter fica só em `instalador.py`,
não testado aqui). `registrar_protocolo_bitinsap` é testado com `winreg` real (HKCU, mesmo
comportamento de produção) porque é stdlib no Windows e não precisa de nenhum privilégio --
limpa a chave de teste no final pra não deixar lixo."""

import sys
import winreg
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

import atalho_windows
import instalador_logica


def test_caminho_instalacao_usa_localappdata(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert instalador_logica.caminho_instalacao() == tmp_path / "AgenteSAP"


def test_copiar_agente_copia_arquivo(tmp_path):
    origem = tmp_path / "origem" / "AgenteSAP.exe"
    origem.parent.mkdir()
    origem.write_bytes(b"conteudo falso do exe")

    destino_dir = tmp_path / "destino"
    resultado = instalador_logica.copiar_agente(origem, destino_dir)

    assert resultado == destino_dir / "AgenteSAP.exe"
    assert resultado.read_bytes() == b"conteudo falso do exe"


def test_copiar_agente_sem_origem_levanta_erro_claro(tmp_path):
    with pytest.raises(FileNotFoundError):
        instalador_logica.copiar_agente(tmp_path / "nao-existe.exe", tmp_path / "destino")


def test_registrar_protocolo_bitinsap_grava_registro_real():
    caminho_falso = r"C:\algum\lugar\AgenteSAP.exe"
    try:
        instalador_logica.registrar_protocolo_bitinsap(Path(caminho_falso))

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\bitinsap") as chave:
            valor, _ = winreg.QueryValueEx(chave, "URL Protocol")
            assert valor == ""

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\bitinsap\shell\open\command") as chave:
            comando, _ = winreg.QueryValueEx(chave, "")
            assert caminho_falso in comando
    finally:
        # Limpa a chave de teste -- se o usuário já tinha um agente de verdade registrado
        # nesta máquina, este teste sobrescreveu com o caminho falso; não tenta restaurar o
        # valor anterior (não temos como saber qual era), só remove a árvore de teste.
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\bitinsap\shell\open\command")
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\bitinsap\shell\open")
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\bitinsap\shell")
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\bitinsap")
        except OSError:
            pass


def test_instalar_nunca_inicia_o_processo(monkeypatch, tmp_path):
    # Achado real motivador desta suíte: o instalador NÃO PODE chamar subprocess.Popen sozinho
    # -- "desativado desde o início" depende só disso. Substitui Popen por uma sentinela que
    # falha o teste se for chamada.
    import subprocess

    def popen_proibido(*args, **kwargs):
        raise AssertionError("instalar() não deveria iniciar nenhum processo sozinho")

    monkeypatch.setattr(subprocess, "Popen", popen_proibido)

    origem = tmp_path / "AgenteSAP.exe"
    origem.write_bytes(b"x")
    monkeypatch.setattr(instalador_logica, "origem_agente_exe", lambda: origem)
    monkeypatch.setattr(instalador_logica, "caminho_instalacao", lambda: tmp_path / "instalado")

    try:
        destino = instalador_logica.instalar()
        assert destino.exists()
    finally:
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\bitinsap\shell\open\command")
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\bitinsap\shell\open")
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\bitinsap\shell")
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\bitinsap")
        except OSError:
            pass
        # `instalar()` também cria atalho no Menu Iniciar + entrada em Programas e Recursos
        # (2026-07-23, ver atalho_windows.py) -- limpa os dois pra não deixar lixo real na
        # máquina de quem roda os testes.
        atalho_windows.remover_atalho_menu_iniciar()
        atalho_windows.remover_de_programas_e_recursos()
