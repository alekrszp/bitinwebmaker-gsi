"""Testa GET /api/v1/agente-sap/download (backend/api/agente_sap.py) -- endpoint público (sem
login, ver docstring do módulo) que serve o Instalador.exe do agente SAP local."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from backend.config import settings  # noqa: E402
from backend.main import app  # noqa: E402

client = TestClient(app)


def test_download_404_quando_instalador_nao_foi_gerado(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "AGENTE_SAP_INSTALADOR_PATH", str(tmp_path / "nao-existe.exe"))
    resp = client.get("/api/v1/agente-sap/download")
    assert resp.status_code == 404
    assert "não foi gerado" in resp.json()["detail"]


def test_download_200_serve_o_arquivo(monkeypatch, tmp_path):
    caminho = tmp_path / "Instalador.exe"
    caminho.write_bytes(b"conteudo falso do instalador")
    monkeypatch.setattr(settings, "AGENTE_SAP_INSTALADOR_PATH", str(caminho))

    resp = client.get("/api/v1/agente-sap/download")

    assert resp.status_code == 200
    assert resp.content == b"conteudo falso do instalador"
    assert "Instalador.exe" in resp.headers["content-disposition"]


def test_download_nao_exige_autenticacao():
    # Público de propósito (ver docstring de agente_sap.py) -- sem Authorization nenhum.
    resp = client.get("/api/v1/agente-sap/download")
    assert resp.status_code != 401
