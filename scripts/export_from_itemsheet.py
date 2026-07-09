#!/usr/bin/env python3
import re
import pandas as pd
from pathlib import Path

CODE_RE = re.compile(r'^[A-Za-z]{2}\d{2}-[A-Za-z0-9\-/]+$')


def export_items(file, sheet='dados teste winshuttle', out_csv='poc_winshuttle_export_full.csv', metadata_from=None, out_with_meta=None):
    df = pd.read_excel(file, sheet_name=sheet, header=None, engine='openpyxl')
    rows = []
    for i in range(df.shape[0]):
        first = str(df.iloc[i,0]).strip() if df.shape[1] > 0 else ''
        if CODE_RE.match(first):
            # take first 24 columns
            vals = []
            for c in range(24):
                if c < df.shape[1]:
                    v = df.iloc[i,c]
                    vals.append('' if pd.isna(v) else str(v))
                else:
                    vals.append('')
            rows.append(vals)
    if not rows:
        print('No item rows matched in', sheet)
        return 1
    # write base CSV/XLSX
    Path(out_csv).write_text('\n'.join([','.join(r) for r in rows]), encoding='utf-8-sig')
    pd.DataFrame(rows).to_excel(Path(out_csv).with_suffix('.xlsx'), index=False, header=False)
    print('Wrote', out_csv, 'rows=', len(rows))

    # if metadata source provided, prepend its first line
    if metadata_from:
        meta_path = Path(metadata_from)
        if meta_path.exists():
            meta_first = meta_path.read_text(encoding='utf-8-sig').splitlines()[0]
            out_with_meta = out_with_meta or Path(out_csv).with_name(Path(out_csv).stem + '_with_meta.csv')
            # write new CSV with metadata first
            with open(out_with_meta, 'w', encoding='utf-8-sig', newline='') as f:
                f.write(meta_first + '\n')
                f.write('\n'.join([','.join(r) for r in rows]))
            # also write xlsx including metadata as first row
            df_meta = pd.DataFrame([meta_first.split(',')])
            df_rows = pd.DataFrame(rows)
            df_combined = pd.concat([df_meta, df_rows], ignore_index=True)
            out_xlsx = Path(out_with_meta).with_suffix('.xlsx')
            df_combined.to_excel(out_xlsx, index=False, header=False)
            print('Wrote', out_with_meta, 'and', out_xlsx)
        else:
            print('metadata_from not found:', metadata_from)
    return 0


if __name__ == '__main__':
    import sys
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('file')
    parser.add_argument('--sheet', default='dados teste winshuttle')
    parser.add_argument('--out', default='poc_winshuttle_export_full.csv')
    parser.add_argument('--metadata-from', default=None, help='CSV file to take metadata (first line) from')
    parser.add_argument('--out-with-meta', default=None, help='Output CSV path including metadata as first line')
    args = parser.parse_args()
    export_items(args.file, sheet=args.sheet, out_csv=args.out, metadata_from=args.metadata_from, out_with_meta=args.out_with_meta)
