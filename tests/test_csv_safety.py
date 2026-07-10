import csv
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import csv_safety  # noqa: E402
import vba_port_export as vpe  # noqa: E402


class SanitizeCellTest(unittest.TestCase):
    def test_formula_prefixes_sao_escapados(self) -> None:
        self.assertEqual(csv_safety.sanitize_cell("=cmd|'/c calc'!A0"), "'=cmd|'/c calc'!A0")
        self.assertEqual(csv_safety.sanitize_cell("+1+1"), "'+1+1")
        self.assertEqual(csv_safety.sanitize_cell("@SUM(A1:A9)"), "'@SUM(A1:A9)")

    def test_hifen_nao_e_escapado(self) -> None:
        # Decisão deliberada: "-" é valor de domínio legítimo (códigos de Alt: "-", "-/P", "-/F").
        self.assertEqual(csv_safety.sanitize_cell("-/P"), "-/P")
        self.assertEqual(csv_safety.sanitize_cell("-"), "-")

    def test_texto_normal_nao_muda(self) -> None:
        self.assertEqual(csv_safety.sanitize_cell("Descrição normal"), "Descrição normal")
        self.assertEqual(csv_safety.sanitize_cell(""), "")

    def test_sanitize_row(self) -> None:
        self.assertEqual(
            csv_safety.sanitize_row(["OK", "=1+1", "-/P", ""]),
            ["OK", "'=1+1", "-/P", ""],
        )


class ExportSanitizationEndToEndTest(unittest.TestCase):
    """Prova que um valor 'malicioso' vindo do BITin (ex.: descrição digitada por um
    engenheiro começando com '=') sai sanitizado no CSV final do Winshuttle."""

    def test_descricao_com_formula_sai_sanitizada_no_export(self) -> None:
        config = vpe.load_config(ROOT / "config" / "vba_mapping.json")
        header_values = {"bitin": "P1/26", "produto": "x", "motivo": "x", "data": "10.07.2026"}
        plan2_row = {7: "=cmd|'/c calc'!A0"}  # Descrição Nova maliciosa

        quirks: dict[int, int] = {}
        plan3_row = vpe.build_plan3_row(plan2_row, header_values, config, quirks)
        max_col = vpe.max_plan3_col(config)
        row = vpe.row_dict_to_list(plan3_row, max_col)

        with tempfile.TemporaryDirectory() as tmp_dir:
            out_csv = Path(tmp_dir) / "out.csv"
            vpe.write_csv(out_csv, [f"col{i}" for i in range(1, max_col + 1)], [row])

            with out_csv.open(encoding="utf-8-sig") as fh:
                rows = list(csv.reader(fh))

        # Coluna 12 (DESCRIÇÃO) na linha de dados (índice 1, depois do cabeçalho).
        self.assertTrue(rows[1][11].startswith("'="))


if __name__ == "__main__":
    unittest.main()
