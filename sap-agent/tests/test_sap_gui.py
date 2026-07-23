"""Testes de `sap_gui.py` com um mock do objeto COM `session` -- não depende de pywin32 nem de
SAP GUI real instalado (roda em qualquer máquina/CI). `obter_sessao()` (que de fato importa
`win32com.client`) não é testada aqui -- só é executável numa máquina Windows com SAP GUI, ver
`sap-agent/README.md`."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

import sap_gui


class FalsoElemento:
    """Um elemento de tela SAP GUI Scripting -- só o que os testes precisam: `.Text`
    (atribuível), `.sendVKey()`, `.Press()`, `.Close()`, `.GetCellValue()`, `.select()`,
    `.Selected`."""

    def __init__(self, comportamento, valor_texto=None, selected=None):
        self.comportamento = comportamento
        self.Text = valor_texto if valor_texto is not None else ""
        self.Selected = bool(selected) if selected is not None else False

    def sendVKey(self, code):
        pass

    def Press(self):
        pass

    def select(self):
        pass

    def Close(self):
        if self.comportamento.get("popup_close_falha"):
            raise RuntimeError("sem popup pra fechar")

    def GetCellValue(self, linha, coluna):
        if self.comportamento.get("material_nao_encontrado"):
            raise RuntimeError("grade vazia -- material não existe")
        return self.comportamento.get("descricao", "DESCRICAO PADRAO")


class FalsaSessao:
    def __init__(self, comportamento=None):
        self.comportamento = comportamento or {}

    def findById(self, id_):
        if self.comportamento.get("tela_mudou"):
            raise RuntimeError("elemento não encontrado -- tela mudou")
        if self.comportamento.get("popup_organizacao_falha") and id_.startswith("wnd[1]"):
            raise RuntimeError("sem popup de organização pra este material")
        if self.comportamento.get("campo_falha_id") == id_:
            raise RuntimeError("elemento não encontrado nesta tela")
        if id_.endswith("chkMBEW-OWNPR") or id_.endswith("chkRM03G-LVOMA"):
            return FalsoElemento(self.comportamento, selected=self.comportamento.get("checkbox_marcado", False))
        return FalsoElemento(self.comportamento, valor_texto=self.comportamento.get("valor_campo", "VALOR"))


def test_material_encontrado_devolve_descricao():
    sessao = FalsaSessao({"descricao": "TUBO MENOR 1/2\""})
    resultado = sap_gui.consultar_material(sessao, "8661")
    assert resultado == {"encontrado": True, "descricao": "TUBO MENOR 1/2\"", "erro": None}


def test_material_nao_encontrado():
    sessao = FalsaSessao({"material_nao_encontrado": True})
    resultado = sap_gui.consultar_material(sessao, "0000")
    assert resultado == {"encontrado": False, "descricao": None, "erro": None}


def test_codigo_vazio_nao_consulta_sap():
    sessao = FalsaSessao()
    resultado = sap_gui.consultar_material(sessao, "   ")
    assert resultado["encontrado"] is False
    assert resultado["erro"] == "Código vazio"


def test_popup_sem_close_nao_quebra():
    # `wnd[1]` não existir é o caso normal (sem popup) -- Close() falhando é engolido, igual
    # ao `On Error Resume Next` da macro original.
    sessao = FalsaSessao({"popup_close_falha": True, "descricao": "OK"})
    resultado = sap_gui.consultar_material(sessao, "1234")
    assert resultado["encontrado"] is True


def test_sap_mudou_de_tela_devolve_erro_estruturado():
    sessao = FalsaSessao({"tela_mudou": True})
    resultado = sap_gui.consultar_material(sessao, "1234")
    assert resultado["encontrado"] is False
    assert "SAP mudou de tela" in resultado["erro"]


def test_consultar_materiais_em_lote():
    sessao = FalsaSessao({"descricao": "PECA X"})
    resultado = sap_gui.consultar_materiais(sessao, ["1111", "2222"])
    assert set(resultado.keys()) == {"1111", "2222"}
    assert all(v["encontrado"] for v in resultado.values())


def test_consultar_dados_basicos_mm03_campo_texto():
    sessao = FalsaSessao({"valor_campo": "C"})
    resultado = sap_gui.consultar_dados_basicos_mm03(sessao, "8661", "2001", ["nivel_revisao"])
    assert resultado == {"nivel_revisao": {"encontrado": True, "valor": "C", "erro": None}}


def test_consultar_dados_basicos_mm03_campo_checkbox():
    sessao = FalsaSessao({"checkbox_marcado": True})
    resultado = sap_gui.consultar_dados_basicos_mm03(sessao, "8661", "2001", ["producao_interna"])
    assert resultado == {"producao_interna": {"encontrado": True, "valor": "X", "erro": None}}


def test_consultar_dados_basicos_mm03_campo_nao_mapeado():
    sessao = FalsaSessao()
    resultado = sap_gui.consultar_dados_basicos_mm03(sessao, "8661", "2001", ["texto_pedidos_compras"])
    assert resultado["texto_pedidos_compras"]["encontrado"] is False
    assert "não mapeado" in resultado["texto_pedidos_compras"]["erro"]


def test_consultar_dados_basicos_mm03_campos_da_segunda_gravacao():
    # Confirma que os campos adicionados via Script2.vbs (2ª gravação) também funcionam pelo
    # mesmo mecanismo genérico -- não precisa de 1 teste por campo, só amostragem.
    sessao = FalsaSessao({"valor_campo": "Z001"})
    resultado = sap_gui.consultar_dados_basicos_mm03(
        sessao, "8661", "2001", ["documento", "grupo_compradores", "status_bloqueio_vendas"]
    )
    assert all(r["encontrado"] for r in resultado.values())
    assert resultado["documento"]["valor"] == "Z001"


def test_consultar_dados_basicos_mm03_sem_popup_organizacao_nao_quebra():
    # Popup de níveis de organização é opcional (só aparece se o SAP ainda não souber o
    # Centro) -- ausência dele não pode quebrar a consulta dos campos em si.
    sessao = FalsaSessao({"popup_organizacao_falha": True, "valor_campo": "X"})
    resultado = sap_gui.consultar_dados_basicos_mm03(sessao, "8661", "2001", ["nivel_revisao"])
    assert resultado["nivel_revisao"]["encontrado"] is True


def test_consultar_flag_eliminacao_mandante_nao_preenche_centro():
    sessao = FalsaSessao({"checkbox_marcado": False})
    resultado = sap_gui.consultar_flag_eliminacao_mandante(sessao)
    assert resultado == {"encontrado": True, "valor": "-", "erro": None}


def test_consultar_flag_eliminacao_centro_preenche_centro():
    sessao = FalsaSessao({"checkbox_marcado": True})
    resultado = sap_gui.consultar_flag_eliminacao_centro(sessao, "2001")
    assert resultado == {"encontrado": True, "valor": "X", "erro": None}


def test_consultar_dados_basicos_mm03_campos_da_quarta_gravacao():
    # Confirma que os campos adicionados via Script4.vbs (4ª gravação, reabrindo a MM03 a cada
    # campo) também funcionam pelo mesmo mecanismo genérico.
    sessao = FalsaSessao({"valor_campo": "01"})
    resultado = sap_gui.consultar_dados_basicos_mm03(
        sessao, "8661", "2001", ["grupo_mercadorias", "peso_bruto", "tipo_suprimento"]
    )
    assert all(r["encontrado"] for r in resultado.values())


def test_obter_sessao_sem_win32com_levanta_erro_claro(monkeypatch):
    # Simula ambiente sem pywin32 (ex.: CI não-Windows) -- garante que a mensagem de erro é
    # clara em vez de um ImportError cru estourando pro chamador.
    import builtins

    real_import = builtins.__import__

    def import_falso(name, *args, **kwargs):
        if name == "win32com.client":
            raise ModuleNotFoundError("No module named 'win32com'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", import_falso)
    with pytest.raises(sap_gui.SapIndisponivelError):
        sap_gui.obter_sessao()
