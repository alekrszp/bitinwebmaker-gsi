#!/usr/bin/env python3
"""Configuração persistida do agente (2026-07-23) --
`%LOCALAPPDATA%\\AgenteSAP\\config.json` (mesma pasta usada pra instalar o `.exe`, ver
`instalador_logica.py::NOME_PASTA_INSTALACAO`). Dois campos hoje:

- `ativo`: default `False` -- "sempre desativado desde o início... só ativa depois da primeira
  instalação" (pedido explícito anterior). O agente só liga o servidor HTTP sozinho, ao abrir,
  se essa configuração já estiver `True` de uma vez anterior (o engenheiro ligou e deixou
  ligado); numa instalação nova, começa sempre desligado até o engenheiro marcar o checkbox
  "Agente ativo" na janela.
- `abrir_com_windows`: default `True` -- "configuração vai ter já pré selecionada para o agente
  abrir com a inicialização do windows, mas com opção de tirar" (pedido explícito)."""

import json
import os
from pathlib import Path
from typing import Any

PADRAO: dict[str, Any] = {"ativo": False, "abrir_com_windows": True}


def caminho_config() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", str(Path.home())))
    return base / "AgenteSAP" / "config.json"


def carregar() -> dict[str, Any]:
    caminho = caminho_config()
    if not caminho.exists():
        return dict(PADRAO)
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return dict(PADRAO)
    if not isinstance(dados, dict):
        return dict(PADRAO)
    return {**PADRAO, **dados}


def salvar(config: dict[str, Any]) -> None:
    caminho = caminho_config()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
