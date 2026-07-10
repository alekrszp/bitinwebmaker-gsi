import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import vba_port_export as vpe  # noqa: E402

CONFIG_PATH = ROOT / "config" / "vba_mapping.json"


class SyncPlan2FromPlan1Test(unittest.TestCase):
    def setUp(self) -> None:
        self.config = vpe.load_config(CONFIG_PATH)

    def test_direct_and_constant_rules(self) -> None:
        plan1_row = {
            1: "MP", 2: "COD123", 4: "1010", 5: "Descrição atual",
            17: "SUB1", 18: "BLOQ1", 19: "DATA1", 22: "COMP1", 23: "GC1",
            26: "TIPOSUP1", 31: "PERFIL1", 36: "MARC1",
        }
        plan2 = vpe.sync_plan2_from_plan1(plan1_row, self.config)

        self.assertEqual(plan2[3], "MP")
        self.assertEqual(plan2[4], "1010")
        self.assertEqual(plan2[5], "COD123")
        self.assertEqual(plan2[6], "Descrição atual")
        self.assertEqual(plan2[30], "SUB1")
        self.assertEqual(plan2[31], "N/A")  # placeholder "Novo" inicial
        self.assertEqual(plan2[32], "BLOQ1")
        self.assertEqual(plan2[33], "N/A")
        self.assertEqual(plan2[68], "MARC1")

    def test_validate_plan1_row_missing_required_fields(self) -> None:
        errors = vpe.validate_plan1_row({}, self.config)
        self.assertEqual(len(errors), 2)
        self.assertTrue(any("TIPO DO MATERIAL" in e for e in errors))
        self.assertTrue(any("CÓDIGO" in e for e in errors))

    def test_validate_plan1_row_ok(self) -> None:
        errors = vpe.validate_plan1_row({1: "MP", 2: "COD1"}, self.config)
        self.assertEqual(errors, [])


class BuildPlan3RowTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = vpe.load_config(CONFIG_PATH)
        self.header = {"bitin": "P330122", "produto": "Silo X", "motivo": "SPN", "data": "09.07.2026"}

    def build(self, plan2_overrides: dict[int, str]) -> tuple[dict[int, str], dict[int, int]]:
        quirks: dict[int, int] = {}
        row = vpe.build_plan3_row(plan2_overrides, self.header, self.config, quirks)
        return row, quirks

    def test_header_and_constant_fields(self) -> None:
        row, _ = self.build({3: "MP", 4: "1010", 5: "COD1"})
        self.assertEqual(row[1], "P330122")
        self.assertEqual(row[2], "Silo X")
        self.assertEqual(row[3], "SPN")
        self.assertEqual(row[4], "09.07.2026")
        self.assertEqual(row[6], "SIM")
        self.assertEqual(row[10], "1010")
        self.assertEqual(row[9], "COD1")

    def test_quirk1_tipo_material_written_to_col106(self) -> None:
        row, quirks = self.build({3: "MP"})
        self.assertEqual(row[106], "MP")
        self.assertEqual(quirks.get(1, 0), 1)

    def test_flag_if_nonempty_descricao_nova_preenchida(self) -> None:
        row, _ = self.build({7: "Descrição nova do engenheiro"})
        self.assertEqual(row[12], "Descrição nova do engenheiro")
        self.assertEqual(row[11], "SIM")

    def test_flag_if_nonempty_descricao_nova_vazia(self) -> None:
        row, _ = self.build({})
        self.assertEqual(row[12], "")
        self.assertEqual(row[11], "")

    def test_flag_if_not_na_material_substituto_alterado(self) -> None:
        row, _ = self.build({31: "SUB_NOVO"})
        self.assertEqual(row[39], "SIM")
        self.assertEqual(row[40], "SUB_NOVO")

    def test_flag_if_not_na_material_substituto_nao_alterado(self) -> None:
        row, _ = self.build({31: "N/A"})
        self.assertNotEqual(row.get(39), "SIM")
        self.assertEqual(row.get(40, ""), "")

    def test_always_copy_with_na_flag_status_bloqueio(self) -> None:
        alterado, _ = self.build({33: "BLOQUEADO"})
        self.assertEqual(alterado[42], "BLOQUEADO")
        self.assertEqual(alterado[41], "SIM")

        nao_alterado, _ = self.build({33: "N/A"})
        self.assertEqual(nao_alterado[42], "N/A")
        self.assertEqual(nao_alterado[41], "")

    def test_quirk2_flag_compartilhada_col65(self) -> None:
        row, quirks = self.build({57: "RESP_NOVO", 59: "PERFIL_NOVO"})
        self.assertEqual(row[65], "SIM")
        self.assertEqual(row[66], "RESP_NOVO")
        self.assertEqual(row[67], "PERFIL_NOVO")
        self.assertEqual(quirks.get(2, 0), 1)

    def test_no_quirk2_when_only_one_field_changes(self) -> None:
        row, quirks = self.build({57: "RESP_NOVO", 59: "N/A"})
        self.assertEqual(row[65], "SIM")
        self.assertEqual(row[66], "RESP_NOVO")
        self.assertEqual(row.get(67, ""), "")
        self.assertEqual(quirks.get(2, 0), 0)

    def test_eliminar_nivel_mandante_direto(self) -> None:
        row, _ = self.build({69: "SIM"})
        self.assertEqual(row[82], "SIM")

    def test_eliminar_nivel_mandante_via_nivel_centro(self) -> None:
        row, _ = self.build({69: "", 71: "SIM"})
        self.assertEqual(row[82], "SIM")

    def test_eliminar_nivel_mandante_vazio(self) -> None:
        row, _ = self.build({})
        self.assertEqual(row.get(82, ""), "")


class RealWorkbookTest(unittest.TestCase):
    """Confirma o estado real do workbook: Plan1 (ZBPP009) ainda não tem dados de material."""

    def test_plan1_sheet_has_no_data_rows_today(self) -> None:
        config = vpe.load_config(CONFIG_PATH)
        workbook = ROOT / "Novo_template_BITin_V2 TESTE.xlsm"
        df = vpe.read_sheet(workbook, config["sheet_codenames"]["Plan1"])
        rows = vpe.read_plan1_rows(df, config)
        self.assertEqual(rows, [])

    def test_plan2_sheet_has_no_data_rows_today(self) -> None:
        config = vpe.load_config(CONFIG_PATH)
        workbook = ROOT / "Novo_template_BITin_V2 TESTE.xlsm"
        df = vpe.read_sheet(workbook, config["sheet_codenames"]["Plan2"])
        rows = vpe.read_plan2_rows(df, config)
        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
