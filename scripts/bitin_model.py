#!/usr/bin/env python3
"""Modelo de dados do BITin: valida o JSON que o engenheiro preenche e converte
para linhas de Plan2 (ZBPP009 + ALTERACAO), prontas para o export Winshuttle de
scripts/vba_port_export.py.

Formato do BITin: ver docs/BITIN_MODEL.md (origem: GPT_Engineering_BITIN/schema.json,
refeito com o mapeamento real de config/vba_mapping.json).
"""

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import csv_safety
import pandas as pd
from bitin_errors import BitinError, make_error

BITIN_NUMBER_RE = re.compile(r"^[PA]\d{4}/\d{2}$")

# "bitin" (número) é gerado pelo sistema no momento do envio (ver backend/), não é
# preenchido pelo engenheiro -- por isso NÃO está nos obrigatórios. "setor" é obrigatório
# porque define o prefixo P/A do número a ser gerado.
REQUIRED_HEADER_FIELDS = ["setor", "produto", "motivo", "solicitante", "data_solicitacao"]
REQUIRED_MATERIAL_FIELDS = ["codigo_material", "centro", "tipo_material"]

# "centro" é a planta SAP (2001 Marau / 2005 Passo Fundo) -- NÃO confundir com "depósito"
# (SAP storage location, códigos tipo 2003 etc, conceito diferente). Restrito a esse
# conjunto fechado porque são as únicas duas plantas em que o BITin opera (2026-07-16).
CENTROS_VALIDOS = {"2001", "2005"}


@lru_cache(maxsize=None)
def load_config(config_path: Path) -> dict[str, Any]:
    return json.loads(config_path.read_text(encoding="utf-8"))


def validate_bitin(bitin: dict[str, Any], config: dict[str, Any]) -> list[BitinError]:
    errors: list[BitinError] = []

    for field in REQUIRED_HEADER_FIELDS:
        if not bitin.get(field):
            errors.append(make_error(field, "required_field_missing", f"campo obrigatório vazio: {field}"))

    numero = bitin.get("bitin", "")
    if numero and not BITIN_NUMBER_RE.match(numero):
        errors.append(make_error(
            "bitin", "invalid_bitin_number_format",
            f"número do BITin fora do formato YXXXX/AA: {numero!r}",
        ))

    materiais = bitin.get("materiais", [])
    if not materiais:
        errors.append(make_error("materiais", "no_materiais", "BITin sem nenhum material em 'materiais'"))

    for idx, material in enumerate(materiais):
        for field in REQUIRED_MATERIAL_FIELDS:
            if not material.get(field):
                errors.append(make_error(
                    f"materiais[{idx}].{field}", "material_required_field_missing",
                    f"materiais[{idx}]: campo obrigatório vazio: {field}",
                ))

        centro = material.get("centro")
        if centro and centro not in CENTROS_VALIDOS:
            errors.append(make_error(
                f"materiais[{idx}].centro", "invalid_centro_value",
                f"materiais[{idx}]: Centro inválido: use 2001 (Marau) ou 2005 (Passo Fundo).",
            ))

    errors.extend(validate_ordem_cliente(bitin))

    return errors


def validate_ordem_cliente(bitin: dict[str, Any]) -> list[BitinError]:
    """Valida a estrutura de ordem_cliente[] (codigo + itens de acrescentar_no_pedido/
    retira_do_pedido). O campo em si é opcional (nem todo BITin afeta ordem de cliente) --
    só valida entradas que existem. A regra de negócio "OC=X exige entrada correspondente"
    (POP Nota 10) fica em bitin_business_rules.py, que já lê só o 'codigo'; aqui é a
    estrutura interna de cada entrada que passa a ser checada."""
    errors: list[BitinError] = []
    for idx, entrada in enumerate(bitin.get("ordem_cliente", [])):
        base_field = f"ordem_cliente[{idx}]"
        if not entrada.get("codigo"):
            errors.append(make_error(
                f"{base_field}.codigo", "required_field_missing",
                f"{base_field}: campo obrigatório vazio: codigo",
            ))

        itens_acrescentar = entrada.get("acrescentar_no_pedido", [])
        itens_retirar = entrada.get("retira_do_pedido", [])
        for lista_nome, itens in (
            ("acrescentar_no_pedido", itens_acrescentar),
            ("retira_do_pedido", itens_retirar),
        ):
            for item_idx, item in enumerate(itens):
                item_field = f"{base_field}.{lista_nome}[{item_idx}]"
                if not item.get("codigo_material"):
                    errors.append(make_error(
                        f"{item_field}.codigo_material", "required_field_missing",
                        f"{item_field}: campo obrigatório vazio: codigo_material",
                    ))
                if not item.get("quantidade"):
                    errors.append(make_error(
                        f"{item_field}.quantidade", "required_field_missing",
                        f"{item_field}: campo obrigatório vazio: quantidade",
                    ))

        if not itens_acrescentar and not itens_retirar:
            errors.append(make_error(
                base_field, "ordem_cliente_sem_itens",
                f"{base_field}: nenhum item em 'acrescentar_no_pedido' nem 'retira_do_pedido' "
                f"— entrada sem efeito",
            ))

    return errors


IMPACTOS_OPERACIONAIS_LABELS = {
    "alt": "Alt",
    "est": "Est",
    "esp": "Esp",
    "lp": "LP",
    "pre": "Pré",
    "oc": "OC",
    "of": "OF",
}

DADOS_BASICOS_LABELS = {
    "descricao": "Descrição",
    "grupo_mercadorias": "Grupo Mercadorias",
    "status": "Status",
    "hierarquia": "Hierarquia",
    "peso_bruto": "Peso Bruto",
    "peso_liquido": "Peso Líquido",
    "unidade_peso": "Unidade Peso",
    "volume": "Volume",
    "unidade_volume": "Unidade Vol.",
    "desenho": "Desenho",
    "nivel_revisao": "Nível Revisão",
    "documento": "Documento",
    "material_substituto": "Material Substituto",
    "status_bloqueio_vendas": "Status Bloqueio vendas",
    "data_bloqueio_vendas": "Data bloqueio vendas",
    "ncm": "NCM",
    "grupo_compradores": "Grupo Compradores",
    "planejador": "Planejador",
    "tipo_suprimento": "Tipo Suprimento",
    "tipo_suprimento_especial": "Tipo Sup. Especial",
    "deposito_producao": "Depósito Produção",
    "deposito_suprimento_externo": "Depósito Sup. Externo",
    "prazo_entrega": "Prazo de Entrega",
    "responsavel_controle_producao": "Resp. Crtrl. Produção",
    "perfil_producao": "Perfil de Produção",
    "utilizacao_material": "Utilização Material",
    "origem_material": "Origem Material",
    "producao_interna": "Produção Interna",
    "texto_pedidos_compras": "Texto Pedidos Compras",
    "marcacao_eliminar_nivel_mandante": "Marcação eliminar nível mandante",
    # Sem coluna correspondente no export SAP (Plan1/ZBPP009 real) -- diferente de
    # "nível mandante" (que tem "de" pré-preenchido pelo SAP, ver plan1_dados_basicos_columns),
    # "nível centro" é sempre declarado manualmente pelo engenheiro (achado ao cruzar a colinha
    # de frases-modelo dos engenheiros com config/vba_mapping.json, 2026-07-17).
    "marcacao_eliminar_nivel_centro": "Marcação eliminar nível centro",
}


def _humanize_label(campo: str) -> str:
    """Fallback só pra campo novo no crosswalk sem entrada em DADOS_BASICOS_LABELS ainda --
    todos os 31 campos atuais já têm rótulo explícito (com acentuação correta em português,
    que um capitalize() ingênuo não reproduz)."""
    return " ".join(palavra.capitalize() for palavra in campo.split("_"))


def build_materiais_schema(vba_mapping_config: dict[str, Any], document_config: dict[str, Any]) -> dict[str, Any]:
    """Monta a definição de colunas do grid de materiais (frontend) a partir do crosswalk
    já existente (`bitin_schema_crosswalk`) e dos valores válidos do POP (`valores_validos`).
    Fonte única de verdade: o frontend não deve hardcodar essas colunas (ver docs/BACKEND.md,
    'Grid de materiais dirigido por schema').

    `dados_basicos` cobre os 30 campos reais da ZBPP009 (não um recorte) -- a tela Códigos SAP
    é idêntica à ZBPP009 (decisão do usuário, 2026-07-15) e usa essa mesma lista pra montar as
    colunas da tabela; a aba BITin usa a mesma lista pra oferecer os campos conhecidos no
    "+Campo" (o resto do texto digitado que não bate com nenhuma dessas chaves vira nota
    livre, ver AlteracaoTable/MaterialEditorCard)."""
    crosswalk = vba_mapping_config["bitin_schema_crosswalk"]
    valores_validos = document_config["valores_validos"]

    identificacao = [
        {"key": "codigo_material", "label": "Código material", "required": True},
        {"key": "descricao_material", "label": "Descrição", "required": False},
        {"key": "centro", "label": "Centro", "required": True},
        {"key": "tipo_material", "label": "Tipo Material", "required": True},
    ]
    dados_basicos = [
        {"key": campo, "label": DADOS_BASICOS_LABELS.get(campo, _humanize_label(campo))}
        for campo in crosswalk["dados_basicos"]
    ]
    impactos_operacionais = [
        {"key": campo, "label": IMPACTOS_OPERACIONAIS_LABELS[campo], "options": valores_validos[campo]}
        for campo in ("alt", "est", "esp", "lp", "pre", "oc", "of")
    ]
    return {
        "identificacao": identificacao,
        "dados_basicos": dados_basicos,
        "impactos_operacionais": impactos_operacionais,
    }


def _na_convention_cols(config: dict[str, Any]) -> set[int]:
    return {
        rule["plan2_col"]
        for rule in config["plan1_to_plan2"]["rules"]
        if rule["type"] == "constant" and rule["value"] == "N/A"
    }


def material_to_plan2_row(material: dict[str, Any], config: dict[str, Any]) -> dict[int, str]:
    crosswalk = config["bitin_schema_crosswalk"]
    na_cols = _na_convention_cols(config)

    row: dict[int, str] = {}

    ident = crosswalk["identificacao"]
    row[ident["tipo_material"]] = material.get("tipo_material", "")
    row[ident["centro"]] = material.get("centro", "")
    row[ident["codigo_material"]] = material.get("codigo_material", "")

    dados_basicos = material.get("alteracoes", {}).get("dados_basicos", {})
    for campo, plan2_col in crosswalk["dados_basicos"].items():
        entry = dados_basicos.get(campo)
        novo_valor = entry.get("para", "") if entry else ""
        if novo_valor == "" and plan2_col in na_cols:
            novo_valor = "N/A"
        row[plan2_col] = novo_valor

    return row


def bitin_to_plan2_rows(bitin: dict[str, Any], config: dict[str, Any]) -> list[dict[int, str]]:
    return [material_to_plan2_row(material, config) for material in bitin.get("materiais", [])]


def bitin_header_values(bitin: dict[str, Any]) -> dict[str, str]:
    return {
        "bitin": bitin.get("bitin", ""),
        "produto": bitin.get("produto", ""),
        "motivo": bitin.get("motivo", ""),
    }


def build_plan2_matrix(bitin: dict[str, Any], config: dict[str, Any]) -> list[list[str]]:
    """Monta a matriz completa da aba Plan2 real: linhas 1-3 (cabeçalho BITIN/Produto/Motivo
    nas células B1/B2/B3, como Módulo2 espera), linha 4 (nomes de coluna) e linha 5+ (dados).
    """
    headers = config["plan2_column_headers"]
    max_col = len(headers)
    header = bitin_header_values(bitin)

    row1 = [""] * max_col
    row1[0], row1[1] = "Número Bitin", header["bitin"]
    row2 = [""] * max_col
    row2[0], row2[1] = "Produto", header["produto"]
    row3 = [""] * max_col
    row3[0], row3[1] = "Motivo", header["motivo"]
    row4 = list(headers)

    matrix = [row1, row2, row3, row4]
    for plan2_row in bitin_to_plan2_rows(bitin, config):
        matrix.append([plan2_row.get(col, "") for col in range(1, max_col + 1)])
    return matrix


def write_plan2_xlsx(bitin: dict[str, Any], config: dict[str, Any], out_path: Path) -> None:
    """Gera um .xlsx com a aba Plan2 (ZBPP009 + ALTERACAO) real, pronto para
    `scripts/vba_port_export.py export` ler diretamente."""
    matrix = [csv_safety.sanitize_row(row) for row in build_plan2_matrix(bitin, config)]
    sheet_name = config["sheet_codenames"]["Plan2"]
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(matrix)
    df.to_excel(out_path, index=False, header=False, sheet_name=sheet_name, engine="openpyxl")


def parse_args():
    import argparse

    parser = argparse.ArgumentParser(
        description="Valida um BITin (JSON) e gera a aba Plan2 (.xlsx) pronta para o export Winshuttle."
    )
    parser.add_argument("bitin_json", help="Arquivo JSON do BITin (ver docs/BITIN_MODEL.md)")
    parser.add_argument("--config", default="config/vba_mapping.json")
    parser.add_argument("--out-xlsx", default=None, help="Gera a aba Plan2 real (.xlsx) neste caminho")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config(Path(args.config))
    bitin = json.loads(Path(args.bitin_json).read_text(encoding="utf-8"))

    errors = validate_bitin(bitin, config)
    if errors:
        print(f"BITin inválido ({len(errors)} erro(s)):")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(f"BITin {bitin['bitin']} válido ({len(bitin['materiais'])} material(is)).")

    if args.out_xlsx:
        write_plan2_xlsx(bitin, config, Path(args.out_xlsx))
        print(f"Gerou {args.out_xlsx}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
