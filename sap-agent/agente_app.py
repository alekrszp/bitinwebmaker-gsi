#!/usr/bin/env python3
"""Ponto de entrada de verdade do agente (2026-07-23) -- mostra uma JANELA de verdade (Tkinter),
tamanho fixo (não redimensiona), com 3 abas -- "Leia-me", "BITin" (liga/desliga o agente) e
"Configurações" (abrir com o Windows, local do executável instalado) -- e um ícone na bandeja
do Windows. Minimizar OU fechar (botão X) só esconde a janela, nunca encerra o processo; só
"Sair" (menu da bandeja) encerra de verdade.

Importante (decisão explícita do usuário): esta janela é só **status/configuração** do agente
em si (conectado, usuário identificado, ativo/inativo, abrir com o Windows) -- os COMANDOS de
verdade (buscar material no SAP, preencher campos) ficam no sistema web (aba "Automação", ver
docs/FRONTEND.md), que já tem autenticação e as validações de negócio que esta janela não tem
("quero algo seguro e com validações").

É este arquivo, não `servidor.py`, que deve ser empacotado pelo PyInstaller
(`pyinstaller --onefile --windowed --name AgenteSAP --icon icone.ico agente_app.py`, ver
README).
"""

import os
import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk

import pystray
from PIL import Image, ImageTk

import config_agente
import estado_agente
import logo_agente
import servidor
import startup_windows

NOME_EXIBIDO = "Agente SAP — BITin"
COR_NAVY = "#32464d"
COR_FUNDO = "#f7f8fa"
COR_TEXTO_MUTED = "#5b6b74"

LEIA_ME_TEXTO = """O que é o Agente SAP - BITin?

Este agente roda nesta máquina e conversa com o SAP GUI que você já tem aberto e logado, via
SAP GUI Scripting -- ele NÃO abre uma conexão direta com o servidor SAP, só automatiza a
mesma tela que você usaria manualmente.

Por que ele existe?
Antes, conferir se um código de material existia no SAP, ou buscar a descrição/peso/NCM de um
material, era 100% manual: abrir o SAP, digitar, copiar, colar de volta no BITin. O agente faz
essas consultas repetitivas por você.

Quem manda no que é buscado?
Os comandos (o que buscar, quando buscar) ficam na tela do BITin, no navegador -- esta janela
nunca decide nada sozinha, só executa o que o sistema web pede.

O que ele NUNCA faz sozinho:
- Nunca abre uma sessão SAP nova (usa a que você já tem aberta).
- Nunca decide o que muda no BITin -- só traz o que já está no SAP; o que muda continua 100%
  sua decisão, declarada no sistema web.
- Nunca fica escondido sem avisar: esta janela e o ícone da bandeja sempre mostram se ele está
  ativo ou não.
"""


def _caminho_executavel_atual() -> str:
    """Onde o `.exe` deste agente está instalado -- exibido na aba Configurações (2026-07-23,
    pedido explícito: "mostra o local do arquivo do agente baixado"). Em dev (rodando via
    `python agente_app.py`, sem `.exe` de verdade) mostra uma mensagem em vez de um caminho que
    não existe."""
    if getattr(sys, "frozen", False):
        return str(Path(sys.executable))
    return "(modo desenvolvimento -- sem .exe, rodando via python)"


def _gerar_icone() -> Image.Image:
    """Ícone da bandeja -- logo do agente (ver `logo_agente.py`), mesmo desenho usado na tela
    de instalação e no frontend (`AgenteLogoIcon.tsx`)."""
    return logo_agente.gerar_logo(64)


class JanelaAgente:
    """Janela principal -- minimizar (barra de tarefas) ou fechar (botão X) só escondem
    (`withdraw`), nunca destroem a janela nem encerram o processo."""

    def __init__(self, root: tk.Tk, servidor_agente: servidor.ServidorAgente):
        self.root = root
        self.servidor_agente = servidor_agente
        self.config = config_agente.carregar()

        root.title(NOME_EXIBIDO)
        root.geometry("420x400")
        root.configure(bg=COR_FUNDO)
        # Tamanho fixo (2026-07-23, pedido explícito: "coloca uma tela que não pode aumentar
        # de tamanho, só deixa esse tamanho inicial") -- min e max iguais ao inicial impedem
        # redimensionar tanto pelo mouse quanto por maximizar.
        root.resizable(False, False)

        root.protocol("WM_DELETE_WINDOW", self.ocultar)
        root.bind("<Unmap>", self._ao_mudar_estado)

        # Cabeçalho com a logo (2026-07-23, pedido explícito: "fazer a UI dele melhor usando a
        # logo") -- mesma imagem do ícone da bandeja/instalador, fica visível o tempo todo,
        # acima das 3 abas. `self._logo_img`/`self._logo_titulo_img` guardados na instância --
        # PhotoImage sem referência viva é coletado pelo GC e o Label fica em branco.
        self._logo_img = ImageTk.PhotoImage(logo_agente.gerar_logo(40))
        root.iconphoto(True, ImageTk.PhotoImage(logo_agente.gerar_logo(64)))

        cabecalho = tk.Frame(root, bg=COR_FUNDO)
        cabecalho.pack(fill="x", padx=14, pady=(14, 0))
        tk.Label(cabecalho, image=self._logo_img, bg=COR_FUNDO).pack(side="left")
        bloco_titulo = tk.Frame(cabecalho, bg=COR_FUNDO)
        bloco_titulo.pack(side="left", padx=(10, 0))
        tk.Label(
            bloco_titulo, text="Agente SAP", font=("Segoe UI", 12, "bold"),
            fg=COR_NAVY, bg=COR_FUNDO, anchor="w",
        ).pack(anchor="w")
        tk.Label(
            bloco_titulo, text="BITin", font=("Segoe UI", 9), fg=COR_TEXTO_MUTED,
            bg=COR_FUNDO, anchor="w",
        ).pack(anchor="w")

        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        aba_leia_me = tk.Frame(notebook, bg=COR_FUNDO)
        aba_bitin = tk.Frame(notebook, bg=COR_FUNDO)
        aba_config = tk.Frame(notebook, bg=COR_FUNDO)
        notebook.add(aba_leia_me, text="Leia-me")
        notebook.add(aba_bitin, text="BITin")
        notebook.add(aba_config, text="Configurações")

        self._montar_aba_leia_me(aba_leia_me)
        self._montar_aba_bitin(aba_bitin)
        self._montar_aba_config(aba_config)

        # Estado inicial reflete a config persistida (2026-07-23: "sempre desativado desde o
        # início" -- só liga sozinho se a última vez que rodou já estava ativo).
        if self.config["ativo"]:
            self.servidor_agente.iniciar()

        self._atualizar_status_periodicamente()

    def _montar_aba_leia_me(self, aba: tk.Frame) -> None:
        texto = tk.Text(
            aba, wrap="word", bg=COR_FUNDO, fg="#16212a", relief="flat",
            font=("Segoe UI", 9), padx=4, pady=4, borderwidth=0, highlightthickness=0,
        )
        texto.insert("1.0", LEIA_ME_TEXTO)
        texto.configure(state="disabled")
        texto.pack(fill="both", expand=True)

    def _montar_aba_bitin(self, aba: tk.Frame) -> None:
        """Aba "BITin" (2026-07-23, pedido explícito) -- é AQUI que ativa/desativa o agente,
        separado da aba "Configurações"."""
        self.label_usuario = tk.Label(
            aba, text="Conectado como: —", font=("Segoe UI", 9, "italic"),
            fg=COR_TEXTO_MUTED, bg=COR_FUNDO, anchor="w", justify="left", wraplength=360,
        )
        self.label_usuario.pack(fill="x", pady=(6, 14))

        self.var_ativo = tk.BooleanVar(value=self.config["ativo"])
        tk.Checkbutton(
            aba, text="Agente ativo (responde à tela do BITin)", variable=self.var_ativo,
            command=self._alternar_ativo, bg=COR_FUNDO, font=("Segoe UI", 9), anchor="w",
        ).pack(fill="x")

    def _montar_aba_config(self, aba: tk.Frame) -> None:
        """Aba "Configurações" (2026-07-23, pedido explícito) -- abrir com o Windows e onde o
        `.exe` está instalado, nada de ativar/desativar aqui (isso é na aba "BITin")."""
        self.var_windows = tk.BooleanVar(value=self.config["abrir_com_windows"])
        tk.Checkbutton(
            aba, text="Abrir automaticamente com o Windows", variable=self.var_windows,
            command=self._alternar_abrir_com_windows, bg=COR_FUNDO, font=("Segoe UI", 9), anchor="w",
        ).pack(fill="x", pady=(6, 14))

        tk.Label(
            aba, text="Local do arquivo:", font=("Segoe UI", 9, "bold"),
            fg="#16212a", bg=COR_FUNDO, anchor="w",
        ).pack(fill="x")
        tk.Label(
            aba, text=_caminho_executavel_atual(), font=("Segoe UI", 8),
            fg=COR_TEXTO_MUTED, bg=COR_FUNDO, anchor="w", justify="left", wraplength=360,
        ).pack(fill="x", pady=(2, 0))

        tk.Label(
            aba, text="Mais opções (flags de comportamento) virão aqui.",
            font=("Segoe UI", 8, "italic"), fg=COR_TEXTO_MUTED, bg=COR_FUNDO, anchor="w",
        ).pack(fill="x", pady=(18, 0))

        # Aplica o registro de "abrir com o Windows" já na primeira execução, se a config
        # (nova, ainda sem valor persistido) já vier com o padrão True -- mantém o registro do
        # Windows sempre em sincronia com o que a tela mostra, mesmo antes de o usuário clicar.
        if self.var_windows.get():
            self._registrar_abrir_com_windows(True)

    def _alternar_ativo(self) -> None:
        ligado = self.var_ativo.get()
        if ligado:
            self.servidor_agente.iniciar()
        else:
            self.servidor_agente.parar()
        self.config["ativo"] = ligado
        config_agente.salvar(self.config)

    def _alternar_abrir_com_windows(self) -> None:
        ligado = self.var_windows.get()
        self.config["abrir_com_windows"] = ligado
        config_agente.salvar(self.config)
        self._registrar_abrir_com_windows(ligado)

    def _registrar_abrir_com_windows(self, ligado: bool) -> None:
        if not getattr(sys, "frozen", False):
            return  # dev (rodando via `python agente_app.py`) não tem .exe de verdade pra apontar
        try:
            if ligado:
                startup_windows.registrar(Path(sys.executable))
            else:
                startup_windows.remover()
        except OSError:
            pass  # falha de registro não pode travar a janela

    def _atualizar_status_periodicamente(self) -> None:
        usuario = estado_agente.obter_usuario()
        if usuario and usuario.get("email"):
            self.label_usuario.config(text=f"Conectado como: {usuario['nome']} ({usuario['email']})")
        else:
            self.label_usuario.config(text="Conectado como: — (aguardando o BITin no navegador)")
        self.root.after(3000, self._atualizar_status_periodicamente)

    def _ao_mudar_estado(self, _event: object) -> None:
        if self.root.state() == "iconic":
            self.ocultar()

    def ocultar(self) -> None:
        self.root.withdraw()

    def mostrar(self) -> None:
        self.root.deiconify()
        self.root.state("normal")
        self.root.lift()
        self.root.focus_force()


def _sair(icon: pystray.Icon, _item: pystray.MenuItem) -> None:
    """"Sair" (menu da bandeja) -- diferente de desativar o servidor (checkbox "Agente ativo"
    na janela): encerra o processo inteiro (janela + bandeja + servidor, se estiver ligado)."""
    icon.stop()
    os._exit(0)


def montar_icone(janela: JanelaAgente) -> pystray.Icon:
    # Callbacks do pystray rodam na thread DELE, não na do Tkinter -- `root.after(0, ...)`
    # agenda a chamada de volta pra thread principal (única onde é seguro mexer em widgets).
    def _abrir(icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        janela.root.after(0, janela.mostrar)

    menu = pystray.Menu(
        pystray.MenuItem("Abrir", _abrir, default=True),
        pystray.MenuItem("Sair", _sair),
    )
    return pystray.Icon("agente_sap_bitin", _gerar_icone(), NOME_EXIBIDO, menu)


def main() -> None:
    servidor_agente = servidor.ServidorAgente()

    root = tk.Tk()
    janela = JanelaAgente(root, servidor_agente)
    montar_icone(janela).run_detached()
    root.mainloop()


if __name__ == "__main__":
    main()
