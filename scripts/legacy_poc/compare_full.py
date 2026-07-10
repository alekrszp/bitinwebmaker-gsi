from pathlib import Path
A=Path('poc_winshuttle_export_full.csv')
B=Path('exported_winshuttle.csv')
sa=A.read_text(encoding='utf-8-sig').splitlines()
sb=B.read_text(encoding='utf-8-sig').splitlines()
print('full aligned lines:', len(sa))
print('exported lines:', len(sb))
set_a=set(sa)
set_b=set(sb)
only_a=sorted(list(set_a-set_b))
only_b=sorted(list(set_b-set_a))
print('\nOnly in full aligned (sample up to 10):')
for x in only_a[:10]:
    print('-', x)
print('\nOnly in exported (sample up to 10):')
for x in only_b[:10]:
    print('-', x)
