import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'winshuttle_export.py'
WORKBOOK = ROOT / 'Novo_template_BITin_V2 TESTE.xlsm'
REFERENCE = ROOT / 'exported_winshuttle.csv'

sys.path.insert(0, str(ROOT / 'scripts'))
from winshuttle_export import build_plan3_rows


class WinshuttleExportTest(unittest.TestCase):
    def test_normalizes_na_values_for_vba_like_output(self) -> None:
        plan2_rows = [{'raw': ['ABC', 'N/A', 'XYZ']}] 
        rows = build_plan3_rows(plan2_rows)

        self.assertEqual(rows[0][0], 'ABC')
        self.assertEqual(rows[0][1], '')
        self.assertEqual(rows[0][2], 'XYZ')

    def test_matches_reference_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            out_csv = tmp_path / 'generated.csv'
            out_xlsx = tmp_path / 'generated.xlsx'

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    str(WORKBOOK),
                    '--sheet',
                    'dados teste winshuttle',
                    '--out',
                    str(out_csv),
                    '--out-xlsx',
                    str(out_xlsx),
                    '--reference',
                    str(REFERENCE),
                    '--verify',
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, msg=completed.stdout + '\n' + completed.stderr)
            self.assertTrue(out_csv.exists())
            self.assertEqual(
                out_csv.read_text(encoding='utf-8-sig').splitlines(),
                REFERENCE.read_text(encoding='utf-8-sig').splitlines(),
            )


if __name__ == '__main__':
    unittest.main()
