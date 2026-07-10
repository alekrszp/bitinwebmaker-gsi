#!/usr/bin/env python3
import sys
import pandas as pd
from pathlib import Path

if len(sys.argv) < 4:
    print('Usage: dump_sheet.py <xlsm> <sheet_name> <rows> [out]')
    sys.exit(1)

file = sys.argv[1]
sheet = sys.argv[2]
rows = int(sys.argv[3])
out = sys.argv[4] if len(sys.argv) > 4 else 'docs/zbpp009_sample.md'

try:
    df = pd.read_excel(file, sheet_name=sheet, header=None, engine='openpyxl')
except Exception as e:
    print('Error reading sheet:', e)
    sys.exit(1)

sample = df.head(rows)
lines = []
lines.append(f'# Sample of sheet: {sheet}\n')
lines.append(f'File: {file}\n')
lines.append(f'Rows in sheet: {len(df)}\n')
lines.append('\n')
# write as CSV-like rows
cols = list(range(sample.shape[1]))
lines.append('| ' + ' | '.join([f'C{c+1}' for c in cols]) + ' |')
lines.append('| ' + ' | '.join(['---']*len(cols)) + ' |')
for idx in sample.index:
    row = sample.loc[idx].fillna('')
    row_vals = [str(row.iloc[c]) for c in cols]
    # escape pipe
    row_vals = [v.replace('|','\|') for v in row_vals]
    lines.append('| ' + ' | '.join(row_vals) + ' |')

p = Path(out)
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text('\n'.join(lines), encoding='utf-8')
print('Wrote', out)
