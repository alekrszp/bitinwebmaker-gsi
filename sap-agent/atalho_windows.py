#!/usr/bin/env python3
"""Atalho no Menu Iniciar + entrada em "Programas e Recursos" (2026-07-23, pedido explícito:
"CRIA LITERALMENTE UM APLICATIVO desse agente, que a pessoa instala e consegue pesquisar na
barra de tarefas") -- sem isso, o agente era só um `.exe` solto numa pasta do
`%LOCALAPPDATA%`, sem nenhuma forma de achar pela busca do Windows nem de desinstalar como um
programa de verdade. HKCU (não HKLM) e a pasta "Programs" do usuário (não a compartilhada de
todos os usuários) -- mesmo espírito do resto do instalador (`instalador_logica.py`,
`startup_windows.py`): nunca precisa de administrador."""

import time
import winreg
from pathlib import Path

import win32com.client

NOME_EXIBIDO = "Agente SAP - BITin"
_CHAVE_DESINSTALAR = rf"Software\Microsoft\Windows\CurrentVersion\Uninstall\{NOME_EXIBIDO}"


def _pasta_menu_iniciar() -> Path:
    # `SpecialFolders("Programs")` -- %APPDATA%\Microsoft\Windows\Start Menu\Programs, por
    # usuário (a busca do Windows/barra de tarefas indexa esta pasta automaticamente).
    shell = win32com.client.Dispatch("WScript.Shell")
    return Path(shell.SpecialFolders("Programs"))


def criar_atalho_menu_iniciar(caminho_exe: Path) -> Path:
    """Cria o `.lnk` no Menu Iniciar -- é isso que faz o agente aparecer na busca do Windows
    (pedido explícito: "consegue pesquisar na barra de tarefas")."""
    destino = _pasta_menu_iniciar() / f"{NOME_EXIBIDO}.lnk"
    shell = win32com.client.Dispatch("WScript.Shell")
    atalho = shell.CreateShortCut(str(destino))
    atalho.TargetPath = str(caminho_exe)
    atalho.WorkingDirectory = str(caminho_exe.parent)
    atalho.IconLocation = str(caminho_exe)
    atalho.Description = "Agente SAP local do BITin"
    atalho.Save()
    return destino


def remover_atalho_menu_iniciar() -> None:
    caminho = _pasta_menu_iniciar() / f"{NOME_EXIBIDO}.lnk"
    # Retry curto (2026-07-23, achado real rodando a suíte de testes: o indexador de busca do
    # Windows -- a MESMA busca que este atalho existe pra alimentar -- às vezes prende um
    # handle no `.lnk` por uma fração de segundo logo depois de criado, e apagar em seguida
    # falha com "arquivo já está sendo usado por outro processo"). 3 tentativas/300ms é
    # suficiente pro indexador soltar o arquivo sem travar a desinstalação de verdade.
    for tentativa in range(3):
        try:
            caminho.unlink(missing_ok=True)
            return
        except PermissionError:
            if tentativa == 2:
                raise
            time.sleep(0.1)


def registrar_em_programas_e_recursos(caminho_exe: Path, versao: str = "1.0.0") -> None:
    """"Programas e Recursos" do Painel de Controle -- pra aparecer/desinstalar como qualquer
    outro aplicativo de verdade, não só um `.exe` solto. `UninstallString` chama o próprio
    `.exe` com `--desinstalar` (ver `agente_app.py::_desinstalar`), sem precisar de um segundo
    executável só pra isso."""
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _CHAVE_DESINSTALAR) as chave:
        winreg.SetValueEx(chave, "DisplayName", 0, winreg.REG_SZ, NOME_EXIBIDO)
        winreg.SetValueEx(chave, "DisplayIcon", 0, winreg.REG_SZ, str(caminho_exe))
        winreg.SetValueEx(chave, "DisplayVersion", 0, winreg.REG_SZ, versao)
        winreg.SetValueEx(chave, "Publisher", 0, winreg.REG_SZ, "Grain & Protein Technologies")
        winreg.SetValueEx(chave, "UninstallString", 0, winreg.REG_SZ, f'"{caminho_exe}" --desinstalar')
        winreg.SetValueEx(chave, "NoModify", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(chave, "NoRepair", 0, winreg.REG_DWORD, 1)


def remover_de_programas_e_recursos() -> None:
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, _CHAVE_DESINSTALAR)
    except FileNotFoundError:
        pass


def esta_registrado_em_programas_e_recursos() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _CHAVE_DESINSTALAR):
            return True
    except FileNotFoundError:
        return False
