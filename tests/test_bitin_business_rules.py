import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import bitin_business_rules as bbr  # noqa: E402
import bitin_document as bd  # noqa: E402

DOCUMENT_CONFIG_PATH = ROOT / "config" / "bitin_document_mapping.json"


def make_bitin(**overrides) -> dict:
    base = {
        "bitin": "P3301/26",
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
                    "dados_basicos": {},
                    "impactos_operacionais": {"alt": "-"},
                },
            }
        ],
    }
    base.update(overrides)
    return base


class ValidateBusinessRulesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.document_config = bd.load_config(DOCUMENT_CONFIG_PATH)

    def validate(self, bitin: dict) -> list[str]:
        return bbr.validate_business_rules(bitin, self.document_config)

    def test_bitin_sem_regras_especiais_passa(self) -> None:
        self.assertEqual(self.validate(make_bitin()), [])

    # --- Nota 2 (desenho aprovado) e Nota 17 (NCM aprovado fiscal) NÃO são mais validadas
    # aqui -- exigem confirmação externa que o sistema não tem como conferir, e não há
    # controle na UI pra marcar `desenho_aprovado`/`ncm_aprovado_fiscal` (decisão do usuário,
    # 2026-07-15). Ver docstring de bitin_business_rules.py e o popover de ajuda da aba BITin.

    # --- Nota 8: sucateamento exige centro de custo ---

    def test_nota8_sucateamento_sem_centro_custo_falha(self) -> None:
        # Checklist é 100% manual agora (2026-07-15) -- Est=S não liga mais o item 22 sozinho,
        # precisa de override explícito. Sem descrição preenchida ali, a regra falha.
        bitin = make_bitin()
        bitin["materiais"][0]["alteracoes"]["impactos_operacionais"] = {"alt": "-", "est": "S"}
        bitin["checklist_overrides"] = {"22": True}
        errors = self.validate(bitin)
        self.assertTrue(any("centro de custo" in e["message"].lower() for e in errors))
        self.assertTrue(any(e["field"] == "checklist_descricoes.22" for e in errors))

    def test_nota8_sucateamento_com_centro_custo_passa(self) -> None:
        bitin = make_bitin()
        bitin["materiais"][0]["alteracoes"]["impactos_operacionais"] = {"alt": "-", "est": "S"}
        bitin["checklist_overrides"] = {"22": True}
        bitin["checklist_descricoes"] = {"22": "Centro de custo 1010, conta razão 99999"}
        # Removendo o dados_basicos herdado de make_bitin (descricao de!=para geraria
        # inconsistência com Alt="-"); aqui o foco é só a regra de sucateamento.
        bitin["materiais"][0]["alteracoes"]["dados_basicos"] = {}
        self.assertEqual(self.validate(bitin), [])

    def test_nota8_item_22_nao_marcado_manualmente_nao_exige_nada(self) -> None:
        # Est=S sozinho (sem override manual do item 22) não ativa mais a regra -- a checklist
        # é responsabilidade exclusiva do engenheiro (2026-07-15).
        bitin = make_bitin()
        bitin["materiais"][0]["alteracoes"]["impactos_operacionais"] = {"alt": "-", "est": "S"}
        bitin["materiais"][0]["alteracoes"]["dados_basicos"] = {}
        self.assertEqual(self.validate(bitin), [])

    def test_nota8_estoque_diferente_de_s_nao_exige_nada(self) -> None:
        bitin = make_bitin()
        bitin["materiais"][0]["alteracoes"]["impactos_operacionais"] = {"alt": "-", "est": "R"}
        bitin["materiais"][0]["alteracoes"]["dados_basicos"] = {}
        self.assertEqual(self.validate(bitin), [])

    # --- Nota 10: ordem de cliente ---

    def test_nota10_oc_sem_entrada_correspondente_falha(self) -> None:
        bitin = make_bitin()
        bitin["materiais"][0]["alteracoes"]["impactos_operacionais"] = {"alt": "-", "oc": "X"}
        errors = self.validate(bitin)
        self.assertTrue(any("ordem_cliente" in e["message"] for e in errors))

    def test_nota10_oc_com_entrada_correspondente_passa(self) -> None:
        bitin = make_bitin()
        bitin["materiais"][0]["alteracoes"]["impactos_operacionais"] = {"alt": "-", "oc": "X"}
        bitin["materiais"][0]["alteracoes"]["dados_basicos"] = {}
        bitin["ordem_cliente"] = [{"codigo": "CT30-7103", "descricao": "x"}]
        self.assertEqual(self.validate(bitin), [])

    # --- Enum: valores válidos do ANEXO A do POP (buraco que motivou essa mudança:
    # antes, qualquer string em alt/est/lp/pre/oc/of passava despercebida) ---

    def test_enum_alt_invalido_falha_com_codigo_estavel(self) -> None:
        bitin = make_bitin()
        bitin["materiais"][0]["alteracoes"]["impactos_operacionais"]["alt"] = "XYZ"
        errors = self.validate(bitin)
        self.assertTrue(any(e["code"] == "invalid_alt_value" for e in errors))
        self.assertTrue(any("materiais[0].impactos_operacionais.alt" == e["field"] for e in errors))

    def test_enum_est_invalido_falha(self) -> None:
        bitin = make_bitin()
        bitin["materiais"][0]["alteracoes"]["impactos_operacionais"]["est"] = "Z"
        errors = self.validate(bitin)
        self.assertTrue(any(e["code"] == "invalid_est_value" for e in errors))

    def test_enum_valores_validos_do_pop_passam(self) -> None:
        bitin = make_bitin()
        bitin["materiais"][0]["alteracoes"]["impactos_operacionais"] = {
            "alt": "-", "est": "U", "esp": "-", "lp": "I", "pre": "PÇ", "oc": "-", "of": "-",
        }
        errors = self.validate(bitin)
        self.assertFalse(any(e["code"].startswith("invalid_") for e in errors))

    # --- Regras gerais (não dependem de código específico) ---

    def test_geral_codigo_e_centro_duplicados_falha(self) -> None:
        bitin = make_bitin()
        bitin["materiais"].append(dict(bitin["materiais"][0]))
        errors = self.validate(bitin)
        self.assertTrue(any("duplicad" in e["message"] for e in errors))

    def test_geral_mesmo_codigo_centros_diferentes_nao_falha(self) -> None:
        """Um mesmo código de material pode legitimamente precisar de alteração em mais
        de um centro no mesmo BITin (ex.: material 8661 em 2001/2003/2005/2006)."""
        bitin = make_bitin()
        outro_centro = dict(bitin["materiais"][0])
        outro_centro["centro"] = "2003"
        bitin["materiais"].append(outro_centro)
        errors = self.validate(bitin)
        self.assertFalse(any("duplicad" in e["message"] for e in errors))

    def test_geral_campo_de_igual_para_falha(self) -> None:
        bitin = make_bitin()
        bitin["materiais"][0]["alteracoes"]["dados_basicos"]["descricao"] = {"de": "X", "para": "X"}
        errors = self.validate(bitin)
        self.assertTrue(any("iguais" in e["message"] for e in errors))

    def test_geral_alt_sem_alteracao_mas_ha_mudancas_falha(self) -> None:
        bitin = make_bitin()
        bitin["materiais"][0]["alteracoes"]["dados_basicos"]["descricao"] = {"de": "X", "para": "Y"}
        # alt continua "-" (sem alteração) mas descricao realmente mudou -> inconsistente.
        errors = self.validate(bitin)
        self.assertTrue(any("confira se o Alt declarado" in e["message"] for e in errors))

    def test_geral_alt_desenho_sem_revisao_mudando_falha(self) -> None:
        bitin = make_bitin()
        bitin["materiais"][0]["alteracoes"]["impactos_operacionais"]["alt"] = "D/-"
        bitin["materiais"][0]["desenho_aprovado"] = True
        errors = self.validate(bitin)
        self.assertTrue(any("Alt=D/-" in e["message"] and "nivel_revisao" in e["message"] for e in errors))

    def test_geral_alt_desenho_com_revisao_mudando_passa_essa_regra(self) -> None:
        bitin = make_bitin()
        bitin["materiais"][0]["desenho_aprovado"] = True
        bitin["materiais"][0]["alteracoes"]["dados_basicos"] = {
            "nivel_revisao": {"de": "A", "para": "B"},
        }
        bitin["materiais"][0]["alteracoes"]["impactos_operacionais"]["alt"] = "D/-"
        self.assertEqual(self.validate(bitin), [])


if __name__ == "__main__":
    unittest.main()
