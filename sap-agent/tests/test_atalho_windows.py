"""Testes de `atalho_windows.py` -- winreg/COM real (HKCU + Menu Iniciar do usuário, sem
privilégio nenhum, mesmo espírito de `test_instalador_logica.py`) -- limpa tudo no final."""

import sys
import winreg
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import atalho_windows


def test_criar_e_remover_atalho_menu_iniciar(tmp_path):
    exe_falso = tmp_path / "AgenteSAP.exe"
    exe_falso.write_bytes(b"x")

    try:
        caminho_atalho = atalho_windows.criar_atalho_menu_iniciar(exe_falso)
        assert caminho_atalho.exists()
        assert caminho_atalho.suffix == ".lnk"
    finally:
        atalho_windows.remover_atalho_menu_iniciar()

    assert not caminho_atalho.exists()


def test_remover_atalho_sem_existir_nao_falha():
    # Idempotente -- desinstalar duas vezes (ou sem nunca ter instalado) não pode levantar erro.
    atalho_windows.remover_atalho_menu_iniciar()


def test_registrar_e_remover_programas_e_recursos(tmp_path):
    exe_falso = tmp_path / "AgenteSAP.exe"
    exe_falso.write_bytes(b"x")

    try:
        atalho_windows.registrar_em_programas_e_recursos(exe_falso, versao="9.9.9")
        assert atalho_windows.esta_registrado_em_programas_e_recursos()

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, atalho_windows._CHAVE_DESINSTALAR) as chave:
            nome, _ = winreg.QueryValueEx(chave, "DisplayName")
            versao, _ = winreg.QueryValueEx(chave, "DisplayVersion")
            desinstalar, _ = winreg.QueryValueEx(chave, "UninstallString")
            assert nome == atalho_windows.NOME_EXIBIDO
            assert versao == "9.9.9"
            assert "--desinstalar" in desinstalar
            assert str(exe_falso) in desinstalar
    finally:
        atalho_windows.remover_de_programas_e_recursos()

    assert not atalho_windows.esta_registrado_em_programas_e_recursos()


def test_remover_programas_e_recursos_sem_existir_nao_falha():
    atalho_windows.remover_de_programas_e_recursos()
