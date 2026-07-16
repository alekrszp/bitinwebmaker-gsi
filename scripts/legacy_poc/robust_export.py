#!/usr/bin/env python3
import argparse
from pathlib import Path

import pandas as pd


def export_sheet_as_winshuttle(file_path: Path, sheet: str, out_csv: Path, out_xlsx: Path | None = None):
    df = pd.read_excel(file_path, sheet_name=sheet, dtype=str, header=0, engine='openpyxl')
    # Normalize blank values to empty strings
    df = df.fillna('')
    # Drop trailing blank data rows where the first column is empty
    if df.shape[1] > 0:
        first_col = df.columns[0]
        df = df.loc[df[first_col].astype(str).str.strip() != '']
    df.to_csv(out_csv, index=False, encoding='utf-8-sig')
    if out_xlsx:
        df.to_excel(out_xlsx, index=False)
    return df


def main():
    parser = argparse.ArgumentParser(description='Exporta a sheet dados teste winshuttle para CSV/XLSX como no arquivo Winshuttle de referência.')
    parser.add_argument('file', help='Arquivo XLSM de entrada')
    parser.add_argument('--sheet', default='dados teste winshuttle', help='Nome da sheet de origem')
    parser.add_argument('--out', default='poc_winshuttle_export_robust.csv', help='Arquivo CSV de saída')
    parser.add_argument('--out-xlsx', default=None, help='Arquivo XLSX de saída (opcional)')
    args = parser.parse_args()

    src = Path(args.file)
    out_csv = Path(args.out)
    out_xlsx = Path(args.out_xlsx) if args.out_xlsx else out_csv.with_suffix('.xlsx')

    if not src.exists():
        raise SystemExit(f'Arquivo não encontrado: {src}')

    df = export_sheet_as_winshuttle(src, args.sheet, out_csv, out_xlsx)
    print(f'Wrote {out_csv} ({len(df)} rows)')
    if out_xlsx:
        print(f'Wrote {out_xlsx}')


if __name__ == '__main__':
    main()
