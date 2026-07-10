import sys
from pathlib import Path

a = Path('poc_winshuttle_export.csv')
b = Path('exported_winshuttle.csv')
if not a.exists() or not b.exists():
    print('Missing file(s)')
    sys.exit(1)

a_lines = a.read_text(encoding='utf-8-sig').splitlines()
b_lines = b.read_text(encoding='utf-8-sig').splitlines()

print('poc lines:', len(a_lines))
print('exported lines:', len(b_lines))
print('poc header:', a_lines[0] if a_lines else '')
print('exported first row:', b_lines[0] if b_lines else '')

set_a = set(a_lines[1:])
set_b = set(b_lines[1:])
only_a = sorted(set_a - set_b)
only_b = sorted(set_b - set_a)
print('\nOnly in poc (sample up to 10):')
for x in only_a[:10]:
    print('-', x)
print('\nOnly in exported (sample up to 10):')
for x in only_b[:10]:
    print('-', x)

# compare columns by splitting first lines
poc_cols = [c.strip() for c in a_lines[0].split(',')] if a_lines else []
export_cols = [c.strip() for c in b_lines[0].split(',')] if b_lines else []
print('\npoc columns count:', len(poc_cols))
print('exported columns count (inferred):', len(export_cols))
print('poc columns:', poc_cols)
print('exported inferred columns sample:', export_cols[:10])
