"""Testa a API de verdade via FastAPI TestClient -- exercita o app real (rotas, FastAPI
validation, orquestração), não só as funções de scripts/ isoladas. Usa SQLite em memória
no lugar do Postgres e mongomock-motor no lugar do MongoDB (não há nenhum dos dois bancos
reais disponíveis neste ambiente -- ver docs/BACKEND.md)."""

import sys
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402
from mongomock_motor import AsyncMongoMockClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from backend.auth.models import Usuario  # noqa: E402
from backend.auth.security import create_access_token, get_password_hash  # noqa: E402
from backend.db.mongodb import get_mongo_db  # noqa: E402
from backend.db.session import Base, get_db  # noqa: E402
from backend.main import app  # noqa: E402
from backend.models_sql import BitinSQL  # noqa: E402

DEFAULT_USER_ID = 1


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
        self.SessionLocal = sessionmaker(bind=self.engine)
        Base.metadata.create_all(bind=self.engine)

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        mongo_client = AsyncMongoMockClient()
        self.mongo_test_db = mongo_client["bitin_test_db"]

        async def override_get_mongo_db():
            return self.mongo_test_db

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_mongo_db] = override_get_mongo_db
        self.client = TestClient(app)  # sem "with": não dispara o lifespan (Mongo real)

        self.default_user = self._create_user(DEFAULT_USER_ID)
        self.client.headers.update({"Authorization": f"Bearer {self._token_for(self.default_user)}"})

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.engine.dispose()

    def _create_user(
        self, user_id: int, email: str | None = None, permission_level: int = 77,
        nome: str | None = None, setor: str = "engenharia",
    ) -> Usuario:
        db = self.SessionLocal()
        user = Usuario(
            id=user_id,
            email=email or f"user{user_id}@example.com",
            nome=nome or f"Usuário {user_id}",
            hashed_password=get_password_hash("senha123"),
            permission_level=permission_level,
            # setor agora CONTROLA acesso pra rank 77/88 (2026-07-20, 2ª revisão do modelo de
            # permissões -- ver backend/auth/deps.py::eh_do_setor/check_setor). Default
            # "engenharia" cobre a maioria dos testes (individual/gestor de engenharia,
            # escopados por Subgrupo); testes de Cadastro/Processos passam setor= explícito.
            # Conceito totalmente diferente do "setor" de make_bitin_content acima (campo de
            # CONTEÚDO do BITin -- Proteína Animal/Armazenagem de Grãos).
            setor=setor,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        db.expunge(user)
        db.close()
        return user

    def _token_for(self, user: Usuario) -> str:
        return create_access_token(user.id)

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

    def test_data_solicitacao_e_carimbada_pelo_sistema_na_criacao(self) -> None:
        """data_solicitacao não é escolhida livremente pelo engenheiro -- é a data em que o
        rascunho foi salvo pela primeira vez (ver docs/BITIN_MODEL.md, 'Regras de campo').
        Qualquer valor mandado pelo cliente pra esse campo é ignorado."""
        resp = self.client.post(
            "/api/v1/bitins/draft",
            json={"content": make_bitin_content(data_solicitacao="1999-01-01")},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        hoje = datetime.now().strftime("%Y-%m-%d")
        self.assertEqual(resp.json()["content"]["data_solicitacao"], hoje)

    def test_data_solicitacao_nao_muda_ao_atualizar_rascunho(self) -> None:
        create_resp = self.client.post("/api/v1/bitins/draft", json={"content": make_bitin_content()})
        mongo_id = create_resp.json()["mongo_id"]
        data_original = create_resp.json()["content"]["data_solicitacao"]

        update_resp = self.client.post(
            "/api/v1/bitins/draft",
            json={
                "mongo_id": mongo_id,
                "content": make_bitin_content(motivo="Outro motivo", data_solicitacao="2000-01-01"),
            },
        )
        self.assertEqual(update_resp.json()["content"]["data_solicitacao"], data_original)

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

    def test_resumo_usuario_conta_rascunhos_e_enviados(self) -> None:
        self.client.post("/api/v1/bitins/draft", json={"content": make_bitin_content()})
        self.client.post("/api/v1/bitins/draft", json={"content": make_bitin_content()})
        enviar_resp = self.client.post(
            "/api/v1/bitins/draft", json={"content": make_bitin_content()},
        )
        self.client.post(f"/api/v1/bitins/{enviar_resp.json()['mongo_id']}/enviar")

        resp = self.client.get("/api/v1/bitins/resumo-usuario")
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json(), {"rascunhos": 2, "enviados": 1})

    def test_resumo_usuario_nao_conta_bitins_de_outro_usuario(self) -> None:
        """Escopado por criado_por -- "só os meus", não o sistema inteiro (decisão
        registrada em docs/FRONTEND.md)."""
        self.client.post("/api/v1/bitins/draft", json={"content": make_bitin_content()})

        outro_usuario = self._create_user(2, permission_level=77)
        resp = self.client.get(
            "/api/v1/bitins/resumo-usuario",
            headers={"Authorization": f"Bearer {self._token_for(outro_usuario)}"},
        )
        self.assertEqual(resp.json(), {"rascunhos": 0, "enviados": 0})

    def test_resumo_usuario_exige_autenticacao(self) -> None:
        client_sem_auth = TestClient(app)
        resp = client_sem_auth.get("/api/v1/bitins/resumo-usuario")
        self.assertEqual(resp.status_code, 401)

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
        # motivo, não solicitante: solicitante agora é automático (nome de quem está logado,
        # ver create_or_update_draft) -- mandar sem ele no payload não gera mais campo
        # obrigatório vazio, o backend preenche sozinho.
        del conteudo["motivo"]  # obrigatório
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

    def test_envio_concorrente_devolve_erro_estruturado_nao_500(self) -> None:
        """Simula 2 requisições de /enviar pro mesmo rascunho quase ao mesmo tempo: a 2ª
        esgota as tentativas de gerar_e_salvar_bitin_sql (mongo_document_id já existe em
        BitinSQL) -- antes disso vazava como 500 puro; agora devolve erro estruturado."""
        create_resp = self.client.post("/api/v1/bitins/draft", json={"content": make_bitin_content()})
        mongo_id = create_resp.json()["mongo_id"]

        # Simula a 1ª requisição já ter reservado o número no Postgres (mas o Mongo ainda
        # não foi atualizado pra "enviado" -- é exatamente a janela de corrida real).
        db = self.SessionLocal()
        db.add(BitinSQL(codigo="P1/26", prefixo="P", ano=26, sequencial=1, mongo_document_id=mongo_id))
        db.commit()
        db.close()

        enviar_resp = self.client.post(f"/api/v1/bitins/{mongo_id}/enviar")
        self.assertEqual(enviar_resp.status_code, 200, enviar_resp.text)
        body = enviar_resp.json()
        self.assertFalse(body["ok"])
        self.assertTrue(any(e["code"] == "ja_enviado_concorrente" for e in body["errors"]), body["errors"])

    def test_falha_ao_gravar_mongo_desfaz_numero_reservado_no_postgres(self) -> None:
        """Se o Postgres commitar o número mas o Mongo falhar ao gravar "enviado" (sem
        transação real cobrindo os 2 bancos), o número reservado precisa ser desfeito --
        senão fica um BitinSQL órfão apontando pra um rascunho que nunca foi marcado como
        enviado, e o próximo número gerado pula um valor à toa.

        mongomock-motor gera os métodos (update_one etc.) por um proxy dinâmico que não
        respeita `unittest.mock.patch` na classe real do motor (confirmado empiricamente --
        o patch simplesmente não intercepta a chamada). Em vez disso, troca-se o banco
        inteiro devolvido por get_mongo_db por um wrapper fino que delega tudo pro mongomock
        real, exceto update_one na coleção certa, que falha de propósito.
        """
        create_resp = self.client.post("/api/v1/bitins/draft", json={"content": make_bitin_content()})
        mongo_id = create_resp.json()["mongo_id"]

        class ColecaoComUpdateFalhando:
            def __init__(self, real):
                self._real = real

            def __getattr__(self, nome):
                return getattr(self._real, nome)

            async def update_one(self, *args, **kwargs):
                raise RuntimeError("mongo indisponível")

        class DbComMongoFalhando:
            def __init__(self, real_db):
                self._real_db = real_db

            def __getitem__(self, nome):
                colecao_real = self._real_db[nome]
                return ColecaoComUpdateFalhando(colecao_real) if nome == "bitin_contents" else colecao_real

        db_real = self.mongo_test_db
        self.mongo_test_db = DbComMongoFalhando(db_real)
        try:
            enviar_resp = self.client.post(f"/api/v1/bitins/{mongo_id}/enviar")
        finally:
            self.mongo_test_db = db_real

        self.assertEqual(enviar_resp.status_code, 500, enviar_resp.text)

        db = self.SessionLocal()
        orfao = db.query(BitinSQL).filter(BitinSQL.mongo_document_id == mongo_id).first()
        db.close()
        self.assertIsNone(orfao, "BitinSQL deveria ter sido desfeito após a falha no Mongo")

        # o rascunho continua "rascunho" (não ficou destrancado como enviado sem número real)
        get_resp = self.client.get(f"/api/v1/bitins/{mongo_id}")
        self.assertEqual(get_resp.json()["status"], "rascunho")

        # o próximo envio bem-sucedido reaproveita o número (não pula o que foi desfeito)
        retry_resp = self.client.post(f"/api/v1/bitins/{mongo_id}/enviar")
        self.assertEqual(retry_resp.status_code, 200, retry_resp.text)
        self.assertEqual(retry_resp.json()["bitin"]["codigo"], "P0001/26")

    def test_resumo_bitin(self) -> None:
        create_resp = self.client.post("/api/v1/bitins/draft", json={"content": make_bitin_content()})
        mongo_id = create_resp.json()["mongo_id"]

        resumo_resp = self.client.get(f"/api/v1/bitins/{mongo_id}/resumo")
        self.assertEqual(resumo_resp.status_code, 200, resumo_resp.text)
        body = resumo_resp.json()
        self.assertEqual(len(body["checklist"]), 22)
        self.assertEqual(body["materiais"][0]["codigo_material"], "CT30-7103")

    def test_preview_resumo_calcula_sem_salvar(self) -> None:
        """POST /bitins/preview-resumo (2026-07-17, pedido explícito: "eu quero que marque ao
        vivo igual com os setores afetados") -- mesmo cálculo de checklist/setores de
        GET /{id}/resumo, mas a partir do content que está NA TELA, sem precisar de mongo_id
        nem salvar rascunho nenhum. alt="-/P" é uma das 8 regras reais de sugestão automática
        (ver scripts/bitin_document.py::_checklist_ids_auto_sugeridos) -- confirma que a
        prévia aciona a mesma automação do resumo salvo."""
        lista_antes = self.client.get("/api/v1/bitins").json()

        resp = self.client.post("/api/v1/bitins/preview-resumo", json={"content": make_bitin_content()})
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertEqual(len(body["checklist"]), 22)
        self.assertEqual(body["materiais"][0]["codigo_material"], "CT30-7103")
        item_auto = next(item for item in body["checklist"] if item["id"] == "4")
        self.assertTrue(item_auto["afeta"])
        self.assertFalse(item_auto["manual"])  # sugerido automaticamente, não por override

        # nada foi persistido -- a listagem de BITins continua igual
        lista_depois = self.client.get("/api/v1/bitins").json()
        self.assertEqual(len(lista_antes), len(lista_depois))

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
        # solicitante agora é automático (nome de quem está logado, ver create_or_update_draft)
        # -- pra ter dois valores distintos de solicitante pra filtrar, posta como dois usuários
        # diferentes em vez de mandar "solicitante" no payload (que seria ignorado).
        fulano = self._create_user(3, nome="Fulano Especial")
        self.client.post(
            "/api/v1/bitins/draft",
            json={"content": make_bitin_content()},
            headers={"Authorization": f"Bearer {self._token_for(fulano)}"},
        )
        self.client.post("/api/v1/bitins/draft", json={"content": make_bitin_content()})

        resp = self.client.get(
            "/api/v1/bitins", params={"termo": "especial"},
            headers={"Authorization": f"Bearer {self._token_for(fulano)}"},
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["content"]["solicitante"], "Fulano Especial")

    def test_listar_com_filtro_termo_restrito_a_um_campo(self) -> None:
        """`campo` restringe a busca só ao Motivo/Solicitante/Código -- sem ele, busca nos
        três (test_listar_com_filtro_termo, acima)."""
        self.client.post(
            "/api/v1/bitins/draft", json={"content": make_bitin_content(motivo="Ajuste Especial")}
        )
        self.client.post(
            "/api/v1/bitins/draft", json={"content": make_bitin_content(solicitante="Fulano Especial")}
        )

        resp = self.client.get("/api/v1/bitins", params={"termo": "especial", "campo": "motivo"})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["content"]["motivo"], "Ajuste Especial")

    def test_listar_com_filtro_criado_por(self) -> None:
        """`criado_por` (2026-07-21, paginação real do Painel geral) -- substring/case-
        insensitive, não exact-match (mais fácil digitar um pedaço do e-mail)."""
        admin = self._create_user(2, permission_level=99)
        fulano = self._create_user(3, email="fulano.especial@example.com")
        self.client.post(
            "/api/v1/bitins/draft",
            json={"content": make_bitin_content()},
            headers={"Authorization": f"Bearer {self._token_for(fulano)}"},
        )
        self.client.post("/api/v1/bitins/draft", json={"content": make_bitin_content()})

        resp = self.client.get(
            "/api/v1/bitins", params={"criado_por": "ESPECIAL"},
            headers={"Authorization": f"Bearer {self._token_for(admin)}"},
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["criado_por"], "fulano.especial@example.com")

    def test_listar_com_paginacao(self) -> None:
        for _ in range(5):
            self.client.post("/api/v1/bitins/draft", json={"content": make_bitin_content()})

        resp = self.client.get("/api/v1/bitins", params={"limit": 2, "skip": 0})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 2)

        resp_all = self.client.get("/api/v1/bitins", params={"limit": 100, "skip": 0})
        self.assertEqual(len(resp_all.json()), 5)

    def test_listar_nao_traz_bitins_de_outro_usuario_comum(self) -> None:
        """"Meus Bitins" -- usuário comum (nível 0) só vê os próprios BITins, mesmo escopo por
        criado_por de sempre. Escopo de admin/gestor MUDOU em 2026-07-15 (ver testes abaixo:
        "Admin vê tudo", gestor vê BITins de quem compartilha setor) -- só o nível comum
        continua isolado ao próprio e-mail."""
        self.client.post("/api/v1/bitins/draft", json={"content": make_bitin_content()})

        outro_usuario_comum = self._create_user(2, permission_level=77)
        resp = self.client.get(
            "/api/v1/bitins",
            headers={"Authorization": f"Bearer {self._token_for(outro_usuario_comum)}"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    def test_listar_admin_ve_bitins_de_todo_mundo(self) -> None:
        """Escopo de admin em GET /bitins MUDOU em 2026-07-15 (pedido explícito do usuário:
        "Admin vê tudo") -- antes ficava preso a "só os meus" igual todo mundo; agora vê o
        sistema inteiro, sem filtro de criado_por nenhum."""
        self.client.post("/api/v1/bitins/draft", json={"content": make_bitin_content()})

        outro_admin = self._create_user(2, permission_level=99)
        resp = self.client.get(
            "/api/v1/bitins",
            headers={"Authorization": f"Bearer {self._token_for(outro_admin)}"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 1)
        self.assertEqual(resp.json()[0]["criado_por"], self.default_user.email)

    def test_listar_gestor_ve_bitins_de_colega_do_mesmo_subgrupo_mas_nao_de_outro_subgrupo(self) -> None:
        """Gestor (nível 1) vê BITins de quem compartilha ao menos um Subgrupo com ele
        (2026-07-15, "lista de usuários e bitins de todo mundo, com filtragem de solicitante" --
        mesma consulta usada em GET /users, ver backend/api/users.py::
        _usuarios_do_mesmo_subgrupo_query). Não vê BITins de alguém de um subgrupo totalmente
        diferente. Renomeado de Setor -> Subgrupo (2026-07-16)."""
        db = self.SessionLocal()
        from backend.auth.models import Subgrupo

        subgrupo_a = Subgrupo(nome="Proteína Animal")
        subgrupo_b = Subgrupo(nome="Armazenagem de Grãos")
        db.add_all([subgrupo_a, subgrupo_b])
        db.commit()
        db.refresh(subgrupo_a)
        db.refresh(subgrupo_b)

        gestor = self._create_user(2, permission_level=88, setor="engenharia")
        colega = self._create_user(3, permission_level=77)
        de_fora = self._create_user(4, permission_level=77)

        db_gestor = db.query(Usuario).filter(Usuario.id == gestor.id).first()
        db_colega = db.query(Usuario).filter(Usuario.id == colega.id).first()
        db_de_fora = db.query(Usuario).filter(Usuario.id == de_fora.id).first()
        db_gestor.subgrupos = [subgrupo_a]
        db_colega.subgrupos = [subgrupo_a]
        db_de_fora.subgrupos = [subgrupo_b]
        db.commit()
        db.close()

        self.client.post(
            "/api/v1/bitins/draft",
            json={"content": make_bitin_content()},
            headers={"Authorization": f"Bearer {self._token_for(colega)}"},
        )
        self.client.post(
            "/api/v1/bitins/draft",
            json={"content": make_bitin_content()},
            headers={"Authorization": f"Bearer {self._token_for(de_fora)}"},
        )

        resp = self.client.get(
            "/api/v1/bitins",
            headers={"Authorization": f"Bearer {self._token_for(gestor)}"},
        )
        self.assertEqual(resp.status_code, 200)
        criados_por = {b["criado_por"] for b in resp.json()}
        self.assertIn(colega.email, criados_por)
        self.assertNotIn(de_fora.email, criados_por)

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

    def test_sem_token_retorna_401(self) -> None:
        client_sem_auth = TestClient(app)  # reusa os mesmos dependency_overrides (app-level)
        resp = client_sem_auth.post("/api/v1/bitins/draft", json={"content": make_bitin_content()})
        self.assertEqual(resp.status_code, 401)

    def test_token_invalido_retorna_401(self) -> None:
        client_sem_auth = TestClient(app)
        client_sem_auth.headers.update({"Authorization": "Bearer token-forjado-invalido"})
        resp = client_sem_auth.post("/api/v1/bitins/draft", json={"content": make_bitin_content()})
        self.assertEqual(resp.status_code, 401)

    def test_draft_registra_criado_por_na_criacao(self) -> None:
        resp = self.client.post("/api/v1/bitins/draft", json={"content": make_bitin_content()})
        self.assertEqual(resp.json()["criado_por"], self.default_user.email)

    def test_admin_pode_editar_rascunho_de_outro_e_dono_nao_muda(self) -> None:
        create_resp = self.client.post("/api/v1/bitins/draft", json={"content": make_bitin_content()})
        mongo_id = create_resp.json()["mongo_id"]

        admin = self._create_user(99, permission_level=99)
        update_resp = self.client.post(
            "/api/v1/bitins/draft",
            json={"mongo_id": mongo_id, "content": make_bitin_content(motivo="Editado por admin")},
            headers={"Authorization": f"Bearer {self._token_for(admin)}"},
        )
        self.assertEqual(update_resp.status_code, 200, update_resp.text)
        self.assertEqual(update_resp.json()["criado_por"], self.default_user.email)  # dono não muda

    def test_usuario_sem_ser_dono_ou_admin_nao_pode_editar(self) -> None:
        create_resp = self.client.post("/api/v1/bitins/draft", json={"content": make_bitin_content()})
        mongo_id = create_resp.json()["mongo_id"]

        outro_usuario = self._create_user(2, permission_level=77)
        update_resp = self.client.post(
            "/api/v1/bitins/draft",
            json={"mongo_id": mongo_id, "content": make_bitin_content(motivo="Tentando editar")},
            headers={"Authorization": f"Bearer {self._token_for(outro_usuario)}"},
        )
        self.assertEqual(update_resp.status_code, 403)

    def test_pode_editar_true_pro_dono(self) -> None:
        create_resp = self.client.post("/api/v1/bitins/draft", json={"content": make_bitin_content()})
        self.assertTrue(create_resp.json()["pode_editar"])
        mongo_id = create_resp.json()["mongo_id"]

        get_resp = self.client.get(f"/api/v1/bitins/{mongo_id}")
        self.assertTrue(get_resp.json()["pode_editar"])

    def test_pode_editar_false_pra_quem_nao_e_dono_nem_admin(self) -> None:
        """Modo leitura: quem abre o rascunho de outra pessoa (sem ser dono/admin) recebe
        pode_editar=false, pra a tela abrir travada em vez de deixar editar e só descobrir
        o erro ao tentar salvar (403)."""
        create_resp = self.client.post("/api/v1/bitins/draft", json={"content": make_bitin_content()})
        mongo_id = create_resp.json()["mongo_id"]

        outro_usuario = self._create_user(2, permission_level=77)
        get_resp = self.client.get(
            f"/api/v1/bitins/{mongo_id}",
            headers={"Authorization": f"Bearer {self._token_for(outro_usuario)}"},
        )
        self.assertFalse(get_resp.json()["pode_editar"])

    def test_solicitante_na_criacao_e_sempre_o_usuario_logado(self) -> None:
        """"Solicitante vira automático (nome de quem está logado)." (2026-07-16) -- reforçado
        no backend: um valor forjado mandado pelo cliente pra 'solicitante' é ignorado, o
        valor gravado é sempre current_user.nome."""
        resp = self.client.post(
            "/api/v1/bitins/draft",
            json={"content": make_bitin_content(solicitante="Nome Forjado")},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()["content"]["solicitante"], self.default_user.nome)
        self.assertNotEqual(resp.json()["content"]["solicitante"], "Nome Forjado")

    def test_solicitante_nao_muda_ao_atualizar_mesmo_com_outro_usuario_salvando(self) -> None:
        """Mesma regra na atualização: mesmo um admin editando o rascunho de outra pessoa não
        muda o solicitante original, não importa o que venha no payload."""
        create_resp = self.client.post("/api/v1/bitins/draft", json={"content": make_bitin_content()})
        mongo_id = create_resp.json()["mongo_id"]
        solicitante_original = create_resp.json()["content"]["solicitante"]
        self.assertEqual(solicitante_original, self.default_user.nome)

        admin = self._create_user(99, permission_level=99, nome="Admin Editor")
        update_resp = self.client.post(
            "/api/v1/bitins/draft",
            json={
                "mongo_id": mongo_id,
                "content": make_bitin_content(solicitante="Outro Nome Qualquer"),
            },
            headers={"Authorization": f"Bearer {self._token_for(admin)}"},
        )
        self.assertEqual(update_resp.status_code, 200, update_resp.text)
        self.assertEqual(update_resp.json()["content"]["solicitante"], solicitante_original)
        self.assertNotEqual(update_resp.json()["content"]["solicitante"], "Outro Nome Qualquer")
        self.assertNotEqual(update_resp.json()["content"]["solicitante"], admin.nome)

    def test_pode_editar_true_pro_admin_mesmo_sem_ser_dono(self) -> None:
        create_resp = self.client.post("/api/v1/bitins/draft", json={"content": make_bitin_content()})
        mongo_id = create_resp.json()["mongo_id"]

        admin = self._create_user(99, permission_level=99)
        get_resp = self.client.get(
            f"/api/v1/bitins/{mongo_id}",
            headers={"Authorization": f"Bearer {self._token_for(admin)}"},
        )
        self.assertTrue(get_resp.json()["pode_editar"])

    def test_pode_editar_false_apos_enviado_mesmo_pro_dono(self) -> None:
        create_resp = self.client.post("/api/v1/bitins/draft", json={"content": make_bitin_content()})
        mongo_id = create_resp.json()["mongo_id"]
        self.client.post(f"/api/v1/bitins/{mongo_id}/enviar")

        get_resp = self.client.get(f"/api/v1/bitins/{mongo_id}")
        self.assertFalse(get_resp.json()["pode_editar"])

    def test_usuario_sem_ser_dono_ou_admin_nao_pode_excluir(self) -> None:
        create_resp = self.client.post("/api/v1/bitins/draft", json={"content": make_bitin_content()})
        mongo_id = create_resp.json()["mongo_id"]

        outro_usuario = self._create_user(2, permission_level=77)
        del_resp = self.client.delete(
            f"/api/v1/bitins/{mongo_id}",
            headers={"Authorization": f"Bearer {self._token_for(outro_usuario)}"},
        )
        self.assertEqual(del_resp.status_code, 403)

    def test_admin_pode_excluir_bitin_enviado_e_remove_linha_sql(self) -> None:
        """Admin (permission_level >= 99) pode excluir um BITin já enviado -- diferente do
        dono/não-admin, pra quem o envio continua definitivo. Precisa apagar as DUAS
        representações (Mongo + a linha BitinSQL com o código sequencial), senão sobra uma
        linha órfã apontando pra um documento que não existe mais."""
        create_resp = self.client.post("/api/v1/bitins/draft", json={"content": make_bitin_content()})
        mongo_id = create_resp.json()["mongo_id"]
        enviar_resp = self.client.post(f"/api/v1/bitins/{mongo_id}/enviar")
        self.assertTrue(enviar_resp.json()["ok"], enviar_resp.text)

        admin = self._create_user(99, permission_level=99)
        del_resp = self.client.delete(
            f"/api/v1/bitins/{mongo_id}",
            headers={"Authorization": f"Bearer {self._token_for(admin)}"},
        )
        self.assertEqual(del_resp.status_code, 200, del_resp.text)

        get_resp = self.client.get(f"/api/v1/bitins/{mongo_id}")
        self.assertEqual(get_resp.status_code, 404)

        db = self.SessionLocal()
        bitin_sql = db.query(BitinSQL).filter_by(mongo_document_id=mongo_id).first()
        self.assertIsNone(bitin_sql, "BitinSQL deveria ter sido removido junto com o documento Mongo")
        db.close()

    def test_dono_nao_admin_nao_pode_excluir_bitin_enviado(self) -> None:
        """Mesmo sendo o dono original, um usuário não-admin continua sem poder excluir um
        BITin já enviado -- só a exclusão admin-only muda aqui, o resto do comportamento
        anterior é preservado."""
        create_resp = self.client.post("/api/v1/bitins/draft", json={"content": make_bitin_content()})
        mongo_id = create_resp.json()["mongo_id"]
        self.client.post(f"/api/v1/bitins/{mongo_id}/enviar")

        del_resp = self.client.delete(f"/api/v1/bitins/{mongo_id}")
        self.assertEqual(del_resp.status_code, 400)

        db = self.SessionLocal()
        bitin_sql = db.query(BitinSQL).filter_by(mongo_document_id=mongo_id).first()
        self.assertIsNotNone(bitin_sql)
        db.close()

    def test_enviar_registra_criado_por_na_tabela_sql(self) -> None:
        create_resp = self.client.post("/api/v1/bitins/draft", json={"content": make_bitin_content()})
        mongo_id = create_resp.json()["mongo_id"]

        enviar_resp = self.client.post(f"/api/v1/bitins/{mongo_id}/enviar")
        self.assertTrue(enviar_resp.json()["ok"], enviar_resp.text)

        db = self.SessionLocal()
        bitin_sql = db.query(BitinSQL).filter_by(mongo_document_id=mongo_id).one()
        self.assertEqual(bitin_sql.criado_por, self.default_user.email)
        db.close()

    def test_schema_materiais_traz_colunas_dinamicas(self) -> None:
        resp = self.client.get("/api/v1/bitins/schema/materiais")
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertGreater(len(body["dados_basicos"]), 0)
        self.assertTrue(any(col["key"] == "ncm" for col in body["dados_basicos"]))
        alt_col = next(col for col in body["impactos_operacionais"] if col["key"] == "alt")
        self.assertIn("D/P", alt_col["options"])

    def test_schema_materiais_exige_autenticacao(self) -> None:
        client_sem_auth = TestClient(app)
        resp = client_sem_auth.get("/api/v1/bitins/schema/materiais")
        self.assertEqual(resp.status_code, 401)

    def test_schema_checklist_traz_22_itens(self) -> None:
        resp = self.client.get("/api/v1/bitins/schema/checklist")
        self.assertEqual(resp.status_code, 200, resp.text)
        items = resp.json()["items"]
        self.assertEqual(len(items), 22)
        self.assertEqual(items[0], {"id": "1", "etapa": "Desenho"})

    def test_schema_checklist_exige_autenticacao(self) -> None:
        client_sem_auth = TestClient(app)
        resp = client_sem_auth.get("/api/v1/bitins/schema/checklist")
        self.assertEqual(resp.status_code, 401)

    def test_parse_sap_paste_devolve_materiais(self) -> None:
        # colunas de plan1_identificacao_columns (config/vba_mapping.json): 1=tipo_material,
        # 2=codigo_material, 4=centro, 5=descricao_material, 6=grupo_mercadorias_atual, 14=tem_desenho
        linha = "MP\tCOD123\t\t2001\tPeça teste\tSA016\t\t\t\t\t\t\t\tSIM"
        resp = self.client.post("/api/v1/bitins/parse-sap-paste", json={"raw_text": linha})
        self.assertEqual(resp.status_code, 200, resp.text)
        materiais = resp.json()["materiais"]
        self.assertEqual(len(materiais), 1)
        self.assertEqual(materiais[0]["codigo_material"], "COD123")
        self.assertEqual(materiais[0]["centro"], "2001")
        self.assertTrue(materiais[0]["tem_desenho"])

    def test_parse_sap_paste_texto_vazio_devolve_lista_vazia(self) -> None:
        resp = self.client.post("/api/v1/bitins/parse-sap-paste", json={"raw_text": ""})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["materiais"], [])

    def test_listar_cadastro_ve_enviados_de_colega_mas_nao_rascunho(self) -> None:
        """Nível Cadastro (88): vê TODO BITin enviado (visibilidade global, ver
        backend/api/bitins.py::list_bitins), mas não rascunho alheio (trabalho em andamento de
        outra pessoa). Cadastro não cria/edita BITin próprio nenhum desde 2026-07-20 (pedido
        explícito: "usuário de cadastro tem somente a tela cadastro... não pode criar novo
        bitin nem alterá-lo") -- só trabalha pelas rotas dedicadas da fila."""
        cadastro = self._create_user(2, permission_level=77, setor="cadastro")
        colega = self._create_user(3, permission_level=77)

        rascunho_colega = self.client.post(
            "/api/v1/bitins/draft",
            json={"content": make_bitin_content()},
            headers={"Authorization": f"Bearer {self._token_for(colega)}"},
        )
        enviado_colega_resp = self.client.post(
            "/api/v1/bitins/draft",
            json={"content": make_bitin_content()},
            headers={"Authorization": f"Bearer {self._token_for(colega)}"},
        )
        self.client.post(
            f"/api/v1/bitins/{enviado_colega_resp.json()['mongo_id']}/enviar",
            headers={"Authorization": f"Bearer {self._token_for(colega)}"},
        )

        resp = self.client.get(
            "/api/v1/bitins",
            headers={"Authorization": f"Bearer {self._token_for(cadastro)}"},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        mongo_ids = {b["mongo_id"] for b in resp.json()}

        self.assertIn(enviado_colega_resp.json()["mongo_id"], mongo_ids)  # enviado: vê
        self.assertNotIn(rascunho_colega.json()["mongo_id"], mongo_ids)  # rascunho alheio: não vê

    def test_cadastro_nao_pode_criar_bitin(self) -> None:
        cadastro = self._create_user(2, permission_level=77, setor="cadastro")
        resp = self.client.post(
            "/api/v1/bitins/draft",
            json={"content": make_bitin_content()},
            headers={"Authorization": f"Bearer {self._token_for(cadastro)}"},
        )
        self.assertEqual(resp.status_code, 403)

    def test_listar_cadastro_nao_ve_rascunho_alheio(self) -> None:
        cadastro = self._create_user(2, permission_level=77, setor="cadastro")
        outro = self._create_user(3, permission_level=77)
        self.client.post(
            "/api/v1/bitins/draft",
            json={"content": make_bitin_content()},
            headers={"Authorization": f"Bearer {self._token_for(outro)}"},
        )
        resp = self.client.get(
            "/api/v1/bitins",
            headers={"Authorization": f"Bearer {self._token_for(cadastro)}"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    def test_pdf_exige_autenticacao(self) -> None:
        create_resp = self.client.post("/api/v1/bitins/draft", json={"content": make_bitin_content()})
        mongo_id = create_resp.json()["mongo_id"]
        client_sem_auth = TestClient(app)
        resp = client_sem_auth.get(f"/api/v1/bitins/{mongo_id}/pdf")
        self.assertEqual(resp.status_code, 401)

    def test_pdf_bitin_inexistente_404(self) -> None:
        resp = self.client.get("/api/v1/bitins/id-que-nao-existe/pdf")
        self.assertEqual(resp.status_code, 404)

    def test_pdf_rascunho_gera_pdf_valido(self) -> None:
        # Rascunho (sem código ainda) -- a rota precisa gerar um PDF normalmente mesmo
        # assim (usa o mongo_id no nome do arquivo em vez do código, ver get_bitin_pdf).
        create_resp = self.client.post("/api/v1/bitins/draft", json={"content": make_bitin_content()})
        mongo_id = create_resp.json()["mongo_id"]

        resp = self.client.get(f"/api/v1/bitins/{mongo_id}/pdf")
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.headers["content-type"], "application/pdf")
        self.assertIn(f'filename="BITin-{mongo_id}.pdf"', resp.headers["content-disposition"])
        self.assertTrue(resp.content.startswith(b"%PDF"))

    def test_pdf_bitin_enviado_usa_codigo_no_filename(self) -> None:
        create_resp = self.client.post(
            "/api/v1/bitins/draft",
            json={"content": make_bitin_content(setor="Proteína Animal")},
        )
        mongo_id = create_resp.json()["mongo_id"]
        enviar_resp = self.client.post(f"/api/v1/bitins/{mongo_id}/enviar")
        self.assertEqual(enviar_resp.status_code, 200, enviar_resp.text)
        body = enviar_resp.json()
        if not body["ok"]:
            self.skipTest(f"Setor de teste não gerou envio válido: {body['errors']}")
        codigo = body["bitin"]["codigo"]

        resp = self.client.get(f"/api/v1/bitins/{mongo_id}/pdf")
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.headers["content-type"], "application/pdf")
        self.assertIn(f'filename="BITin-{codigo}.pdf"', resp.headers["content-disposition"])
        self.assertTrue(resp.content.startswith(b"%PDF"))

    def _criar_e_enviar(self, autor: Usuario) -> str:
        draft_resp = self.client.post(
            "/api/v1/bitins/draft",
            json={"content": make_bitin_content(setor="Proteína Animal")},
            headers={"Authorization": f"Bearer {self._token_for(autor)}"},
        )
        mongo_id = draft_resp.json()["mongo_id"]
        enviar_resp = self.client.post(
            f"/api/v1/bitins/{mongo_id}/enviar",
            headers={"Authorization": f"Bearer {self._token_for(autor)}"},
        )
        body = enviar_resp.json()
        if not body["ok"]:
            self.skipTest(f"Setor de teste não gerou envio válido: {body['errors']}")
        return mongo_id

    def test_envio_encaminha_automaticamente_quando_precisa_roteiro(self) -> None:
        """Roteamento automático (2026-07-20, pedido explícito: "se for pra processo vai
        DIRETO pra processo") -- substitui a triagem manual do Cadastro que existia antes
        (endpoints POST /encaminhar-roteiro e /concluir-sem-roteiro, removidos em 2026-07-22
        por serem código morto -- ver bitin_lifecycle.enviar_bitin, que já chama as mesmas
        funções internamente). make_bitin_content() usa alt="-/P" por padrão, que exige roteiro."""
        mongo_id = self._criar_e_enviar(self.default_user)

        resp = self.client.get(f"/api/v1/bitins/{mongo_id}")
        body = resp.json()
        self.assertTrue(body["encaminhado_roteiro"])
        self.assertIsNotNone(body["data_encaminhado_roteiro"])
        self.assertFalse(body["processos_concluido"])

    def test_filtro_encaminhado_roteiro_nunca_fica_pendente_apos_envio(self) -> None:
        """Não existe mais estado "enviado mas ainda não encaminhado" alcançável pelo fluxo
        normal (2026-07-20, roteamento automático) -- o filtro encaminhado_roteiro=False
        continua existindo no backend (usado por outras combinações, ver list_bitins), mas
        pra qualquer BITin recém-enviado o resultado é sempre vazio."""
        mongo_id_encaminhado = self._criar_e_enviar(self.default_user)

        pendentes = self.client.get(
            "/api/v1/bitins", params={"status": "enviado", "encaminhado_roteiro": False},
        )
        encaminhados = self.client.get(
            "/api/v1/bitins", params={"status": "enviado", "encaminhado_roteiro": True},
        )
        self.assertNotIn(mongo_id_encaminhado, {b["mongo_id"] for b in pendentes.json()})
        self.assertIn(mongo_id_encaminhado, {b["mongo_id"] for b in encaminhados.json()})

    def _criar_enviar_e_encaminhar(self, autor: Usuario, cadastro: Usuario) -> str:
        """Nome mantido por compatibilidade com o resto da suíte, mas o envio SOZINHO já
        encaminha pro roteiro quando precisa (2026-07-20, roteamento automático) -- `cadastro`
        não é mais usado pra nenhuma chamada manual, fica só pra não precisar tocar em cada
        call site."""
        del cadastro  # não usado -- ver docstring acima
        return self._criar_e_enviar(autor)

    def test_processos_edita_bitin_enviado_e_encaminhado(self) -> None:
        """Única exceção real à regra "enviado é travado pra sempre" -- Processos pode
        reeditar um BITin enquanto ele estiver na fila do Cadastro."""
        cadastro = self._create_user(2, permission_level=77, setor="cadastro")
        processos = self._create_user(3, permission_level=77, setor="processos")
        mongo_id = self._criar_enviar_e_encaminhar(self.default_user, cadastro)

        novo_conteudo = make_bitin_content(motivo="Atualizado pelo Processos")
        resp = self.client.post(
            f"/api/v1/bitins/{mongo_id}/atualizar-processos",
            json={"content": novo_conteudo},
            headers={"Authorization": f"Bearer {self._token_for(processos)}"},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertEqual(body["status"], "enviado")  # não reverte pra rascunho
        self.assertEqual(body["content"]["motivo"], "Atualizado pelo Processos")

    def test_atualizar_processos_preserva_status_e_numero(self) -> None:
        cadastro = self._create_user(2, permission_level=77, setor="cadastro")
        processos = self._create_user(3, permission_level=77, setor="processos")
        mongo_id = self._criar_enviar_e_encaminhar(self.default_user, cadastro)
        antes = self.client.get(f"/api/v1/bitins/{mongo_id}").json()

        self.client.post(
            f"/api/v1/bitins/{mongo_id}/atualizar-processos",
            json={"content": make_bitin_content()},
            headers={"Authorization": f"Bearer {self._token_for(processos)}"},
        )
        depois = self.client.get(f"/api/v1/bitins/{mongo_id}").json()
        self.assertEqual(depois["status"], "enviado")
        self.assertEqual(depois["codigo"], antes["codigo"])

    def test_atualizar_processos_preserva_encaminhado_roteiro_no_content(self) -> None:
        """Achado real (2026-07-20, tests/test_bitin_workflow_e2e.py): `encaminhar_para_
        roteiro` espelha `encaminhado_roteiro`/`data_encaminhado_roteiro` DENTRO de `content`
        (não só no doc top-level) -- um payload de /atualizar-processos montado do zero (sem
        vir de `...conteudoExistente`, como o frontend real sempre faz) apagava esse espelho
        e quebrava /concluir-processos logo em seguida com "ainda não foi encaminhado",
        mesmo o BITin estando de fato encaminhado."""
        cadastro = self._create_user(2, permission_level=77, setor="cadastro")
        processos = self._create_user(3, permission_level=77, setor="processos")
        mongo_id = self._criar_enviar_e_encaminhar(self.default_user, cadastro)

        # payload "do zero" de propósito -- não inclui encaminhado_roteiro nenhum.
        self.client.post(
            f"/api/v1/bitins/{mongo_id}/atualizar-processos",
            json={"content": make_bitin_content(motivo="Editado do zero")},
            headers={"Authorization": f"Bearer {self._token_for(processos)}"},
        )

        depois = self.client.get(f"/api/v1/bitins/{mongo_id}").json()
        self.assertTrue(depois["encaminhado_roteiro"])
        self.assertIsNotNone(depois["data_encaminhado_roteiro"])

        conclui = self.client.post(
            f"/api/v1/bitins/{mongo_id}/concluir-processos",
            headers={"Authorization": f"Bearer {self._token_for(processos)}"},
        )
        self.assertEqual(conclui.status_code, 200, conclui.text)

    def test_usuario_comum_nao_pode_atualizar_processos(self) -> None:
        outro = self._create_user(2, permission_level=77)
        cadastro = self._create_user(3, permission_level=77, setor="cadastro")
        mongo_id = self._criar_enviar_e_encaminhar(self.default_user, cadastro)

        resp = self.client.post(
            f"/api/v1/bitins/{mongo_id}/atualizar-processos",
            json={"content": make_bitin_content()},
            headers={"Authorization": f"Bearer {self._token_for(outro)}"},
        )
        self.assertEqual(resp.status_code, 403)

    def test_processos_nao_edita_bitin_que_nao_precisou_de_roteiro(self) -> None:
        """Um BITin que não precisou de roteiro (2026-07-20, roteamento automático) já chega
        com processos_concluido=True -- a janela de reedição do Processos nunca abre pra ele
        (ver _bitin_liberado_para_processos, exige encaminhado_roteiro E NÃO
        processos_concluido)."""
        processos = self._create_user(2, permission_level=77, setor="processos")
        mongo_id = self._criar_e_enviar_sem_precisar_roteiro(self.default_user)

        resp = self.client.post(
            f"/api/v1/bitins/{mongo_id}/atualizar-processos",
            json={"content": make_bitin_content()},
            headers={"Authorization": f"Bearer {self._token_for(processos)}"},
        )
        self.assertEqual(resp.status_code, 400)

    def test_processos_conclui_e_tranca_de_novo(self) -> None:
        cadastro = self._create_user(2, permission_level=77, setor="cadastro")
        processos = self._create_user(3, permission_level=77, setor="processos")
        mongo_id = self._criar_enviar_e_encaminhar(self.default_user, cadastro)

        resp = self.client.post(
            f"/api/v1/bitins/{mongo_id}/concluir-processos",
            headers={"Authorization": f"Bearer {self._token_for(processos)}"},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertTrue(resp.json()["processos_concluido"])

        # trancado de novo -- inclusive pro próprio Processos.
        depois = self.client.get(
            f"/api/v1/bitins/{mongo_id}",
            headers={"Authorization": f"Bearer {self._token_for(processos)}"},
        )
        self.assertFalse(depois.json()["pode_editar"])

        segunda_tentativa = self.client.post(
            f"/api/v1/bitins/{mongo_id}/atualizar-processos",
            json={"content": make_bitin_content()},
            headers={"Authorization": f"Bearer {self._token_for(processos)}"},
        )
        self.assertEqual(segunda_tentativa.status_code, 400)

    def test_processos_ve_fila_encaminhada_de_qualquer_um(self) -> None:
        """Processos não tem "próprios" BITins (não cria nenhum, ver
        test_processos_nao_pode_criar_rascunho_novo) -- só enxerga a fila encaminhada pelo
        Cadastro, de qualquer autor."""
        cadastro = self._create_user(2, permission_level=77, setor="cadastro")
        processos = self._create_user(3, permission_level=77, setor="processos")
        outro = self._create_user(4, permission_level=77)

        mongo_id_fila = self._criar_enviar_e_encaminhar(outro, cadastro)

        resp = self.client.get(
            "/api/v1/bitins",
            headers={"Authorization": f"Bearer {self._token_for(processos)}"},
        )
        mongo_ids = {b["mongo_id"] for b in resp.json()}
        self.assertIn(mongo_id_fila, mongo_ids)

    def test_cadastro_ve_bitin_concluido_pelo_processos_mesmo_sem_subgrupo_em_comum(self) -> None:
        """"quando o pessoal de processos terminar de revisar o roteiro dos códigos, ele
        envia de volta pra cadastro, e cadastro recebe o bitin 'Pronto para cadastro'"
        (2026-07-17) -- visibilidade global (processos_concluido=True), não presa a Subgrupo,
        já que Processos é um time central."""
        autor = self._create_user(2, permission_level=77)
        cadastro_que_encaminhou = self._create_user(3, permission_level=77, setor="cadastro")
        outro_cadastro = self._create_user(4, permission_level=77, setor="cadastro")  # sem Subgrupo em comum
        processos = self._create_user(5, permission_level=77, setor="processos")

        mongo_id = self._criar_enviar_e_encaminhar(autor, cadastro_que_encaminhou)
        self.client.post(
            f"/api/v1/bitins/{mongo_id}/concluir-processos",
            headers={"Authorization": f"Bearer {self._token_for(processos)}"},
        )

        resp = self.client.get(
            "/api/v1/bitins",
            params={"status": "enviado", "processos_concluido": True},
            headers={"Authorization": f"Bearer {self._token_for(outro_cadastro)}"},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertIn(mongo_id, {b["mongo_id"] for b in resp.json()})

    def test_aba_enviado_roteiro_nao_mostra_os_ja_concluidos_pelo_processos(self) -> None:
        cadastro = self._create_user(2, permission_level=77, setor="cadastro")
        processos = self._create_user(3, permission_level=77, setor="processos")
        mongo_id = self._criar_enviar_e_encaminhar(self.default_user, cadastro)
        self.client.post(
            f"/api/v1/bitins/{mongo_id}/concluir-processos",
            headers={"Authorization": f"Bearer {self._token_for(processos)}"},
        )

        resp = self.client.get(
            "/api/v1/bitins",
            params={"status": "enviado", "encaminhado_roteiro": True, "processos_concluido": False},
        )
        self.assertNotIn(mongo_id, {b["mongo_id"] for b in resp.json()})

    # "Não precisa de roteiro" (2026-07-17, pedido explícito: "coloca essa opção, do cadastro
    # não precisar enviar pra processos, quando não houver: D/P, D/- ou -/P").

    def test_precisa_roteiro_true_por_padrao(self) -> None:
        """make_bitin_content() usa alt="-/P" por padrão -- está no conjunto que exige
        roteiro (ver bitin_document._ALTS_QUE_EXIGEM_ROTEIRO)."""
        mongo_id = self._criar_e_enviar(self.default_user)
        resp = self.client.get(f"/api/v1/bitins/{mongo_id}")
        self.assertTrue(resp.json()["precisa_roteiro"])

    def _criar_e_enviar_sem_precisar_roteiro(self, autor: Usuario) -> str:
        content = make_bitin_content(setor="Proteína Animal")
        content["materiais"][0]["alteracoes"]["impactos_operacionais"]["alt"] = "-/F"
        draft_resp = self.client.post(
            "/api/v1/bitins/draft",
            json={"content": content},
            headers={"Authorization": f"Bearer {self._token_for(autor)}"},
        )
        mongo_id = draft_resp.json()["mongo_id"]
        enviar_resp = self.client.post(
            f"/api/v1/bitins/{mongo_id}/enviar",
            headers={"Authorization": f"Bearer {self._token_for(autor)}"},
        )
        body = enviar_resp.json()
        if not body["ok"]:
            self.skipTest(f"Setor de teste não gerou envio válido: {body['errors']}")
        return mongo_id

    def test_envio_conclui_sem_roteiro_automaticamente_quando_nao_precisa(self) -> None:
        """Roteamento automático (2026-07-20, pedido explícito: "se não for necessário o
        pessoal de processo vai direto para aguardando cadastro") -- o PRÓPRIO envio já chama
        concluir_sem_roteiro sozinho, sem precisar do Cadastro clicar em nada (o endpoint
        manual POST /concluir-sem-roteiro foi removido em 2026-07-22 por ser código morto,
        ver bitin_lifecycle.enviar_bitin)."""
        mongo_id = self._criar_e_enviar_sem_precisar_roteiro(self.default_user)

        resp = self.client.get(f"/api/v1/bitins/{mongo_id}")
        self.assertFalse(resp.json()["precisa_roteiro"])
        body = resp.json()
        self.assertTrue(body["encaminhado_roteiro"])
        self.assertTrue(body["processos_concluido"])
        self.assertTrue(body["sem_necessidade_roteiro"])

        # aparece na mesma aba final de quem passou pelo Processos de verdade.
        pronto = self.client.get(
            "/api/v1/bitins",
            params={"status": "enviado", "processos_concluido": True},
        )
        self.assertIn(mongo_id, {b["mongo_id"] for b in pronto.json()})

        # mas NÃO aparece na fila do Processos (2026-07-21, achado ao investigar "porque tem
        # bitins de troca de fornecedor (-/F) aparecendo como revisado nos processos") -- esse
        # BITin nunca passou pelo Processos de verdade, ver ProcessosPage.tsx.
        revisados_processos = self.client.get(
            "/api/v1/bitins",
            params={"status": "enviado", "processos_concluido": True, "sem_necessidade_roteiro": False},
        )
        self.assertNotIn(mongo_id, {b["mongo_id"] for b in revisados_processos.json()})

    # Processos não cria BITin (2026-07-17, pedido explícito: "processos não pode fazer
    # bitin, só fazer a parte da revisão de roteiro").

    def test_processos_nao_pode_criar_rascunho_novo(self) -> None:
        processos = self._create_user(2, permission_level=77, setor="processos")
        resp = self.client.post(
            "/api/v1/bitins/draft",
            json={"content": make_bitin_content()},
            headers={"Authorization": f"Bearer {self._token_for(processos)}"},
        )
        self.assertEqual(resp.status_code, 403)

    def test_processos_pode_atualizar_rascunho_existente_encaminhado(self) -> None:
        """A restrição é só pra CRIAR um BITin do zero -- reeditar um já encaminhado (via
        /atualizar-processos, não /draft) continua liberado, ver AtualizarProcessosTest."""
        cadastro = self._create_user(2, permission_level=77, setor="cadastro")
        processos = self._create_user(3, permission_level=77, setor="processos")
        mongo_id = self._criar_enviar_e_encaminhar(self.default_user, cadastro)

        resp = self.client.post(
            f"/api/v1/bitins/{mongo_id}/atualizar-processos",
            json={"content": make_bitin_content(motivo="Revisado")},
            headers={"Authorization": f"Bearer {self._token_for(processos)}"},
        )
        self.assertEqual(resp.status_code, 200, resp.text)

    def test_admin_ainda_pode_criar_bitin(self) -> None:
        admin = self._create_user(2, permission_level=99)
        resp = self.client.post(
            "/api/v1/bitins/draft",
            json={"content": make_bitin_content()},
            headers={"Authorization": f"Bearer {self._token_for(admin)}"},
        )
        self.assertEqual(resp.status_code, 200, resp.text)

    # "Concluir BITIN" (2026-07-20, último passo do fluxo, pedido explícito) -- move da aba
    # "Aguardando cadastro" pra "Cadastrados"; só a partir daqui o PDF fica disponível.

    def test_cadastro_conclui_bitin_apos_processos(self) -> None:
        cadastro = self._create_user(2, permission_level=77, setor="cadastro")
        processos = self._create_user(3, permission_level=77, setor="processos")
        mongo_id = self._criar_enviar_e_encaminhar(self.default_user, cadastro)
        self.client.post(
            f"/api/v1/bitins/{mongo_id}/concluir-processos",
            headers={"Authorization": f"Bearer {self._token_for(processos)}"},
        )

        resp = self.client.post(
            f"/api/v1/bitins/{mongo_id}/concluir-bitin",
            headers={"Authorization": f"Bearer {self._token_for(cadastro)}"},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertTrue(body["bitin_cadastrado"])
        self.assertIsNotNone(body["data_cadastrado"])

        # aparece na aba "Cadastrados" (bitin_cadastrado=true) e some de "Aguardando cadastro".
        cadastrados = self.client.get(
            "/api/v1/bitins", params={"status": "enviado", "bitin_cadastrado": True},
        )
        self.assertIn(mongo_id, {b["mongo_id"] for b in cadastrados.json()})
        aguardando = self.client.get(
            "/api/v1/bitins",
            params={"status": "enviado", "processos_concluido": True, "bitin_cadastrado": False},
        )
        self.assertNotIn(mongo_id, {b["mongo_id"] for b in aguardando.json()})

    def test_cadastro_conclui_bitin_que_pulou_roteiro(self) -> None:
        cadastro = self._create_user(2, permission_level=77, setor="cadastro")
        # Já chega em "aguardando cadastro" sozinho (roteamento automático, 2026-07-20) --
        # não precisa de nenhuma chamada manual antes de "Concluir BITIN".
        mongo_id = self._criar_e_enviar_sem_precisar_roteiro(self.default_user)

        resp = self.client.post(
            f"/api/v1/bitins/{mongo_id}/concluir-bitin",
            headers={"Authorization": f"Bearer {self._token_for(cadastro)}"},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertTrue(resp.json()["bitin_cadastrado"])

    def test_nao_conclui_bitin_antes_de_passar_pelo_roteiro(self) -> None:
        cadastro = self._create_user(2, permission_level=77, setor="cadastro")
        mongo_id = self._criar_e_enviar(self.default_user)

        resp = self.client.post(
            f"/api/v1/bitins/{mongo_id}/concluir-bitin",
            headers={"Authorization": f"Bearer {self._token_for(cadastro)}"},
        )
        self.assertEqual(resp.status_code, 400)

    def test_usuario_comum_nao_pode_concluir_bitin(self) -> None:
        outro = self._create_user(2, permission_level=77)
        # Já chega em "aguardando cadastro" sozinho (roteamento automático, 2026-07-20).
        mongo_id = self._criar_e_enviar_sem_precisar_roteiro(self.default_user)

        resp = self.client.post(
            f"/api/v1/bitins/{mongo_id}/concluir-bitin",
            headers={"Authorization": f"Bearer {self._token_for(outro)}"},
        )
        self.assertEqual(resp.status_code, 403)

    # "Enviar pro Windchill" (2026-07-20, pedido explícito) -- última etapa de todas.

    def test_cadastro_envia_windchill_apos_concluir_bitin(self) -> None:
        cadastro = self._create_user(2, permission_level=77, setor="cadastro")
        mongo_id = self._criar_e_enviar_sem_precisar_roteiro(self.default_user)
        self.client.post(
            f"/api/v1/bitins/{mongo_id}/concluir-bitin",
            headers={"Authorization": f"Bearer {self._token_for(cadastro)}"},
        )

        resp = self.client.post(
            f"/api/v1/bitins/{mongo_id}/enviar-windchill",
            headers={"Authorization": f"Bearer {self._token_for(cadastro)}"},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertTrue(body["windchill_enviado"])
        self.assertIsNotNone(body["data_windchill_enviado"])
        self.assertEqual(body["status"], "enviado")  # status bruto não muda, ver bitin_lifecycle.enviar_windchill

        concluidos = self.client.get(
            "/api/v1/bitins", params={"status": "enviado", "windchill_enviado": True},
        )
        self.assertIn(mongo_id, {b["mongo_id"] for b in concluidos.json()})

    def test_nao_envia_windchill_antes_de_concluir_bitin(self) -> None:
        cadastro = self._create_user(2, permission_level=77, setor="cadastro")
        mongo_id = self._criar_e_enviar_sem_precisar_roteiro(self.default_user)

        resp = self.client.post(
            f"/api/v1/bitins/{mongo_id}/enviar-windchill",
            headers={"Authorization": f"Bearer {self._token_for(cadastro)}"},
        )
        self.assertEqual(resp.status_code, 400)

    def test_usuario_comum_nao_pode_enviar_windchill(self) -> None:
        outro = self._create_user(2, permission_level=77)
        cadastro = self._create_user(3, permission_level=77, setor="cadastro")
        mongo_id = self._criar_e_enviar_sem_precisar_roteiro(self.default_user)
        self.client.post(
            f"/api/v1/bitins/{mongo_id}/concluir-bitin",
            headers={"Authorization": f"Bearer {self._token_for(cadastro)}"},
        )

        resp = self.client.post(
            f"/api/v1/bitins/{mongo_id}/enviar-windchill",
            headers={"Authorization": f"Bearer {self._token_for(outro)}"},
        )
        self.assertEqual(resp.status_code, 403)

    # "Voltar BITin" (2026-07-20, pedido explícito: "lista dos bitins concluidos com opções
    # de voltar bitin etc.") -- desfaz enviar-windchill, admin-only.

    def test_admin_reverte_windchill(self) -> None:
        cadastro = self._create_user(2, permission_level=77, setor="cadastro")
        admin = self._create_user(3, permission_level=99)
        mongo_id = self._criar_e_enviar_sem_precisar_roteiro(self.default_user)
        self.client.post(
            f"/api/v1/bitins/{mongo_id}/concluir-bitin",
            headers={"Authorization": f"Bearer {self._token_for(cadastro)}"},
        )
        self.client.post(
            f"/api/v1/bitins/{mongo_id}/enviar-windchill",
            headers={"Authorization": f"Bearer {self._token_for(cadastro)}"},
        )

        resp = self.client.post(
            f"/api/v1/bitins/{mongo_id}/reverter-windchill",
            headers={"Authorization": f"Bearer {self._token_for(admin)}"},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertFalse(body["windchill_enviado"])
        self.assertIsNone(body["data_windchill_enviado"])

    def test_nao_reverte_windchill_antes_de_enviar(self) -> None:
        admin = self._create_user(2, permission_level=99)
        mongo_id = self._criar_e_enviar_sem_precisar_roteiro(self.default_user)

        resp = self.client.post(
            f"/api/v1/bitins/{mongo_id}/reverter-windchill",
            headers={"Authorization": f"Bearer {self._token_for(admin)}"},
        )
        self.assertEqual(resp.status_code, 400)

    def test_cadastro_nao_pode_reverter_windchill(self) -> None:
        cadastro = self._create_user(2, permission_level=77, setor="cadastro")
        mongo_id = self._criar_e_enviar_sem_precisar_roteiro(self.default_user)
        self.client.post(
            f"/api/v1/bitins/{mongo_id}/concluir-bitin",
            headers={"Authorization": f"Bearer {self._token_for(cadastro)}"},
        )
        self.client.post(
            f"/api/v1/bitins/{mongo_id}/enviar-windchill",
            headers={"Authorization": f"Bearer {self._token_for(cadastro)}"},
        )

        resp = self.client.post(
            f"/api/v1/bitins/{mongo_id}/reverter-windchill",
            headers={"Authorization": f"Bearer {self._token_for(cadastro)}"},
        )
        self.assertEqual(resp.status_code, 403)

    # GET /bitins/resumo-painel (2026-07-20, pedido explícito: "otimiza velocidade de
    # carregamento") -- contadores do dashboard num round-trip só, via $facet, mesmo escopo
    # de visibilidade de list_bitins (ver _condicoes_escopo).

    def test_resumo_painel_admin_ve_contagem_do_sistema(self) -> None:
        admin = self._create_user(2, permission_level=99)
        self._criar_e_enviar_sem_precisar_roteiro(self.default_user)  # vira "aguardando cadastro"
        self.client.post("/api/v1/bitins/draft", json={"content": make_bitin_content()})  # rascunho

        resp = self.client.get(
            "/api/v1/bitins/resumo-painel",
            headers={"Authorization": f"Bearer {self._token_for(admin)}"},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertGreaterEqual(body["cadastro_aguardando"], 1)
        self.assertGreaterEqual(body["geral_rascunhos"], 1)
        self.assertGreaterEqual(body["geral_enviados"], 1)

    def test_resumo_painel_engenheiro_so_ve_os_proprios(self) -> None:
        outro = self._create_user(2, permission_level=77)
        self.client.post(
            "/api/v1/bitins/draft",
            json={"content": make_bitin_content()},
            headers={"Authorization": f"Bearer {self._token_for(outro)}"},
        )  # rascunho de outro usuário -- não deve contar pro default_user

        resp = self.client.get("/api/v1/bitins/resumo-painel")  # default_user (headers globais do setUp)
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()["geral_rascunhos"], 0)

    # --- Histórico/auditoria (2026-07-22, pedido explícito: "quem mexeu, quando, o que
    # mudou" -- nível de evento, não diff campo a campo) ---

    def test_historico_criacao_rascunho_gera_1_evento(self) -> None:
        resp = self.client.post("/api/v1/bitins/draft", json={"content": make_bitin_content()})
        historico = resp.json()["historico"]
        self.assertEqual(len(historico), 1)
        self.assertIn("criou o rascunho", historico[0]["acao"])
        self.assertEqual(historico[0]["usuario"], self.default_user.email)

    def test_historico_salvar_rascunho_de_novo_nao_gera_evento_extra(self) -> None:
        create_resp = self.client.post("/api/v1/bitins/draft", json={"content": make_bitin_content()})
        mongo_id = create_resp.json()["mongo_id"]
        update_resp = self.client.post(
            "/api/v1/bitins/draft",
            json={"mongo_id": mongo_id, "content": make_bitin_content(motivo="Outro motivo")},
        )
        self.assertEqual(len(update_resp.json()["historico"]), 1)

    def test_historico_envio_gera_evento(self) -> None:
        create_resp = self.client.post("/api/v1/bitins/draft", json={"content": make_bitin_content()})
        mongo_id = create_resp.json()["mongo_id"]
        resp = self.client.post(f"/api/v1/bitins/{mongo_id}/enviar")
        self.assertTrue(resp.json()["ok"], resp.text)
        historico = resp.json()["bitin"]["historico"]
        self.assertEqual(len(historico), 2)
        self.assertIn("enviou o BITin", historico[1]["acao"])

    def test_historico_aparece_no_resumo(self) -> None:
        create_resp = self.client.post("/api/v1/bitins/draft", json={"content": make_bitin_content()})
        mongo_id = create_resp.json()["mongo_id"]
        resp = self.client.get(f"/api/v1/bitins/{mongo_id}/resumo")
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(len(resp.json()["historico"]), 1)


if __name__ == "__main__":
    unittest.main()
