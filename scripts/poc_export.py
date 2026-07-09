#!/usr/bin/env python3
"""PoC exporter: monta Plan2 a partir da aba fonte e gera CSV/XLSX compatível com Winshuttle.

Uso:
  python scripts/poc_export.py Novo_template_BITin_V2\ TESTE.xlsm --source-sheet Planilha1 --out poc_winshuttle_export.csv
"""
import argparse
import pandas as pd
from pathlib import Path


# mapping: plan2_col_index (1-based) -> plan1_col_index (1-based)
PLAN1_TO_PLAN2 = {
    3: 1,
    4: 4,
    5: 2,
    6: 5,
    8: 6,
    10:7,
    12:8,
    14:9,
    16:10,
    18:11,
    20:12,
    22:13,
    24:14,
    26:15,
    28:16,
    30:17,
    32:18,
    34:19,
    36:20,
    38:21,
    40:22,
    42:23,
    44:24,
    46:25,
    48:26,
    50:27,
    52:28,
    54:29,
    56:30,
    58:31,
    60:32,
    62:33,
    64:34,
    66:35,
    68:36,
}


FIELDS = [
    ("BITIN", (1,2)),
    ("Produto", (2,2)),
    ("Motivo", (3,2)),
    ("Date", None),
    ("TipoMaterial", (None,3)),
    ("Centro", (None,4)),
    ("Codigo", (None,5)),
    ("Descricao", (None,6)),
    ("NCM", (None,40)),
]


def build_plan2(df_plan1):
    # df_plan1: pandas DF read with header=None, rows starting at index 1 (row 2 in Excel)
    rows = []
    # iterate rows until first column (col 0) empty
    for idx in range(len(df_plan1)):
        # Módulo1 starts reading at Linha1 = 2 (1-based) -> index 1
        # but caller may pass trimmed df; we'll just process all rows where col0 not null
        row = df_plan1.iloc[idx]
        if pd.isna(row.iloc[0]):
            continue
        plan2_row = {}
        # populate using mapping
        for p2_col, p1_col in PLAN1_TO_PLAN2.items():
            val = None
            # convert to zero-based
            p1_idx = p1_col - 1
            if p1_idx < len(row):
                val = row.iloc[p1_idx]
            plan2_row[f"c{p2_col}"] = val
        rows.append(plan2_row)
    return pd.DataFrame(rows)


def export_outputs(plan2_df, source_df, out_csv, out_xlsx):
    # derive header values
    bitin = None
    try:
        bitin = source_df.iloc[0,1]
    except Exception:
        bitin = ''
    produto = ''
    motivo = ''
    try:
        produto = source_df.iloc[1,1]
        motivo = source_df.iloc[2,1]
    except Exception:
        pass

    rows = []
    from datetime import datetime
    date_str = datetime.now().strftime('%d.%m.%Y')
    for _, r in plan2_df.iterrows():
        # stop condition in VBA is column 3 empty (plan2 col 3)
        if pd.isna(r.get('c3')):
            continue
        out = {
            'BITIN': bitin,
            'Produto': produto,
            'Motivo': motivo,
            'Date': date_str,
            'TipoMaterial': r.get('c3'),
            'Centro': r.get('c4'),
            'Codigo': r.get('c5'),
            'Descricao': r.get('c6'),
            'NCM': r.get('c40'),
        }
        rows.append(out)

    df_out = pd.DataFrame(rows)
    df_out.to_csv(out_csv, index=False, encoding='utf-8-sig')
    df_out.to_excel(out_xlsx, index=False)
    print(f'Wrote {out_csv} and {out_xlsx} ({len(df_out)} rows)')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('file')
    parser.add_argument('--source-sheet', default='Planilha1')
    parser.add_argument('--out', default='poc_winshuttle_export.csv')
    parser.add_argument('--align-with', default=None, help='CSV file to align column count with')
    parser.add_argument('--full-extract', action='store_true', help='Extract full item rows (first 24 columns) from item sheet')
    args = parser.parse_args()

    src = Path(args.file)
    if not src.exists():
        print('File not found:', args.file)
        raise SystemExit(1)

    # read source sheet without header; if empty, try common alternative sheets
    try:
        df_src = pd.read_excel(src, sheet_name=args.source_sheet, header=None, engine='openpyxl')
    except Exception:
        df_src = pd.DataFrame()

    plan2 = build_plan2(df_src) if not df_src.empty else pd.DataFrame()
    if plan2.shape[0] == 0:
        candidates = ['Planilha1', 'Plan1', 'ZBPP009 + ALTERACAO', 'ZBPP009', 'Plan2', 'Dados', 'ZBPP009', 'Formulário Winshuttle']
        for s in candidates:
            try:
                df_try = pd.read_excel(src, sheet_name=s, header=None, engine='openpyxl')
            except Exception:
                continue
            # prefer sheets where first column has non-null values
            if df_try.shape[0] == 0:
                continue
            if df_try.iloc[:,0].notna().sum() > 0:
                print(f'Auto-selected source sheet: {s}')
                df_src = df_try
                plan2 = build_plan2(df_src)
                break
    out_csv = args.out
    out_xlsx = Path(out_csv).with_suffix('.xlsx')

    if args.align_with:
        # read target to get column count
        target = Path(args.align_with)
        if not target.exists():
            print('Align target not found:', args.align_with)
            raise SystemExit(1)
        first = target.read_text(encoding='utf-8-sig').splitlines()[0]
        ncols = len(first.split(','))
        rows = []
        for _, r in plan2.iterrows():
            if pd.isna(r.get('c3')):
                continue
            row = [''] * ncols
            # place Codigo in col0, Centro in col1, Descricao in col7 if available
            row[0] = '' if pd.isna(r.get('c5')) else str(r.get('c5'))
            if ncols > 1:
                row[1] = '' if pd.isna(r.get('c4')) else str(r.get('c4'))
            if ncols > 7:
                row[7] = '' if pd.isna(r.get('c6')) else str(r.get('c6'))
            rows.append(row)
        # write aligned CSV
        import csv
        with open(out_csv, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            for r in rows:
                writer.writerow(r)
        print(f'Wrote aligned {out_csv} ({len(rows)} rows, cols={ncols})')
        # also write xlsx
        import pandas as _pd
        df_al = _pd.DataFrame(rows)
        df_al.to_excel(str(out_xlsx), index=False, header=False)
        raise SystemExit(0)
    if args.full_extract:
        # try common item sheets
        candidates = ['ZBPP009 + ALTERACAO', 'Plan2', 'ZBPP009', 'dados teste winshuttle']
        src_sheet = None
        for s in candidates:
            try:
                df_try = pd.read_excel(src, sheet_name=s, header=None, engine='openpyxl')
            except Exception:
                continue
            if df_try.shape[0] == 0:
                continue
            # choose sheet where many rows have non-empty first col
            if df_try.iloc[:,0].notna().sum() > 0:
                src_sheet = s
                df_items = df_try
                break
        if src_sheet is None:
            print('No suitable item sheet found for full extract')
            raise SystemExit(1)
        print('Full extract from sheet:', src_sheet)
        ncols = 24
        rows = []
        import re
        code_re = re.compile(r'^[A-Za-z0-9\-_/]+$')
        # find start of item block: look for first row where any of probable item cols is non-empty
        cols_to_check = [4, 2, 0, 6]  # prefer column 5 (index 4), fallback to others
        start_idx = None
        for i in range(df_items.shape[0]):
            row = df_items.iloc[i]
            for c in cols_to_check:
                if c < len(row) and not pd.isna(row.iloc[c]) and str(row.iloc[c]).strip() != '':
                    # skip obvious header words
                    sval = str(row.iloc[c]).strip().lower()
                    if sval in ('codigo', 'código', 'n°', 'n', 'cod', 'tipo'):
                        continue
                    start_idx = i
                    break
            if start_idx is not None:
                break

        if start_idx is None:
            # fallback: scan for any non-empty in first column
            for i in range(df_items.shape[0]):
                if str(df_items.iloc[i,0]).strip() != '':
                    start_idx = i
                    break

        if start_idx is None:
            print('No item rows detected in', src_sheet)
            raise SystemExit(1)

        # collect contiguous block until many empty rows
        consecutive_empty = 0
        max_consecutive = 10
        for i in range(start_idx, df_items.shape[0]):
            row = df_items.iloc[i]
            if all((c >= len(row) or pd.isna(row.iloc[c]) or str(row.iloc[c]).strip() == '') for c in cols_to_check):
                consecutive_empty += 1
                if consecutive_empty >= max_consecutive:
                    break
                else:
                    continue
            consecutive_empty = 0
            out_row = []
            for c in range(ncols):
                val = ''
                if c < len(row):
                    val = row.iloc[c]
                out_row.append('' if pd.isna(val) else str(val))
            rows.append(out_row)

        import csv
        with open(out_csv, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            for r in rows:
                writer.writerow(r)
        print(f'Wrote full extract {out_csv} ({len(rows)} rows, cols={ncols})')
        # write xlsx
        pd.DataFrame(rows).to_excel(str(out_xlsx), index=False, header=False)
        raise SystemExit(0)

    export_outputs(plan2, df_src, out_csv, str(out_xlsx))


if __name__ == '__main__':
    main()
