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

from backend.auth.models import Usuario  # noqa: E402
from backend.auth.security import create_access_token, get_password_hash  # noqa: E402
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
            hashed_password=get_password_hash("senha123"),
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
            json={"email": "primeiro@example.com", "nome": "Primeiro", "password": "senha123"},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()["permission_level"], 99)

    def test_segundo_usuario_registrado_nao_vira_admin(self) -> None:
        self.client.post(
            "/api/v1/auth/register",
            json={"email": "primeiro@example.com", "nome": "Primeiro", "password": "senha123"},
        )
        resp = self.client.post(
            "/api/v1/auth/register",
            json={"email": "segundo@example.com", "nome": "Segundo", "password": "senha123"},
        )
        self.assertEqual(resp.json()["permission_level"], 0)

    def test_registro_ignora_permission_level_enviado_pelo_cliente(self) -> None:
        """A vulnerabilidade encontrada na revisão do GPT_Engineering_authAPI: o cliente não
        pode se auto-promover a admin mandando permission_level no corpo da requisição --
        UserCreate nem tem esse campo, então um valor extra é simplesmente ignorado."""
        self.client.post(  # primeiro usuário -- garante que o próximo não seja bootstrap-admin
            "/api/v1/auth/register",
            json={"email": "primeiro@example.com", "nome": "Primeiro", "password": "senha123"},
        )
        resp = self.client.post(
            "/api/v1/auth/register",
            json={
                "email": "invasor@example.com", "nome": "Invasor", "password": "senha123",
                "permission_level": 99,
            },
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()["permission_level"], 0)

    def test_registro_com_email_duplicado_falha(self) -> None:
        payload = {"email": "dup@example.com", "nome": "Dup", "password": "senha123"}
        self.client.post("/api/v1/auth/register", json=payload)
        resp = self.client.post("/api/v1/auth/register", json=payload)
        self.assertEqual(resp.status_code, 400)

    def test_login_com_credenciais_corretas_devolve_token(self) -> None:
        self.client.post(
            "/api/v1/auth/register",
            json={"email": "login@example.com", "nome": "Login", "password": "senha123"},
        )
        resp = self.client.post(
            "/api/v1/auth/login",
            data={"username": "login@example.com", "password": "senha123"},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertIn("access_token", resp.json())

    def test_login_com_senha_errada_falha(self) -> None:
        self.client.post(
            "/api/v1/auth/register",
            json={"email": "login2@example.com", "nome": "Login2", "password": "senha123"},
        )
        resp = self.client.post(
            "/api/v1/auth/login",
            data={"username": "login2@example.com", "password": "errada"},
        )
        self.assertEqual(resp.status_code, 400)

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
