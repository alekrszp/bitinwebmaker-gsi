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


def build_campo_alterado_diffs(material: dict[str, Any], vba_mapping_config: dict[str, Any]) -> list[dict[str, Any]]:
    """'Campo alterado / De: / Para:' por material, direto do JSON do BITin (não precisa
    reconsultar Plan2) — replica a tabela que Módulo4 monta em Plan4 por campo mudado.

    Campos livres (achado ao revisar um BITin real, A263326.xlsm): o engenheiro nem sempre
    preenche um campo SAP reconhecido — às vezes escreve uma nota solta ("Salvar DWG",
    "Alterado peso e IS") direto na coluna "Campo alterado". Se o texto não bate com nenhuma
    chave do crosswalk, mostra exatamente como foi escrito em vez de derrubar a requisição com
    KeyError — decisão registrada com o usuário: "tudo que for escrito deve ficar visível"."""
    crosswalk = vba_mapping_config["bitin_schema_crosswalk"]["dados_basicos"]
    headers = vba_mapping_config["plan2_column_headers"]
    dados_basicos = material.get("alteracoes", {}).get("dados_basicos", {})

    diffs: list[dict[str, Any]] = []
    for campo, entry in dados_basicos.items():
        de = entry.get("de", "")
        para = entry.get("para", "")
        plan2_col_novo = crosswalk.get(campo)
        livre = plan2_col_novo is None
        if not livre:
            # Campo SAP reconhecido: "para" vazio continua sem representar uma mudança real
            # (mesmo comportamento de sempre).
            if para == "":
                continue
            label = headers[plan2_col_novo - 2]  # coluna "atual" = Novo - 1; índice = col - 1
        else:
            # Campo livre (não está no crosswalk): a própria chave já é a informação escrita
            # pelo engenheiro -- nunca pula, mesmo sem de/para ("Salvar DWG" real,
            # A263326.xlsm, é só uma nota solta, sem par de/para). "livre" marca isso pro
            # frontend destacar visualmente (decisão do usuário, 2026-07-14).
            label = campo  # mostra exatamente como foi escrito
        diffs.append({"campo": label, "de": de, "para": para, "livre": livre})
    return diffs


def build_checklist_schema(config: dict[str, Any]) -> list[dict[str, str]]:
    """Os 22 itens fixos do checklist (Quadro 01 do POP), só id+etapa -- fonte única de
    verdade pro frontend montar a tabela de checklist editável na tela de cadastro (ver
    docs/BACKEND.md). Mesma lista usada por build_checklist, sem o cálculo de 'afeta'."""
    return [{"id": item["id"], "etapa": item["etapa"]} for item in config["checklist_items"]]


def build_checklist(bitin: dict[str, Any], materiais: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    """Checklist 100% manual -- 'afeta' vem só de `bitin['checklist_overrides']` (dict
    id -> bool); qualquer item nunca clicado pelo engenheiro fica 'afeta=False' por padrão.
    Antes (até 2026-07-14) o sistema sugeria 'afeta' automaticamente a partir dos materiais
    (Alt/Esp/Est/OC/OF/atualizar_dwg_sat/LP/Pre/bitex) e o override só existia pra corrigir a
    sugestão; decisão do usuário, 2026-07-15: 'tirar esse autocomplete de acordo com os códigos
    da checklist, checklist é marcada manualmente' -- a checklist é responsabilidade exclusiva
    do engenheiro, sem inferência a partir dos códigos SAP dos materiais. `materiais` e
    `config['alt_to_checklist_id']` deixaram de ser usados aqui (mantidos como parâmetro/config
    por compatibilidade e porque `alt_to_checklist_id` ainda pode servir de referência, mas não
    há mais leitura automática). Setores acionados (build_setores_afetados) sempre leem o
    resultado final daqui, então marcar um item manualmente aciona os setores do mesmo jeito
    que a sugestão automática acionava antes."""
    overrides = bitin.get("checklist_overrides", {})
    # Anotação livre por item (2026-07-15) -- ex.: "Centro de custo (se tem sucata)" (id 22)
    # usa isso pra registrar o centro de custo/conta razão do sucateamento (POP Nota 8), no
    # lugar de um campo estruturado por material (decisão do usuário: "isso é colocado no
    # campo de descrição lá em cima na checklist ao lado do campo da checklist referente").
    descricoes = bitin.get("checklist_descricoes", {})
    return [
        {
            **item,
            "afeta": overrides.get(item["id"], False),
            "manual": item["id"] in overrides,
            "descricao": descricoes.get(item["id"], ""),
        }
        for item in config["checklist_items"]
    ]


def build_setores_afetados(checklist: list[dict[str, Any]], config: dict[str, Any]) -> list[str]:
    """Departamentos acionados pelas etapas marcadas 'afeta' -- crosswalk fixo
    (config['checklist_setores'], extraído de um BITin real, aba 'SETORES CHECKLIST' de
    A263326.xlsm). Uma etapa pode acionar mais de um setor; devolve a união, sem repetir,
    em ordem alfabética (não importa qual etapa acionou qual -- só quem precisa agir)."""
    setores_config = config.get("checklist_setores", {})
    setores: set[str] = set()
    for item in checklist:
        if item["afeta"]:
            setores.update(setores_config.get(item["id"], []))
    return sorted(setores)
