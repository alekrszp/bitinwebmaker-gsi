#!/usr/bin/env python3
"""PoC: exporta a sheet de 'dados teste winshuttle' ou 'Formulário Winshuttle' para CSV.

Uso:
  python scripts/export_winshuttle_csv.py "Novo_template_BITin_V2 TESTE.xlsm" --sheet "dados teste winshuttle" --out exported.csv
"""
import argparse
import pandas as pd


def export_sheet(path, sheet_name, out_csv):
    try:
        df = pd.read_excel(path, sheet_name=sheet_name, engine='openpyxl')
    except Exception as e:
        print('Erro ao ler sheet:', e)
        return 1
    df.to_csv(out_csv, index=False, encoding='utf-8-sig')
    print(f'Wrote {out_csv} ({len(df)} rows)')
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('file')
    parser.add_argument('--sheet', '-s', default='dados teste winshuttle')
    parser.add_argument('--out', '-o', default='exported_winshuttle.csv')
    args = parser.parse_args()
    return_code = export_sheet(args.file, args.sheet, args.out)
    raise SystemExit(return_code)


if __name__ == '__main__':
    main()
