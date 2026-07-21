"""Testa autenticação/usuários/subgrupos via FastAPI TestClient -- unificados neste backend
(ver docs/BACKEND.md, seção 'Autenticação'). SQLite em memória, mesmo padrão de
tests/test_backend_bitins.py."""

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

from backend.auth.models import SessaoUsuario, TentativaLogin, Usuario  # noqa: E402
from backend.auth.security import create_access_token, get_password_hash, hash_token  # noqa: E402
from backend.db.mongodb import get_mongo_db  # noqa: E402
from backend.db.session import Base, get_db  # noqa: E402
from backend.main import app  # noqa: E402

# Conta fixa de deps.CONTAS_SUPER_ADMIN (2026-07-20, ver backend/api/users.py::
# _exigir_super_admin) -- Gestão de usuários inteira agora exige essa conta específica, não
# só permission_level=99. Testes que chamam rotas de users como "admin" comum precisam dela
# pra passar da 1ª barreira; os poucos que testam "outro admin (não-super) é barrado" ficam
# de fora de propósito (ver test_admin_nao_pode_ser_rebaixado_nem_por_outro_admin /
# test_admin_nao_pode_excluir_outro_admin, que agora esperam 403 antes de chegar na regra
# antiga de "não mexe em admin").
SUPER_ADMIN_EMAIL = "alessandro.pereiradarosafilho@grainproteintech.com"


class AuthApiTest(unittest.TestCase):
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

        async def override_get_mongo_db():
            return mongo_client["bitin_test_db"]

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_mongo_db] = override_get_mongo_db
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.engine.dispose()

    def _create_user(
        self, user_id: int, permission_level: int = 77, setor: str = "engenharia", email: str | None = None,
    ) -> Usuario:
        db = self.SessionLocal()
        user = Usuario(
            id=user_id,
            email=email or f"user{user_id}@example.com",
            nome=f"Usuário {user_id}",
            hashed_password=get_password_hash("Senha123!"),
            permission_level=permission_level,
            # setor é só um rótulo descritivo do cargo da pessoa (2026-07-16, decisão explícita
            # do usuário) -- NÃO controla nenhuma regra de acesso, isso continua sendo só
            # permission_level. Default "usuario" aqui só pra satisfazer o NOT NULL da coluna
            # em testes que não se importam com o valor.
            setor=setor,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        db.expunge(user)
        db.close()
        return user

    def test_primeiro_usuario_registrado_vira_admin(self) -> None:
        """Bootstrap: sem isso, o sistema nasceria sem nenhum admin (ver comentário em
        backend/auth/routes.py)."""
        resp = self.client.post(
            "/api/v1/auth/register",
            json={
                "email": "primeiro@example.com", "nome": "Primeiro", "password": "Senha123!",
                "setor": "cadastro",
            },
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()["permission_level"], 99)

    def test_segundo_usuario_registrado_nao_vira_admin(self) -> None:
        self.client.post(
            "/api/v1/auth/register",
            json={
                "email": "primeiro@example.com", "nome": "Primeiro", "password": "Senha123!",
                "setor": "cadastro",
            },
        )
        resp = self.client.post(
            "/api/v1/auth/register",
            json={
                "email": "segundo@example.com", "nome": "Segundo", "password": "Senha123!",
                "setor": "engenharia",
            },
        )
        self.assertEqual(resp.json()["permission_level"], 77)

    def test_registro_ignora_permission_level_enviado_pelo_cliente(self) -> None:
        """A vulnerabilidade encontrada na revisão do GPT_Engineering_authAPI: o cliente não
        pode se auto-promover a admin mandando permission_level no corpo da requisição --
        UserCreate nem tem esse campo, então um valor extra é simplesmente ignorado."""
        self.client.post(  # primeiro usuário -- garante que o próximo não seja bootstrap-admin
            "/api/v1/auth/register",
            json={
                "email": "primeiro@example.com", "nome": "Primeiro", "password": "Senha123!",
                "setor": "cadastro",
            },
        )
        resp = self.client.post(
            "/api/v1/auth/register",
            json={
                "email": "invasor@example.com", "nome": "Invasor", "password": "Senha123!",
                "permission_level": 99, "setor": "engenharia",
            },
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()["permission_level"], 77)

    def test_registro_com_email_duplicado_falha(self) -> None:
        payload = {"email": "dup@example.com", "nome": "Dup", "password": "Senha123!", "setor": "engenharia"}
        self.client.post("/api/v1/auth/register", json=payload)
        resp = self.client.post("/api/v1/auth/register", json=payload)
        self.assertEqual(resp.status_code, 400)

    def test_registro_com_setor_invalido_falha(self) -> None:
        """Usuario.setor (rótulo de cargo) só aceita cadastro/gestor/usuario/processos --
        validado via SETORES_VALIDOS (backend/auth/schemas.py). NÃO tem relação com controle
        de acesso."""
        resp = self.client.post(
            "/api/v1/auth/register",
            json={
                "email": "setorinvalido2@example.com", "nome": "Invalido", "password": "Senha123!",
                "setor": "gerente",
            },
        )
        self.assertEqual(resp.status_code, 422, resp.text)

    def test_registro_sem_setor_falha(self) -> None:
        """setor é obrigatório em UserCreate (2026-07-16) -- omitir o campo dá 422."""
        resp = self.client.post(
            "/api/v1/auth/register",
            json={"email": "semsetorcampo@example.com", "nome": "SemCampo", "password": "Senha123!"},
        )
        self.assertEqual(resp.status_code, 422, resp.text)

    def test_login_com_credenciais_corretas_devolve_token(self) -> None:
        self.client.post(
            "/api/v1/auth/register",
            json={
                "email": "login@example.com", "nome": "Login", "password": "Senha123!",
                "setor": "engenharia",
            },
        )
        resp = self.client.post(
            "/api/v1/auth/login",
            data={"username": "login@example.com", "password": "Senha123!"},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertIn("access_token", resp.json())

    def test_login_com_senha_errada_falha(self) -> None:
        self.client.post(
            "/api/v1/auth/register",
            json={
                "email": "login2@example.com", "nome": "Login2", "password": "Senha123!",
                "setor": "engenharia",
            },
        )
        resp = self.client.post(
            "/api/v1/auth/login",
            data={"username": "login2@example.com", "password": "errada"},
        )
        self.assertEqual(resp.status_code, 400)

    def test_login_com_muitas_tentativas_erradas_bloqueia_temporariamente(self) -> None:
        """Desde 2026-07-15, o limite é lastreado em TentativaLogin (backend/auth/models.py),
        não mais num dict em memória (backend/auth/rate_limit.py virou um wrapper fino sobre
        consultas ao banco) -- mesma política (5 tentativas/5 minutos), agora sobrevivendo a
        um restart do processo."""
        from backend.auth import rate_limit

        email = "rate-limit-test@example.com"
        self.client.post(
            "/api/v1/auth/register",
            json={"email": email, "nome": "RL", "password": "Senha123!", "setor": "engenharia"},
        )

        for _ in range(rate_limit.MAX_TENTATIVAS):
            resp = self.client.post(
                "/api/v1/auth/login", data={"username": email, "password": "errada"},
            )
            self.assertEqual(resp.status_code, 400)

        # a próxima tentativa é bloqueada mesmo com a senha CERTA -- o limite é por e-mail,
        # não depende de continuar errando.
        bloqueado = self.client.post(
            "/api/v1/auth/login", data={"username": email, "password": "Senha123!"},
        )
        self.assertEqual(bloqueado.status_code, 429)

    def test_rate_limit_falha_grava_tentativa_login_no_banco(self) -> None:
        """Substitui o teste antigo que checava o dict em memória diretamente -- agora a
        prova de que uma tentativa foi registrada é uma linha em TentativaLogin."""
        db = self.SessionLocal()
        self.assertEqual(db.query(TentativaLogin).count(), 0)
        db.close()

        self.client.post(
            "/api/v1/auth/login", data={"username": "ninguem@example.com", "password": "x"},
        )

        db = self.SessionLocal()
        tentativas = db.query(TentativaLogin).all()
        db.close()
        self.assertEqual(len(tentativas), 1)
        self.assertEqual(tentativas[0].email, "ninguem@example.com")
        self.assertFalse(tentativas[0].sucesso)

    def test_login_bem_sucedido_atualiza_ultimo_acesso_e_cria_sessao(self) -> None:
        self.client.post(
            "/api/v1/auth/register",
            json={
                "email": "sessao@example.com", "nome": "Sessao", "password": "Senha123!",
                "setor": "engenharia",
            },
        )
        resp = self.client.post(
            "/api/v1/auth/login",
            data={"username": "sessao@example.com", "password": "Senha123!"},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        token = resp.json()["access_token"]

        db = self.SessionLocal()
        usuario = db.query(Usuario).filter(Usuario.email == "sessao@example.com").first()
        self.assertIsNotNone(usuario.ultimo_acesso)

        sessao = db.query(SessaoUsuario).filter(SessaoUsuario.token == hash_token(token)).first()
        self.assertIsNotNone(sessao)
        self.assertFalse(sessao.revogada)
        db.close()

    def test_logout_revoga_sessao_e_bloqueia_uso_posterior_do_token(self) -> None:
        self.client.post(
            "/api/v1/auth/register",
            json={
                "email": "logout@example.com", "nome": "Logout", "password": "Senha123!",
                "setor": "engenharia",
            },
        )
        login_resp = self.client.post(
            "/api/v1/auth/login",
            data={"username": "logout@example.com", "password": "Senha123!"},
        )
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # antes do logout, o token funciona normalmente
        antes = self.client.get("/api/v1/users/me", headers=headers)
        self.assertEqual(antes.status_code, 200, antes.text)

        logout_resp = self.client.post("/api/v1/auth/logout", headers=headers)
        self.assertEqual(logout_resp.status_code, 200, logout_resp.text)

        depois = self.client.get("/api/v1/users/me", headers=headers)
        self.assertEqual(depois.status_code, 401, depois.text)

    def test_registro_com_numero_eng_faz_round_trip(self) -> None:
        resp = self.client.post(
            "/api/v1/auth/register",
            json={
                "email": "eng@example.com", "nome": "Engenheiro", "password": "Senha123!",
                "numero_eng": "ENG-123", "setor": "engenharia",
            },
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()["numero_eng"], "ENG-123")

    def _criar_subgrupo(self, nome: str) -> int:
        db = self.SessionLocal()
        from backend.auth.models import Subgrupo

        subgrupo = Subgrupo(nome=nome)
        db.add(subgrupo)
        db.commit()
        db.refresh(subgrupo)
        subgrupo_id = subgrupo.id
        db.close()
        return subgrupo_id

    def _atribuir_subgrupos(self, user_id: int, subgrupo_ids: list[int]) -> None:
        db = self.SessionLocal()
        from backend.auth.models import Subgrupo

        usuario = db.query(Usuario).filter(Usuario.id == user_id).first()
        usuario.subgrupos = db.query(Subgrupo).filter(Subgrupo.id.in_(subgrupo_ids)).all()
        db.commit()
        db.close()

    def test_usuario_pode_pertencer_a_dois_subgrupos_ao_mesmo_tempo(self) -> None:
        """2026-07-15, pedido explícito: "colocar a opção de um usuário poder ser tanto
        armazenagem tanto quanto proteina" -- Usuario.sector_id virou many-to-many. Renomeado
        de Setor -> Subgrupo (2026-07-16)."""
        subgrupo_a = self._criar_subgrupo("Proteína Animal")
        subgrupo_b = self._criar_subgrupo("Armazenagem de Grãos")
        usuario = self._create_user(1)
        self._atribuir_subgrupos(usuario.id, [subgrupo_a, subgrupo_b])

        resp = self.client.get(
            "/api/v1/users/me", headers={"Authorization": f"Bearer {create_access_token(usuario.id)}"},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(sorted(resp.json()["subgrupo_ids"]), sorted([subgrupo_a, subgrupo_b]))

    def test_registro_com_subgrupo_ids_persiste_multiplos_subgrupos(self) -> None:
        subgrupo_a = self._criar_subgrupo("Proteína Animal")
        subgrupo_b = self._criar_subgrupo("Armazenagem de Grãos")
        resp = self.client.post(
            "/api/v1/auth/register",
            json={
                "email": "multisetor@example.com", "nome": "Multi", "password": "Senha123!",
                "subgrupo_ids": [subgrupo_a, subgrupo_b], "setor": "engenharia",
            },
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(sorted(resp.json()["subgrupo_ids"]), sorted([subgrupo_a, subgrupo_b]))

    def test_registro_com_subgrupo_inexistente_falha(self) -> None:
        resp = self.client.post(
            "/api/v1/auth/register",
            json={
                "email": "setorinvalido@example.com", "nome": "Invalido", "password": "Senha123!",
                "subgrupo_ids": [99999], "setor": "engenharia",
            },
        )
        self.assertEqual(resp.status_code, 400, resp.text)

    def test_admin_continua_vendo_todo_mundo_em_users(self) -> None:
        admin = self._create_user(1, permission_level=99, email=SUPER_ADMIN_EMAIL)
        self._create_user(2, permission_level=77)
        self._create_user(3, permission_level=77)

        resp = self.client.get(
            "/api/v1/users", headers={"Authorization": f"Bearer {create_access_token(admin.id)}"},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(len(resp.json()), 3)

    def test_users_me_com_token_valido(self) -> None:
        user = self._create_user(1)
        token = create_access_token(user.id)
        resp = self.client.get(
            "/api/v1/users/me", headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()["email"], user.email)

    # GET /users e GET /users/{id} SÓ ADMIN (2026-07-16, pedido explícito do usuário: "em
    # hipótese alguma 88, 77, 66 podem ver permissões e usuários que existem. gestão de
    # usuários é só admin") -- revogado o acesso que Gestor(77) tinha antes.

    def test_users_list_exige_admin_gestor_e_negado(self) -> None:
        comum = self._create_user(1, permission_level=77)
        resp = self.client.get(
            "/api/v1/users", headers={"Authorization": f"Bearer {create_access_token(comum.id)}"},
        )
        self.assertEqual(resp.status_code, 403)

        gestor = self._create_user(2, permission_level=88)
        resp_gestor = self.client.get(
            "/api/v1/users", headers={"Authorization": f"Bearer {create_access_token(gestor.id)}"},
        )
        self.assertEqual(resp_gestor.status_code, 403, resp_gestor.text)

        cadastro = self._create_user(3, permission_level=88)
        resp_cadastro = self.client.get(
            "/api/v1/users", headers={"Authorization": f"Bearer {create_access_token(cadastro.id)}"},
        )
        self.assertEqual(resp_cadastro.status_code, 403, resp_cadastro.text)

        admin = self._create_user(4, permission_level=99, email=SUPER_ADMIN_EMAIL)
        resp_admin = self.client.get(
            "/api/v1/users", headers={"Authorization": f"Bearer {create_access_token(admin.id)}"},
        )
        self.assertEqual(resp_admin.status_code, 200, resp_admin.text)

    def test_get_user_por_id_exige_admin_gestor_e_negado(self) -> None:
        gestor = self._create_user(1, permission_level=88)
        alvo = self._create_user(2, permission_level=77)

        resp = self.client.get(
            f"/api/v1/users/{alvo.id}",
            headers={"Authorization": f"Bearer {create_access_token(gestor.id)}"},
        )
        self.assertEqual(resp.status_code, 403, resp.text)

        admin = self._create_user(3, permission_level=99, email=SUPER_ADMIN_EMAIL)
        resp_admin = self.client.get(
            f"/api/v1/users/{alvo.id}",
            headers={"Authorization": f"Bearer {create_access_token(admin.id)}"},
        )
        self.assertEqual(resp_admin.status_code, 200, resp_admin.text)

    def test_promover_usuario_exige_admin(self) -> None:
        gestor = self._create_user(1, permission_level=88)
        alvo = self._create_user(2, permission_level=77)

        resp_negado = self.client.patch(
            f"/api/v1/users/{alvo.id}/permission",
            json={"permission_level": 99, "senha_admin": "Senha123!"},
            headers={"Authorization": f"Bearer {create_access_token(gestor.id)}"},
        )
        self.assertEqual(resp_negado.status_code, 403)

        admin = self._create_user(3, permission_level=99, email=SUPER_ADMIN_EMAIL)
        resp_ok = self.client.patch(
            f"/api/v1/users/{alvo.id}/permission",
            json={"permission_level": 99, "senha_admin": "Senha123!"},
            headers={"Authorization": f"Bearer {create_access_token(admin.id)}"},
        )
        self.assertEqual(resp_ok.status_code, 200, resp_ok.text)
        self.assertEqual(resp_ok.json()["permission_level"], 99)

    def test_alterar_permissao_com_senha_admin_incorreta_falha(self) -> None:
        """"quando eu trocar permissão de usuário já cadastrado sempre pedir a minha senha
        para confirmar" (2026-07-17, pedido explícito) -- checada ANTES de qualquer outra
        validação, mesmo padrão de create_user_by_admin."""
        admin = self._create_user(1, permission_level=99, email=SUPER_ADMIN_EMAIL)  # senha real: "Senha123!"
        alvo = self._create_user(2, permission_level=77)

        resp = self.client.patch(
            f"/api/v1/users/{alvo.id}/permission",
            json={"permission_level": 77, "senha_admin": "SenhaErrada1!"},
            headers={"Authorization": f"Bearer {create_access_token(admin.id)}"},
        )
        self.assertEqual(resp.status_code, 400, resp.text)
        self.assertIn("Senha incorreta", resp.json()["detail"])

        db = self.SessionLocal()
        inalterado = db.query(Usuario).filter(Usuario.id == alvo.id).first()
        db.close()
        self.assertEqual(inalterado.permission_level, 77)

    def test_alterar_permissao_sem_senha_admin_da_422(self) -> None:
        admin = self._create_user(1, permission_level=99, email=SUPER_ADMIN_EMAIL)
        alvo = self._create_user(2, permission_level=77)
        resp = self.client.patch(
            f"/api/v1/users/{alvo.id}/permission",
            json={"permission_level": 77},
            headers={"Authorization": f"Bearer {create_access_token(admin.id)}"},
        )
        self.assertEqual(resp.status_code, 422, resp.text)

    def test_subgrupos_listar_e_publico(self) -> None:
        resp = self.client.get("/api/v1/subgrupos")
        self.assertEqual(resp.status_code, 200)

    def test_registro_com_senha_fraca_e_rejeitado(self) -> None:
        """Reforço de autenticação pedido pelo usuário (2026-07-15) -- ver
        backend/auth/security.py::validate_password_strength. Só se aplica daqui pra frente
        (registro/troca novos), as 2 contas de exemplo com senha "123" no banco real não são
        tocadas por isso."""
        resp = self.client.post(
            "/api/v1/auth/register",
            json={"email": "fraco@example.com", "nome": "Fraco", "password": "123", "setor": "engenharia"},
        )
        self.assertEqual(resp.status_code, 422, resp.text)

    def test_registro_com_senha_forte_e_aceito(self) -> None:
        resp = self.client.post(
            "/api/v1/auth/register",
            json={
                "email": "forte@example.com", "nome": "Forte", "password": "Senha123!",
                "setor": "engenharia",
            },
        )
        self.assertEqual(resp.status_code, 200, resp.text)

    def test_change_password_com_senha_atual_errada_falha(self) -> None:
        self.client.post(
            "/api/v1/auth/register",
            json={
                "email": "troca1@example.com", "nome": "Troca1", "password": "Senha123!",
                "setor": "engenharia",
            },
        )
        login_resp = self.client.post(
            "/api/v1/auth/login",
            data={"username": "troca1@example.com", "password": "Senha123!"},
        )
        headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

        resp = self.client.post(
            "/api/v1/auth/change-password",
            json={"senha_atual": "errada", "senha_nova": "OutraSenha456!"},
            headers=headers,
        )
        self.assertEqual(resp.status_code, 400, resp.text)

    def test_change_password_com_senha_nova_fraca_falha(self) -> None:
        self.client.post(
            "/api/v1/auth/register",
            json={
                "email": "troca2@example.com", "nome": "Troca2", "password": "Senha123!",
                "setor": "engenharia",
            },
        )
        login_resp = self.client.post(
            "/api/v1/auth/login",
            data={"username": "troca2@example.com", "password": "Senha123!"},
        )
        headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

        resp = self.client.post(
            "/api/v1/auth/change-password",
            json={"senha_atual": "Senha123!", "senha_nova": "123"},
            headers=headers,
        )
        self.assertEqual(resp.status_code, 422, resp.text)

    def test_change_password_com_sucesso_troca_senha_e_revoga_outras_sessoes(self) -> None:
        self.client.post(
            "/api/v1/auth/register",
            json={
                "email": "troca3@example.com", "nome": "Troca3", "password": "Senha123!",
                "setor": "engenharia",
            },
        )
        login1 = self.client.post(
            "/api/v1/auth/login",
            data={"username": "troca3@example.com", "password": "Senha123!"},
        )
        headers1 = {"Authorization": f"Bearer {login1.json()['access_token']}"}

        # Segunda "sessão" criada direto no banco (não via /auth/login de novo): o JWT só
        # codifica sub+exp em segundos, então dois logins no mesmo segundo pro mesmo usuário
        # gerariam tokens idênticos e violariam o UNIQUE de sessoes_usuario.token -- inserir
        # direto simula outro dispositivo/navegador sem depender de um segundo real de
        # diferença de relógio.
        from datetime import datetime, timedelta, timezone

        outro_token = create_access_token(1, expires_delta=timedelta(minutes=1))
        db = self.SessionLocal()
        db.add(
            SessaoUsuario(
                usuario_id=1,
                token=hash_token(outro_token),
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
                revogada=False,
            )
        )
        db.commit()
        db.close()
        headers2 = {"Authorization": f"Bearer {outro_token}"}

        resp = self.client.post(
            "/api/v1/auth/change-password",
            json={"senha_atual": "Senha123!", "senha_nova": "NovaSenha789!"},
            headers=headers1,
        )
        self.assertEqual(resp.status_code, 200, resp.text)

        # senha antiga não funciona mais no login
        login_antigo = self.client.post(
            "/api/v1/auth/login",
            data={"username": "troca3@example.com", "password": "Senha123!"},
        )
        self.assertEqual(login_antigo.status_code, 400)

        # senha nova funciona -- sleep pra garantir um `exp` (segundos) diferente do login1,
        # já que o JWT só codifica sub+exp: dois logins no mesmo segundo pro mesmo usuário
        # gerariam o mesmo token e violariam o UNIQUE de sessoes_usuario.token (achado ao
        # escrever este teste, não uma limitação nova introduzida aqui).
        import time

        time.sleep(1)
        login_novo = self.client.post(
            "/api/v1/auth/login",
            data={"username": "troca3@example.com", "password": "NovaSenha789!"},
        )
        self.assertEqual(login_novo.status_code, 200)

        # a sessão que fez a troca continua válida...
        ainda_valido = self.client.get("/api/v1/users/me", headers=headers1)
        self.assertEqual(ainda_valido.status_code, 200, ainda_valido.text)

        # ...mas a outra sessão (login2) foi revogada
        outra_revogada = self.client.get("/api/v1/users/me", headers=headers2)
        self.assertEqual(outra_revogada.status_code, 401, outra_revogada.text)

    def test_subgrupos_criar_exige_admin(self) -> None:
        comum = self._create_user(1, permission_level=77)
        resp = self.client.post(
            "/api/v1/subgrupos", json={"nome": "Engenharia"},
            headers={"Authorization": f"Bearer {create_access_token(comum.id)}"},
        )
        self.assertEqual(resp.status_code, 403)

        admin = self._create_user(2, permission_level=99, email=SUPER_ADMIN_EMAIL)
        resp_ok = self.client.post(
            "/api/v1/subgrupos", json={"nome": "Engenharia"},
            headers={"Authorization": f"Bearer {create_access_token(admin.id)}"},
        )
        self.assertEqual(resp_ok.status_code, 200, resp_ok.text)

    # Cadastro de usuário só por admin (2026-07-15, POST /users -- backend/api/users.py::
    # create_user_by_admin), pedido explícito: "tela de cadastro de usuário SÓ PARA ADMIN
    # para não ter que cadastrar no banco".

    def test_criar_usuario_por_admin_exige_permissao_99(self) -> None:
        gestor = self._create_user(1, permission_level=88)
        resp = self.client.post(
            "/api/v1/users",
            json={
                "email": "novo@example.com", "nome": "Novo", "permission_level": 77,
                "setor": "engenharia", "senha_admin": "Senha123!",
            },
            headers={"Authorization": f"Bearer {create_access_token(gestor.id)}"},
        )
        self.assertEqual(resp.status_code, 403, resp.text)

    def test_criar_usuario_por_admin_com_sucesso_gera_senha_temporaria_valida(self) -> None:
        admin = self._create_user(1, permission_level=99, email=SUPER_ADMIN_EMAIL)
        subgrupo = self._criar_subgrupo("Engenharia")
        resp = self.client.post(
            "/api/v1/users",
            json={
                "email": "Novo@Example.com", "nome": "Novo", "permission_level": 77,
                "subgrupo_ids": [subgrupo], "setor": "engenharia", "senha_admin": "Senha123!",
            },
            headers={"Authorization": f"Bearer {create_access_token(admin.id)}"},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        senha_gerada = body["senha_temporaria_gerada"]
        # Não confia "por sorte" -- roda a mesma validação de força que o servidor rodaria
        # contra qualquer senha de registro/troca (backend/auth/security.py::
        # validate_password_strength), garantindo que o gerador realmente cumpre a regra.
        from backend.auth.security import validate_password_strength

        validate_password_strength(senha_gerada)  # não deve levantar
        self.assertTrue(body["senha_temporaria"])
        self.assertEqual(body["setor"], "engenharia")

        db = self.SessionLocal()
        criado = db.query(Usuario).filter(Usuario.email == "novo@example.com").first()
        db.close()
        self.assertIsNotNone(criado)
        self.assertTrue(criado.senha_temporaria)

    def test_criar_usuario_por_admin_com_email_duplicado_falha(self) -> None:
        admin = self._create_user(1, permission_level=99, email=SUPER_ADMIN_EMAIL)
        self._create_user(2, permission_level=77)  # email user2@example.com
        resp = self.client.post(
            "/api/v1/users",
            json={
                "email": "user2@example.com", "nome": "Duplicado", "permission_level": 77,
                "setor": "engenharia", "senha_admin": "Senha123!",
            },
            headers={"Authorization": f"Bearer {create_access_token(admin.id)}"},
        )
        self.assertEqual(resp.status_code, 400, resp.text)

    def test_criar_usuario_com_setor_invalido_falha(self) -> None:
        """Usuario.setor (rótulo de cargo cadastro/gestor/usuario) validado contra
        SETORES_VALIDOS -- valor fora da lista dá 422 (validação Pydantic), não chega a
        tocar no banco."""
        admin = self._create_user(1, permission_level=99, email=SUPER_ADMIN_EMAIL)
        resp = self.client.post(
            "/api/v1/users",
            json={
                "email": "setorruim@example.com", "nome": "Ruim", "permission_level": 99,
                "setor": "diretor", "senha_admin": "Senha123!",
            },
            headers={"Authorization": f"Bearer {create_access_token(admin.id)}"},
        )
        self.assertEqual(resp.status_code, 422, resp.text)

    def test_login_com_senha_temporaria_gerada_por_admin_funciona(self) -> None:
        admin = self._create_user(1, permission_level=99, email=SUPER_ADMIN_EMAIL)
        subgrupo = self._criar_subgrupo("Engenharia")
        criar = self.client.post(
            "/api/v1/users",
            json={
                "email": "temp@example.com", "nome": "Temp", "permission_level": 77,
                "subgrupo_ids": [subgrupo], "setor": "engenharia", "senha_admin": "Senha123!",
            },
            headers={"Authorization": f"Bearer {create_access_token(admin.id)}"},
        )
        senha_gerada = criar.json()["senha_temporaria_gerada"]

        login_resp = self.client.post(
            "/api/v1/auth/login",
            data={"username": "temp@example.com", "password": senha_gerada},
        )
        self.assertEqual(login_resp.status_code, 200, login_resp.text)
        headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

        me = self.client.get("/api/v1/users/me", headers=headers)
        self.assertEqual(me.status_code, 200, me.text)
        self.assertTrue(me.json()["senha_temporaria"])

        troca = self.client.post(
            "/api/v1/auth/change-password",
            json={"senha_atual": senha_gerada, "senha_nova": "MinhaSenhaSecreta1!"},
            headers=headers,
        )
        self.assertEqual(troca.status_code, 200, troca.text)

        me_depois = self.client.get("/api/v1/users/me", headers=headers)
        self.assertEqual(me_depois.status_code, 200, me_depois.text)
        self.assertFalse(me_depois.json()["senha_temporaria"])

    # 2ª revisão do modelo de permissões (2026-07-20): 77 Individual, 88 Gestor, 99 Admin,
    # cruzado com Usuario.setor (cadastro/processos/engenharia). Só Engenharia exige ao
    # menos 1 subgrupo (qualquer rank); Cadastro/Processos são times centrais, não presos a
    # um Subgrupo específico. Admin nunca precisou, mesmo com setor="engenharia".

    def test_criar_usuario_engenharia_individual_sem_subgrupo_falha(self) -> None:
        admin = self._create_user(1, permission_level=99, email=SUPER_ADMIN_EMAIL)
        resp = self.client.post(
            "/api/v1/users",
            json={
                "email": "semsubgrupo77@example.com", "nome": "Sem Subgrupo", "permission_level": 77,
                "setor": "engenharia", "senha_admin": "Senha123!",
            },
            headers={"Authorization": f"Bearer {create_access_token(admin.id)}"},
        )
        self.assertEqual(resp.status_code, 400, resp.text)

    def test_criar_usuario_engenharia_gestor_sem_subgrupo_falha(self) -> None:
        admin = self._create_user(1, permission_level=99, email=SUPER_ADMIN_EMAIL)
        resp = self.client.post(
            "/api/v1/users",
            json={
                "email": "semsubgrupo88@example.com", "nome": "Sem Subgrupo", "permission_level": 88,
                "setor": "engenharia", "senha_admin": "Senha123!",
            },
            headers={"Authorization": f"Bearer {create_access_token(admin.id)}"},
        )
        self.assertEqual(resp.status_code, 400, resp.text)

    def test_criar_usuario_cadastro_individual_sem_subgrupo_sucede(self) -> None:
        """Cadastro é um time central que recebe BITins de qualquer Subgrupo -- não exige
        subgrupo (ver backend/auth/schemas.py::exige_subgrupo)."""
        admin = self._create_user(1, permission_level=99, email=SUPER_ADMIN_EMAIL)
        resp = self.client.post(
            "/api/v1/users",
            json={
                "email": "semsubgrupocadastro@example.com", "nome": "Sem Subgrupo", "permission_level": 77,
                "setor": "cadastro", "senha_admin": "Senha123!",
            },
            headers={"Authorization": f"Bearer {create_access_token(admin.id)}"},
        )
        self.assertEqual(resp.status_code, 200, resp.text)

    def test_criar_usuario_processos_individual_sem_subgrupo_sucede(self) -> None:
        """Processos, mesmo raciocínio do Cadastro logo acima."""
        admin = self._create_user(1, permission_level=99, email=SUPER_ADMIN_EMAIL)
        resp = self.client.post(
            "/api/v1/users",
            json={
                "email": "semsubgrupoprocessos@example.com", "nome": "Sem Subgrupo", "permission_level": 77,
                "setor": "processos", "senha_admin": "Senha123!",
            },
            headers={"Authorization": f"Bearer {create_access_token(admin.id)}"},
        )
        self.assertEqual(resp.status_code, 200, resp.text)

    def test_criar_usuario_gestor_cadastro_com_subgrupo_sucede(self) -> None:
        """Subgrupo é opcional pra Cadastro, mas informar um continua válido -- exige_subgrupo
        só bloqueia a AUSÊNCIA de subgrupo pra Engenharia, não proíbe Cadastro de ter um."""
        admin = self._create_user(1, permission_level=99, email=SUPER_ADMIN_EMAIL)
        subgrupo = self._criar_subgrupo("Engenharia")
        resp = self.client.post(
            "/api/v1/users",
            json={
                "email": "gestorcadastro@example.com", "nome": "Gestor Cadastro", "permission_level": 88,
                "subgrupo_ids": [subgrupo], "setor": "cadastro", "senha_admin": "Senha123!",
            },
            headers={"Authorization": f"Bearer {create_access_token(admin.id)}"},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()["permission_level"], 88)

    def test_criar_usuario_nivel_99_sem_subgrupo_sucede(self) -> None:
        """Admin (99) é o único rank que pode ficar sem subgrupo nenhum mesmo com
        setor="engenharia" (que normalmente exige subgrupo pra 77/88) -- exige_subgrupo tem
        um bypass explícito pra NIVEL_ADMIN."""
        admin = self._create_user(1, permission_level=99, email=SUPER_ADMIN_EMAIL)
        resp = self.client.post(
            "/api/v1/users",
            json={
                "email": "outroadmin99@example.com", "nome": "Outro Admin", "permission_level": 99,
                "setor": "engenharia", "senha_admin": "Senha123!",
            },
            headers={"Authorization": f"Bearer {create_access_token(admin.id)}"},
        )
        self.assertEqual(resp.status_code, 200, resp.text)

    def test_admin_nao_pode_ser_rebaixado_nem_por_outro_admin(self) -> None:
        """Um admin (99) comum -- não a conta super-admin -- nem chega na regra antiga de
        "não mexe em admin": a rota inteira agora é reservada ao super-admin
        (2026-07-20, ver _exigir_super_admin), então o 403 já bloqueia antes disso.
        test_super_admin_pode_rebaixar_outro_admin logo abaixo cobre o caso em que quem
        chama É o super-admin."""
        admin1 = self._create_user(1, permission_level=99)
        admin_alvo = self._create_user(2, permission_level=99)

        resp = self.client.patch(
            f"/api/v1/users/{admin_alvo.id}/permission",
            json={"permission_level": 77, "senha_admin": "Senha123!"},
            headers={"Authorization": f"Bearer {create_access_token(admin1.id)}"},
        )
        self.assertEqual(resp.status_code, 403, resp.text)

        db = self.SessionLocal()
        ainda_admin = db.query(Usuario).filter(Usuario.id == admin_alvo.id).first()
        db.close()
        self.assertEqual(ainda_admin.permission_level, 99)

    # Super-admin oculto (2026-07-17, pedido explícito: "me coloca como admin TOTAL... isso
    # vai ser uma permissão escondida no front que só existe no back") -- ver
    # backend/auth/deps.py::CONTAS_SUPER_ADMIN/eh_super_admin. Só essa conta específica ignora
    # a proteção "admin não mexe em admin"; autoproteção continua valendo até pra ela.

    def test_super_admin_pode_rebaixar_outro_admin(self) -> None:
        super_admin = self._create_user(1, permission_level=99, email=SUPER_ADMIN_EMAIL)
        admin_alvo = self._create_user(2, permission_level=99)

        resp = self.client.patch(
            f"/api/v1/users/{admin_alvo.id}/permission",
            json={"permission_level": 77, "senha_admin": "Senha123!"},
            headers={"Authorization": f"Bearer {create_access_token(super_admin.id)}"},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()["permission_level"], 77)

    def test_super_admin_nao_pode_alterar_o_proprio_nivel(self) -> None:
        super_admin = self._create_user(1, permission_level=99, email=SUPER_ADMIN_EMAIL)
        resp = self.client.patch(
            f"/api/v1/users/{super_admin.id}/permission",
            json={"permission_level": 77, "senha_admin": "Senha123!"},
            headers={"Authorization": f"Bearer {create_access_token(super_admin.id)}"},
        )
        self.assertEqual(resp.status_code, 400, resp.text)

    def test_super_admin_pode_excluir_outro_admin(self) -> None:
        super_admin = self._create_user(1, permission_level=99, email=SUPER_ADMIN_EMAIL)
        admin_alvo = self._create_user(2, permission_level=99)

        resp = self.client.delete(
            f"/api/v1/users/{admin_alvo.id}",
            headers={"Authorization": f"Bearer {create_access_token(super_admin.id)}"},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertFalse(resp.json()["ativo"])

    def test_super_admin_nao_pode_se_auto_excluir(self) -> None:
        super_admin = self._create_user(1, permission_level=99, email=SUPER_ADMIN_EMAIL)
        resp = self.client.delete(
            f"/api/v1/users/{super_admin.id}",
            headers={"Authorization": f"Bearer {create_access_token(super_admin.id)}"},
        )
        self.assertEqual(resp.status_code, 400, resp.text)

    # Exclusão de usuário (2026-07-17, pedido explícito) -- DELETE /users/{id} é soft-delete
    # (backend/api/users.py::delete_user marca ativo=False), mesmas proteções de
    # update_user_permission (admin não pode ser excluído, ninguém se auto-exclui). GET /users
    # devolve ativos e inativos juntos (2026-07-17, era só ativo=True -- revertido pra dar
    # suporte ao filtro Ativados/Desativados de GestaoUsuarios.tsx), `ativo=False` no corpo é
    # quem distingue.

    def test_admin_exclui_usuario_com_sucesso(self) -> None:
        admin = self._create_user(1, permission_level=99, email=SUPER_ADMIN_EMAIL)
        alvo = self._create_user(2, permission_level=77)

        resp = self.client.delete(
            f"/api/v1/users/{alvo.id}",
            headers={"Authorization": f"Bearer {create_access_token(admin.id)}"},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertFalse(resp.json()["ativo"])

        db = self.SessionLocal()
        excluido = db.query(Usuario).filter(Usuario.id == alvo.id).first()
        db.close()
        self.assertFalse(excluido.ativo)

        resp_list = self.client.get(
            "/api/v1/users", headers={"Authorization": f"Bearer {create_access_token(admin.id)}"},
        )
        usuarios_por_id = {u["id"]: u for u in resp_list.json()}
        self.assertIn(alvo.id, usuarios_por_id)
        self.assertFalse(usuarios_por_id[alvo.id]["ativo"])

    def test_admin_reativa_usuario_excluido(self) -> None:
        """"quando eu reativo aparece de novo com uma nova senha do 0 e novo email"
        (2026-07-17, pedido explícito) -- reativar sempre gera senha nova e aceita e-mail
        novo (repetir o mesmo e-mail também é válido, ver teste abaixo)."""
        admin = self._create_user(1, permission_level=99, email=SUPER_ADMIN_EMAIL)
        alvo = self._create_user(2, permission_level=77)  # senha real: "Senha123!"
        self.client.delete(
            f"/api/v1/users/{alvo.id}", headers={"Authorization": f"Bearer {create_access_token(admin.id)}"},
        )

        resp = self.client.post(
            f"/api/v1/users/{alvo.id}/reativar",
            json={"email": "novo.email@example.com"},
            headers={"Authorization": f"Bearer {create_access_token(admin.id)}"},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertTrue(resp.json()["ativo"])
        self.assertEqual(resp.json()["email"], "novo.email@example.com")
        senha_nova = resp.json()["senha_temporaria_gerada"]
        self.assertTrue(senha_nova)

        db = self.SessionLocal()
        reativado = db.query(Usuario).filter(Usuario.id == alvo.id).first()
        db.close()
        self.assertTrue(reativado.ativo)
        self.assertEqual(reativado.email, "novo.email@example.com")

        # A senha ANTIGA ("Senha123!") não funciona mais -- foi trocada do zero.
        login_antiga = self.client.post(
            "/api/v1/auth/login", data={"username": "novo.email@example.com", "password": "Senha123!"},
        )
        self.assertEqual(login_antiga.status_code, 400, login_antiga.text)

        login_nova = self.client.post(
            "/api/v1/auth/login", data={"username": "novo.email@example.com", "password": senha_nova},
        )
        self.assertEqual(login_nova.status_code, 200, login_nova.text)

    def test_reativar_com_email_ja_em_uso_falha(self) -> None:
        admin = self._create_user(1, permission_level=99, email=SUPER_ADMIN_EMAIL)
        outro = self._create_user(2, permission_level=77)
        excluido = self._create_user(3, permission_level=77)
        self.client.delete(
            f"/api/v1/users/{excluido.id}", headers={"Authorization": f"Bearer {create_access_token(admin.id)}"},
        )

        resp = self.client.post(
            f"/api/v1/users/{excluido.id}/reativar",
            json={"email": outro.email},
            headers={"Authorization": f"Bearer {create_access_token(admin.id)}"},
        )
        self.assertEqual(resp.status_code, 400, resp.text)

    def test_admin_reseta_senha_de_usuario(self) -> None:
        """"Esqueci minha senha" (2026-07-21, pedido explícito) -- sem SMTP, virou uma opção
        do admin dentro de Gestão de usuários em vez de self-service por e-mail. Mesmo padrão
        de reativar (senha nova, texto puro uma única vez, senha_temporaria=True), mas sem
        mexer em email/ativo."""
        admin = self._create_user(1, permission_level=99, email=SUPER_ADMIN_EMAIL)
        alvo = self._create_user(2, permission_level=77)  # senha real: "Senha123!"

        resp = self.client.post(
            f"/api/v1/users/{alvo.id}/resetar-senha",
            headers={"Authorization": f"Bearer {create_access_token(admin.id)}"},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()["email"], alvo.email)  # email não muda
        senha_nova = resp.json()["senha_temporaria_gerada"]
        self.assertTrue(senha_nova)

        db = self.SessionLocal()
        atualizado = db.query(Usuario).filter(Usuario.id == alvo.id).first()
        db.close()
        self.assertTrue(atualizado.senha_temporaria)

        login_antiga = self.client.post(
            "/api/v1/auth/login", data={"username": alvo.email, "password": "Senha123!"},
        )
        self.assertEqual(login_antiga.status_code, 400, login_antiga.text)

        login_nova = self.client.post(
            "/api/v1/auth/login", data={"username": alvo.email, "password": senha_nova},
        )
        self.assertEqual(login_nova.status_code, 200, login_nova.text)

    def test_resetar_senha_de_usuario_excluido_falha(self) -> None:
        admin = self._create_user(1, permission_level=99, email=SUPER_ADMIN_EMAIL)
        alvo = self._create_user(2, permission_level=77)
        self.client.delete(
            f"/api/v1/users/{alvo.id}", headers={"Authorization": f"Bearer {create_access_token(admin.id)}"},
        )

        resp = self.client.post(
            f"/api/v1/users/{alvo.id}/resetar-senha",
            headers={"Authorization": f"Bearer {create_access_token(admin.id)}"},
        )
        self.assertEqual(resp.status_code, 400, resp.text)

    def test_usuario_comum_nao_pode_resetar_senha_de_outro(self) -> None:
        admin = self._create_user(1, permission_level=99, email=SUPER_ADMIN_EMAIL)
        outro_admin_nao_super = self._create_user(2, permission_level=99)
        alvo = self._create_user(3, permission_level=77)

        resp_comum = self.client.post(
            f"/api/v1/users/{alvo.id}/resetar-senha",
            headers={"Authorization": f"Bearer {create_access_token(alvo.id)}"},
        )
        self.assertEqual(resp_comum.status_code, 403)

        resp_admin_nao_super = self.client.post(
            f"/api/v1/users/{alvo.id}/resetar-senha",
            headers={"Authorization": f"Bearer {create_access_token(outro_admin_nao_super.id)}"},
        )
        self.assertEqual(resp_admin_nao_super.status_code, 403)

    def test_recadastrar_email_de_usuario_excluido_reativa_a_mesma_linha(self) -> None:
        """"quando um usuário é excluído... e eu tento cadastrar ele de novo, deve permitir"
        (2026-07-17, pedido explícito) -- email é UNIQUE, então create_user_by_admin precisa
        REATIVAR a linha existente em vez de tentar inserir outra."""
        admin = self._create_user(1, permission_level=99, email=SUPER_ADMIN_EMAIL)
        alvo = self._create_user(2, permission_level=77)
        alvo_id = alvo.id
        self.client.delete(
            f"/api/v1/users/{alvo_id}", headers={"Authorization": f"Bearer {create_access_token(admin.id)}"},
        )

        resp = self.client.post(
            "/api/v1/users",
            json={
                "email": alvo.email, "nome": "Recriado", "permission_level": 99,
                "setor": "cadastro", "senha_admin": "Senha123!",
            },
            headers={"Authorization": f"Bearer {create_access_token(admin.id)}"},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()["id"], alvo_id)  # mesma linha, não uma nova
        self.assertTrue(resp.json()["ativo"])
        self.assertEqual(resp.json()["nome"], "Recriado")

        db = self.SessionLocal()
        self.assertEqual(db.query(Usuario).filter(Usuario.email == alvo.email).count(), 1)
        db.close()

    def test_recadastrar_email_de_usuario_ativo_ainda_falha(self) -> None:
        admin = self._create_user(1, permission_level=99, email=SUPER_ADMIN_EMAIL)
        ativo = self._create_user(2, permission_level=77)
        resp = self.client.post(
            "/api/v1/users",
            json={
                "email": ativo.email, "nome": "Duplicado", "permission_level": 77,
                "setor": "cadastro", "subgrupo_ids": [], "senha_admin": "Senha123!",
            },
            headers={"Authorization": f"Bearer {create_access_token(admin.id)}"},
        )
        self.assertEqual(resp.status_code, 400, resp.text)

    def test_usuario_excluido_nao_consegue_mais_logar(self) -> None:
        admin = self._create_user(1, permission_level=99, email=SUPER_ADMIN_EMAIL)
        alvo = self._create_user(2, permission_level=77)  # senha real: "Senha123!"

        self.client.delete(
            f"/api/v1/users/{alvo.id}",
            headers={"Authorization": f"Bearer {create_access_token(admin.id)}"},
        )

        resp = self.client.post(
            "/api/v1/auth/login", data={"username": alvo.email, "password": "Senha123!"},
        )
        self.assertEqual(resp.status_code, 400, resp.text)

    def test_admin_nao_pode_excluir_a_si_mesmo(self) -> None:
        admin = self._create_user(1, permission_level=99, email=SUPER_ADMIN_EMAIL)
        resp = self.client.delete(
            f"/api/v1/users/{admin.id}",
            headers={"Authorization": f"Bearer {create_access_token(admin.id)}"},
        )
        self.assertEqual(resp.status_code, 400, resp.text)

    def test_admin_nao_pode_excluir_outro_admin(self) -> None:
        """Mesmo raciocínio de test_admin_nao_pode_ser_rebaixado_nem_por_outro_admin acima --
        admin1 não é o super-admin, então é barrado pelo 403 de _exigir_super_admin antes de
        chegar na regra antiga "não exclui admin"."""
        admin1 = self._create_user(1, permission_level=99)
        admin_alvo = self._create_user(2, permission_level=99)

        resp = self.client.delete(
            f"/api/v1/users/{admin_alvo.id}",
            headers={"Authorization": f"Bearer {create_access_token(admin1.id)}"},
        )
        self.assertEqual(resp.status_code, 403, resp.text)

    def test_gestor_nao_pode_excluir_usuario(self) -> None:
        gestor = self._create_user(1, permission_level=88)
        alvo = self._create_user(2, permission_level=77)
        resp = self.client.delete(
            f"/api/v1/users/{alvo.id}",
            headers={"Authorization": f"Bearer {create_access_token(gestor.id)}"},
        )
        self.assertEqual(resp.status_code, 403, resp.text)

    def test_users_list_cadastro_e_gestor_recebem_403(self) -> None:
        """GET /users fica restrito SÓ A ADMIN (2026-07-16, pedido explícito do usuário: "em
        hipótese alguma 88, 77, 66 podem ver permissões e usuários que existem. gestão de
        usuários é só admin") -- nem Cadastro(88) nem Gestor(77) podem mais chamar."""
        cadastro = self._create_user(1, permission_level=88)
        resp = self.client.get(
            "/api/v1/users", headers={"Authorization": f"Bearer {create_access_token(cadastro.id)}"},
        )
        self.assertEqual(resp.status_code, 403, resp.text)

        gestor = self._create_user(2, permission_level=88)
        resp_gestor = self.client.get(
            "/api/v1/users", headers={"Authorization": f"Bearer {create_access_token(gestor.id)}"},
        )
        self.assertEqual(resp_gestor.status_code, 403, resp_gestor.text)

    # Reconfirmação de senha do admin ao cadastrar usuário novo (2026-07-16, pedido explícito) --
    # senha_admin precisa bater com a senha ATUAL de quem chama POST /users, checado ANTES de
    # qualquer escrita no banco (backend/api/users.py::create_user_by_admin).

    def test_criar_usuario_com_senha_admin_incorreta_falha(self) -> None:
        admin = self._create_user(1, permission_level=99, email=SUPER_ADMIN_EMAIL)  # senha real: "Senha123!"
        resp = self.client.post(
            "/api/v1/users",
            json={
                "email": "novo@example.com", "nome": "Novo", "permission_level": 99,
                "setor": "cadastro", "senha_admin": "SenhaErrada1!",
            },
            headers={"Authorization": f"Bearer {create_access_token(admin.id)}"},
        )
        self.assertEqual(resp.status_code, 400, resp.text)

        db = self.SessionLocal()
        nao_criado = db.query(Usuario).filter(Usuario.email == "novo@example.com").first()
        db.close()
        self.assertIsNone(nao_criado)

    def test_criar_usuario_com_senha_admin_correta_sucede(self) -> None:
        admin = self._create_user(1, permission_level=99, email=SUPER_ADMIN_EMAIL)
        resp = self.client.post(
            "/api/v1/users",
            json={
                "email": "novo@example.com", "nome": "Novo", "permission_level": 99,
                "setor": "cadastro", "senha_admin": "Senha123!",
            },
            headers={"Authorization": f"Bearer {create_access_token(admin.id)}"},
        )
        self.assertEqual(resp.status_code, 200, resp.text)

    # Reatribuição de subgrupo(s) de um usuário já cadastrado (2026-07-16, pedido explícito do
    # admin) -- PATCH /users/{id}/subgrupos, endpoint dedicado (backend/api/users.py::
    # update_user_subgrupos), mesma regra de NIVEIS_QUE_EXIGEM_SUBGRUPO de create_user_by_admin.
    # Renomeado de PATCH /users/{id}/sectors.

    def test_admin_reatribui_subgrupo_de_usuario_66_com_sucesso(self) -> None:
        admin = self._create_user(1, permission_level=99, email=SUPER_ADMIN_EMAIL)
        subgrupo_a = self._criar_subgrupo("Armazenagem")
        subgrupo_b = self._criar_subgrupo("Proteína")
        alvo = self._create_user(2, permission_level=77)

        resp = self.client.patch(
            f"/api/v1/users/{alvo.id}/subgrupos",
            json={"subgrupo_ids": [subgrupo_a, subgrupo_b]},
            headers={"Authorization": f"Bearer {create_access_token(admin.id)}"},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(sorted(resp.json()["subgrupo_ids"]), sorted([subgrupo_a, subgrupo_b]))

    def test_admin_nao_pode_deixar_usuario_66_sem_subgrupo(self) -> None:
        admin = self._create_user(1, permission_level=99, email=SUPER_ADMIN_EMAIL)
        subgrupo = self._criar_subgrupo("Armazenagem")
        alvo = self._create_user(2, permission_level=77)
        # Subgrupo inicial pra garantir que a rejeição é da regra, não de já estar vazio.
        self.client.patch(
            f"/api/v1/users/{alvo.id}/subgrupos",
            json={"subgrupo_ids": [subgrupo]},
            headers={"Authorization": f"Bearer {create_access_token(admin.id)}"},
        )

        resp = self.client.patch(
            f"/api/v1/users/{alvo.id}/subgrupos",
            json={"subgrupo_ids": []},
            headers={"Authorization": f"Bearer {create_access_token(admin.id)}"},
        )
        self.assertEqual(resp.status_code, 400, resp.text)

    def test_admin_pode_deixar_usuario_99_sem_subgrupo(self) -> None:
        """Admin (99) não é afetado pela regra de subgrupo obrigatório -- pode ficar sem
        subgrupo nenhum, mesma exceção de create_user_by_admin."""
        admin = self._create_user(1, permission_level=99, email=SUPER_ADMIN_EMAIL)
        outro_admin = self._create_user(2, permission_level=99)

        resp = self.client.patch(
            f"/api/v1/users/{outro_admin.id}/subgrupos",
            json={"subgrupo_ids": []},
            headers={"Authorization": f"Bearer {create_access_token(admin.id)}"},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()["subgrupo_ids"], [])

    # Novo campo Usuario.setor (2026-07-16) -- rótulo descritivo de cargo, PATCH dedicado.

    def test_admin_troca_setor_de_usuario_com_sucesso(self) -> None:
        admin = self._create_user(1, permission_level=99, email=SUPER_ADMIN_EMAIL)
        alvo = self._create_user(2, permission_level=88, setor="engenharia")

        resp = self.client.patch(
            f"/api/v1/users/{alvo.id}/setor",
            json={"setor": "processos"},
            headers={"Authorization": f"Bearer {create_access_token(admin.id)}"},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()["setor"], "processos")

    def test_troca_setor_exige_admin(self) -> None:
        gestor = self._create_user(1, permission_level=88)
        alvo = self._create_user(2, permission_level=77)

        resp = self.client.patch(
            f"/api/v1/users/{alvo.id}/setor",
            json={"setor": "processos"},
            headers={"Authorization": f"Bearer {create_access_token(gestor.id)}"},
        )
        self.assertEqual(resp.status_code, 403, resp.text)

    def test_troca_setor_com_valor_invalido_falha(self) -> None:
        admin = self._create_user(1, permission_level=99, email=SUPER_ADMIN_EMAIL)
        alvo = self._create_user(2, permission_level=77)

        resp = self.client.patch(
            f"/api/v1/users/{alvo.id}/setor",
            json={"setor": "diretor"},
            headers={"Authorization": f"Bearer {create_access_token(admin.id)}"},
        )
        self.assertEqual(resp.status_code, 422, resp.text)

if __name__ == "__main__":
    unittest.main()
