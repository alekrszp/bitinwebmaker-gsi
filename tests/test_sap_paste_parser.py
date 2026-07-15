import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import sap_paste_parser as spp  # noqa: E402
import vba_port_export as vpe  # noqa: E402

CONFIG_PATH = ROOT / "config" / "vba_mapping.json"


def make_sap_row(overrides: dict[int, str] | None = None) -> str:
    """Monta uma linha colada do SAP com TAB reais entre as 36 colunas de ZBPP009,
    usando como base o exemplo real (material 8661, TUBO MENOR 1/2") passado pelo
    usuário -- reconstruído explicitamente com \\t porque a fidelidade do espaçamento
    de uma mensagem de chat colada não é garantida."""
    campos = {
        1: "HALB", 2: "8661", 3: "PC", 4: "2001", 5: 'TUBO MENOR 1/2"', 6: "MP026",
        7: "LIB", 8: "00007B000300000003", 9: "0,061", 10: "0,061", 11: "KG",
        12: "3,377", 13: "CM3", 14: "SIM", 15: "A", 16: "REVISADO/G0019/11",
        17: "", 18: "", 19: "00.00.0000", 20: "Y", 21: "", 22: "8479.90.90",
        23: "120", 24: "317", 25: "F", 26: "", 27: "0001", 28: "40", 29: "",
        30: "1", 31: "0", 32: "", 33: "", 34: "", 35: "", 36: "",
    }
    campos.update(overrides or {})
    return "\t".join(campos[i] for i in range(1, 37))


class ParseSapPasteTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = vpe.load_config(CONFIG_PATH)

    def test_uma_linha_vira_um_dict_de_36_colunas(self) -> None:
        rows = spp.parse_sap_paste(make_sap_row())
        self.assertEqual(len(rows), 1)
        self.assertEqual(len(rows[0]), 36)
        self.assertEqual(rows[0][1], "HALB")
        self.assertEqual(rows[0][2], "8661")
        self.assertEqual(rows[0][5], 'TUBO MENOR 1/2"')  # descrição com espaço interno

    def test_descricao_com_espaco_nao_quebra_colunas(self) -> None:
        """O ponto que motivou o parser: TAB (não espaço) separa colunas, então uma
        descrição como 'TUBO MENOR 1/2"' não vaza pra coluna seguinte."""
        rows = spp.parse_sap_paste(make_sap_row())
        self.assertEqual(rows[0][6], "MP026")  # coluna seguinte intacta

    def test_multiplas_linhas_multiplos_centros(self) -> None:
        """Caso real do usuário: mesmo material (8661) em centros diferentes (2001,
        2003, 2005, 2006) -- cada linha colada é uma entrada distinta."""
        texto = "\n".join(
            [
                make_sap_row({4: "2001"}),
                make_sap_row({4: "2003"}),
                make_sap_row({4: "2005"}),
            ]
        )
        rows = spp.parse_sap_paste(texto)
        self.assertEqual(len(rows), 3)
        self.assertEqual([r[4] for r in rows], ["2001", "2003", "2005"])

    def test_linhas_em_branco_sao_ignoradas(self) -> None:
        texto = make_sap_row() + "\n\n" + make_sap_row({4: "2003"}) + "\n"
        rows = spp.parse_sap_paste(texto)
        self.assertEqual(len(rows), 2)

    def test_plan1_row_to_material_atual(self) -> None:
        rows = spp.parse_sap_paste(make_sap_row())
        material = spp.plan1_row_to_material_atual(rows[0], self.config)
        self.assertEqual(material["tipo_material"], "HALB")
        self.assertEqual(material["codigo_material"], "8661")
        self.assertEqual(material["centro"], "2001")
        self.assertEqual(material["descricao_material"], 'TUBO MENOR 1/2"')
        self.assertEqual(material["grupo_mercadorias_atual"], "MP026")
        self.assertTrue(material["tem_desenho"])

    def test_dados_basicos_atual_traz_o_snapshot_completo(self) -> None:
        """Tela Códigos SAP é idêntica à ZBPP009 (decisão do usuário, 2026-07-15): o colar
        do SAP preenche o 'de' de todos os 30 campos de dados_basicos, não só um recorte."""
        rows = spp.parse_sap_paste(make_sap_row())
        material = spp.plan1_row_to_material_atual(rows[0], self.config)
        dados_basicos = material["dados_basicos_atual"]
        self.assertEqual(len(dados_basicos), 30)
        self.assertEqual(dados_basicos["descricao"], 'TUBO MENOR 1/2"')
        self.assertEqual(dados_basicos["grupo_mercadorias"], "MP026")
        self.assertEqual(dados_basicos["peso_bruto"], "0,061")
        self.assertEqual(dados_basicos["ncm"], "8479.90.90")
        self.assertEqual(dados_basicos["marcacao_eliminar_nivel_mandante"], "")

    def test_parse_sap_paste_to_materiais_varios_centros(self) -> None:
        texto = "\n".join([make_sap_row({4: "2001"}), make_sap_row({4: "2003"})])
        materiais = spp.parse_sap_paste_to_materiais(texto, self.config)
        self.assertEqual(len(materiais), 2)
        self.assertEqual([m["centro"] for m in materiais], ["2001", "2003"])
        self.assertTrue(all(m["codigo_material"] == "8661" for m in materiais))


if __name__ == "__main__":
    unittest.main()
