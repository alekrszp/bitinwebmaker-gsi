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


if __name__ == "__main__":
    unittest.main()
