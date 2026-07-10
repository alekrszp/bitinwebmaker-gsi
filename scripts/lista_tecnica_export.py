#!/usr/bin/env python3
"""Export de lista técnica (CS02/BOM) a partir do BITin.

Diferente do fluxo Módulo1/Módulo2 (MM02), a alteração de lista técnica nunca teve
automação em VBA — a aba real "Lista técnica" é preenchida manualmente, direto no
formato final do Winshuttle. Este módulo gera essa aba a partir de
materiais[].alteracoes.lista_tecnica[] do BITin. Ver docs/BITIN_MODEL.md, seção
"Export de lista_tecnica[]".

Cada item de lista_tecnica[] tem um campo 'operacao' (inserir/alterar/excluir, default
alterar) -- cobre tanto alteração de quantidade quanto troca de componente (um item
'excluir' pro código antigo + um item 'inserir' pro novo).
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

import csv_safety
from bitin_errors import BitinError, make_error


@lru_cache(maxsize=None)
def load_config(config_path: Path) -> dict[str, Any]:
    return json.loads(config_path.read_text(encoding="utf-8"))


OPERACOES_VALIDAS = {"inserir", "alterar", "excluir"}


def validate_lista_tecnica(bitin: dict[str, Any]) -> list[BitinError]:
    errors: list[BitinError] = []
    for m_idx, material in enumerate(bitin.get("materiais", [])):
        itens = material.get("alteracoes", {}).get("lista_tecnica", [])
        for i_idx, item in enumerate(itens):
            base_field = f"materiais[{m_idx}].alteracoes.lista_tecnica[{i_idx}]"
            prefix = base_field
            operacao = item.get("operacao", "alterar")

            if operacao not in OPERACOES_VALIDAS:
                errors.append(make_error(
                    f"{base_field}.operacao", "invalid_operacao_value",
                    f"{prefix}: operacao inválida: {operacao!r} (use inserir/alterar/excluir)",
                ))
            if not item.get("codigo_filho"):
                errors.append(make_error(
                    f"{base_field}.codigo_filho", "required_field_missing",
                    f"{prefix}: campo obrigatório vazio: codigo_filho",
                ))
            if operacao in ("inserir", "alterar") and not item.get("quantidade_para"):
                errors.append(make_error(
                    f"{base_field}.quantidade_para", "required_field_missing",
                    f"{prefix}: campo obrigatório vazio: quantidade_para (operacao={operacao})",
                ))
            if operacao == "excluir" and not item.get("quantidade_de"):
                errors.append(make_error(
                    f"{base_field}.quantidade_de", "required_field_missing",
                    f"{prefix}: campo obrigatório vazio: quantidade_de (operacao=excluir)",
                ))
    return errors


def bitin_to_lista_tecnica_rows(bitin: dict[str, Any], config: dict[str, Any]) -> list[list[str]]:
    numero_bitin = bitin.get("bitin", "")
    stlan = config["stlan_default"]

    rows: list[list[str]] = []
    for material in bitin.get("materiais", []):
        codigo_material = material.get("codigo_material", "")
        centro = material.get("centro", "")
        itens = material.get("alteracoes", {}).get("lista_tecnica", [])
        for item in itens:
            operacao = item.get("operacao", "alterar")
            quantidade = item.get("quantidade_de", "") if operacao == "excluir" else item.get("quantidade_para", "")
            rows.append(
                [
                    codigo_material,
                    centro,
                    stlan,
                    numero_bitin,
                    item.get("codigo_filho", ""),
                    quantidade,
                    "X" if operacao == "inserir" else "",
                    "X" if operacao == "alterar" else "",
                    "X" if operacao == "excluir" else "",
                ]
            )
    return rows


def write_lista_tecnica_xlsx(bitin: dict[str, Any], config: dict[str, Any], out_path: Path) -> None:
    rows = [csv_safety.sanitize_row(row) for row in bitin_to_lista_tecnica_rows(bitin, config)]
    matrix = [config["column_headers"]] + rows
    sheet_name = config["sheet_name"]
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(matrix)
    df.to_excel(out_path, index=False, header=False, sheet_name=sheet_name, engine="openpyxl")


def write_lista_tecnica_csv(bitin: dict[str, Any], config: dict[str, Any], out_path: Path) -> None:
    import csv

    rows = bitin_to_lista_tecnica_rows(bitin, config)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(config["column_headers"])
        writer.writerows(csv_safety.sanitize_row(row) for row in rows)


def parse_args():
    import argparse

    parser = argparse.ArgumentParser(
        description="Gera o export de lista técnica (CS02/BOM) a partir do JSON do BITin."
    )
    parser.add_argument("bitin_json", help="Arquivo JSON do BITin (ver docs/BITIN_MODEL.md)")
    parser.add_argument("--config", default="config/lista_tecnica_mapping.json")
    parser.add_argument("--out-csv", default=None)
    parser.add_argument("--out-xlsx", default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config(Path(args.config))
    bitin = json.loads(Path(args.bitin_json).read_text(encoding="utf-8"))

    errors = validate_lista_tecnica(bitin)
    if errors:
        print(f"Lista técnica inválida ({len(errors)} erro(s)):")
        for error in errors:
            print(f"  - {error}")
        return 1

    rows = bitin_to_lista_tecnica_rows(bitin, config)
    print(f"{len(rows)} linha(s) de alteração de lista técnica.")

    if args.out_csv:
        write_lista_tecnica_csv(bitin, config, Path(args.out_csv))
        print(f"Gerou {args.out_csv}")
    if args.out_xlsx:
        write_lista_tecnica_xlsx(bitin, config, Path(args.out_xlsx))
        print(f"Gerou {args.out_xlsx}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
