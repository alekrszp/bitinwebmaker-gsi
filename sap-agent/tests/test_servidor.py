"""Testes de `servidor.py` -- `/identificar-usuario` via Flask test client (sem precisar
abrir socket de verdade), e `ServidorAgente` start/stop numa porta dedicada de teste (não a
39217 de produção, pra não colidir com um agente real rodando na mesma máquina)."""

import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import estado_agente
import servidor

PORTA_TESTE = 39218


def test_origens_permitidas_inclui_dev_por_padrao():
    assert "http://localhost:5173" in servidor._origens_permitidas()


def test_origens_permitidas_le_env_var_extra(monkeypatch):
    # Achado real (2026-07-23, revisão de segurança): sem isso, o agente ficava inutilizável em
    # qualquer deploy que não fosse localhost -- mesmo bug que backend/config.py já tinha
    # corrigido antes (CORS_ORIGINS via env var).
    monkeypatch.setenv("BITIN_AGENTE_CORS_ORIGENS", "https://bitin.empresa.exemplo, https://outra.exemplo")
    origens = servidor._origens_permitidas()
    assert "https://bitin.empresa.exemplo" in origens
    assert "https://outra.exemplo" in origens
    assert "http://localhost:5173" in origens  # dev continua funcionando junto


def test_identificar_usuario_guarda_no_estado_compartilhado():
    cliente = servidor.app.test_client()
    resp = cliente.post(
        "/identificar-usuario",
        json={"nome": "Fulano", "email": "fulano@empresa.com", "setor": "engenharia"},
    )
    assert resp.status_code == 200
    assert estado_agente.obter_usuario() == {"nome": "Fulano", "email": "fulano@empresa.com", "setor": "engenharia"}


def test_status_sempre_ok_via_test_client():
    cliente = servidor.app.test_client()
    resp = cliente.get("/status")
    assert resp.status_code == 200
    assert resp.get_json() == {"ok": True}


def _get(url: str, timeout: float = 2.0) -> int | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status
    except (urllib.error.URLError, ConnectionError):
        return None


def test_servidor_agente_iniciar_e_parar_controla_a_porta_de_verdade():
    servidor_agente = servidor.ServidorAgente(porta=PORTA_TESTE)
    url = f"http://127.0.0.1:{PORTA_TESTE}/status"
    try:
        assert servidor_agente.ativo is False
        assert _get(url) is None

        servidor_agente.iniciar()
        time.sleep(0.3)
        assert servidor_agente.ativo is True
        assert _get(url) == 200

        estado_agente.definir_usuario({"nome": "Fulano", "email": "fulano@empresa.com", "setor": "engenharia"})
        servidor_agente.parar()
        time.sleep(0.3)
        assert servidor_agente.ativo is False
        assert _get(url) is None
        # Desativar limpa o usuário identificado (ver ServidorAgente.parar) -- não faz
        # sentido mostrar "conectado como" com o servidor fora do ar.
        assert estado_agente.obter_usuario() is None
    finally:
        servidor_agente.parar()


def test_servidor_agente_iniciar_duas_vezes_e_idempotente():
    servidor_agente = servidor.ServidorAgente(porta=PORTA_TESTE)
    try:
        servidor_agente.iniciar()
        time.sleep(0.2)
        servidor_agente.iniciar()  # não deve levantar erro nem trocar a thread
        assert servidor_agente.ativo is True
    finally:
        servidor_agente.parar()
