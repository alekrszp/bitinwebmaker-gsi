import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import bitin_document as bd  # noqa: E402

CONFIG_PATH = ROOT / "config" / "bitin_document_mapping.json"
VBA_MAPPING_CONFIG_PATH = ROOT / "config" / "vba_mapping.json"


class SuggestAltRealDataTest(unittest.TestCase):
    """suggest_alt/suggest_dwg_sat_action são sugestões opcionais (não autoritativas,
    ver docs/BITIN_MODEL.md) baseadas em código SAP. Casos extraídos de bitin teste 2.xlsm
    (BITin real P0812/26, aba ZBPP009 + ALTERACAO) — o Alt autoritativo vem declarado pelo
    engenheiro (ver test_bitin_business_rules.py)."""

    def setUp(self) -> None:
        self.config = bd.load_config(CONFIG_PATH)

    def test_nap_5213_revisao_alterada_grupo_sa016(self) -> None:
        # NAP-5213: col8=SA016, col24=SIM (tem desenho), col27='D' (revisão mudou)
        plan2_row = {8: "SA016", 9: "", 24: "SIM", 27: "D", 67: "N/A"}
        self.assertEqual(bd.suggest_alt(plan2_row, self.config), "D/P")
        self.assertEqual(bd.suggest_dwg_sat_action(plan2_row, self.config), "SALVAR DWG")

    def test_nap_0734_sem_desenho_sem_fornecedor(self) -> None:
        # NAP-0734: col8=SA006, col24=NÃO (sem desenho)
        plan2_row = {8: "SA006", 9: "", 24: "NÃO", 27: "", 67: "N/A"}
        self.assertEqual(bd.suggest_alt(plan2_row, self.config), "-")
        self.assertIsNone(bd.suggest_dwg_sat_action(plan2_row, self.config))

    def test_nap_2339_sem_desenho_grupo_pa020(self) -> None:
        # NAP-2339: col8=PA020, col24=NÃO
        plan2_row = {8: "PA020", 9: "", 24: "NÃO", 27: "", 67: "N/A"}
        self.assertEqual(bd.suggest_alt(plan2_row, self.config), "-")

    def test_desenho_com_fornecedor_atual(self) -> None:
        plan2_row = {8: "SA014", 9: "", 24: "SIM", 27: "B", 67: "N/A"}
        self.assertEqual(bd.suggest_alt(plan2_row, self.config), "D/F")

    def test_desenho_com_fornecedor_novo(self) -> None:
        plan2_row = {8: "SA003", 9: "SA014", 24: "SIM", 27: "B", 67: "N/A"}
        self.assertEqual(bd.suggest_alt(plan2_row, self.config), "D/F")

    def test_mp_prefix_forca_fornecedor(self) -> None:
        plan2_row = {8: "MP001", 9: "", 24: "SIM", 27: "B", 67: "N/A"}
        self.assertEqual(bd.suggest_alt(plan2_row, self.config), "D/F")

    def test_sem_desenho_sem_revisao_dwg_sat_sat(self) -> None:
        plan2_row = {8: "SA013", 9: "", 24: "SIM", 27: "", 67: "N/A"}
        self.assertEqual(bd.suggest_dwg_sat_action(plan2_row, self.config), "SALVAR SAT")
        self.assertEqual(bd.suggest_alt(plan2_row, self.config), "-")


class SuggestEspTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = bd.load_config(CONFIG_PATH)

    def test_sem_alteracao_texto_pedido(self) -> None:
        plan2_row = {8: "SA006", 9: "", 67: "N/A"}
        self.assertEqual(bd.suggest_esp(plan2_row, self.config), "-")

    def test_com_alteracao_texto_pedido_grupo_mp(self) -> None:
        plan2_row = {8: "MP001", 9: "", 67: "Especificação nova"}
        self.assertEqual(bd.suggest_esp(plan2_row, self.config), "X")

    def test_com_alteracao_texto_pedido_grupo_normal(self) -> None:
        plan2_row = {8: "SA010", 9: "", 67: "Especificação nova"}
        self.assertEqual(bd.suggest_esp(plan2_row, self.config), "-")


class BuildChecklistTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = bd.load_config(CONFIG_PATH)

    def test_checklist_ids_ativados_para_bitin_real(self) -> None:
        """Reconstrói (parcialmente) o BITin real P0812/26 (Alt/Esp/atualizar_dwg_sat
        já declarados pelo engenheiro, batendo com o que foi observado em bitin teste
        2.xlsm, aba Template apresentação) e confirma os itens de checklist ativados."""
        bitin = {"bitin": "P0812/26", "produto": "Ninho", "motivo": "Ajustes de Campo"}

        nap_0734 = {
            "codigo_material": "NAP-0734",
            "alteracoes": {
                "lista_tecnica": [{"operacao": "alterar", "codigo_filho": "NAP-5483", "quantidade_de": "4", "quantidade_para": "8"}],
                "impactos_operacionais": {"alt": "-", "est": "R", "of": "X"},
            },
        }
        nap_5213 = {
            "codigo_material": "NAP-5213",
            "alteracoes": {
                "impactos_operacionais": {"alt": "D/P", "est": "R", "of": "X", "atualizar_dwg_sat": True},
            },
        }

        checklist = bd.build_checklist(bitin, [nap_0734, nap_5213], self.config)
        afeta_ids = {item["id"] for item in checklist if item["afeta"]}

        self.assertIn("2", afeta_ids)  # Desenho/Processo
        self.assertIn("7", afeta_ids)  # Alteração lista técnica
        self.assertIn("8", afeta_ids)  # Retrabalhar ou descartar estoque
        self.assertIn("17", afeta_ids)  # Atualizar ordem de fabricação
        self.assertIn("18", afeta_ids)  # Atualizar DWG / SAT
        self.assertNotIn("1", afeta_ids)  # Desenho (D/-) não ocorreu
        self.assertNotIn("22", afeta_ids)  # Centro de custo (sucata) — Est nunca foi "S"

    def test_bitex_ativa_checklist_id_11(self) -> None:
        bitin = {"bitin": "P1/26", "produto": "x", "motivo": "x", "bitex": "SIM"}
        checklist = bd.build_checklist(bitin, [], self.config)
        afeta_ids = {item["id"] for item in checklist if item["afeta"]}
        self.assertIn("11", afeta_ids)

    def test_checklist_has_all_22_items(self) -> None:
        checklist = bd.build_checklist({"bitin": "x", "produto": "x", "motivo": "x"}, [], self.config)
        self.assertEqual(len(checklist), 22)
        self.assertEqual({item["id"] for item in checklist}, {str(i) for i in range(1, 23)})


class BuildChecklistSchemaTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = bd.load_config(CONFIG_PATH)

    def test_22_itens_so_id_e_etapa(self) -> None:
        schema = bd.build_checklist_schema(self.config)
        self.assertEqual(len(schema), 22)
        self.assertEqual(set(schema[0].keys()), {"id", "etapa"})
        self.assertEqual(schema[0], {"id": "1", "etapa": "Desenho"})


class BuildCampoAlteradoDiffsTest(unittest.TestCase):
    def setUp(self) -> None:
        import bitin_model as bm

        self.vba_mapping_config = bm.load_config(VBA_MAPPING_CONFIG_PATH)

    def test_diff_matches_real_bitin_teste_2_nivel_revisao(self) -> None:
        # NAP-5213 real (bitin teste 2.xlsm, Plan4 linhas 53-55): Nível Revisão C -> D
        material = {
            "codigo_material": "NAP-5213",
            "alteracoes": {"dados_basicos": {"nivel_revisao": {"de": "C", "para": "D"}}},
        }
        diffs = bd.build_campo_alterado_diffs(material, self.vba_mapping_config)
        self.assertEqual(diffs, [{"campo": "Nível Revisão", "de": "C", "para": "D"}])

    def test_campo_sem_para_nao_aparece(self) -> None:
        material = {"alteracoes": {"dados_basicos": {"ncm": {"de": "123", "para": ""}}}}
        self.assertEqual(bd.build_campo_alterado_diffs(material, self.vba_mapping_config), [])

    def test_sem_dados_basicos(self) -> None:
        self.assertEqual(bd.build_campo_alterado_diffs({}, self.vba_mapping_config), [])


if __name__ == "__main__":
    unittest.main()
