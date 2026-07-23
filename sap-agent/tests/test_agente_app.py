"""Testes de `agente_app.py` -- só a montagem do ícone/menu (nunca `.run()`, que bloqueia e
precisa de um backend gráfico de verdade, indisponível em CI/dev headless)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import agente_app


def test_gerar_icone_devolve_imagem_rgba_64x64():
    imagem = agente_app._gerar_icone()
    assert imagem.size == (64, 64)
    assert imagem.mode == "RGBA"


class _JanelaFalsa:
    """Substitui `JanelaAgente` real (que precisa de um display Tk de verdade) só pra testar a
    montagem do ícone/menu -- `montar_icone` só usa `janela.root.after`."""

    class _RootFalso:
        def after(self, _delay, callback):
            callback()

    def __init__(self):
        self.root = self._RootFalso()
        self.mostrada = False

    def mostrar(self):
        self.mostrada = True


def test_montar_icone_tem_titulo_e_menu_com_opcoes_abrir_e_sair():
    janela = _JanelaFalsa()
    icone = agente_app.montar_icone(janela)
    assert "Agente SAP" in icone.title
    rotulos = [item.text for item in icone.menu.items]
    assert any("Abrir" in rotulo for rotulo in rotulos)
    assert any("Sair" in rotulo for rotulo in rotulos)


def test_montar_icone_abrir_chama_mostrar_da_janela():
    janela = _JanelaFalsa()
    icone = agente_app.montar_icone(janela)
    item_abrir = next(item for item in icone.menu.items if "Abrir" in item.text)
    item_abrir(icone)
    assert janela.mostrada is True


def test_sair_chama_stop_do_icone_e_encerra_processo():
    chamadas = {"stop": 0, "exit": 0}

    class IconeFalso:
        def stop(self):
            chamadas["stop"] += 1

    def exit_falso(_codigo):
        chamadas["exit"] += 1

    original_exit = agente_app.os._exit
    agente_app.os._exit = exit_falso
    try:
        agente_app._sair(IconeFalso(), None)
    finally:
        agente_app.os._exit = original_exit

    assert chamadas == {"stop": 1, "exit": 1}
