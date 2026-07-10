import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import bitin_document as bd  # noqa: E402
import bitin_model as bm  # noqa: E402
import bitin_view as bv  # noqa: E402

VBA_MAPPING_CONFIG_PATH = ROOT / "config" / "vba_mapping.json"
DOCUMENT_CONFIG_PATH = ROOT / "config" / "bitin_document_mapping.json"


class RenderBitinSummaryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.vba_mapping_config = bm.load_config(VBA_MAPPING_CONFIG_PATH)
        self.document_config = bd.load_config(DOCUMENT_CONFIG_PATH)

    def test_resumo_bate_com_bitin_real_nap5213(self) -> None:
        """Reconstrói (parcialmente) o BITin real P0812/26 e confirma que o resumo de
        visualização mostra corretamente a diff de Nível de Revisão e o checklist."""
        bitin = {
            "bitin": "P0812/26",
            "produto": "Ninho",
            "motivo": "Ajustes de Campo",
            "solicitante": "Edilson Santin",
            "data_solicitacao": "2026-02-20",
            "materiais": [
                {
                    "codigo_material": "NAP-5213",
                    "descricao_material": "COBERTURA MOD BIPARTIDO 2,44M",
                    "centro": "2001",
                    "tipo_material": "HALB",
                    "desenho_aprovado": True,
                    "alteracoes": {
                        "dados_basicos": {"nivel_revisao": {"de": "C", "para": "D"}},
                        "impactos_operacionais": {"alt": "D/P", "atualizar_dwg_sat": True},
                    },
                }
            ],
        }

        resumo = bv.render_bitin_summary(bitin, self.vba_mapping_config, self.document_config)

        self.assertEqual(resumo["bitin"], "P0812/26")
        self.assertEqual(resumo["status"], "rascunho")
        self.assertIsNone(resumo["data_envio"])

        material_resumo = resumo["materiais"][0]
        self.assertEqual(material_resumo["codigo_material"], "NAP-5213")
        self.assertEqual(material_resumo["impactos_operacionais"]["alt"], "D/P")
        self.assertEqual(
            material_resumo["dados_basicos_alterados"],
            [{"campo": "Nível Revisão", "de": "C", "para": "D"}],
        )

        self.assertIn("Desenho/Processo", resumo["checklist_pendencias"])
        self.assertIn("Atualizar DWG / SAT", resumo["checklist_pendencias"])
        self.assertNotIn("Desenho", resumo["checklist_pendencias"])

    def test_resumo_reflete_status_enviado(self) -> None:
        bitin = {
            "bitin": "P1/26", "produto": "x", "motivo": "x",
            "status": "enviado", "data_envio": "2026-07-10",
            "materiais": [],
        }
        resumo = bv.render_bitin_summary(bitin, self.vba_mapping_config, self.document_config)
        self.assertEqual(resumo["status"], "enviado")
        self.assertEqual(resumo["data_envio"], "2026-07-10")
        self.assertEqual(resumo["materiais"], [])
        self.assertEqual(len(resumo["checklist"]), 22)


if __name__ == "__main__":
    unittest.main()
