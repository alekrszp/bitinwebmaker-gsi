#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

# Ensure local scripts/ directory can be imported when running directly
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from export_from_itemsheet import export_items  # noqa: E402 -- precisa vir depois do sys.path.insert acima


def read_lines(path: Path):
    return path.read_text(encoding='utf-8-sig').splitlines()


def compare_files(a: Path, b: Path):
    sa = read_lines(a)
    sb = read_lines(b)
    return sa == sb, sa, sb


def write_diff_report(a: Path, b: Path, out: Path, sa: list[str], sb: list[str]):
    out.parent.mkdir(parents=True, exist_ok=True)
    set_a = set(sa)
    set_b = set(sb)
    only_a = sorted(set_a - set_b)
    only_b = sorted(set_b - set_a)
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
    return len(only_a) == 0 and len(only_b) == 0


def main():
    parser = argparse.ArgumentParser(description='Exporta e valida o PoC de Winshuttle contra um CSV de referência.')
    parser.add_argument('file', nargs='?', default='Novo_template_BITin_V2 TESTE.xlsm')
    parser.add_argument('--sheet', default='dados teste winshuttle')
    parser.add_argument('--out', default='poc_winshuttle_export_full.csv')
    parser.add_argument('--metadata-from', default='exported_winshuttle.csv')
    parser.add_argument('--out-with-meta', default='poc_winshuttle_export_full_with_meta.csv')
    parser.add_argument('--reference', default='exported_winshuttle.csv')
    parser.add_argument('--report', default='reports/diff_report.txt')
    args = parser.parse_args()

    template_path = Path(args.file)
    if not template_path.exists():
        raise SystemExit(f'File not found: {template_path}')

    rc = export_items(str(template_path), sheet=args.sheet, out_csv=args.out, metadata_from=args.metadata_from, out_with_meta=args.out_with_meta)
    if rc != 0:
        raise SystemExit(rc)

    actual_path = Path(args.out_with_meta)
    reference_path = Path(args.reference)
    if not actual_path.exists():
        raise SystemExit(f'Output with metadata not found: {actual_path}')
    if not reference_path.exists():
        raise SystemExit(f'Reference file not found: {reference_path}')

    identical, sa, sb = compare_files(actual_path, reference_path)
    if identical:
        print('Success: generated file matches reference exactly.')
    else:
        print('Mismatch: generated file differs from reference.')
    if write_diff_report(actual_path, reference_path, Path(args.report), sa, sb):
        print(f'Diff report written to {args.report} (no set differences found)')
    else:
        print(f'Diff report written to {args.report} (differences found)')
    raise SystemExit(0 if identical else 1)


if __name__ == '__main__':
    main()
