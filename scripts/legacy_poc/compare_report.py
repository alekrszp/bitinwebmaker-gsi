from pathlib import Path
import sys

def read_lines(p: Path):
    return p.read_text(encoding='utf-8-sig').splitlines()

def main():
    a = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('poc_winshuttle_export_full_with_meta.csv')
    b = Path(sys.argv[2]) if len(sys.argv) > 2 else Path('exported_winshuttle.csv')
    out = Path(sys.argv[3]) if len(sys.argv) > 3 else Path('reports/diff_report.txt')
    out.parent.mkdir(parents=True, exist_ok=True)

    sa = read_lines(a)
    sb = read_lines(b)

    set_a = set(sa)
    set_b = set(sb)
    only_a = sorted(list(set_a - set_b))
    only_b = sorted(list(set_b - set_a))

    with out.open('w', encoding='utf-8') as fh:
        fh.write(f'A: {a}\n')
        fh.write(f'B: {b}\n')
        fh.write(f'lines A: {len(sa)}\n')
        fh.write(f'lines B: {len(sb)}\n')
        fh.write('\nOnly in A (sample up to 50):\n')
        for x in only_a[:50]:
            fh.write(x + '\n')
        fh.write('\nOnly in B (sample up to 50):\n')
        for x in only_b[:50]:
            fh.write(x + '\n')

    print('Wrote report to', out)
    print('A lines:', len(sa), 'B lines:', len(sb))
    print('Only in A:', len(only_a), 'Only in B:', len(only_b))

if __name__ == '__main__':
    main()
