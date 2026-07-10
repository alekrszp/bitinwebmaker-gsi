import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import lista_tecnica_export as lte  # noqa: E402

CONFIG_PATH = ROOT / "config" / "lista_tecnica_mapping.json"


def make_bitin_with_lista_tecnica(**overrides) -> dict:
    base = {
        "bitin": "P3301/26",
        "produto": "Silo X",
        "motivo": "Ajuste de lista técnica",
        "materiais": [
            {
                "codigo_material": "S2048-102AAB",
                "centro": "2005",
                "alteracoes": {
                    "lista_tecnica": [
                        {
                            "codigo_filho": "S2048-122264",
                            "descricao_filho": "Componente teste",
                            "quantidade_de": "1",
                            "quantidade_para": "2",
                        }
                    ]
                },
            }
        ],
    }
    base.update(overrides)
    return base


class ValidateListaTecnicaTest(unittest.TestCase):
    def test_valid_has_no_errors(self) -> None:
        self.assertEqual(lte.validate_lista_tecnica(make_bitin_with_lista_tecnica()), [])

    def test_missing_codigo_filho(self) -> None:
        bitin = make_bitin_with_lista_tecnica()
        del bitin["materiais"][0]["alteracoes"]["lista_tecnica"][0]["codigo_filho"]
        errors = lte.validate_lista_tecnica(bitin)
        self.assertTrue(any("codigo_filho" in e["message"] for e in errors))

    def test_missing_quantidade_para(self) -> None:
        bitin = make_bitin_with_lista_tecnica()
        del bitin["materiais"][0]["alteracoes"]["lista_tecnica"][0]["quantidade_para"]
        errors = lte.validate_lista_tecnica(bitin)
        self.assertTrue(any("quantidade_para" in e["message"] for e in errors))

    def test_no_lista_tecnica_no_errors(self) -> None:
        bitin = make_bitin_with_lista_tecnica()
        bitin["materiais"][0]["alteracoes"] = {}
        self.assertEqual(lte.validate_lista_tecnica(bitin), [])

    def test_excluir_requires_quantidade_de_not_para(self) -> None:
        bitin = make_bitin_with_lista_tecnica()
        bitin["materiais"][0]["alteracoes"]["lista_tecnica"][0] = {
            "operacao": "excluir", "codigo_filho": "X1",
        }
        errors = lte.validate_lista_tecnica(bitin)
        self.assertTrue(any("quantidade_de" in e["message"] for e in errors))

    def test_invalid_operacao(self) -> None:
        bitin = make_bitin_with_lista_tecnica()
        bitin["materiais"][0]["alteracoes"]["lista_tecnica"][0]["operacao"] = "trocar"
        errors = lte.validate_lista_tecnica(bitin)
        self.assertTrue(any("operacao inválida" in e["message"] for e in errors))


class BitinToListaTecnicaRowsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = lte.load_config(CONFIG_PATH)

    def test_row_shape_matches_real_column_layout(self) -> None:
        rows = lte.bitin_to_lista_tecnica_rows(make_bitin_with_lista_tecnica(), self.config)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        # [material pai, centro, STLAN, nº modificação, componente filho, quantidade, INSERIR, ALTERAR, EXCLUIR]
        self.assertEqual(
            row,
            ["S2048-102AAB", "2005", "5", "P3301/26", "S2048-122264", "2", "", "X", ""],
        )

    def test_multiple_materiais_and_multiple_itens(self) -> None:
        bitin = make_bitin_with_lista_tecnica()
        bitin["materiais"].append(
            {
                "codigo_material": "S2048-112AAB",
                "centro": "2005",
                "alteracoes": {
                    "lista_tecnica": [
                        {"codigo_filho": "S2048-122264", "quantidade_de": "1", "quantidade_para": "3"},
                        {"codigo_filho": "S2048-999999", "quantidade_de": "0", "quantidade_para": "1"},
                    ]
                },
            }
        )
        rows = lte.bitin_to_lista_tecnica_rows(bitin, self.config)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[1][0], "S2048-112AAB")
        self.assertEqual(rows[1][4], "S2048-122264")
        self.assertEqual(rows[2][4], "S2048-999999")

    def test_material_sem_lista_tecnica_nao_gera_linha(self) -> None:
        bitin = make_bitin_with_lista_tecnica()
        bitin["materiais"][0]["alteracoes"] = {}
        rows = lte.bitin_to_lista_tecnica_rows(bitin, self.config)
        self.assertEqual(rows, [])

    def test_troca_de_componente_replica_exemplo_real(self) -> None:
        """Reconstrói o caso real observado em bitin teste 2.xlsm (aba Lista técnica,
        BITin histórico A0618/23): troca do componente S2048-122264 (qtd 1) pelo
        S2048-122232 (qtd 2), no material pai S2048-102AAB, centro 2005."""
        bitin = {
            "bitin": "A0618/23",
            "produto": "x",
            "motivo": "x",
            "materiais": [
                {
                    "codigo_material": "S2048-102AAB",
                    "centro": "2005",
                    "alteracoes": {
                        "lista_tecnica": [
                            {"operacao": "excluir", "codigo_filho": "S2048-122264", "quantidade_de": "1"},
                            {"operacao": "inserir", "codigo_filho": "S2048-122232", "quantidade_para": "2"},
                        ]
                    },
                }
            ],
        }
        self.assertEqual(lte.validate_lista_tecnica(bitin), [])
        rows = lte.bitin_to_lista_tecnica_rows(bitin, self.config)

        self.assertEqual(
            rows[0],
            ["S2048-102AAB", "2005", "5", "A0618/23", "S2048-122264", "1", "", "", "X"],
        )
        self.assertEqual(
            rows[1],
            ["S2048-102AAB", "2005", "5", "A0618/23", "S2048-122232", "2", "X", "", ""],
        )


class WriteListaTecnicaXlsxTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = lte.load_config(CONFIG_PATH)
        self.bitin = make_bitin_with_lista_tecnica()

    def test_generated_xlsx_matches_expected_layout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_path = Path(tmp_dir) / "lista_tecnica.xlsx"
            lte.write_lista_tecnica_xlsx(self.bitin, self.config, out_path)

            df = pd.read_excel(
                out_path, sheet_name=self.config["sheet_name"], header=None, dtype=str,
                engine="openpyxl", keep_default_na=False,
            )

        self.assertEqual(df.iloc[0].tolist(), self.config["column_headers"])
        self.assertEqual(
            df.iloc[1].tolist(),
            ["S2048-102AAB", "2005", "5", "P3301/26", "S2048-122264", "2", "", "X", ""],
        )


if __name__ == "__main__":
    unittest.main()
