import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config_agente


def test_carregar_sem_arquivo_devolve_padrao(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    config = config_agente.carregar()
    assert config == {"ativo": False, "abrir_com_windows": True}


def test_salvar_e_carregar_roundtrip(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    config_agente.salvar({"ativo": True, "abrir_com_windows": False})
    assert config_agente.carregar() == {"ativo": True, "abrir_com_windows": False}


def test_carregar_arquivo_corrompido_devolve_padrao(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    caminho = config_agente.caminho_config()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text("{ nao eh json valido", encoding="utf-8")
    assert config_agente.carregar() == {"ativo": False, "abrir_com_windows": True}


def test_carregar_preenche_campos_faltando_com_padrao(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    config_agente.salvar({"ativo": True})
    assert config_agente.carregar() == {"ativo": True, "abrir_com_windows": True}
