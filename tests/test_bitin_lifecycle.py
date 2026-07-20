import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import bitin_document as bd  # noqa: E402
import bitin_lifecycle as bl  # noqa: E402
import bitin_model as bm  # noqa: E402

VBA_MAPPING_CONFIG_PATH = ROOT / "config" / "vba_mapping.json"
DOCUMENT_CONFIG_PATH = ROOT / "config" / "bitin_document_mapping.json"


def make_valid_bitin() -> dict:
    return {
        "bitin": "P3301/26",
        "setor": "Proteína Animal",
        "produto": "Silo X",
        "motivo": "Correção",
        "solicitante": "Alessandro",
        "data_solicitacao": "2026-07-09",
        "materiais": [
            {
                "codigo_material": "CT30-7103",
                "centro": "2001",
                "tipo_material": "HALB",
                "alteracoes": {
                    "dados_basicos": {"descricao": {"de": "X", "para": "Y"}},
                    "impactos_operacionais": {"alt": "-/P"},
                },
            }
        ],
    }


class LifecycleTest(unittest.TestCase):
    def setUp(self) -> None:
        self.vba_mapping_config = bm.load_config(VBA_MAPPING_CONFIG_PATH)
        self.document_config = bd.load_config(DOCUMENT_CONFIG_PATH)

    def enviar(self, bitin: dict) -> tuple[bool, list[str]]:
        return bl.enviar_bitin(bitin, self.vba_mapping_config, self.document_config)

    def test_bitin_novo_e_editavel_e_rascunho(self) -> None:
        bitin = make_valid_bitin()
        self.assertTrue(bl.is_editable(bitin))
        self.assertEqual(bitin.get("status", bl.STATUS_RASCUNHO), bl.STATUS_RASCUNHO)

    def test_require_editable_nao_levanta_para_rascunho(self) -> None:
        bl.require_editable(make_valid_bitin())  # não deve levantar

    def test_require_editable_levanta_para_enviado(self) -> None:
        bitin = make_valid_bitin()
        bitin["status"] = bl.STATUS_ENVIADO
        with self.assertRaises(ValueError):
            bl.require_editable(bitin)

    def test_enviar_bitin_valido_muda_status_e_carimba_data(self) -> None:
        bitin = make_valid_bitin()
        ok, errors = self.enviar(bitin)
        self.assertTrue(ok)
        self.assertEqual(errors, [])
        self.assertEqual(bitin["status"], bl.STATUS_ENVIADO)
        self.assertIn("data_envio", bitin)
        self.assertFalse(bl.is_editable(bitin))

    def test_enviar_bitin_invalido_continua_rascunho(self) -> None:
        bitin = make_valid_bitin()
        del bitin["solicitante"]
        ok, errors = self.enviar(bitin)
        self.assertFalse(ok)
        self.assertTrue(len(errors) > 0)
        self.assertEqual(bitin.get("status", bl.STATUS_RASCUNHO), bl.STATUS_RASCUNHO)

    def test_nao_pode_reenviar_bitin_ja_enviado(self) -> None:
        bitin = make_valid_bitin()
        ok1, _ = self.enviar(bitin)
        self.assertTrue(ok1)
        ok2, errors2 = self.enviar(bitin)
        self.assertFalse(ok2)
        self.assertTrue(any("já foi enviado" in e["message"] for e in errors2))


class EncaminharRoteiroTest(unittest.TestCase):
    """Fila do setor Cadastro (2026-07-17, substitui o e-mail automático do Módulo12.bas)."""

    def setUp(self) -> None:
        self.vba_mapping_config = bm.load_config(VBA_MAPPING_CONFIG_PATH)
        self.document_config = bd.load_config(DOCUMENT_CONFIG_PATH)

    def test_encaminha_bitin_enviado(self) -> None:
        bitin = make_valid_bitin()
        bl.enviar_bitin(bitin, self.vba_mapping_config, self.document_config)
        bl.encaminhar_para_roteiro(bitin)
        self.assertTrue(bitin["encaminhado_roteiro"])
        self.assertIn("data_encaminhado_roteiro", bitin)

    def test_nao_encaminha_bitin_ainda_em_rascunho(self) -> None:
        bitin = make_valid_bitin()
        with self.assertRaises(ValueError):
            bl.encaminhar_para_roteiro(bitin)

    def test_nao_encaminha_duas_vezes(self) -> None:
        bitin = make_valid_bitin()
        bl.enviar_bitin(bitin, self.vba_mapping_config, self.document_config)
        bl.encaminhar_para_roteiro(bitin)
        with self.assertRaises(ValueError):
            bl.encaminhar_para_roteiro(bitin)


class ConcluirProcessamentoTest(unittest.TestCase):
    """Setor Processos (2026-07-17) -- fecha a janela de reedição aberta por
    encaminhar_para_roteiro."""

    def setUp(self) -> None:
        self.vba_mapping_config = bm.load_config(VBA_MAPPING_CONFIG_PATH)
        self.document_config = bd.load_config(DOCUMENT_CONFIG_PATH)

    def _bitin_encaminhado(self) -> dict:
        bitin = make_valid_bitin()
        bl.enviar_bitin(bitin, self.vba_mapping_config, self.document_config)
        bl.encaminhar_para_roteiro(bitin)
        return bitin

    def test_conclui_bitin_encaminhado(self) -> None:
        bitin = self._bitin_encaminhado()
        bl.concluir_processamento(bitin)
        self.assertTrue(bitin["processos_concluido"])
        self.assertIn("data_processos_concluido", bitin)

    def test_nao_conclui_bitin_ainda_nao_encaminhado(self) -> None:
        bitin = make_valid_bitin()
        bl.enviar_bitin(bitin, self.vba_mapping_config, self.document_config)
        with self.assertRaises(ValueError):
            bl.concluir_processamento(bitin)

    def test_nao_conclui_duas_vezes(self) -> None:
        bitin = self._bitin_encaminhado()
        bl.concluir_processamento(bitin)
        with self.assertRaises(ValueError):
            bl.concluir_processamento(bitin)


class ConcluirSemRoteiroTest(unittest.TestCase):
    """Alternativa a encaminhar_para_roteiro quando o BITin não precisa passar pelo Processos
    (2026-07-17, ver bitin_document.precisa_roteiro)."""

    def setUp(self) -> None:
        self.vba_mapping_config = bm.load_config(VBA_MAPPING_CONFIG_PATH)
        self.document_config = bd.load_config(DOCUMENT_CONFIG_PATH)

    def test_conclui_direto_sem_roteiro(self) -> None:
        bitin = make_valid_bitin()
        bl.enviar_bitin(bitin, self.vba_mapping_config, self.document_config)
        bl.concluir_sem_roteiro(bitin)
        self.assertTrue(bitin["encaminhado_roteiro"])
        self.assertTrue(bitin["processos_concluido"])
        self.assertTrue(bitin["sem_necessidade_roteiro"])
        self.assertIn("data_encaminhado_roteiro", bitin)
        self.assertIn("data_processos_concluido", bitin)

    def test_nao_conclui_bitin_ainda_em_rascunho(self) -> None:
        bitin = make_valid_bitin()
        with self.assertRaises(ValueError):
            bl.concluir_sem_roteiro(bitin)

    def test_nao_conclui_bitin_ja_encaminhado(self) -> None:
        bitin = make_valid_bitin()
        bl.enviar_bitin(bitin, self.vba_mapping_config, self.document_config)
        bl.encaminhar_para_roteiro(bitin)
        with self.assertRaises(ValueError):
            bl.concluir_sem_roteiro(bitin)


if __name__ == "__main__":
    unittest.main()
