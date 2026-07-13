#!/usr/bin/env python3
"""Documento do BITin (Alt/Esp/DWG-SAT/checklist), portado de Módulo4+Módulo10+Módulo13.

Diferente do Módulo1/Módulo2 (posições de coluna que o SAP/Winshuttle realmente lê, onde
qualquer divergência tem risco real de quebrar um upload), o checklist aqui é uma estrutura
de dados nova (não escreve em células de planilha legada) — por isso, quando os dados reais
de exemplo (bitin teste 2.xlsm) divergiram das linhas hardcoded no Módulo4.bas extraído, foi
usado o mapeamento semântico (por rótulo do item), que bateu com os dados reais, em vez da
posição de linha literal do .bas (ver docs/BITIN_MODEL.md, seção "Documento do BITin").
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


@lru_cache(maxsize=None)
def load_config(config_path: Path) -> dict[str, Any]:
    return json.loads(config_path.read_text(encoding="utf-8"))


def suggest_dwg_sat_action(plan2_row: dict[int, str], config: dict[str, Any]) -> str | None:
    """Sugestão opcional (não autoritativa) baseada em códigos SAP de Grupo Mercadorias.
    Frágil por natureza (catálogo de códigos é vasto e muda com o tempo) — não usar para
    validação; o campo autoritativo é materiais[].atualizar_dwg_sat, declarado pelo
    engenheiro. Ver docs/BITIN_MODEL.md, seção "Alt/Esp declarados pelo engenheiro"."""
    cols = config["plan2_columns"]
    dwg_sat_map = config["grupo_mercadorias_dwg_sat"]

    action = dwg_sat_map.get(plan2_row.get(cols["grupo_mercadorias_atual"], ""))
    novo = plan2_row.get(cols["grupo_mercadorias_novo"], "")
    if novo != "":
        action = dwg_sat_map.get(novo, action)
    return action


def suggest_alt(plan2_row: dict[int, str], config: dict[str, Any]) -> str:
    """Sugestão opcional (não autoritativa) — mesma ressalva de suggest_dwg_sat_action."""
    cols = config["plan2_columns"]
    fornecedor_code = config["grupo_mercadorias_fornecedor"]
    mp_prefix = config["mp_prefix"]

    atual = plan2_row.get(cols["grupo_mercadorias_atual"], "")
    novo = plan2_row.get(cols["grupo_mercadorias_novo"], "")
    tem_desenho = plan2_row.get(cols["desenho_atual"], "") == "SIM"
    revisao_mudou = plan2_row.get(cols["nivel_revisao_novo"], "") != ""

    def _por_grupo_mercadorias(alt_fornecedor: str, alt_default: str) -> str:
        if novo[:2] == mp_prefix or atual[:2] == mp_prefix:
            return alt_fornecedor
        if atual == fornecedor_code:
            return alt_fornecedor if novo == "" else alt_default
        # atual != fornecedor_code
        return alt_fornecedor if novo == fornecedor_code else alt_default

    if tem_desenho:
        if revisao_mudou:
            return _por_grupo_mercadorias("D/F", "D/P")
        return _por_grupo_mercadorias("-/F", "-")

    # Sem desenho: Módulo4 verifica "Texto Pedido Compras Novo" <> Empty, mas esse campo
    # é sempre pelo menos "N/A" (nunca Empty) — a checagem é sempre verdadeira na prática.
    # Replicado fielmente (ver docs/BITIN_MODEL.md).
    return _por_grupo_mercadorias("-/F", "-")


def suggest_esp(plan2_row: dict[int, str], config: dict[str, Any]) -> str:
    """Sugestão opcional (não autoritativa) — mesma ressalva de suggest_dwg_sat_action."""
    cols = config["plan2_columns"]
    fornecedor_code = config["grupo_mercadorias_fornecedor"]
    mp_prefix = config["mp_prefix"]

    texto_pedido = plan2_row.get(cols["texto_pedido_compras_novo"], "")
    if texto_pedido == "" or texto_pedido == "N/A":
        return "-"

    atual = plan2_row.get(cols["grupo_mercadorias_atual"], "")
    novo = plan2_row.get(cols["grupo_mercadorias_novo"], "")
    if atual[:2] == mp_prefix or novo[:2] == mp_prefix:
        return "X"
    if atual != fornecedor_code and novo == fornecedor_code:
        return "X"
    if atual == fornecedor_code:
        return "X"
    return "-"


def read_impactos_operacionais(material: dict[str, Any]) -> dict[str, Any]:
    """Alt/Esp/Est/LP/Pre/OC/OF/atualizar_dwg_sat são declarados pelo engenheiro
    (impactos_operacionais), não derivados de código SAP — ver docs/BITIN_MODEL.md,
    seção "Alt/Esp declarados pelo engenheiro"."""
    impactos = material.get("alteracoes", {}).get("impactos_operacionais", {})
    return {
        "alt": impactos.get("alt", "-"),
        "esp": impactos.get("esp", "-"),
        "est": impactos.get("est", "-"),
        "lp": impactos.get("lp", "-"),
        "pre": impactos.get("pre", "-"),
        "oc": impactos.get("oc", "-"),
        "of": impactos.get("of", "-"),
        "atualizar_dwg_sat": bool(impactos.get("atualizar_dwg_sat", False)),
        "centro_custo": impactos.get("centro_custo", ""),
        "conta_razao": impactos.get("conta_razao", ""),
    }


def build_campo_alterado_diffs(material: dict[str, Any], vba_mapping_config: dict[str, Any]) -> list[dict[str, str]]:
    """'Campo alterado / De: / Para:' por material, direto do JSON do BITin (não precisa
    reconsultar Plan2) — replica a tabela que Módulo4 monta em Plan4 por campo mudado."""
    crosswalk = vba_mapping_config["bitin_schema_crosswalk"]["dados_basicos"]
    headers = vba_mapping_config["plan2_column_headers"]
    dados_basicos = material.get("alteracoes", {}).get("dados_basicos", {})

    diffs: list[dict[str, str]] = []
    for campo, entry in dados_basicos.items():
        para = entry.get("para", "")
        if para == "":
            continue
        plan2_col_novo = crosswalk[campo]
        label = headers[plan2_col_novo - 2]  # coluna "atual" = Novo - 1; índice = col - 1
        diffs.append({"campo": label, "de": entry.get("de", ""), "para": para})
    return diffs


def build_checklist_schema(config: dict[str, Any]) -> list[dict[str, str]]:
    """Os 22 itens fixos do checklist (Quadro 01 do POP), só id+etapa -- fonte única de
    verdade pro frontend montar a tabela de checklist editável na tela de cadastro (ver
    docs/BACKEND.md). Mesma lista usada por build_checklist, sem o cálculo de 'afeta'."""
    return [{"id": item["id"], "etapa": item["etapa"]} for item in config["checklist_items"]]


def build_checklist(bitin: dict[str, Any], materiais: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    ativos: set[str] = set()

    if bitin.get("bitex") == "SIM":
        ativos.add("11")

    for material in materiais:
        impactos = read_impactos_operacionais(material)
        alt_id = config["alt_to_checklist_id"].get(impactos["alt"])
        if alt_id:
            ativos.add(alt_id)
        if impactos["esp"] == "X":
            ativos.add("6")
        if material.get("alteracoes", {}).get("lista_tecnica"):
            ativos.add("7")
        if impactos["est"] not in ("", "-"):
            ativos.add("8")
        if impactos["est"] == "S":
            ativos.add("22")
        if impactos["oc"] not in ("", "-"):
            ativos.add("10")
        if impactos["of"] not in ("", "-"):
            ativos.add("17")
        if impactos["atualizar_dwg_sat"]:
            ativos.add("18")
        if impactos["lp"] not in ("", "-"):
            ativos.add("19")
        if impactos["pre"] not in ("", "-"):
            ativos.add("20")

    return [
        {**item, "afeta": item["id"] in ativos}
        for item in config["checklist_items"]
    ]
