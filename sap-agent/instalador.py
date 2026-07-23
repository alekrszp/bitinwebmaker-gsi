#!/usr/bin/env python3
"""Tela de instalação do agente SAP (2026-07-23) -- Tkinter (vem junto com o Python padrão do
Windows, sem dependência nova pra empacotar). Fluxo: tela inicial com escolha de pasta de
destino + botão "Instalar" -> copia o `AgenteSAP.exe` pra lá + registra `bitinsap://` (ver
`instalador_logica.py`) -> tela final confirmando, com um botão opcional "Ativar agora" (só aí
o agente roda pela primeira vez -- nunca sozinho, ver docstring de `instalador_logica.py`)."""

import subprocess
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from PIL import ImageTk

import logo_agente
from instalador_logica import caminho_instalacao, instalar

COR_NAVY = "#32464d"
COR_FUNDO = "#f7f8fa"
COR_TEXTO_MUTED = "#5b6b74"


class InstaladorApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Instalar Agente SAP — BITin")
        self.root.geometry("460x360")
        self.root.configure(bg=COR_FUNDO)
        self.root.resizable(False, False)
        self.pasta_destino = tk.StringVar(value=str(caminho_instalacao()))
        self._tela_inicial()

    def _limpar(self) -> None:
        for widget in self.root.winfo_children():
            widget.destroy()

    def _tela_inicial(self) -> None:
        self._limpar()
        # `self._logo_img` guardado na instância -- PhotoImage sem referência viva é coletado
        # pelo GC e o Label fica em branco (achado clássico do Tkinter).
        self._logo_img = ImageTk.PhotoImage(logo_agente.gerar_logo(56))
        tk.Label(self.root, image=self._logo_img, bg=COR_FUNDO).pack(pady=(24, 6))
        tk.Label(
            self.root, text="Agente SAP — BITin", font=("Segoe UI", 14, "bold"),
            fg=COR_NAVY, bg=COR_FUNDO,
        ).pack()
        tk.Label(
            self.root,
            text="Instala o agente nesta máquina e registra o atalho\nusado pela tela do BITin.\n\n"
            "O agente fica DESATIVADO até você ativar manualmente\n(nesta tela ou depois, pela tela do BITin/agente).",
            font=("Segoe UI", 9), fg=COR_TEXTO_MUTED, bg=COR_FUNDO, justify="center",
        ).pack(pady=(8, 16))

        # Escolha de pasta (2026-07-23, pedido explícito: "vai pedir um local do arquivo para
        # deixar o aplicativo do agente, como se fosse qualquer outro executável") -- já vem
        # preenchido com o padrão (`caminho_instalacao()`), mas dá pra trocar.
        tk.Label(self.root, text="Instalar em:", font=("Segoe UI", 9), fg=COR_TEXTO_MUTED, bg=COR_FUNDO).pack(
            anchor="w", padx=32,
        )
        linha_pasta = tk.Frame(self.root, bg=COR_FUNDO)
        linha_pasta.pack(fill="x", padx=32, pady=(2, 18))
        tk.Entry(linha_pasta, textvariable=self.pasta_destino, font=("Segoe UI", 9)).pack(
            side="left", fill="x", expand=True,
        )
        tk.Button(
            linha_pasta, text="Escolher...", font=("Segoe UI", 9), command=self._escolher_pasta,
        ).pack(side="left", padx=(6, 0))

        tk.Button(
            self.root, text="Instalar", font=("Segoe UI", 10, "bold"), fg="white", bg=COR_NAVY,
            activebackground=COR_NAVY, relief="flat", padx=24, pady=8, command=self._instalar,
        ).pack()

    def _escolher_pasta(self) -> None:
        pasta = filedialog.askdirectory(initialdir=self.pasta_destino.get() or str(Path.home()))
        if pasta:
            self.pasta_destino.set(pasta)

    def _instalar(self) -> None:
        try:
            caminho_exe = instalar(Path(self.pasta_destino.get()))
        except Exception as exc:
            messagebox.showerror("Erro na instalação", str(exc))
            return
        self._tela_concluida(caminho_exe)

    def _tela_concluida(self, caminho_exe: Path) -> None:
        self._limpar()
        tk.Label(self.root, text="✅", font=("Segoe UI Emoji", 32), bg=COR_FUNDO).pack(pady=(28, 8))
        tk.Label(
            self.root, text="Instalação concluída!", font=("Segoe UI", 13, "bold"),
            fg=COR_NAVY, bg=COR_FUNDO,
        ).pack()
        tk.Label(
            self.root, text=f"Instalado em:\n{caminho_exe}", font=("Segoe UI", 8),
            fg=COR_TEXTO_MUTED, bg=COR_FUNDO, justify="center",
        ).pack(pady=(6, 4))
        tk.Label(
            self.root,
            text="O agente está desativado por padrão.\nAtive quando quiser usar, aqui ou na janela do agente.",
            font=("Segoe UI", 9), fg=COR_TEXTO_MUTED, bg=COR_FUNDO, justify="center",
        ).pack(pady=(6, 20))
        tk.Button(
            self.root, text="Ativar agora", font=("Segoe UI", 10, "bold"), fg="white", bg=COR_NAVY,
            activebackground=COR_NAVY, relief="flat", padx=20, pady=8,
            command=lambda: self._ativar_agora(caminho_exe),
        ).pack()
        tk.Button(
            self.root, text="Fechar", font=("Segoe UI", 9), fg=COR_TEXTO_MUTED, bg=COR_FUNDO,
            relief="flat", command=self.root.destroy,
        ).pack(pady=(8, 0))

    def _ativar_agora(self, caminho_exe: Path) -> None:
        subprocess.Popen([str(caminho_exe)])
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    InstaladorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
