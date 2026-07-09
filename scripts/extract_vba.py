#!/usr/bin/env python3
"""Extrai módulos VBA de um arquivo .xlsm usando oletools (olevba).

Se oletools não estiver instalado, instrui como instalar.
"""
import argparse
import os


def extract_with_olevba(path, outdir):
    try:
        from oletools.olevba import VBA_Parser
    except Exception as e:
        print('oletools não está instalado. Instale com: pip install oletools')
        raise

    parser = VBA_Parser(path)
    if not os.path.exists(outdir):
        os.makedirs(outdir, exist_ok=True)

    for (subfile, stream_path, vba_filename, vba_code) in parser.extract_macros():
        safe_name = vba_filename or stream_path.replace('/', '_')
        out_path = os.path.join(outdir, safe_name)
        with open(out_path, 'w', encoding='utf-8', errors='replace') as f:
            f.write(vba_code)
        print('Wrote', out_path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('file')
    parser.add_argument('--outdir', '-o', default='artifacts/vba')
    args = parser.parse_args()
    extract_with_olevba(args.file, args.outdir)


if __name__ == '__main__':
    main()
