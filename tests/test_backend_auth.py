"""Testa autenticação/usuários/setores via FastAPI TestClient -- unificados neste backend
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

    def _create_user(self, user_id: int, permission_level: int = 0) -> Usuario:
        db = self.SessionLocal()
        user = Usuario(
            id=user_id,
            email=f"user{user_id}@example.com",
            nome=f"Usuário {user_id}",
            hashed_password=get_password_hash("Senha123!"),
            permission_level=permission_level,
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
            json={"email": "primeiro@example.com", "nome": "Primeiro", "password": "Senha123!"},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()["permission_level"], 99)

    def test_segundo_usuario_registrado_nao_vira_admin(self) -> None:
        self.client.post(
            "/api/v1/auth/register",
            json={"email": "primeiro@example.com", "nome": "Primeiro", "password": "Senha123!"},
        )
        resp = self.client.post(
            "/api/v1/auth/register",
            json={"email": "segundo@example.com", "nome": "Segundo", "password": "Senha123!"},
        )
        self.assertEqual(resp.json()["permission_level"], 0)

    def test_registro_ignora_permission_level_enviado_pelo_cliente(self) -> None:
        """A vulnerabilidade encontrada na revisão do GPT_Engineering_authAPI: o cliente não
        pode se auto-promover a admin mandando permission_level no corpo da requisição --
        UserCreate nem tem esse campo, então um valor extra é simplesmente ignorado."""
        self.client.post(  # primeiro usuário -- garante que o próximo não seja bootstrap-admin
            "/api/v1/auth/register",
            json={"email": "primeiro@example.com", "nome": "Primeiro", "password": "Senha123!"},
        )
        resp = self.client.post(
            "/api/v1/auth/register",
            json={
                "email": "invasor@example.com", "nome": "Invasor", "password": "Senha123!",
                "permission_level": 99,
            },
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()["permission_level"], 0)

    def test_registro_com_email_duplicado_falha(self) -> None:
        payload = {"email": "dup@example.com", "nome": "Dup", "password": "Senha123!"}
        self.client.post("/api/v1/auth/register", json=payload)
        resp = self.client.post("/api/v1/auth/register", json=payload)
        self.assertEqual(resp.status_code, 400)

    def test_login_com_credenciais_corretas_devolve_token(self) -> None:
        self.client.post(
            "/api/v1/auth/register",
            json={"email": "login@example.com", "nome": "Login", "password": "Senha123!"},
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
            json={"email": "login2@example.com", "nome": "Login2", "password": "Senha123!"},
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
            json={"email": email, "nome": "RL", "password": "Senha123!"},
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
            json={"email": "sessao@example.com", "nome": "Sessao", "password": "Senha123!"},
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
            json={"email": "logout@example.com", "nome": "Logout", "password": "Senha123!"},
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
                "numero_eng": "ENG-123",
            },
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()["numero_eng"], "ENG-123")

    def test_users_me_com_token_valido(self) -> None:
        user = self._create_user(1)
        token = create_access_token(user.id)
        resp = self.client.get(
            "/api/v1/users/me", headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()["email"], user.email)

    def test_users_list_exige_nivel_gestor_ou_admin(self) -> None:
        comum = self._create_user(1, permission_level=0)
        resp = self.client.get(
            "/api/v1/users", headers={"Authorization": f"Bearer {create_access_token(comum.id)}"},
        )
        self.assertEqual(resp.status_code, 403)

        gestor = self._create_user(2, permission_level=1)
        resp = self.client.get(
            "/api/v1/users", headers={"Authorization": f"Bearer {create_access_token(gestor.id)}"},
        )
        self.assertEqual(resp.status_code, 200)

    def test_promover_usuario_exige_admin(self) -> None:
        gestor = self._create_user(1, permission_level=1)
        alvo = self._create_user(2, permission_level=0)

        resp_negado = self.client.patch(
            f"/api/v1/users/{alvo.id}/permission",
            json={"permission_level": 99},
            headers={"Authorization": f"Bearer {create_access_token(gestor.id)}"},
        )
        self.assertEqual(resp_negado.status_code, 403)

        admin = self._create_user(3, permission_level=99)
        resp_ok = self.client.patch(
            f"/api/v1/users/{alvo.id}/permission",
            json={"permission_level": 99},
            headers={"Authorization": f"Bearer {create_access_token(admin.id)}"},
        )
        self.assertEqual(resp_ok.status_code, 200, resp_ok.text)
        self.assertEqual(resp_ok.json()["permission_level"], 99)

    def test_sectors_listar_e_publico(self) -> None:
        resp = self.client.get("/api/v1/sectors")
        self.assertEqual(resp.status_code, 200)

    def test_registro_com_senha_fraca_e_rejeitado(self) -> None:
        """Reforço de autenticação pedido pelo usuário (2026-07-15) -- ver
        backend/auth/security.py::validate_password_strength. Só se aplica daqui pra frente
        (registro/troca novos), as 2 contas de exemplo com senha "123" no banco real não são
        tocadas por isso."""
        resp = self.client.post(
            "/api/v1/auth/register",
            json={"email": "fraco@example.com", "nome": "Fraco", "password": "123"},
        )
        self.assertEqual(resp.status_code, 422, resp.text)

    def test_registro_com_senha_forte_e_aceito(self) -> None:
        resp = self.client.post(
            "/api/v1/auth/register",
            json={"email": "forte@example.com", "nome": "Forte", "password": "Senha123!"},
        )
        self.assertEqual(resp.status_code, 200, resp.text)

    def test_change_password_com_senha_atual_errada_falha(self) -> None:
        self.client.post(
            "/api/v1/auth/register",
            json={"email": "troca1@example.com", "nome": "Troca1", "password": "Senha123!"},
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
            json={"email": "troca2@example.com", "nome": "Troca2", "password": "Senha123!"},
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
            json={"email": "troca3@example.com", "nome": "Troca3", "password": "Senha123!"},
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

    def test_sectors_criar_exige_admin(self) -> None:
        comum = self._create_user(1, permission_level=0)
        resp = self.client.post(
            "/api/v1/sectors", json={"nome": "Engenharia"},
            headers={"Authorization": f"Bearer {create_access_token(comum.id)}"},
        )
        self.assertEqual(resp.status_code, 403)

        admin = self._create_user(2, permission_level=99)
        resp_ok = self.client.post(
            "/api/v1/sectors", json={"nome": "Engenharia"},
            headers={"Authorization": f"Bearer {create_access_token(admin.id)}"},
        )
        self.assertEqual(resp_ok.status_code, 200, resp_ok.text)


if __name__ == "__main__":
    unittest.main()
