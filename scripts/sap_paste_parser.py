#!/usr/bin/env python3
"""Parser do texto colado do SAP (ZBPP009/relatório equivalente) direto na interface web.

Confirmado com o responsável do projeto: ao copiar a grade do SAP GUI, o Excel separa em
colunas sozinho -- isso só acontece porque o SAP usa caracteres TAB reais entre células, não
espaços. Por isso o parser separa por TAB (não por espaço/largura fixa), o que lida
corretamente com campos de texto livre que têm espaços internos (ex.: descrição
'TUBO MENOR 1/2"') sem ambiguidade nenhuma.

Cada linha colada vira uma linha de Plan1 (ZBPP009) -- mesma estrutura de 36 colunas que
scripts/vba_port_export.py lê do arquivo .xlsm real -- e alimenta diretamente os campos de
snapshot "atual" do material no BITin (ver docs/BITIN_MODEL.md).
"""

from typing import Any


def parse_sap_paste(raw_text: str) -> list[dict[int, str]]:
    """Cada linha colada -> dict {coluna (1-indexada): valor}. Linhas em branco são
    ignoradas. Linhas mais curtas que o esperado ficam só com as colunas presentes
    (não preenche com vazio o que não veio)."""
    rows: list[dict[int, str]] = []
    for line in raw_text.splitlines():
        if line.strip() == "":
            continue
        fields = line.split("\t")
        rows.append({col: value.strip() for col, value in enumerate(fields, start=1)})
    return rows


def plan1_row_to_material_atual(plan1_row: dict[int, str], vba_mapping_config: dict[str, Any]) -> dict[str, Any]:
    """Extrai os campos de identificação + o snapshot 'atual' completo (todos os campos de
    dados_basicos, colados direto da ZBPP009) -- a tela Códigos SAP é idêntica à ZBPP009
    (decisão do usuário, 2026-07-15): lista TODOS os campos SAP do material, não um recorte.
    O 'de' de cada campo de dados_basicos vem daqui; o 'para' fica em branco até o engenheiro
    declarar a alteração na aba BITin."""
    cols = vba_mapping_config["plan1_identificacao_columns"]
    dados_basicos_cols = vba_mapping_config["plan1_dados_basicos_columns"]
    return {
        "tipo_material": plan1_row.get(cols["tipo_material"], ""),
        "codigo_material": plan1_row.get(cols["codigo_material"], ""),
        "centro": plan1_row.get(cols["centro"], ""),
        "descricao_material": plan1_row.get(cols["descricao_material"], ""),
        "grupo_mercadorias_atual": plan1_row.get(cols["grupo_mercadorias_atual"], ""),
        "tem_desenho": plan1_row.get(cols["tem_desenho_col"], "") == "SIM",
        "dados_basicos_atual": {
            campo: plan1_row.get(col, "")
            for campo, col in dados_basicos_cols.items()
        },
    }


def parse_sap_paste_to_materiais(raw_text: str, vba_mapping_config: dict[str, Any]) -> list[dict[str, Any]]:
    """Cola do SAP -> lista de materiais (campos de identificação + snapshot atual),
    prontos para virar materiais[] no BITin (o engenheiro completa alteracoes.* depois)."""
    return [
        plan1_row_to_material_atual(row, vba_mapping_config)
        for row in parse_sap_paste(raw_text)
    ]
