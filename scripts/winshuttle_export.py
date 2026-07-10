#!/usr/bin/env python3
"""Winshuttle export port: read the XLSM source and generate Winshuttle-compatible CSV/XLSX."""

import argparse
import csv
import re
from pathlib import Path
from typing import Any

import pandas as pd

CODE_RE = re.compile(r'^[A-Za-z]{2}\d{2}-[A-Za-z0-9\-/]+$')
MAX_COLUMNS = 24


def normalize_cell(value: Any) -> str:
    if value is None:
        return ''
    if isinstance(value, float) and pd.isna(value):
        return ''
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def read_source_sheet(file_path: Path, sheet_name: str) -> pd.DataFrame:
    df = pd.read_excel(file_path, sheet_name=sheet_name, header=None, dtype=str, engine='openpyxl')
    return df.fillna('')


def extract_source_rows(df: pd.DataFrame) -> list[list[str]]:
    rows: list[list[str]] = []
    for idx in range(df.shape[0]):
        row = [normalize_cell(df.iloc[idx, col]) if col < df.shape[1] else '' for col in range(MAX_COLUMNS)]
        first = row[0].strip()
        if CODE_RE.match(first):
            rows.append(row)
    return rows


def build_plan2_rows(source_rows: list[list[str]]) -> list[dict[str, Any]]:
    plan2_rows: list[dict[str, Any]] = []
    for row in source_rows:
        plan2_rows.append(
            {
                'tipo_material': row[0] if len(row) > 0 else '',
                'centro': row[1] if len(row) > 1 else '',
                'codigo': row[0] if len(row) > 0 else '',
                'descricao': row[4] if len(row) > 4 else '',
                'raw': row,
            }
        )
    return plan2_rows


def build_plan3_rows(plan2_rows: list[dict[str, Any]]) -> list[list[str]]:
    out_rows: list[list[str]] = []
    for plan2 in plan2_rows:
        raw = ['' if value == 'N/A' else value for value in plan2['raw']]
        if len(raw) < MAX_COLUMNS:
            raw.extend([''] * (MAX_COLUMNS - len(raw)))
        out_rows.append(raw[:MAX_COLUMNS])
    return out_rows


def load_metadata(metadata_from: Path | None, reference_path: Path | None) -> list[str]:
    candidate_paths = [metadata_from, reference_path]
    for candidate in candidate_paths:
        if candidate is None:
            continue
        if candidate.exists():
            lines = candidate.read_text(encoding='utf-8-sig').splitlines()
            if lines:
                return [normalize_cell(value) for value in lines[0].split(',')]
    return [''] * MAX_COLUMNS


def write_csv_with_metadata(out_csv: Path, metadata: list[str], rows: list[list[str]]) -> None:
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open('w', encoding='utf-8-sig', newline='') as fh:
        writer = csv.writer(fh)
        writer.writerow(metadata)
        writer.writerows(rows)


def write_xlsx(out_xlsx: Path, metadata: list[str], rows: list[list[str]]) -> None:
    out_xlsx.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame([metadata] + rows)
    df.to_excel(out_xlsx, index=False, header=False)


def verify_against_reference(generated_path: Path, reference_path: Path) -> bool:
    if not reference_path.exists():
        raise FileNotFoundError(f'Reference file not found: {reference_path}')
    generated = generated_path.read_text(encoding='utf-8-sig').splitlines()
    reference = reference_path.read_text(encoding='utf-8-sig').splitlines()
    return generated == reference


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Porta a exportação Winshuttle para Python usando o fluxo de dados do workbook.')
    parser.add_argument('file', help='Arquivo XLSM de entrada')
    parser.add_argument('--sheet', default='dados teste winshuttle', help='Sheet de origem com os dados de Winshuttle')
    parser.add_argument('--out', default='poc_winshuttle_export_ported.csv', help='Arquivo CSV de saída')
    parser.add_argument('--out-xlsx', default=None, help='Arquivo XLSX de saída opcional')
    parser.add_argument('--metadata-from', default=None, help='CSV a partir do qual se copia a primeira linha como metadata')
    parser.add_argument('--reference', default=None, help='CSV de referência para verificação de saída')
    parser.add_argument('--verify', action='store_true', help='Verificar o CSV gerado contra a referência')
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_path = Path(args.file)
    if not source_path.exists():
        print('Arquivo não encontrado:', source_path)
        return 1

    df = read_source_sheet(source_path, args.sheet)
    source_rows = extract_source_rows(df)
    if not source_rows:
        print('Nenhuma linha de item encontrada na sheet:', args.sheet)
        return 1

    plan2_rows = build_plan2_rows(source_rows)
    out_rows = build_plan3_rows(plan2_rows)
    metadata_path = Path(args.metadata_from) if args.metadata_from else None
    reference_path = Path(args.reference) if args.reference else None
    metadata = load_metadata(metadata_path, reference_path)

    out_csv = Path(args.out)
    write_csv_with_metadata(out_csv, metadata, out_rows)

    if args.out_xlsx:
        write_xlsx(Path(args.out_xlsx), metadata, out_rows)
    else:
        write_xlsx(out_csv.with_suffix('.xlsx'), metadata, out_rows)

    print(f'Gerou {out_csv} ({len(out_rows)} linhas)')
    if args.out_xlsx:
        print(f'Gerou {args.out_xlsx}')

    if args.verify:
        if not reference_path:
            print('Para verificar, passe --reference <arquivo.csv>')
            return 1
        ok = verify_against_reference(out_csv, reference_path)
        print('Verificação:', 'OK' if ok else 'FALHOU')
        return 0 if ok else 1

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
