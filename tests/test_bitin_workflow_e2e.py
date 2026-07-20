"""Suite de ponta a ponta do fluxo completo do BITin (2026-07-20) -- criada a pedido
explícito do usuário: "cria uma bagagem de testes para isso para uso presente e futuro".

Diferente dos testes unitários já existentes em test_backend_bitins.py (que cobrem cada
endpoint/regra isoladamente), este arquivo conta a HISTÓRIA de um BITin do início ao fim,
pelos 4 papéis envolvidos, e serve como documentação viva do fluxo real:

    Engenheiro cria/envia -> Cadastro decide (precisa de roteiro ou não) ->
        [precisa] Processos revisa e conclui -> volta pro Cadastro com PDF
        [não precisa] Cadastro conclui direto -> PDF na hora

A decisão "precisa de roteiro" é automática (bitin_document.precisa_roteiro): true se
QUALQUER material tem Alt em {"D/P", "D/-", "-/P"} (pedido explícito do usuário, 2026-07-17).

Cada teste também confere que SÓ quem deveria ver/agir em cada etapa consegue -- isolamento
de visibilidade entre papéis é o ponto central que motivou este arquivo.
"""

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

from backend.auth.models import Usuario  # noqa: E402
from backend.auth.security import create_access_token, get_password_hash  # noqa: E402
from backend.db.mongodb import get_mongo_db  # noqa: E402
from backend.db.session import Base, get_db  # noqa: E402
from backend.main import app  # noqa: E402

# Níveis (espelha backend/auth/deps.py) -- nomeados aqui pra cada teste ficar legível sem
# precisar ir consultar o arquivo de permissões toda hora.
NIVEL_USUARIO = 66
NIVEL_GESTOR = 77
NIVEL_CADASTRO = 88
NIVEL_PROCESSOS = 89
NIVEL_ADMIN = 99

# Alts que exigem passar pelo setor Processos (bitin_document._ALTS_QUE_EXIGEM_ROTEIRO) --
# "quando não houver: D/P, D/- ou -/P... se tiver isso na alteração do código é roteiro,
# quando não tiver não é" (pedido explícito do usuário, 2026-07-17).
ALTS_COM_ROTEIRO = ("D/P", "D/-", "-/P")
ALTS_SEM_ROTEIRO = ("D/F", "-/F", "-")


def _dados_basicos_consistentes_com_alt(alt: str) -> dict:
    """bitin_business_rules.py bloqueia o envio se o Alt declarado não bater com o que
    dados_basicos realmente mudou: Alt começando com "D" exige mudança de `nivel_revisao`;
    Alt="-" exige NENHUMA mudança real (senão "alt_inconsistent_no_changes"). Centralizado
    aqui pra cada teste poder variar o Alt sem precisar saber dessa regra de cor."""
    if alt.startswith("D"):
        return {"nivel_revisao": {"de": "A", "para": "B"}}
    if alt == "-":
        return {}
    return {"descricao": {"de": "X", "para": "Y"}}


def make_bitin_content(alt: str = "-/P", **overrides) -> dict:
    base = {
        "setor": "Proteína Animal",
        "produto": "Silo X",
        "motivo": "Correção de roteiro",
        "solicitante": "Engenheiro Teste",
        "data_solicitacao": "2026-07-20",
        "materiais": [
            {
                "codigo_material": "CT30-7103",
                "centro": "2001",
                "tipo_material": "HALB",
                "alteracoes": {
                    "dados_basicos": _dados_basicos_consistentes_com_alt(alt),
                    "impactos_operacionais": {"alt": alt},
                },
            }
        ],
    }
    base.update(overrides)
    return base


class BitinWorkflowTestBase(unittest.TestCase):
    """Harness compartilhado (mesmo padrão de test_backend_bitins.py) -- SQLite em memória +
    mongomock, um usuário novo por teste (sem @self.client.headers global, pra cada chamada
    ficar explícita sobre QUEM está agindo -- é o ponto central deste arquivo)."""

    def setUp(self) -> None:
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
        self.mongo_test_db = mongo_client["bitin_workflow_test_db"]

        async def override_get_mongo_db():
            return self.mongo_test_db

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_mongo_db] = override_get_mongo_db
        self.client = TestClient(app)

        self._next_user_id = 1
        self.engenheiro = self._criar_usuario(NIVEL_USUARIO, setor="usuario", nome="Engenheiro")
        self.outro_engenheiro = self._criar_usuario(NIVEL_USUARIO, setor="usuario", nome="Outro Engenheiro")
        self.cadastro = self._criar_usuario(NIVEL_CADASTRO, setor="cadastro", nome="Cadastro")
        self.processos = self._criar_usuario(NIVEL_PROCESSOS, setor="processos", nome="Processos")
        self.admin = self._criar_usuario(NIVEL_ADMIN, setor="usuario", nome="Admin")

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.engine.dispose()

    def _criar_usuario(self, permission_level: int, setor: str, nome: str) -> Usuario:
        db = self.SessionLocal()
        user = Usuario(
            id=self._next_user_id,
            email=f"{nome.lower().replace(' ', '.')}@example.com",
            nome=nome,
            hashed_password=get_password_hash("Senha123!"),
            permission_level=permission_level,
            setor=setor,
        )
        self._next_user_id += 1
        db.add(user)
        db.commit()
        db.refresh(user)
        db.expunge(user)
        db.close()
        return user

    def _auth(self, user: Usuario) -> dict:
        return {"Authorization": f"Bearer {create_access_token(user.id)}"}

    def _enviar_bitin(self, autor: Usuario, alt: str) -> str:
        """Cria o rascunho como `autor` e envia -- devolve o mongo_id. `skipTest` se o setor
        de teste não gerar um envio válido (mesma defesa usada em test_backend_bitins.py)."""
        draft = self.client.post(
            "/api/v1/bitins/draft",
            json={"content": make_bitin_content(alt=alt)},
            headers=self._auth(autor),
        )
        self.assertEqual(draft.status_code, 200, draft.text)
        mongo_id = draft.json()["mongo_id"]

        enviar = self.client.post(f"/api/v1/bitins/{mongo_id}/enviar", headers=self._auth(autor))
        body = enviar.json()
        if not body["ok"]:
            self.skipTest(f"Setor de teste não gerou envio válido: {body['errors']}")
        return mongo_id

    def _bitins_visiveis_para(self, user: Usuario, **params) -> set[str]:
        resp = self.client.get("/api/v1/bitins", params=params, headers=self._auth(user))
        self.assertEqual(resp.status_code, 200, resp.text)
        return {b["mongo_id"] for b in resp.json()}


class ComRoteiroWorkflowTest(BitinWorkflowTestBase):
    """BITin com Alt que EXIGE passar pelo setor Processos (D/P, D/-, -/P) -- história
    completa: Engenheiro -> Cadastro (Recebidos) -> Processos (revisão) -> Cadastro
    (Retornados, PDF pronto)."""

    def test_fluxo_completo_alt_dp(self) -> None:
        self._roda_fluxo_completo("D/P")

    def test_fluxo_completo_alt_d_traco(self) -> None:
        self._roda_fluxo_completo("D/-")

    def test_fluxo_completo_alt_traco_p(self) -> None:
        self._roda_fluxo_completo("-/P")

    def _roda_fluxo_completo(self, alt: str) -> None:
        # 1) Engenheiro cria e envia.
        mongo_id = self._enviar_bitin(self.engenheiro, alt=alt)

        detalhe = self.client.get(f"/api/v1/bitins/{mongo_id}", headers=self._auth(self.engenheiro))
        self.assertEqual(detalhe.status_code, 200)
        self.assertEqual(detalhe.json()["status"], "enviado")
        self.assertTrue(detalhe.json()["precisa_roteiro"], f"Alt {alt} deveria exigir roteiro")
        self.assertFalse(detalhe.json()["encaminhado_roteiro"])
        self.assertFalse(detalhe.json()["pode_editar"])  # travado assim que enviado

        # 2) Isolamento: outro engenheiro (sem relação nenhuma) não vê este BITin.
        self.assertNotIn(mongo_id, self._bitins_visiveis_para(self.outro_engenheiro))
        # Processos ainda não vê -- só entra na fila depois de encaminhado.
        self.assertNotIn(mongo_id, self._bitins_visiveis_para(self.processos))

        # 3) Cadastro enxerga na aba "Recebidos" (encaminhado_roteiro=false).
        recebidos = self._bitins_visiveis_para(
            self.cadastro, status="enviado", encaminhado_roteiro=False,
        )
        self.assertIn(mongo_id, recebidos)

        # 4) Só Cadastro/admin podem encaminhar -- engenheiro comum toma 403.
        negado = self.client.post(
            f"/api/v1/bitins/{mongo_id}/encaminhar-roteiro", headers=self._auth(self.engenheiro),
        )
        self.assertEqual(negado.status_code, 403)

        encaminhar = self.client.post(
            f"/api/v1/bitins/{mongo_id}/encaminhar-roteiro", headers=self._auth(self.cadastro),
        )
        self.assertEqual(encaminhar.status_code, 200, encaminhar.text)
        self.assertTrue(encaminhar.json()["encaminhado_roteiro"])

        # 5) Some de "Recebidos", aparece em "Enviados para roteiros" pro Cadastro.
        self.assertNotIn(mongo_id, self._bitins_visiveis_para(
            self.cadastro, status="enviado", encaminhado_roteiro=False,
        ))
        self.assertIn(mongo_id, self._bitins_visiveis_para(
            self.cadastro, status="enviado", encaminhado_roteiro=True, processos_concluido=False,
        ))

        # 6) Agora Processos enxerga (fila global) e PODE editar -- única exceção ao "enviado
        # é travado pra sempre" no sistema inteiro.
        self.assertIn(mongo_id, self._bitins_visiveis_para(self.processos))
        detalhe_processos = self.client.get(f"/api/v1/bitins/{mongo_id}", headers=self._auth(self.processos))
        self.assertTrue(detalhe_processos.json()["pode_editar"])

        # 7) Engenheiro comum não pode editar via /atualizar-processos (só Processos/admin).
        negado_edicao = self.client.post(
            f"/api/v1/bitins/{mongo_id}/atualizar-processos",
            json={"content": make_bitin_content(alt=alt, motivo="Tentativa indevida")},
            headers=self._auth(self.engenheiro),
        )
        self.assertEqual(negado_edicao.status_code, 403)

        # 8) Processos edita de verdade -- status/número continuam intactos.
        editar = self.client.post(
            f"/api/v1/bitins/{mongo_id}/atualizar-processos",
            json={"content": make_bitin_content(alt=alt, motivo="Roteiro revisado pelo Processos")},
            headers=self._auth(self.processos),
        )
        self.assertEqual(editar.status_code, 200, editar.text)
        self.assertEqual(editar.json()["status"], "enviado")
        self.assertEqual(editar.json()["content"]["motivo"], "Roteiro revisado pelo Processos")
        self.assertEqual(editar.json()["codigo"], detalhe.json()["codigo"])

        # 9) Só Processos/admin concluem -- Cadastro (que só encaminha) toma 403.
        negado_conclusao = self.client.post(
            f"/api/v1/bitins/{mongo_id}/concluir-processos", headers=self._auth(self.cadastro),
        )
        self.assertEqual(negado_conclusao.status_code, 403)

        concluir = self.client.post(
            f"/api/v1/bitins/{mongo_id}/concluir-processos", headers=self._auth(self.processos),
        )
        self.assertEqual(concluir.status_code, 200, concluir.text)
        self.assertTrue(concluir.json()["processos_concluido"])
        self.assertFalse(concluir.json()["sem_necessidade_roteiro"])  # passou pelo Processos de verdade

        # 10) Trava de novo -- nem o próprio Processos edita mais.
        detalhe_final_processos = self.client.get(f"/api/v1/bitins/{mongo_id}", headers=self._auth(self.processos))
        self.assertFalse(detalhe_final_processos.json()["pode_editar"])
        reedicao_negada = self.client.post(
            f"/api/v1/bitins/{mongo_id}/atualizar-processos",
            json={"content": make_bitin_content(alt=alt)},
            headers=self._auth(self.processos),
        )
        self.assertEqual(reedicao_negada.status_code, 400)

        # 11) Some de "Enviados para roteiros", aparece em "Retornados de roteiro" pro Cadastro.
        self.assertNotIn(mongo_id, self._bitins_visiveis_para(
            self.cadastro, status="enviado", encaminhado_roteiro=True, processos_concluido=False,
        ))
        self.assertIn(mongo_id, self._bitins_visiveis_para(
            self.cadastro, status="enviado", processos_concluido=True,
        ))

        # 12) PDF pronto pra registro externo -- qualquer autenticado baixa (mesma regra de
        # GET /{id}/pdf), sem autenticação nenhuma toma 401.
        pdf = self.client.get(f"/api/v1/bitins/{mongo_id}/pdf", headers=self._auth(self.cadastro))
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf.headers["content-type"], "application/pdf")
        self.assertTrue(pdf.content.startswith(b"%PDF"))
        sem_auth = self.client.get(f"/api/v1/bitins/{mongo_id}/pdf")
        self.assertEqual(sem_auth.status_code, 401)


class SemRoteiroWorkflowTest(BitinWorkflowTestBase):
    """BITin com Alt que NÃO exige o setor Processos (D/F, -/F, -) -- o Cadastro conclui
    direto, sem passar pela fila de Processos."""

    def test_fluxo_completo_sem_necessidade_de_roteiro(self) -> None:
        for alt in ALTS_SEM_ROTEIRO:
            with self.subTest(alt=alt):
                self._roda_fluxo_sem_roteiro(alt)

    def _roda_fluxo_sem_roteiro(self, alt: str) -> None:
        mongo_id = self._enviar_bitin(self.engenheiro, alt=alt)

        detalhe = self.client.get(f"/api/v1/bitins/{mongo_id}", headers=self._auth(self.engenheiro))
        self.assertFalse(detalhe.json()["precisa_roteiro"], f"Alt {alt} não deveria exigir roteiro")

        # Aparece pro Cadastro em "Recebidos", igual qualquer outro.
        self.assertIn(mongo_id, self._bitins_visiveis_para(
            self.cadastro, status="enviado", encaminhado_roteiro=False,
        ))

        # Engenheiro comum não pode concluir sem roteiro (só Cadastro/admin).
        negado = self.client.post(
            f"/api/v1/bitins/{mongo_id}/concluir-sem-roteiro", headers=self._auth(self.engenheiro),
        )
        self.assertEqual(negado.status_code, 403)

        concluir = self.client.post(
            f"/api/v1/bitins/{mongo_id}/concluir-sem-roteiro", headers=self._auth(self.cadastro),
        )
        self.assertEqual(concluir.status_code, 200, concluir.text)
        body = concluir.json()
        self.assertTrue(body["encaminhado_roteiro"])
        self.assertTrue(body["processos_concluido"])
        self.assertTrue(body["sem_necessidade_roteiro"])  # pulou o Processos

        # Nunca passa pela aba "Enviados para roteiros" -- vai direto pra "Retornados".
        self.assertNotIn(mongo_id, self._bitins_visiveis_para(
            self.cadastro, status="enviado", encaminhado_roteiro=True, processos_concluido=False,
        ))
        self.assertIn(mongo_id, self._bitins_visiveis_para(
            self.cadastro, status="enviado", processos_concluido=True,
        ))

        # Processos enxerga (entra na fila global por encaminhado_roteiro=true), mas NÃO pode
        # editar -- já chegou concluído.
        self.assertIn(mongo_id, self._bitins_visiveis_para(self.processos))
        detalhe_processos = self.client.get(f"/api/v1/bitins/{mongo_id}", headers=self._auth(self.processos))
        self.assertFalse(detalhe_processos.json()["pode_editar"])

        # PDF pronto na hora, sem esperar Processos.
        pdf = self.client.get(f"/api/v1/bitins/{mongo_id}/pdf", headers=self._auth(self.cadastro))
        self.assertEqual(pdf.status_code, 200)
        self.assertTrue(pdf.content.startswith(b"%PDF"))

    def test_concluir_sem_roteiro_rejeitado_se_alt_exige_roteiro(self) -> None:
        """Reforço no servidor -- Cadastro não consegue pular o Processos só porque quis,
        se a regra automática diz que precisa (não confia só no frontend esconder o botão)."""
        mongo_id = self._enviar_bitin(self.engenheiro, alt="D/P")
        resp = self.client.post(
            f"/api/v1/bitins/{mongo_id}/concluir-sem-roteiro", headers=self._auth(self.cadastro),
        )
        self.assertEqual(resp.status_code, 400)


class VisibilidadePorPapelTest(BitinWorkflowTestBase):
    """Matriz de visibilidade: cada papel só enxerga o que faz sentido pra ele. Um teste por
    papel, todos rodando contra o MESMO conjunto de BITins (criados uma vez em setUp)."""

    def setUp(self) -> None:
        super().setUp()
        # Um BITin de cada "dono" possível, em estágios diferentes -- cenário fixo reutilizado
        # por todos os testes desta classe.
        self.rascunho_engenheiro = self.client.post(
            "/api/v1/bitins/draft",
            json={"content": make_bitin_content(alt="D/P")},
            headers=self._auth(self.engenheiro),
        ).json()["mongo_id"]
        self.enviado_engenheiro = self._enviar_bitin(self.engenheiro, alt="D/P")
        self.encaminhado = self._enviar_bitin(self.outro_engenheiro, alt="D/P")
        self.client.post(f"/api/v1/bitins/{self.encaminhado}/encaminhar-roteiro", headers=self._auth(self.cadastro))

    def test_usuario_comum_so_ve_os_proprios(self) -> None:
        vistos = self._bitins_visiveis_para(self.engenheiro)
        self.assertIn(self.rascunho_engenheiro, vistos)
        self.assertIn(self.enviado_engenheiro, vistos)
        self.assertNotIn(self.encaminhado, vistos)  # é do outro_engenheiro

    def test_cadastro_nao_ve_rascunho_alheio_mas_ve_enviados(self) -> None:
        vistos = self._bitins_visiveis_para(self.cadastro)
        self.assertNotIn(self.rascunho_engenheiro, vistos)  # rascunho de outra pessoa: privado
        self.assertIn(self.enviado_engenheiro, vistos)
        self.assertIn(self.encaminhado, vistos)

    def test_processos_so_ve_a_fila_encaminhada(self) -> None:
        vistos = self._bitins_visiveis_para(self.processos)
        self.assertNotIn(self.rascunho_engenheiro, vistos)
        self.assertNotIn(self.enviado_engenheiro, vistos)  # ainda não foi encaminhado
        self.assertIn(self.encaminhado, vistos)

    def test_admin_ve_tudo(self) -> None:
        vistos = self._bitins_visiveis_para(self.admin)
        self.assertIn(self.rascunho_engenheiro, vistos)
        self.assertIn(self.enviado_engenheiro, vistos)
        self.assertIn(self.encaminhado, vistos)

    def test_processos_nao_cria_bitin_mas_admin_sim(self) -> None:
        negado = self.client.post(
            "/api/v1/bitins/draft",
            json={"content": make_bitin_content()},
            headers=self._auth(self.processos),
        )
        self.assertEqual(negado.status_code, 403)

        permitido = self.client.post(
            "/api/v1/bitins/draft",
            json={"content": make_bitin_content()},
            headers=self._auth(self.admin),
        )
        self.assertEqual(permitido.status_code, 200)


if __name__ == "__main__":
    unittest.main()
