#!/usr/bin/env python3
"""Port fiel do fluxo real Plan1 (ZBPP009) -> Plan2 (ZBPP009 + ALTERACAO) -> Plan3 (Formulário Winshuttle).

Reproduz Módulo1.PREENCHER + Módulo2.Winshuttle + Módulo11.clear_winshuttle a partir de
artifacts/vba/, orientado pelo mapeamento declarativo em config/vba_mapping.json.

Módulo1 e Módulo2 rodam em momentos diferentes na vida real: entre os dois, o engenheiro
solicitante preenche à mão as colunas "... Novo" de Plan2 com os valores que quer alterar
(ver docs/VBA_EXPORT_MAPPING.md, seção "Padrão atual vs. Novo"). Por isso este script tem
dois subcomandos separados em vez de uma pipeline única:

  sync   - Módulo1: (re)popula as colunas de valor atual de Plan2 a partir de Plan1/ZBPP009.
  export - Módulo2: lê Plan2 como está no arquivo (incluindo as colunas "... Novo" já
           preenchidas) e gera o export Winshuttle (Plan3).
"""

import argparse
import csv
import json
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

import csv_safety

QUIRK_LABELS = {
    1: "coluna 106 (TIPO MATERIAL fora do intervalo normal do Plan3)",
    2: "coluna 65 (flag compartilhada entre Resp. Crtrl. Produção Novo e Perfil de Produção Novo)",
}


@lru_cache(maxsize=None)
def load_config(config_path: Path) -> dict[str, Any]:
    """Cacheado: os .json de config são lidos do disco só uma vez por caminho, não a
    cada chamada -- relevante se isso virar um serviço web chamado repetidamente."""
    return json.loads(config_path.read_text(encoding="utf-8"))


def normalize_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def read_sheet(file_path: Path, sheet_name: str) -> pd.DataFrame:
    # keep_default_na=False: "N/A" é um valor de negócio real neste domínio (ver docs/VBA_EXPORT_MAPPING.md,
    # padrão "atual vs. Novo"), não deve ser tratado como célula vazia/ausente pelo pandas.
    df = pd.read_excel(
        file_path, sheet_name=sheet_name, header=None, dtype=str, engine="openpyxl", keep_default_na=False
    )
    return df.fillna("")


def cell(df: pd.DataFrame, row: int, col: int) -> str:
    """Acessa (row, col) em coordenadas 1-indexadas, no estilo VBA Cells(row, col)."""
    r, c = row - 1, col - 1
    if r < 0 or c < 0 or r >= df.shape[0] or c >= df.shape[1]:
        return ""
    return normalize_cell(df.iloc[r, c])


# ---------------------------------------------------------------------------
# sync: Módulo1.PREENCHER (Plan1 -> colunas de valor atual de Plan2)
# ---------------------------------------------------------------------------


def read_plan1_rows(df: pd.DataFrame, config: dict[str, Any]) -> list[dict[int, str]]:
    mapping = config["plan1_to_plan2"]
    start_row = mapping["start_row_plan1"]
    terminator_col = mapping["loop_terminator_plan1_col"]
    max_col = max(rule.get("plan1_col", 0) for rule in mapping["rules"] if rule["type"] == "direct")

    rows: list[dict[int, str]] = []
    row_idx = start_row
    while cell(df, row_idx, terminator_col) != "":
        row = {col: cell(df, row_idx, col) for col in range(1, max_col + 1)}
        rows.append(row)
        row_idx += 1
    return rows


def validate_plan1_row(row: dict[int, str], config: dict[str, Any]) -> list[str]:
    errors = []
    for requirement in config["validation"]["required_plan1_fields"]:
        if row.get(requirement["plan1_col"], "") == "":
            errors.append(f"campo obrigatório vazio: {requirement['field']} (Plan1 col {requirement['plan1_col']})")
    return errors


def sync_plan2_from_plan1(plan1_row: dict[int, str], config: dict[str, Any]) -> dict[int, str]:
    """Módulo1.PREENCHER: calcula só as colunas de valor atual (+ placeholders 'Novo' iniciais).

    Não sobrescreve colunas 'Novo' já editadas manualmente — quem chama esta função decide
    se aplica o resultado sobre um Plan2 novo (placeholders) ou faz merge preservando edições.
    """
    plan2: dict[int, str] = {}
    for rule in config["plan1_to_plan2"]["rules"]:
        if rule["type"] == "direct":
            plan2[rule["plan2_col"]] = plan1_row.get(rule["plan1_col"], "")
        elif rule["type"] == "constant":
            plan2[rule["plan2_col"]] = rule["value"]
        else:
            raise ValueError(f"Tipo de regra plan1_to_plan2 desconhecido: {rule['type']}")
    return plan2


# ---------------------------------------------------------------------------
# export: Módulo2.Winshuttle (Plan2, como está no arquivo -> Plan3)
# ---------------------------------------------------------------------------


def read_plan2_rows(df: pd.DataFrame, config: dict[str, Any]) -> list[dict[int, str]]:
    """Lê Plan2 diretamente do arquivo real, fiel ao Excel (inclui colunas 'Novo' já editadas)."""
    mapping = config["plan2_to_plan3"]
    start_row = mapping["start_row_plan2"]
    terminator_col = mapping["loop_terminator_plan2_col"]

    max_col = 0
    for rule in config["plan1_to_plan2"]["rules"]:
        max_col = max(max_col, rule["plan2_col"])
    for rule in mapping["rules"]:
        for key, value in rule.items():
            if key.startswith("plan2_col") and isinstance(value, int):
                max_col = max(max_col, value)

    rows: list[dict[int, str]] = []
    row_idx = start_row
    while cell(df, row_idx, terminator_col) != "":
        row = {col: cell(df, row_idx, col) for col in range(1, max_col + 1)}
        rows.append(row)
        row_idx += 1
    return rows


def read_plan2_header(df: pd.DataFrame, config: dict[str, Any]) -> tuple[str, str, str]:
    header = config["plan2_to_plan3"]["header"]
    bitin = cell(df, *header["bitin_plan2_cell"])
    produto = cell(df, *header["produto_plan2_cell"])
    motivo = cell(df, *header["motivo_plan2_cell"])
    return bitin, produto, motivo


def build_plan3_row(
    plan2_row: dict[int, str],
    header_values: dict[str, str],
    config: dict[str, Any],
    quirk_counter: dict[int, int],
) -> dict[int, str]:
    plan3: dict[int, str] = {}
    for rule in config["plan2_to_plan3"]["rules"]:
        rule_type = rule["type"]
        quirk = rule.get("quirk")

        if rule_type == "header_constant":
            plan3[rule["plan3_col"]] = header_values[rule["source"]]

        elif rule_type == "constant":
            plan3[rule["plan3_col"]] = rule["value"]

        elif rule_type == "direct":
            value = plan2_row.get(rule["plan2_col"], "")
            plan3[rule["plan3_col"]] = value
            if quirk and value != "":
                quirk_counter[quirk] = quirk_counter.get(quirk, 0) + 1

        elif rule_type == "flag_if_nonempty":
            value = plan2_row.get(rule["plan2_col"], "")
            plan3[rule["value_col"]] = value
            plan3[rule["flag_col"]] = "SIM" if value != "" else ""

        elif rule_type == "flag_if_not_na":
            value = plan2_row.get(rule["plan2_col"], "")
            already_set = plan3.get(rule["flag_col"], "") == "SIM"
            if value != "N/A":
                plan3[rule["flag_col"]] = "SIM"
                plan3[rule["value_col"]] = value
                if quirk and already_set:
                    quirk_counter[quirk] = quirk_counter.get(quirk, 0) + 1
            else:
                plan3.setdefault(rule["flag_col"], "")
                plan3.setdefault(rule["value_col"], "")

        elif rule_type == "always_copy_with_na_flag":
            value = plan2_row.get(rule["plan2_col"], "")
            plan3[rule["value_col"]] = value
            plan3[rule["flag_col"]] = "" if value == "N/A" else "SIM"

        elif rule_type == "eliminar_nivel_mandante":
            direct_value = plan2_row.get(rule["plan2_col_direct"], "")
            trigger_value = plan2_row.get(rule["plan2_col_sim_trigger"], "")
            plan3[rule["plan3_col"]] = "SIM" if trigger_value == "SIM" else direct_value

        else:
            raise ValueError(f"Tipo de regra plan2_to_plan3 desconhecido: {rule_type}")

    return plan3


def row_dict_to_list(row: dict[int, str], max_col: int) -> list[str]:
    return [row.get(col, "") for col in range(1, max_col + 1)]


def max_plan3_col(config: dict[str, Any]) -> int:
    cols = []
    for rule in config["plan2_to_plan3"]["rules"]:
        cols.extend(
            value
            for key, value in rule.items()
            if key in ("plan3_col", "value_col", "flag_col") and isinstance(value, int)
        )
    return max(cols)


def write_csv(out_csv: Path, header_row: list[str], rows: list[list[str]]) -> None:
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(header_row)
        writer.writerows(csv_safety.sanitize_row(row) for row in rows)


def write_xlsx(out_xlsx: Path, header_row: list[str], rows: list[list[str]]) -> None:
    out_xlsx.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame([header_row] + [csv_safety.sanitize_row(row) for row in rows])
    df.to_excel(out_xlsx, index=False, header=False)


def write_audit_report(
    audit_path: Path,
    total_rows: int,
    skipped: list[tuple[int, list[str]]],
    quirk_counter: dict[int, int],
) -> None:
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "Relatório de auditoria — scripts/vba_port_export.py export",
        f"Linhas lidas em Plan2: {total_rows}",
        f"Linhas puladas por validação: {len(skipped)}",
    ]
    for row_number, errors in skipped:
        lines.append(f"  - linha Plan2 #{row_number}: {'; '.join(errors)}")
    lines.append("Quirks do VBA original acionados:")
    if quirk_counter:
        for quirk_id, count in sorted(quirk_counter.items()):
            lines.append(f"  - quirk {quirk_id} ({QUIRK_LABELS.get(quirk_id, '?')}): {count}x")
    else:
        lines.append("  - nenhum quirk acionado")
    audit_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Port fiel Plan1->Plan2->Plan3 (Módulo1+Módulo2+Módulo11) orientado por config/vba_mapping.json."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    sync_parser = subparsers.add_parser("sync", help="Módulo1: recalcula valores atuais de Plan2 a partir de Plan1")
    sync_parser.add_argument("file", help="Arquivo XLSM de entrada")
    sync_parser.add_argument("--config", default="config/vba_mapping.json")
    sync_parser.add_argument("--sheet-plan1", default=None)
    sync_parser.add_argument("--out-xlsx", default="plan2_sync.xlsx", help="Arquivo XLSX de saída com o Plan2 sincronizado")

    export_parser = subparsers.add_parser("export", help="Módulo2: gera o export Winshuttle a partir de Plan2")
    export_parser.add_argument("file", help="Arquivo XLSM de entrada")
    export_parser.add_argument("--config", default="config/vba_mapping.json")
    export_parser.add_argument("--sheet-plan2", default=None)
    export_parser.add_argument("--out", default="plan3_export.csv")
    export_parser.add_argument("--out-xlsx", default=None)
    export_parser.add_argument("--bitin", default=None)
    export_parser.add_argument("--produto", default=None)
    export_parser.add_argument("--motivo", default=None)
    export_parser.add_argument("--audit-report", default=None)

    return parser.parse_args()


def run_sync(args: argparse.Namespace) -> int:
    source_path = Path(args.file)
    if not source_path.exists():
        print("Arquivo não encontrado:", source_path)
        return 1

    config = load_config(Path(args.config))
    sheet_plan1 = args.sheet_plan1 or config["sheet_codenames"]["Plan1"]

    plan1_df = read_sheet(source_path, sheet_plan1)
    plan1_rows = read_plan1_rows(plan1_df, config)
    if not plan1_rows:
        print(f"Nenhuma linha de item encontrada em Plan1 ({sheet_plan1}).")
        return 1

    skipped: list[tuple[int, list[str]]] = []
    plan2_rows: list[dict[int, str]] = []
    start_row_plan1 = config["plan1_to_plan2"]["start_row_plan1"]
    for offset, row in enumerate(plan1_rows):
        errors = validate_plan1_row(row, config)
        if errors:
            skipped.append((start_row_plan1 + offset, errors))
            continue
        plan2_rows.append(sync_plan2_from_plan1(row, config))

    max_col = max(rule["plan2_col"] for rule in config["plan1_to_plan2"]["rules"])
    out_rows = [row_dict_to_list(row, max_col) for row in plan2_rows]
    header_row = [f"col{i}" for i in range(1, max_col + 1)]

    write_xlsx(Path(args.out_xlsx), header_row, out_rows)
    print(f"Gerou {args.out_xlsx} ({len(out_rows)} linhas, {len(skipped)} puladas)")
    return 0


def run_export(args: argparse.Namespace) -> int:
    source_path = Path(args.file)
    if not source_path.exists():
        print("Arquivo não encontrado:", source_path)
        return 1

    config = load_config(Path(args.config))
    sheet_plan2 = args.sheet_plan2 or config["sheet_codenames"]["Plan2"]

    plan2_df = read_sheet(source_path, sheet_plan2)
    plan2_rows = read_plan2_rows(plan2_df, config)
    if not plan2_rows:
        print(f"Nenhuma linha de item encontrada em Plan2 ({sheet_plan2}).")
        return 1

    bitin, produto, motivo = read_plan2_header(plan2_df, config)
    header_values = {
        "bitin": args.bitin if args.bitin is not None else bitin,
        "produto": args.produto if args.produto is not None else produto,
        "motivo": args.motivo if args.motivo is not None else motivo,
        "data": datetime.now().strftime(config["plan2_to_plan3"]["header"]["date_format"]),
    }

    quirk_counter: dict[int, int] = {}
    plan3_rows = [build_plan3_row(row, header_values, config, quirk_counter) for row in plan2_rows]

    max_col = max_plan3_col(config)
    out_rows = [row_dict_to_list(row, max_col) for row in plan3_rows]
    header_row = [f"col{i}" for i in range(1, max_col + 1)]

    out_csv = Path(args.out)
    write_csv(out_csv, header_row, out_rows)
    print(f"Gerou {out_csv} ({len(out_rows)} linhas)")

    if args.out_xlsx:
        write_xlsx(Path(args.out_xlsx), header_row, out_rows)
        print(f"Gerou {args.out_xlsx}")

    if args.audit_report:
        write_audit_report(Path(args.audit_report), len(plan2_rows), [], quirk_counter)
        print(f"Gerou relatório de auditoria: {args.audit_report}")

    return 0


def main() -> int:
    args = parse_args()
    if args.command == "sync":
        return run_sync(args)
    if args.command == "export":
        return run_export(args)
    raise ValueError(f"Comando desconhecido: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
