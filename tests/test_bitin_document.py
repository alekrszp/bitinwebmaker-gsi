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

    def test_checklist_ignora_dados_dos_materiais_sem_override(self) -> None:
        """Checklist é 100% manual (2026-07-15) -- mesmo com materiais que teriam ativado
        vários itens no cálculo automático antigo (Alt/Esp/Est/OF/atualizar_dwg_sat), nada
        fica 'afeta' sem override explícito do engenheiro (bitin teste 2.xlsm, P0812/26)."""
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
        self.assertEqual(afeta_ids, set())

    def test_bitex_sim_nao_ativa_mais_checklist_id_11_sozinho(self) -> None:
        # bitex=SIM não ativa mais nada sozinho -- checklist é 100% manual (2026-07-15).
        bitin = {"bitin": "P1/26", "produto": "x", "motivo": "x", "bitex": "SIM"}
        checklist = bd.build_checklist(bitin, [], self.config)
        afeta_ids = {item["id"] for item in checklist if item["afeta"]}
        self.assertEqual(afeta_ids, set())

    def test_checklist_override_manual_liga_item_11_mesmo_com_bitex_sim(self) -> None:
        bitin = {
            "bitin": "P1/26", "produto": "x", "motivo": "x", "bitex": "SIM",
            "checklist_overrides": {"11": True},
        }
        checklist = bd.build_checklist(bitin, [], self.config)
        afeta_ids = {item["id"] for item in checklist if item["afeta"]}
        self.assertIn("11", afeta_ids)

    def test_checklist_has_all_22_items(self) -> None:
        checklist = bd.build_checklist({"bitin": "x", "produto": "x", "motivo": "x"}, [], self.config)
        self.assertEqual(len(checklist), 22)
        self.assertEqual({item["id"] for item in checklist}, {str(i) for i in range(1, 23)})

    def test_checklist_override_manual_liga_item(self) -> None:
        # Checklist é 100% manual (2026-07-15) -- o único jeito de um item ficar "afeta" é o
        # engenheiro clicar nele (override).
        bitin = {"bitin": "x", "produto": "x", "motivo": "x", "checklist_overrides": {"1": True}}
        checklist = bd.build_checklist(bitin, [], self.config)
        item = next(i for i in checklist if i["id"] == "1")
        self.assertTrue(item["afeta"])
        self.assertTrue(item["manual"])

    def test_checklist_override_manual_desliga_item_mesmo_com_material_relacionado(self) -> None:
        # Mesmo com um material cujo Alt indicaria alteração de desenho, sem override o item
        # continua "não" (checklist não deriva mais de materiais); override explícito False
        # continua marcado como "manual" (engenheiro já revisou aquele item).
        nap_0734 = {
            "codigo_material": "NAP-0734",
            "alteracoes": {"impactos_operacionais": {"alt": "D/-"}},
        }
        bitin = {"bitin": "x", "produto": "x", "motivo": "x", "checklist_overrides": {"1": False}}
        checklist = bd.build_checklist(bitin, [nap_0734], self.config)
        item = next(i for i in checklist if i["id"] == "1")
        self.assertFalse(item["afeta"])
        self.assertTrue(item["manual"])

    def test_checklist_item_sem_override_nao_e_manual(self) -> None:
        checklist = bd.build_checklist({"bitin": "x", "produto": "x", "motivo": "x"}, [], self.config)
        self.assertTrue(all(not item["manual"] for item in checklist))


class BuildSetoresAfetadosTest(unittest.TestCase):
    """Crosswalk etapa -> setores extraído de um BITin real (A263326.xlsm, aba
    'SETORES CHECKLIST'), casado por posição com checklist_items."""

    def setUp(self) -> None:
        self.config = bd.load_config(CONFIG_PATH)

    def test_setores_do_bitin_real_a263326(self) -> None:
        # Mesmas etapas ativadas no A263326 real: Desenho, Desenho/Fornecedor, Retrabalhar ou
        # descartar estoque, Atualizar ordem de fabricação, Atualizar DWG/SAT, Centro de custo.
        checklist = [
            {"id": "1", "etapa": "Desenho", "afeta": True},
            {"id": "3", "etapa": "Desenho/Fornecedor", "afeta": True},
            {"id": "8", "etapa": "Retrabalhar ou descartar estoque", "afeta": True},
            {"id": "17", "etapa": "Atualizar ordem de fabricação", "afeta": True},
            {"id": "18", "etapa": "Atualizar DWG / SAT", "afeta": True},
            {"id": "22", "etapa": "Centro de custo (se tem sucata)", "afeta": True},
            {"id": "2", "etapa": "Desenho/Processo", "afeta": False},
        ]
        setores = bd.build_setores_afetados(checklist, self.config)
        self.assertEqual(
            setores,
            sorted({"PCP", "ENG INDUS", "QUALIDADE", "COMPRAS", "CONTROLADORIA", "LOGÍSTICA"}),
        )

    def test_sem_etapas_afetadas_devolve_lista_vazia(self) -> None:
        checklist = [{"id": "1", "etapa": "Desenho", "afeta": False}]
        self.assertEqual(bd.build_setores_afetados(checklist, self.config), [])

    def test_setores_nao_repete_quando_mais_de_uma_etapa_aciona_o_mesmo_setor(self) -> None:
        # ids 1 e 2 acionam os dois PCP+ENG INDUS -- não deve duplicar
        checklist = [
            {"id": "1", "etapa": "Desenho", "afeta": True},
            {"id": "2", "etapa": "Desenho/Processo", "afeta": True},
        ]
        setores = bd.build_setores_afetados(checklist, self.config)
        self.assertEqual(setores, ["ENG INDUS", "PCP"])


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
        self.assertEqual(diffs, [{"campo": "Nível Revisão", "de": "C", "para": "D", "livre": False}])

    def test_campo_sem_para_nao_aparece(self) -> None:
        material = {"alteracoes": {"dados_basicos": {"ncm": {"de": "123", "para": ""}}}}
        self.assertEqual(bd.build_campo_alterado_diffs(material, self.vba_mapping_config), [])

    def test_sem_dados_basicos(self) -> None:
        self.assertEqual(bd.build_campo_alterado_diffs({}, self.vba_mapping_config), [])

    def test_campo_livre_nao_reconhecido_mostra_como_foi_escrito(self) -> None:
        """Achado num BITin real (A263326.xlsm): o engenheiro escreveu 'Alterado lista
        tecnica' -> 'Alterado peso e IS' -- não é nenhum campo SAP do crosswalk. Antes disso
        derrubava a requisição com KeyError; agora mostra o texto livre como veio."""
        material = {
            "alteracoes": {"dados_basicos": {"Alterado lista tecnica": {"de": "", "para": "Alterado peso e IS"}}}
        }
        diffs = bd.build_campo_alterado_diffs(material, self.vba_mapping_config)
        self.assertEqual(
            diffs, [{"campo": "Alterado lista tecnica", "de": "", "para": "Alterado peso e IS", "livre": True}]
        )

    def test_campo_livre_sem_de_nem_para_e_uma_nota_solta_ainda_aparece(self) -> None:
        """'Salvar DWG' real (A263326.xlsm, material RE-M1563): nota solta, sem de/para --
        diferente de um campo SAP incompleto, ainda deve aparecer (documento é "tudo que foi
        escrito fica visível", não só diffs estruturados)."""
        material = {"alteracoes": {"dados_basicos": {"Salvar DWG": {}}}}
        diffs = bd.build_campo_alterado_diffs(material, self.vba_mapping_config)
        self.assertEqual(diffs, [{"campo": "Salvar DWG", "de": "", "para": "", "livre": True}])


if __name__ == "__main__":
    unittest.main()
