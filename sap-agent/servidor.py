#!/usr/bin/env python3
"""Servidor HTTP local do agente SAP -- roda no PC do engenheiro, expõe `localhost:39217` pra
a tela ZBPP009 (`frontend/src/lib/sapAgent.ts`) chamar via `fetch()`. Não fala com o backend
FastAPI do BITin (nenhuma mudança lá é necessária) -- é só uma ponte entre o navegador e o
SAP GUI já aberto/logado nesta máquina (ver `sap_gui.py`).

CORS restrito às origens conhecidas do frontend (mesmo padrão de
`backend/config.py::CORS_ORIGINS`/`cors_origins_list`) -- nunca `origins="*"`, mesmo sendo só
localhost: um site malicioso aberto no mesmo navegador não pode ter permissão de disparar
consultas no SAP do engenheiro.
"""

import os
import threading

from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.serving import make_server

import estado_agente
import sap_gui

PORTA = 39217

_ORIGENS_DEV = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
]


def _origens_permitidas() -> list[str]:
    """Mesmo padrão de `backend/config.py::CORS_ORIGINS` (env var, string separada por vírgula)
    -- achado real numa revisão de segurança (2026-07-23): esta lista só cobria as portas de
    dev do Vite, exatamente o mesmo bug que `backend/config.py` já tinha corrigido antes (ver
    docs/DEPLOY.md, "achado ao preparar o deploy de teste/produção") -- sem isso, o agente
    ficaria inutilizável em QUALQUER deploy real (o navegador bloqueia a chamada do BITin pro
    agente local se a origem não bater). `BITIN_AGENTE_CORS_ORIGENS` deixa quem empacota o
    agente pra uso interno na empresa acrescentar a URL de verdade do sistema web, sem editar
    código."""
    extra = os.environ.get("BITIN_AGENTE_CORS_ORIGENS", "")
    origens_extra = [origem.strip() for origem in extra.split(",") if origem.strip()]
    return _ORIGENS_DEV + origens_extra


ORIGENS_PERMITIDAS = _origens_permitidas()

app = Flask(__name__)
CORS(app, origins=ORIGENS_PERMITIDAS)


@app.get("/status")
def status():
    """Health check -- só confirma que o agente está de pé, não abre o SAP GUI nem consulta
    nada (poll leve, ~15s, ver AgenteSapStatus.tsx). Testar a sessão SAP de verdade só acontece
    em /consultar-materiais, quando o engenheiro realmente pede."""
    return jsonify({"ok": True})


@app.post("/consultar-materiais")
def consultar_materiais():
    body = request.get_json(silent=True) or {}
    codigos = body.get("codigos")
    if not isinstance(codigos, list) or not codigos:
        return jsonify({"erro": "Envie 'codigos': lista não vazia de códigos de material."}), 400

    try:
        session = sap_gui.obter_sessao()
    except sap_gui.SapIndisponivelError as exc:
        return jsonify({"erro": str(exc)}), 503

    resultados = sap_gui.consultar_materiais(session, [str(c) for c in codigos])
    return jsonify({"resultados": resultados})


@app.post("/identificar-usuario")
def identificar_usuario():
    """O sistema web manda quem está logado assim que detecta o agente conectado (2026-07-23,
    pedido explícito: "com o agente aberto ele vai validar com o sistema... pegar a conta
    logada, todas as informações do usuário") -- só pra exibir na janela do agente quem está
    usando, não é autenticação de verdade (ver docstring de estado_agente.py)."""
    body = request.get_json(silent=True) or {}
    estado_agente.definir_usuario({
        "nome": str(body.get("nome", "")),
        "email": str(body.get("email", "")),
        "setor": str(body.get("setor", "")),
    })
    return jsonify({"ok": True})


@app.get("/campos-disponiveis")
def campos_disponiveis():
    """Lista os campos de dados_basicos que o agente já sabe buscar de verdade (mapeados com
    ID de tela real, ver sap_gui.py::CAMPOS_MM03) -- a tela nova ("código + campos") só oferece
    esses na hora de escolher, nunca um campo ainda não mapeado."""
    campos_mm06 = ["marcacao_eliminar_nivel_mandante", "marcacao_eliminar_nivel_centro"]
    campos = sorted(sap_gui.CAMPOS_MM03.keys()) + campos_mm06
    return jsonify({"campos": campos})


@app.post("/preencher-dados-basicos")
def preencher_dados_basicos():
    """Modo 'código + campos' (2026-07-22, pedido explícito do usuário) -- um material, um
    Centro e a lista de campos escolhidos -> valores lidos direto do MM03 (+ MM06 se
    `marcacao_eliminar_nivel_mandante`/`marcacao_eliminar_nivel_centro` forem pedidos). Sempre 1
    material por chamada (a tela escolhe o campo por vez que o engenheiro quer ver preenchido,
    diferente do lote de /consultar-materiais que só confere descrição)."""
    body = request.get_json(silent=True) or {}
    material = str(body.get("material", "")).strip()
    centro = str(body.get("centro", "")).strip()
    campos = body.get("campos")
    if not material or not centro or not isinstance(campos, list) or not campos:
        return jsonify({"erro": "Envie 'material', 'centro' e 'campos' (lista não vazia)."}), 400

    try:
        session = sap_gui.obter_sessao()
    except sap_gui.SapIndisponivelError as exc:
        return jsonify({"erro": str(exc)}), 503

    campos_mm06 = {c for c in campos if c in ("marcacao_eliminar_nivel_mandante", "marcacao_eliminar_nivel_centro")}
    campos_mm03 = [c for c in campos if c not in campos_mm06]

    resultados = sap_gui.consultar_dados_basicos_mm03(session, material, centro, campos_mm03) if campos_mm03 else {}
    if "marcacao_eliminar_nivel_mandante" in campos_mm06:
        resultados["marcacao_eliminar_nivel_mandante"] = sap_gui.consultar_flag_eliminacao_mandante(session)
    if "marcacao_eliminar_nivel_centro" in campos_mm06:
        resultados["marcacao_eliminar_nivel_centro"] = sap_gui.consultar_flag_eliminacao_centro(session, centro)

    return jsonify({"resultados": resultados})


class ServidorAgente:
    """Controla o ciclo de vida do servidor HTTP de verdade -- start/stop, não só `app.run()`
    (que bloqueia e não tem desligamento gracioso). Usado pela janela do agente pro checkbox
    "Agente ativo" (2026-07-23, pedido explícito: "vai ter opção de ativar e desativar o agente
    ali na tela dele. onde o sistema vai validar em tempo real se o agente está ou não ativo")
    -- desativar aqui fecha a porta de verdade, então o poll de `/status` que o BITin já faz
    detecta a queda sozinho, sem precisar de nenhuma mudança no formato da resposta."""

    def __init__(self, porta: int = PORTA):
        self._porta = porta
        self._servidor = None
        self._thread: threading.Thread | None = None

    @property
    def ativo(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def iniciar(self) -> None:
        if self.ativo:
            return
        self._servidor = make_server("127.0.0.1", self._porta, app)
        self._thread = threading.Thread(target=self._servidor.serve_forever, daemon=True)
        self._thread.start()

    def parar(self) -> None:
        if not self.ativo:
            return
        assert self._servidor is not None
        self._servidor.shutdown()
        self._thread.join(timeout=3)
        self._servidor = None
        self._thread = None
        estado_agente.limpar_usuario()


def main():
    # Modo simples (bloqueante) -- pra rodar via terminal/depuração sem a janela do agente
    # (ver agente_app.py, que usa ServidorAgente em vez disto). host 127.0.0.1 (não 0.0.0.0) --
    # só a própria máquina acessa, nunca a rede.
    app.run(host="127.0.0.1", port=PORTA, debug=False)


if __name__ == "__main__":
    main()
