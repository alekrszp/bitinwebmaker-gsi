import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import bitin_model as bm  # noqa: E402
import vba_port_export as vpe  # noqa: E402

CONFIG_PATH = ROOT / "config" / "vba_mapping.json"
DOCUMENT_CONFIG_PATH = ROOT / "config" / "bitin_document_mapping.json"


def make_bitin(**overrides) -> dict:
    base = {
        "bitin": "P3301/26",
        "setor": "Proteína Animal",
        "produto": "Silo X",
        "motivo": "SPN",
        "solicitante": "Alessandro",
        "data_solicitacao": "2026-07-09",
        "materiais": [
            {
                "codigo_material": "COD123",
                "descricao_material": "Peça teste",
                "centro": "2001",
                "tipo_material": "MP",
                "alteracoes": {
                    "dados_basicos": {
                        "descricao": {"de": "Descrição antiga", "para": "Descrição nova"},
                        "material_substituto": {"de": "N/A", "para": "SUB999"},
                    }
                },
            }
        ],
    }
    base.update(overrides)
    return base


class ValidateBitinTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = bm.load_config(CONFIG_PATH)

    def test_valid_bitin_has_no_errors(self) -> None:
        errors = bm.validate_bitin(make_bitin(), self.config)
        self.assertEqual(errors, [])

    def test_missing_header_field(self) -> None:
        bitin = make_bitin()
        del bitin["solicitante"]
        errors = bm.validate_bitin(bitin, self.config)
        self.assertTrue(any("solicitante" in e["message"] for e in errors))

    def test_invalid_bitin_number_format(self) -> None:
        errors = bm.validate_bitin(make_bitin(bitin="330122"), self.config)
        self.assertTrue(any("formato YXXXX/AA" in e["message"] for e in errors))

    def test_bitin_number_nao_e_obrigatorio_no_rascunho(self) -> None:
        """'bitin' (número) é gerado pelo sistema no envio -- rascunho sem ele é válido."""
        bitin = make_bitin()
        del bitin["bitin"]
        errors = bm.validate_bitin(bitin, self.config)
        self.assertEqual(errors, [])

    def test_setor_e_obrigatorio(self) -> None:
        """'setor' define o prefixo P/A do número gerado -- precisa estar presente."""
        bitin = make_bitin()
        del bitin["setor"]
        errors = bm.validate_bitin(bitin, self.config)
        self.assertTrue(any("setor" in e["message"] for e in errors))

    def test_missing_material_centro(self) -> None:
        bitin = make_bitin()
        del bitin["materiais"][0]["centro"]
        errors = bm.validate_bitin(bitin, self.config)
        self.assertTrue(any("centro" in e["message"] for e in errors))

    def test_no_materiais(self) -> None:
        errors = bm.validate_bitin(make_bitin(materiais=[]), self.config)
        self.assertTrue(any("nenhum material" in e["message"] for e in errors))

    def test_ordem_cliente_ausente_nao_gera_erro(self) -> None:
        """ordem_cliente[] é opcional -- BITin sem nenhuma entrada é válido."""
        errors = bm.validate_bitin(make_bitin(), self.config)
        self.assertEqual(errors, [])

    def test_ordem_cliente_sem_codigo_falha(self) -> None:
        bitin = make_bitin(ordem_cliente=[{"acrescentar_no_pedido": [
            {"codigo_material": "COD999", "quantidade": "2 pçs"}
        ]}])
        errors = bm.validate_bitin(bitin, self.config)
        self.assertTrue(any(
            e["code"] == "required_field_missing" and e["field"] == "ordem_cliente[0].codigo"
            for e in errors
        ))

    def test_ordem_cliente_sem_nenhum_item_falha(self) -> None:
        bitin = make_bitin(ordem_cliente=[{"codigo": "COD123", "descricao": "x"}])
        errors = bm.validate_bitin(bitin, self.config)
        self.assertTrue(any(e["code"] == "ordem_cliente_sem_itens" for e in errors))

    def test_ordem_cliente_item_sem_quantidade_falha(self) -> None:
        bitin = make_bitin(ordem_cliente=[{
            "codigo": "COD123",
            "retira_do_pedido": [{"codigo_material": "COD999"}],
        }])
        errors = bm.validate_bitin(bitin, self.config)
        self.assertTrue(any(
            e["code"] == "required_field_missing"
            and e["field"] == "ordem_cliente[0].retira_do_pedido[0].quantidade"
            for e in errors
        ))

    def test_ordem_cliente_valida_passa(self) -> None:
        bitin = make_bitin(ordem_cliente=[{
            "codigo": "COD123",
            "descricao": "Pedido especial",
            "acrescentar_no_pedido": [{"codigo_material": "COD999", "quantidade": "2 pçs"}],
        }])
        errors = bm.validate_bitin(bitin, self.config)
        self.assertEqual(errors, [])


class MaterialToPlan2RowTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = bm.load_config(CONFIG_PATH)

    def test_identificacao_columns(self) -> None:
        material = make_bitin()["materiais"][0]
        row = bm.material_to_plan2_row(material, self.config)
        self.assertEqual(row[3], "MP")
        self.assertEqual(row[4], "2001")
        self.assertEqual(row[5], "COD123")

    def test_dados_basicos_com_valor_novo(self) -> None:
        material = make_bitin()["materiais"][0]
        row = bm.material_to_plan2_row(material, self.config)
        self.assertEqual(row[7], "Descrição nova")  # descricao -> col 7
        self.assertEqual(row[31], "SUB999")  # material_substituto -> col 31

    def test_campo_com_convencao_na_sem_alteracao(self) -> None:
        material = make_bitin()["materiais"][0]
        row = bm.material_to_plan2_row(material, self.config)
        # status_bloqueio_vendas não foi informado -> deve virar "N/A" (convenção N/A)
        self.assertEqual(row[33], "N/A")

    def test_campo_sem_convencao_na_sem_alteracao(self) -> None:
        material = make_bitin()["materiais"][0]
        row = bm.material_to_plan2_row(material, self.config)
        # grupo_mercadorias não foi informado -> deve ficar vazio (convenção vazio)
        self.assertEqual(row[9], "")


class MateriaisSchemaTest(unittest.TestCase):
    """build_materiais_schema é a fonte única de colunas do grid de materiais no frontend
    (ver docs/BACKEND.md, 'Grid de materiais dirigido por schema') -- cobre que ela reflete
    o crosswalk e os valores válidos reais, sem duplicar essas listas na UI."""

    def setUp(self) -> None:
        self.vba_config = bm.load_config(CONFIG_PATH)
        self.document_config = bm.load_config(DOCUMENT_CONFIG_PATH)
        self.schema = bm.build_materiais_schema(self.vba_config, self.document_config)

    def test_dados_basicos_reflete_o_crosswalk_na_mesma_ordem(self) -> None:
        campos_crosswalk = list(self.vba_config["bitin_schema_crosswalk"]["dados_basicos"].keys())
        campos_schema = [col["key"] for col in self.schema["dados_basicos"]]
        self.assertEqual(campos_schema, campos_crosswalk)

    def test_impactos_operacionais_traz_as_opcoes_do_pop(self) -> None:
        alt_col = next(col for col in self.schema["impactos_operacionais"] if col["key"] == "alt")
        self.assertEqual(alt_col["options"], self.document_config["valores_validos"]["alt"])

    def test_identificacao_marca_campos_obrigatorios(self) -> None:
        chaves_obrigatorias = {col["key"] for col in self.schema["identificacao"] if col["required"]}
        self.assertEqual(chaves_obrigatorias, {"codigo_material", "centro", "tipo_material"})

    def test_impactos_condicionais_referencia_est_igual_s(self) -> None:
        centro_custo = next(col for col in self.schema["impactos_condicionais"] if col["key"] == "centro_custo")
        self.assertEqual(centro_custo["required_when"], {"field": "impactos_operacionais.est", "equals": "S"})


class EndToEndBitinToPlan3Test(unittest.TestCase):
    """Prova a ponta a ponta: JSON do BITin -> linhas Plan2 -> export Winshuttle (Plan3)."""

    def setUp(self) -> None:
        self.config = bm.load_config(CONFIG_PATH)

    def test_bitin_json_flows_into_plan3_export(self) -> None:
        bitin = make_bitin()
        self.assertEqual(bm.validate_bitin(bitin, self.config), [])

        plan2_rows = bm.bitin_to_plan2_rows(bitin, self.config)
        header_values = bm.bitin_header_values(bitin)
        header_values["data"] = "09.07.2026"

        quirks: dict[int, int] = {}
        plan3_row = vpe.build_plan3_row(plan2_rows[0], header_values, self.config, quirks)

        self.assertEqual(plan3_row[1], "P3301/26")
        self.assertEqual(plan3_row[9], "COD123")
        self.assertEqual(plan3_row[10], "2001")
        self.assertEqual(plan3_row[12], "Descrição nova")
        self.assertEqual(plan3_row[11], "SIM")
        self.assertEqual(plan3_row[39], "SIM")
        self.assertEqual(plan3_row[40], "SUB999")


class WritePlan2XlsxRoundTripTest(unittest.TestCase):
    """Gera o .xlsx real da aba Plan2 e confirma que scripts/vba_port_export.py
    consegue ler esse arquivo diretamente e reproduzir o mesmo resultado do
    caminho em memória (bitin_to_plan2_rows -> build_plan3_row)."""

    def setUp(self) -> None:
        self.config = bm.load_config(CONFIG_PATH)
        self.bitin = make_bitin()

    def test_generated_xlsx_matches_in_memory_pipeline(self) -> None:
        in_memory_rows = bm.bitin_to_plan2_rows(self.bitin, self.config)

        with tempfile.TemporaryDirectory() as tmp_dir:
            out_path = Path(tmp_dir) / "plan2_generated.xlsx"
            bm.write_plan2_xlsx(self.bitin, self.config, out_path)

            sheet_name = self.config["sheet_codenames"]["Plan2"]
            df = vpe.read_sheet(out_path, sheet_name)
            file_rows = vpe.read_plan2_rows(df, self.config)

            bitin_h, produto_h, motivo_h = vpe.read_plan2_header(df, self.config)

        self.assertEqual(len(file_rows), len(in_memory_rows))
        self.assertEqual(file_rows[0][3], in_memory_rows[0][3])  # tipo_material
        self.assertEqual(file_rows[0][7], in_memory_rows[0][7])  # descricao Nova
        self.assertEqual(file_rows[0][31], in_memory_rows[0][31])  # material_substituto Novo
        self.assertEqual(file_rows[0][33], in_memory_rows[0][33])  # status_bloqueio (N/A default)

        self.assertEqual(bitin_h, self.bitin["bitin"])
        self.assertEqual(produto_h, self.bitin["produto"])
        self.assertEqual(motivo_h, self.bitin["motivo"])

    def test_generated_xlsx_export_matches_in_memory_export(self) -> None:
        header_values = bm.bitin_header_values(self.bitin)
        header_values["data"] = "09.07.2026"
        in_memory_plan2 = bm.bitin_to_plan2_rows(self.bitin, self.config)
        in_memory_plan3 = vpe.build_plan3_row(in_memory_plan2[0], header_values, self.config, {})

        with tempfile.TemporaryDirectory() as tmp_dir:
            out_path = Path(tmp_dir) / "plan2_generated.xlsx"
            bm.write_plan2_xlsx(self.bitin, self.config, out_path)

            sheet_name = self.config["sheet_codenames"]["Plan2"]
            df = vpe.read_sheet(out_path, sheet_name)
            file_rows = vpe.read_plan2_rows(df, self.config)
            file_plan3 = vpe.build_plan3_row(file_rows[0], header_values, self.config, {})

        self.assertEqual(file_plan3, in_memory_plan3)


if __name__ == "__main__":
    unittest.main()
