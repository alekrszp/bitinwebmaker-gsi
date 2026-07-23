"""Testes de `instancia_unica.py` -- mutex/janela reais do Windows, mas com nome/título
próprios de teste (nunca o `_MUTEX_NOME`/`NOME_JANELA` de produção) pra não colidir com um
agente de verdade que porventura esteja rodando na máquina de quem roda os testes."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import instancia_unica


def test_adquirir_primeira_vez_devolve_true(monkeypatch):
    monkeypatch.setattr(instancia_unica, "_MUTEX_NOME", "BitinAgenteSAP_Teste_1a")
    assert instancia_unica.adquirir() is True


def test_adquirir_segunda_vez_no_mesmo_processo_devolve_false(monkeypatch):
    # Mesmo processo mantendo o mutex já adquirido -- CreateMutex de novo com o MESMO nome
    # também reporta ERROR_ALREADY_EXISTS (é exatamente esse sinal que `adquirir()` usa pra
    # detectar "já tem uma instância"), então isso já simula o cenário real de uma 2ª
    # instância tentando abrir.
    monkeypatch.setattr(instancia_unica, "_MUTEX_NOME", "BitinAgenteSAP_Teste_1b")
    assert instancia_unica.adquirir() is True
    assert instancia_unica.adquirir() is False


def test_mostrar_instancia_existente_sem_janela_devolve_false(monkeypatch):
    monkeypatch.setattr(instancia_unica, "NOME_JANELA", "Janela De Teste Que Nunca Existe Xyz123")
    assert instancia_unica.mostrar_instancia_existente() is False
