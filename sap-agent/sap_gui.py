#!/usr/bin/env python3
"""Ponte Python -> SAP GUI Scripting (COM), port de `Módulo4.ValidarListaTecnica_MM60`
(macro VBA real, `PESQUISA_CODIGO 11.xlsm`) -- roda no PC do engenheiro, que já tem o SAP GUI
aberto e logado. NÃO é uma API SAP (REST/RFC/BAPI/OData): é automação de interface, serial
(um material por vez) e dependente dos mesmos IDs de tela que a macro original usava.

`win32com.client` (pywin32) só existe no Windows -- importado dentro das funções, não no
topo do módulo, pra este arquivo poder ser importado (e testado com mock) em qualquer SO.
"""

from typing import Any, Protocol


class SapIndisponivelError(Exception):
    """SAP GUI não está aberto, ou não há conexão/sessão ativa nesta máquina."""


class SapSession(Protocol):
    """Formato mínimo do objeto `session` do SAP GUI Scripting que este módulo usa --
    só o suficiente pra permitir mock nos testes sem depender de pywin32/SAP GUI real."""

    def findById(self, id_: str) -> Any: ...


def obter_sessao() -> SapSession:
    """Replica `GetObject("SAPGUI")` -> `GetScriptingEngine` -> `Children(0)` -> `Children(0)`
    da macro original. Levanta SapIndisponivelError com mensagem clara em cada ponto onde a
    macro original simplesmente pularia pro `MsgBox "Erro: SAP mudou de tela ou ID não
    encontrado"`."""
    try:
        import pythoncom
        import win32com.client
    except ImportError as exc:
        raise SapIndisponivelError(
            "pywin32 não está instalado nesta máquina -- o agente só funciona no Windows."
        ) from exc

    # O servidor HTTP (Flask/Werkzeug) processa cada request numa thread própria, que nunca
    # teve COM inicializado -- achado real ao testar contra SAP GUI de verdade (2026-07-22):
    # `GetObject("SAPGUI")` funciona direto num script, mas falha silenciosamente vindo do
    # servidor até essa thread chamar `CoInitialize` pelo menos uma vez. Chamar de novo numa
    # thread já inicializada é inofensivo (retorna S_FALSE, não levanta exceção).
    pythoncom.CoInitialize()

    try:
        sap_gui_auto = win32com.client.GetObject("SAPGUI")
    except Exception as exc:
        raise SapIndisponivelError(
            "SAP GUI não está aberto nesta máquina (GetObject('SAPGUI') falhou)."
        ) from exc

    sap_app = sap_gui_auto.GetScriptingEngine
    if sap_app.Children.Count == 0:
        raise SapIndisponivelError("SAP GUI aberto, mas sem nenhuma conexão ativa.")
    sap_con = sap_app.Children(0)

    if sap_con.Children.Count == 0:
        raise SapIndisponivelError("Conexão SAP aberta, mas sem nenhuma sessão ativa.")
    return sap_con.Children(0)


def consultar_material(session: SapSession, codigo: str) -> dict[str, Any]:
    """Um material -> `MM60` -> `{"encontrado": bool, "descricao": str | None, "erro": str | None}`.

    Mesmos passos de `ValidarListaTecnica_MM60` (ver docstring do módulo): abre MM60, fecha
    popup se aparecer, digita o material em `MS_MATNR-LOW`, executa (`btn[8]`), lê
    `GetCellValue(0, "KTEXT")` da grade -- se essa leitura falhar (mesmo `On Error Resume Next`
    da macro, aqui como `try/except`), o material não existe/não tem lista técnica visível.
    Qualquer outra falha ao longo do caminho (tela mudou, ID não encontrado -- mesmo `GoTo Erro`
    da macro) volta como `erro` estruturado, nunca como exceção não tratada -- o chamador
    (`servidor.py`) processa uma lista inteira e não pode travar no meio por causa de 1 material.
    """
    codigo = codigo.strip()
    if not codigo:
        return {"encontrado": False, "descricao": None, "erro": "Código vazio"}

    try:
        session.findById("wnd[0]/tbar[0]/okcd").Text = "/nMM60"
        session.findById("wnd[0]").sendVKey(0)

        try:
            session.findById("wnd[1]").Close()
        except Exception:
            pass

        session.findById("wnd[0]/usr/ctxtMS_MATNR-LOW").Text = codigo
        session.findById("wnd[0]/tbar[1]/btn[8]").Press()

        try:
            descricao = session.findById(
                "wnd[0]/usr/cntlGRID1/shellcont/shell"
            ).GetCellValue(0, "KTEXT")
        except Exception:
            return {"encontrado": False, "descricao": None, "erro": None}

        return {"encontrado": True, "descricao": descricao, "erro": None}
    except Exception as exc:
        return {"encontrado": False, "descricao": None, "erro": f"SAP mudou de tela ou ID não encontrado: {exc}"}


def consultar_materiais(session: SapSession, codigos: list[str]) -> dict[str, dict[str, Any]]:
    """Lote (decisão do usuário: "só em lote") -- sequencial, mesma limitação da macro
    original (SAP GUI Scripting não paraleliza)."""
    return {codigo: consultar_material(session, codigo) for codigo in codigos}


# Campos de `dados_basicos` (ver DADOS_BASICOS_LABELS em scripts/bitin_model.py) automatizáveis
# via MM03, com o ID de tela REAL de cada um -- confirmado por gravação real do SAP GUI
# Scripting feita pelo usuário (`Script1.vbs`, 2026-07-22), NUNCA inferido/adivinhado a partir
# do nome da tabela/campo ABAP (achado real: subtelas do MM03 não são previsíveis por nome de
# campo -- ver conversa que motivou essa gravação). Cada entrada tem a aba (`tab`, `tabpSPxx`),
# o caminho do elemento dali pra baixo (`id`) e o tipo de leitura (`texto` -> `.Text`,
# `checkbox` -> `.Selected`, mapeado pro mesmo domínio X/- já usado em
# frontend/src/lib/dadosBasicosValidacao.ts).
#
# Ainda SEM id confirmado (pendente nova gravação, ver sap-agent/README.md):
# texto_pedidos_compras (única aba de bloco de texto, ainda não clicada em nenhuma gravação).
CAMPOS_MM03: dict[str, dict[str, str]] = {
    "nivel_revisao": {
        "tab": "tabpSP01",
        "id": "ssubTABFRA1:SAPLMGMM:2004/subSUB1:SAPLMGD1:1002/txtRMMZU-REVLV",
        "tipo": "texto",
    },
    "material_substituto": {
        "tab": "tabpSP02",
        "id": "ssubTABFRA1:SAPLMGMM:2004/subSUB2:SAPLMGD1:2002/txtMARA-NORMT",
        "tipo": "texto",
    },
    "planejador": {
        "tab": "tabpSP12",
        "id": "ssubTABFRA1:SAPLMGMM:2000/subSUB3:SAPLMGD1:2482/ctxtMARC-DISPO",
        "tipo": "texto",
    },
    "prazo_entrega": {
        "tab": "tabpSP13",
        "id": "ssubTABFRA1:SAPLMGMM:2000/subSUB3:SAPLMGD1:2485/txtMARC-PLIFZ",
        "tipo": "texto",
    },
    "perfil_producao": {
        "tab": "tabpSP17",
        "id": "ssubTABFRA1:SAPLMGMM:2000/subSUB2:SAPLMGD1:2601/ctxtMARC-SFCPF",
        "tipo": "texto",
    },
    "producao_interna": {
        "tab": "tabpSP25",
        "id": "ssubTABFRA1:SAPLMGMM:2000/subSUB4:SAPLMGD1:2806/chkMBEW-OWNPR",
        "tipo": "checkbox",
    },
    "data_bloqueio_vendas": {
        "tab": "tabpSP04",
        "id": "ssubTABFRA1:SAPLMGMM:2000/subSUB2:SAPLMGD1:2158/ctxtMARA-MSTDV",
        "tipo": "texto",
    },
    "ncm": {
        "tab": "tabpSP07",
        "id": "ssubTABFRA1:SAPLMGMM:2004/subSUB2:SAPLMGD1:2205/ctxtMARC-STEUC",
        "tipo": "texto",
    },
    # Confirmados em Script2.vbs (2026-07-22, 2ª gravação):
    "unidade_volume": {
        "tab": "tabpSP01",
        "id": "ssubTABFRA1:SAPLMGMM:2004/subSUB4:SAPLMGD1:2007/ctxtMARA-VOLEH",
        "tipo": "texto",
    },
    "documento": {
        "tab": "tabpSP02",
        "id": "ssubTABFRA1:SAPLMGMM:2004/subSUB5:SAPLMGD1:2004/txtMARA-ZEINR",
        "tipo": "texto",
    },
    "grupo_compradores": {
        "tab": "tabpSP12",
        "id": "ssubTABFRA1:SAPLMGMM:2000/subSUB2:SAPLMGD1:2481/ctxtMARC-EKGRP",
        "tipo": "texto",
    },
    "deposito_suprimento_externo": {
        "tab": "tabpSP13",
        "id": "ssubTABFRA1:SAPLMGMM:2000/subSUB2:SAPLMGD1:2484/ctxtMARC-LGFSB",
        "tipo": "texto",
    },
    "responsavel_controle_producao": {
        "tab": "tabpSP17",
        "id": "ssubTABFRA1:SAPLMGMM:2000/subSUB2:SAPLMGD1:2601/ctxtMARC-FEVOR",
        "tipo": "texto",
    },
    "status_bloqueio_vendas": {
        "tab": "tabpSP04",
        "id": "ssubTABFRA1:SAPLMGMM:2000/subSUB2:SAPLMGD1:2158/ctxtMARA-MSTAV",
        "tipo": "texto",
    },
    "origem_material": {
        "tab": "tabpSP25",
        "id": "ssubTABFRA1:SAPLMGMM:2000/subSUB4:SAPLMGD1:2806/ctxtMBEW-MTORG",
        "tipo": "texto",
    },
    # Confirmados em Script3.vbs (2026-07-22, 3ª gravação):
    "volume": {
        "tab": "tabpSP01",
        "id": "ssubTABFRA1:SAPLMGMM:2004/subSUB4:SAPLMGD1:2007/txtMARA-VOLUM",
        "tipo": "texto",
    },
    "deposito_producao": {
        "tab": "tabpSP13",
        "id": "ssubTABFRA1:SAPLMGMM:2000/subSUB2:SAPLMGD1:2484/ctxtMARC-LGPRO",
        "tipo": "texto",
    },
    "utilizacao_material": {
        "tab": "tabpSP25",
        "id": "ssubTABFRA1:SAPLMGMM:2000/subSUB4:SAPLMGD1:2806/ctxtMBEW-MTUSE",
        "tipo": "texto",
    },
    # Confirmados em Script4.vbs (2026-07-22, 4ª gravação -- reabrindo a MM03 a cada campo,
    # único jeito que capturou de forma confiável mais de 1 campo por aba):
    "grupo_mercadorias": {
        "tab": "tabpSP01",
        "id": "ssubTABFRA1:SAPLMGMM:2004/subSUB2:SAPLMGD1:2001/ctxtMARA-MATKL",
        "tipo": "texto",
    },
    "hierarquia": {
        "tab": "tabpSP01",
        "id": "ssubTABFRA1:SAPLMGMM:2004/subSUB2:SAPLMGD1:2001/ctxtMARA-PRDHA",
        "tipo": "texto",
    },
    "peso_bruto": {
        "tab": "tabpSP01",
        "id": "ssubTABFRA1:SAPLMGMM:2004/subSUB4:SAPLMGD1:2007/txtMARA-BRGEW",
        "tipo": "texto",
    },
    "peso_liquido": {
        "tab": "tabpSP01",
        "id": "ssubTABFRA1:SAPLMGMM:2004/subSUB4:SAPLMGD1:2007/txtMARA-NTGEW",
        "tipo": "texto",
    },
    "unidade_peso": {
        "tab": "tabpSP01",
        "id": "ssubTABFRA1:SAPLMGMM:2004/subSUB4:SAPLMGD1:2007/ctxtMARA-GEWEI",
        "tipo": "texto",
    },
    "tipo_suprimento": {
        "tab": "tabpSP13",
        "id": "ssubTABFRA1:SAPLMGMM:2000/subSUB2:SAPLMGD1:2484/ctxtMARC-BESKZ",
        "tipo": "texto",
    },
    "tipo_suprimento_especial": {
        "tab": "tabpSP13",
        "id": "ssubTABFRA1:SAPLMGMM:2000/subSUB2:SAPLMGD1:2484/ctxtMARC-SOBSL",
        "tipo": "texto",
    },
}


def _selecionar_centro_mm03(session: SapSession, centro: str) -> None:
    """Preenche o Centro no popup de níveis de organização que aparece ao abrir o MM03
    (confirmado em `Script1.vbs`: botão 'Níveis de organização' = `tbar[0]/btn[20]` dentro do
    popup `wnd[1]`). `try/except` porque o popup só aparece se o SAP ainda não sabe o centro
    pra este material nesta sessão -- mesmo espírito do `On Error Resume Next` das macros
    originais ao redor de popups opcionais."""
    try:
        session.findById("wnd[1]/tbar[0]/btn[20]").Press()
        session.findById("wnd[1]").sendVKey(0)
        session.findById("wnd[1]/usr/ctxtRMMG1-WERKS").Text = centro
        session.findById("wnd[1]").sendVKey(0)
    except Exception:
        pass


def consultar_dados_basicos_mm03(
    session: SapSession, material: str, centro: str, campos: list[str]
) -> dict[str, dict[str, Any]]:
    """Abre o MM03 pro material (com o Centro informado) e lê os `campos` pedidos (chaves de
    `CAMPOS_MM03`) -- cada um devolvido como `{"encontrado": bool, "valor": str | None, "erro":
    str | None}`. Campo pedido mas ainda sem ID mapeado (fora de `CAMPOS_MM03`) devolve erro
    claro em vez de tentar adivinhar."""
    try:
        session.findById("wnd[0]/tbar[0]/okcd").Text = "/nMM03"
        session.findById("wnd[0]").sendVKey(0)
        session.findById("wnd[0]/usr/ctxtRMMG1-MATNR").Text = material
        session.findById("wnd[0]").sendVKey(0)
        _selecionar_centro_mm03(session, centro)
    except Exception as exc:
        erro = f"Erro ao abrir MM03 para {material!r}: {exc}"
        return {campo: {"encontrado": False, "valor": None, "erro": erro} for campo in campos}

    resultado: dict[str, dict[str, Any]] = {}
    for campo in campos:
        info = CAMPOS_MM03.get(campo)
        if info is None:
            resultado[campo] = {
                "encontrado": False,
                "valor": None,
                "erro": "Campo ainda não mapeado no agente (ver sap-agent/README.md)",
            }
            continue
        try:
            session.findById(f"wnd[0]/usr/tabsTABSPR1/{info['tab']}").select()
            elemento = session.findById(f"wnd[0]/usr/tabsTABSPR1/{info['tab']}/{info['id']}")
            valor = ("X" if elemento.Selected else "-") if info["tipo"] == "checkbox" else elemento.Text
            resultado[campo] = {"encontrado": True, "valor": valor, "erro": None}
        except Exception as exc:
            resultado[campo] = {"encontrado": False, "valor": None, "erro": f"Não foi possível ler: {exc}"}

    return resultado


def _consultar_flag_mm06(session: SapSession, centro: str | None) -> dict[str, Any]:
    """`marcacao_eliminar_nivel_mandante`/`marcacao_eliminar_nivel_centro` vivem na mesma tela
    da MM06 (`RM03G-LVOMA`), não na MM03 -- chamar logo depois de `consultar_dados_basicos_mm03`
    NO MESMO material/sessão (o material digitado no MM03 momentos antes é reaproveitado via
    memória de parâmetro SET/GET do SAP, comportamento real observado em 3 gravações).

    O que distingue mandante de centro é só se o Centro (`RM03G-WERKS`) é preenchido antes de
    ler o checkbox (confirmado comparando `Script1.vbs`/`Script3.vbs`, que preenchem o Centro,
    contra `Script2.vbs`, que não preenche nada -- mesma descrição do usuário: "MM06 -> Material"
    é nível mandante, "MM06 -> Colocar o centro no campo de centro -> Material" é nível centro)."""
    try:
        session.findById("wnd[0]/tbar[0]/okcd").Text = "/nMM06"
        session.findById("wnd[0]").sendVKey(0)
        if centro is not None:
            session.findById("wnd[0]/usr/ctxtRM03G-WERKS").Text = centro
            session.findById("wnd[0]").sendVKey(0)
        marcado = session.findById("wnd[0]/usr/chkRM03G-LVOMA").Selected
        return {"encontrado": True, "valor": "X" if marcado else "-", "erro": None}
    except Exception as exc:
        return {"encontrado": False, "valor": None, "erro": f"Não foi possível ler MM06: {exc}"}


def consultar_flag_eliminacao_mandante(session: SapSession) -> dict[str, Any]:
    """Nível mandante: MM06 SEM preencher o Centro (ver `_consultar_flag_mm06`)."""
    return _consultar_flag_mm06(session, centro=None)


def consultar_flag_eliminacao_centro(session: SapSession, centro: str) -> dict[str, Any]:
    """Nível centro: MM06 preenchendo o Centro antes de ler o checkbox (ver
    `_consultar_flag_mm06`)."""
    return _consultar_flag_mm06(session, centro=centro)
