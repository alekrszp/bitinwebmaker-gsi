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


def make_bitin_enviado_manual() -> dict:
    """Bitin já "enviado" via manipulação direta do dict, SEM passar por `enviar_bitin`
    (2026-07-20, ver comentário abaixo) -- usado pelos testes de EncaminharRoteiroTest/
    ConcluirProcessamentoTest/ConcluirSemRoteiroTest/ConcluirBitinTest, que testam essas
    funções de transição em ISOLAMENTO, sem o roteamento automático que `enviar_bitin` agora
    aplica sozinho (ver LifecycleTest.EnviarBitinRoteamentoAutomaticoTest abaixo, que testa
    esse roteamento especificamente). Alt="-/P" (a mesma de make_valid_bitin) exige roteiro,
    mas isso não importa aqui -- este fixture nunca passa por `enviar_bitin`, só seta
    status=enviado manualmente, então `encaminhado_roteiro`/`processos_concluido` continuam
    ausentes até o teste chamar a função sob teste."""
    bitin = make_valid_bitin()
    bitin["status"] = bl.STATUS_ENVIADO
    bitin["data_envio"] = "2026-07-09"
    return bitin


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


class EnviarBitinRoteamentoAutomaticoTest(unittest.TestCase):
    """Roteamento automático (2026-07-20, pedido explícito: "se for pra processo vai DIRETO
    pra processo. se não for necessário o pessoal de processo vai direto para aguardando
    cadastro") -- `enviar_bitin` agora decide sozinho, sem passar pela triagem manual do
    Cadastro (removida, ver CadastroPage.tsx)."""

    def setUp(self) -> None:
        self.vba_mapping_config = bm.load_config(VBA_MAPPING_CONFIG_PATH)
        self.document_config = bd.load_config(DOCUMENT_CONFIG_PATH)

    def test_alt_que_precisa_roteiro_encaminha_direto_pro_processos(self) -> None:
        bitin = make_valid_bitin()  # Alt="-/P" -- exige roteiro
        bl.enviar_bitin(bitin, self.vba_mapping_config, self.document_config)
        self.assertTrue(bitin["encaminhado_roteiro"])
        self.assertFalse(bitin.get("processos_concluido", False))
        self.assertFalse(bitin.get("sem_necessidade_roteiro", False))

    def test_alt_que_nao_precisa_vai_direto_pra_aguardando_cadastro(self) -> None:
        bitin = make_valid_bitin()
        bitin["materiais"][0]["alteracoes"]["impactos_operacionais"]["alt"] = "-/F"
        bl.enviar_bitin(bitin, self.vba_mapping_config, self.document_config)
        self.assertTrue(bitin["encaminhado_roteiro"])
        self.assertTrue(bitin["processos_concluido"])
        self.assertTrue(bitin["sem_necessidade_roteiro"])


class EncaminharRoteiroTest(unittest.TestCase):
    """Fila do setor Cadastro (2026-07-17, substitui o e-mail automático do Módulo12.bas) --
    função de transição testada em ISOLAMENTO aqui (fixture com status=enviado manual, ver
    make_bitin_enviado_manual), não mais via `enviar_bitin` (que desde 2026-07-20 já chama
    isso sozinho quando precisa de roteiro, ver EnviarBitinRoteamentoAutomaticoTest acima) --
    a função em si continua existindo como escape hatch (ver backend/api/bitins.py::
    encaminhar_roteiro_endpoint), só não é mais chamada no fluxo normal."""

    def test_encaminha_bitin_enviado(self) -> None:
        bitin = make_bitin_enviado_manual()
        bl.encaminhar_para_roteiro(bitin)
        self.assertTrue(bitin["encaminhado_roteiro"])
        self.assertIn("data_encaminhado_roteiro", bitin)

    def test_nao_encaminha_bitin_ainda_em_rascunho(self) -> None:
        bitin = make_valid_bitin()
        with self.assertRaises(ValueError):
            bl.encaminhar_para_roteiro(bitin)

    def test_nao_encaminha_duas_vezes(self) -> None:
        bitin = make_bitin_enviado_manual()
        bl.encaminhar_para_roteiro(bitin)
        with self.assertRaises(ValueError):
            bl.encaminhar_para_roteiro(bitin)


class ConcluirProcessamentoTest(unittest.TestCase):
    """Setor Processos (2026-07-17) -- fecha a janela de reedição aberta por
    encaminhar_para_roteiro. Mesmo isolamento de EncaminharRoteiroTest acima."""

    def _bitin_encaminhado(self) -> dict:
        bitin = make_bitin_enviado_manual()
        bl.encaminhar_para_roteiro(bitin)
        return bitin

    def test_conclui_bitin_encaminhado(self) -> None:
        bitin = self._bitin_encaminhado()
        bl.concluir_processamento(bitin)
        self.assertTrue(bitin["processos_concluido"])
        self.assertIn("data_processos_concluido", bitin)

    def test_nao_conclui_bitin_ainda_nao_encaminhado(self) -> None:
        bitin = make_bitin_enviado_manual()
        with self.assertRaises(ValueError):
            bl.concluir_processamento(bitin)

    def test_nao_conclui_duas_vezes(self) -> None:
        bitin = self._bitin_encaminhado()
        bl.concluir_processamento(bitin)
        with self.assertRaises(ValueError):
            bl.concluir_processamento(bitin)


class ConcluirSemRoteiroTest(unittest.TestCase):
    """Alternativa a encaminhar_para_roteiro quando o BITin não precisa passar pelo Processos
    (2026-07-17, ver bitin_document.precisa_roteiro). Mesmo isolamento das classes acima."""

    def test_conclui_direto_sem_roteiro(self) -> None:
        bitin = make_bitin_enviado_manual()
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
        bitin = make_bitin_enviado_manual()
        bl.encaminhar_para_roteiro(bitin)
        with self.assertRaises(ValueError):
            bl.concluir_sem_roteiro(bitin)


class ConcluirBitinTest(unittest.TestCase):
    """Último passo do fluxo (2026-07-20) -- o Cadastro marca que já fez o cadastro/
    liberação de verdade no SAP; só a partir daqui o PDF fica disponível. Mesmo isolamento
    das classes acima."""

    def test_conclui_bitin_que_passou_pelo_processos(self) -> None:
        bitin = make_bitin_enviado_manual()
        bl.encaminhar_para_roteiro(bitin)
        bl.concluir_processamento(bitin)
        bl.concluir_bitin(bitin)
        self.assertTrue(bitin["bitin_cadastrado"])
        self.assertIn("data_cadastrado", bitin)

    def test_conclui_bitin_que_pulou_o_roteiro(self) -> None:
        bitin = make_bitin_enviado_manual()
        bl.concluir_sem_roteiro(bitin)
        bl.concluir_bitin(bitin)
        self.assertTrue(bitin["bitin_cadastrado"])

    def test_nao_conclui_bitin_que_ainda_nao_passou_pelo_roteiro(self) -> None:
        bitin = make_bitin_enviado_manual()
        with self.assertRaises(ValueError):
            bl.concluir_bitin(bitin)

    def test_nao_conclui_bitin_duas_vezes(self) -> None:
        bitin = make_bitin_enviado_manual()
        bl.concluir_sem_roteiro(bitin)
        bl.concluir_bitin(bitin)
        with self.assertRaises(ValueError):
            bl.concluir_bitin(bitin)


class EnviarWindchillTest(unittest.TestCase):
    """Última etapa de todas (2026-07-20, pedido explícito: "coloca uma ultima etapa na
    parte de cadastro que é: enviado pro windchill") -- mesmo isolamento das classes acima."""

    def test_envia_windchill_apos_cadastrado(self) -> None:
        bitin = make_bitin_enviado_manual()
        bl.concluir_sem_roteiro(bitin)
        bl.concluir_bitin(bitin)
        bl.enviar_windchill(bitin)
        self.assertTrue(bitin["windchill_enviado"])
        self.assertIn("data_windchill_enviado", bitin)

    def test_nao_envia_windchill_antes_de_cadastrar(self) -> None:
        bitin = make_bitin_enviado_manual()
        bl.concluir_sem_roteiro(bitin)
        with self.assertRaises(ValueError):
            bl.enviar_windchill(bitin)

    def test_nao_envia_windchill_duas_vezes(self) -> None:
        bitin = make_bitin_enviado_manual()
        bl.concluir_sem_roteiro(bitin)
        bl.concluir_bitin(bitin)
        bl.enviar_windchill(bitin)
        with self.assertRaises(ValueError):
            bl.enviar_windchill(bitin)


class ReverterWindchillTest(unittest.TestCase):
    """"Voltar BITin" (2026-07-20, pedido explícito: "lista dos bitins concluidos com opções
    de voltar bitin etc.") -- desfaz enviar_windchill, mesmo isolamento das classes acima."""

    def test_reverte_windchill_apos_enviado(self) -> None:
        bitin = make_bitin_enviado_manual()
        bl.concluir_sem_roteiro(bitin)
        bl.concluir_bitin(bitin)
        bl.enviar_windchill(bitin)
        bl.reverter_windchill(bitin)
        self.assertFalse(bitin["windchill_enviado"])
        self.assertIsNone(bitin["data_windchill_enviado"])

    def test_nao_reverte_windchill_antes_de_enviar(self) -> None:
        bitin = make_bitin_enviado_manual()
        bl.concluir_sem_roteiro(bitin)
        bl.concluir_bitin(bitin)
        with self.assertRaises(ValueError):
            bl.reverter_windchill(bitin)


if __name__ == "__main__":
    unittest.main()
