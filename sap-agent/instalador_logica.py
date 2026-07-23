#!/usr/bin/env python3
"""Lógica pura do instalador (sem Tkinter) -- separada de `instalador.py` pra poder testar sem
abrir janela nenhuma (2026-07-23, pedido explícito: "eu quero isso criar um executável com tela
de instalação... deixe sempre desativado desde o início... só ativa depois da primeira
instalação").

O instalador NUNCA inicia o agente sozinho -- só copia o `.exe`, registra o protocolo
`bitinsap://` e pronto. O agente só roda quando alguém pede de verdade (botão "Ativar agora" na
tela final do instalador, clique em "Ativar agente?"/"Instalar" na tela do BITin, ou abrindo o
`.exe` manualmente depois) -- por isso não existe nenhum estado "ativo"/"inativo" persistido:
"desativado desde o início" é simplesmente o instalador nunca dar `subprocess.Popen` sozinho.
"""

import shutil
import sys
import winreg
from pathlib import Path

NOME_EXE_AGENTE = "AgenteSAP.exe"
NOME_PASTA_INSTALACAO = "AgenteSAP"  # nome simples, mesmo em todo lugar (pasta/exe/registro)


def caminho_instalacao() -> Path:
    """Pasta de instalação -- `%LOCALAPPDATA%` (por usuário, não precisa de admin, mesmo
    espírito do registro do protocolo em HKCU)."""
    import os

    base = Path(os.environ.get("LOCALAPPDATA", str(Path.home())))
    return base / NOME_PASTA_INSTALACAO


def origem_agente_exe() -> Path:
    """`AgenteSAP.exe` vem EMBUTIDO dentro do `Instalador.exe` (2026-07-23, pedido explícito:
    o engenheiro baixa 1 arquivo só pelo sistema web, não dois) -- empacotado via
    `--add-data "dist/AgenteSAP.exe;."` (ver README), extraído em tempo de execução pro diretório
    temporário do PyInstaller (`sys._MEIPASS`). `sys.frozen` só é `True` dentro do `.exe` de
    verdade; rodando este arquivo direto (`python instalador.py`, modo dev) não há nada
    embutido, então aponta pra onde ficaria em `dist/` (precisa ter sido buildado antes)."""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        return base / NOME_EXE_AGENTE
    return Path(__file__).resolve().parent / "dist" / NOME_EXE_AGENTE


def copiar_agente(origem: Path, destino_dir: Path) -> Path:
    if not origem.exists():
        raise FileNotFoundError(f"Não encontrei {NOME_EXE_AGENTE} em {origem}")
    destino_dir.mkdir(parents=True, exist_ok=True)
    destino = destino_dir / NOME_EXE_AGENTE
    shutil.copy2(origem, destino)
    return destino


def registrar_protocolo_bitinsap(caminho_exe: Path) -> None:
    """Mesmo registro de `registrar_protocolo.ps1`, só que direto em Python (`winreg`, stdlib
    no Windows) -- HKCU (não HKLM), não precisa de administrador."""
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\bitinsap") as chave:
        winreg.SetValueEx(chave, "", 0, winreg.REG_SZ, "URL:Agente BITin SAP")
        winreg.SetValueEx(chave, "URL Protocol", 0, winreg.REG_SZ, "")
    caminho_comando = r"Software\Classes\bitinsap\shell\open\command"
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, caminho_comando) as chave:
        winreg.SetValueEx(chave, "", 0, winreg.REG_SZ, f'"{caminho_exe}" "%1"')


def instalar(destino_dir: Path | None = None) -> Path:
    """Copia o agente + registra o protocolo. NÃO inicia o processo -- ver docstring do
    módulo. `destino_dir` é escolhido pelo usuário na tela do instalador (2026-07-23, pedido
    explícito: "vai pedir um local do arquivo para deixar o aplicativo do agente, como se fosse
    qualquer outro executável") -- default `caminho_instalacao()` se não vier nada. Devolve o
    caminho final do `.exe` instalado (pra quem chamou oferecer "Ativar agora", se quiser)."""
    destino = copiar_agente(origem_agente_exe(), destino_dir or caminho_instalacao())
    registrar_protocolo_bitinsap(destino)
    return destino
