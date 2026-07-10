"""Testa a API de verdade via FastAPI TestClient -- exercita o app real (rotas, FastAPI
validation, orquestração), não só as funções de scripts/ isoladas. Usa SQLite em memória
no lugar do Postgres e mongomock-motor no lugar do MongoDB (não há nenhum dos dois bancos
reais disponíveis neste ambiente -- ver docs/BACKEND.md)."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402
from mongomock_motor import AsyncMongoMockClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from backend.db.mongodb import get_mongo_db  # noqa: E402
from backend.db.session import Base, get_db  # noqa: E402
from backend.main import app  # noqa: E402


def make_bitin_content(**overrides) -> dict:
    base = {
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
    base.update(overrides)
    return base


class BitinApiTest(unittest.TestCase):
    def setUp(self) -> None:
        # SQLite em memória isolado por teste. StaticPool: força todas as "conexões" do
        # pool a compartilhar a mesma conexão física -- senão cada checkout do pool abre
        # um banco em memória NOVO e vazio (pegadinha clássica do SQLite in-memory).
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        TestSessionLocal = sessionmaker(bind=self.engine)
        Base.metadata.create_all(bind=self.engine)

        def override_get_db():
            db = TestSessionLocal()
            try:
                yield db
            finally:
                db.close()

        mongo_client = AsyncMongoMockClient()
        mongo_test_db = mongo_client["bitin_test_db"]

        async def override_get_mongo_db():
            return mongo_test_db

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_mongo_db] = override_get_mongo_db
        self.client = TestClient(app)  # sem "with": não dispara o lifespan (Mongo real)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.engine.dispose()

    def test_criar_rascunho(self) -> None:
        resp = self.client.post("/api/v1/bitins/draft", json={"content": make_bitin_content()})
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertEqual(body["status"], "rascunho")
        self.assertIsNone(body["codigo"])
        self.assertIn("mongo_id", body)

    def test_atualizar_rascunho_existente(self) -> None:
        create_resp = self.client.post("/api/v1/bitins/draft", json={"content": make_bitin_content()})
        mongo_id = create_resp.json()["mongo_id"]

        update_resp = self.client.post(
            "/api/v1/bitins/draft",
            json={"mongo_id": mongo_id, "content": make_bitin_content(motivo="Motivo atualizado")},
        )
        self.assertEqual(update_resp.status_code, 200, update_resp.text)
        self.assertEqual(update_resp.json()["content"]["motivo"], "Motivo atualizado")
        self.assertEqual(update_resp.json()["mongo_id"], mongo_id)  # não cria um novo

    def test_rascunho_incompleto_nao_bloqueia_salvar(self) -> None:
        """Liberdade de edição: salvar rascunho não valida nada, mesmo incompleto."""
        conteudo_incompleto = {"produto": "x"}  # falta quase tudo
        resp = self.client.post("/api/v1/bitins/draft", json={"content": conteudo_incompleto})
        self.assertEqual(resp.status_code, 200, resp.text)

    def test_buscar_bitin_por_id(self) -> None:
        create_resp = self.client.post("/api/v1/bitins/draft", json={"content": make_bitin_content()})
        mongo_id = create_resp.json()["mongo_id"]

        get_resp = self.client.get(f"/api/v1/bitins/{mongo_id}")
        self.assertEqual(get_resp.status_code, 200)
        self.assertEqual(get_resp.json()["mongo_id"], mongo_id)

    def test_buscar_bitin_inexistente_404(self) -> None:
        resp = self.client.get("/api/v1/bitins/nao-existe")
        self.assertEqual(resp.status_code, 404)

    def test_listar_bitins(self) -> None:
        self.client.post("/api/v1/bitins/draft", json={"content": make_bitin_content()})
        self.client.post("/api/v1/bitins/draft", json={"content": make_bitin_content()})
        resp = self.client.get("/api/v1/bitins")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 2)

    def test_deletar_rascunho(self) -> None:
        create_resp = self.client.post("/api/v1/bitins/draft", json={"content": make_bitin_content()})
        mongo_id = create_resp.json()["mongo_id"]

        del_resp = self.client.delete(f"/api/v1/bitins/{mongo_id}")
        self.assertEqual(del_resp.status_code, 200)

        get_resp = self.client.get(f"/api/v1/bitins/{mongo_id}")
        self.assertEqual(get_resp.status_code, 404)

    def test_enviar_bitin_invalido_devolve_erros_estruturados(self) -> None:
        """O ponto-chave: enviar roda a validação real e devolve erros no formato
        {field, code, message}, sem travar nem gerar número."""
        conteudo = make_bitin_content()
        del conteudo["solicitante"]  # obrigatório
        create_resp = self.client.post("/api/v1/bitins/draft", json={"content": conteudo})
        mongo_id = create_resp.json()["mongo_id"]

        enviar_resp = self.client.post(f"/api/v1/bitins/{mongo_id}/enviar")
        self.assertEqual(enviar_resp.status_code, 200)
        body = enviar_resp.json()
        self.assertFalse(body["ok"])
        self.assertTrue(any(e["code"] == "required_field_missing" for e in body["errors"]))
        self.assertIsNone(body["bitin"])

        # confirma que continua rascunho (não travou, não gerou número)
        get_resp = self.client.get(f"/api/v1/bitins/{mongo_id}")
        self.assertEqual(get_resp.json()["status"], "rascunho")

    def test_enviar_bitin_valido_gera_numero_e_trava(self) -> None:
        create_resp = self.client.post("/api/v1/bitins/draft", json={"content": make_bitin_content()})
        mongo_id = create_resp.json()["mongo_id"]

        enviar_resp = self.client.post(f"/api/v1/bitins/{mongo_id}/enviar")
        self.assertEqual(enviar_resp.status_code, 200, enviar_resp.text)
        body = enviar_resp.json()
        self.assertTrue(body["ok"], body["errors"])
        self.assertEqual(body["bitin"]["status"], "enviado")
        self.assertRegex(body["bitin"]["codigo"], r"^P\d+/\d{2}$")

    def test_enviar_bitin_ja_enviado_falha(self) -> None:
        create_resp = self.client.post("/api/v1/bitins/draft", json={"content": make_bitin_content()})
        mongo_id = create_resp.json()["mongo_id"]
        self.client.post(f"/api/v1/bitins/{mongo_id}/enviar")

        segunda_tentativa = self.client.post(f"/api/v1/bitins/{mongo_id}/enviar")
        self.assertEqual(segunda_tentativa.status_code, 400)

    def test_nao_pode_editar_bitin_enviado(self) -> None:
        create_resp = self.client.post("/api/v1/bitins/draft", json={"content": make_bitin_content()})
        mongo_id = create_resp.json()["mongo_id"]
        self.client.post(f"/api/v1/bitins/{mongo_id}/enviar")

        update_resp = self.client.post(
            "/api/v1/bitins/draft",
            json={"mongo_id": mongo_id, "content": make_bitin_content(motivo="Tentando editar")},
        )
        self.assertEqual(update_resp.status_code, 400)

    def test_nao_pode_deletar_bitin_enviado(self) -> None:
        create_resp = self.client.post("/api/v1/bitins/draft", json={"content": make_bitin_content()})
        mongo_id = create_resp.json()["mongo_id"]
        self.client.post(f"/api/v1/bitins/{mongo_id}/enviar")

        del_resp = self.client.delete(f"/api/v1/bitins/{mongo_id}")
        self.assertEqual(del_resp.status_code, 400)

    def test_numeros_sequenciais_incrementam(self) -> None:
        codigos = []
        for _ in range(3):
            create_resp = self.client.post("/api/v1/bitins/draft", json={"content": make_bitin_content()})
            mongo_id = create_resp.json()["mongo_id"]
            enviar_resp = self.client.post(f"/api/v1/bitins/{mongo_id}/enviar")
            codigos.append(enviar_resp.json()["bitin"]["codigo"])

        sequenciais = [int(c.split("/")[0][1:]) for c in codigos]
        self.assertEqual(sequenciais, sorted(sequenciais))
        self.assertEqual(len(set(codigos)), 3)  # todos únicos

    def test_setor_invalido_falha_sem_gerar_numero(self) -> None:
        create_resp = self.client.post(
            "/api/v1/bitins/draft", json={"content": make_bitin_content(setor="Setor Inexistente")}
        )
        mongo_id = create_resp.json()["mongo_id"]
        enviar_resp = self.client.post(f"/api/v1/bitins/{mongo_id}/enviar")
        body = enviar_resp.json()
        self.assertFalse(body["ok"])
        self.assertTrue(any(e["code"] == "invalid_setor_value" for e in body["errors"]))

    def test_resumo_bitin(self) -> None:
        create_resp = self.client.post("/api/v1/bitins/draft", json={"content": make_bitin_content()})
        mongo_id = create_resp.json()["mongo_id"]

        resumo_resp = self.client.get(f"/api/v1/bitins/{mongo_id}/resumo")
        self.assertEqual(resumo_resp.status_code, 200, resumo_resp.text)
        body = resumo_resp.json()
        self.assertEqual(len(body["checklist"]), 22)
        self.assertEqual(body["materiais"][0]["codigo_material"], "CT30-7103")

    def test_enviar_bitin_completamente_vazio_nao_quebra(self) -> None:
        """Entrada degenerada (content={}) não pode derrubar a API com 500 -- deve
        devolver erros estruturados normalmente, como qualquer outro rascunho inválido."""
        create_resp = self.client.post("/api/v1/bitins/draft", json={"content": {}})
        mongo_id = create_resp.json()["mongo_id"]

        enviar_resp = self.client.post(f"/api/v1/bitins/{mongo_id}/enviar")
        self.assertEqual(enviar_resp.status_code, 200, enviar_resp.text)
        body = enviar_resp.json()
        self.assertFalse(body["ok"])
        self.assertTrue(len(body["errors"]) >= 1)
        self.assertIsNone(body["bitin"])

    def test_listar_com_filtro_status(self) -> None:
        rascunho_resp = self.client.post("/api/v1/bitins/draft", json={"content": make_bitin_content()})
        enviado_resp = self.client.post("/api/v1/bitins/draft", json={"content": make_bitin_content()})
        self.client.post(f"/api/v1/bitins/{enviado_resp.json()['mongo_id']}/enviar")

        resp = self.client.get("/api/v1/bitins", params={"status": "rascunho"})
        self.assertEqual(resp.status_code, 200)
        mongo_ids = [b["mongo_id"] for b in resp.json()]
        self.assertIn(rascunho_resp.json()["mongo_id"], mongo_ids)
        self.assertNotIn(enviado_resp.json()["mongo_id"], mongo_ids)

    def test_listar_com_filtro_termo(self) -> None:
        self.client.post(
            "/api/v1/bitins/draft", json={"content": make_bitin_content(solicitante="Fulano Especial")}
        )
        self.client.post("/api/v1/bitins/draft", json={"content": make_bitin_content(solicitante="Outro")})

        resp = self.client.get("/api/v1/bitins", params={"termo": "especial"})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["content"]["solicitante"], "Fulano Especial")

    def test_listar_com_paginacao(self) -> None:
        for _ in range(5):
            self.client.post("/api/v1/bitins/draft", json={"content": make_bitin_content()})

        resp = self.client.get("/api/v1/bitins", params={"limit": 2, "skip": 0})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 2)

        resp_all = self.client.get("/api/v1/bitins", params={"limit": 100, "skip": 0})
        self.assertEqual(len(resp_all.json()), 5)

    def test_criar_draft_sem_content_retorna_422(self) -> None:
        resp = self.client.post("/api/v1/bitins/draft", json={})
        self.assertEqual(resp.status_code, 422)

    def test_resumo_com_lista_tecnica(self) -> None:
        conteudo = make_bitin_content()
        conteudo["materiais"][0]["alteracoes"]["lista_tecnica"] = [
            {"operacao": "alterar", "codigo_filho": "COMP-1", "quantidade_de": "1", "quantidade_para": "2"}
        ]
        create_resp = self.client.post("/api/v1/bitins/draft", json={"content": conteudo})
        mongo_id = create_resp.json()["mongo_id"]

        resumo_resp = self.client.get(f"/api/v1/bitins/{mongo_id}/resumo")
        self.assertEqual(resumo_resp.status_code, 200, resumo_resp.text)
        lista_tecnica = resumo_resp.json()["materiais"][0]["lista_tecnica"]
        self.assertEqual(lista_tecnica[0]["codigo_filho"], "COMP-1")

    def test_enviar_com_lista_tecnica_invalida_falha(self) -> None:
        conteudo = make_bitin_content()
        conteudo["materiais"][0]["alteracoes"]["lista_tecnica"] = [
            {"operacao": "alterar", "quantidade_para": "2"}  # falta codigo_filho
        ]
        create_resp = self.client.post("/api/v1/bitins/draft", json={"content": conteudo})
        mongo_id = create_resp.json()["mongo_id"]

        enviar_resp = self.client.post(f"/api/v1/bitins/{mongo_id}/enviar")
        self.assertEqual(enviar_resp.status_code, 200, enviar_resp.text)
        body = enviar_resp.json()
        self.assertFalse(body["ok"])
        self.assertTrue(any(
            e["code"] == "required_field_missing" and "codigo_filho" in e["field"]
            for e in body["errors"]
        ))


if __name__ == "__main__":
    unittest.main()
