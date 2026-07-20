#!/usr/bin/env python3
"""Ciclo de vida do BITin: rascunho (editável, sem validação) -> enviado (travado).

Decisão de produto: o engenheiro tem liberdade total pra editar um BITin em rascunho --
toda a validação (estrutural + lista técnica + regras de negócio do POP + regras gerais)
só roda de uma vez, no envio. Depois de enviado, o BITin fica travado (nenhuma edição).
Ver docs/BITIN_MODEL.md, seção "Ciclo de vida do BITin".
"""

from datetime import datetime
from typing import Any

import bitin_business_rules
import bitin_model
import lista_tecnica_export
from bitin_errors import BitinError, make_error

STATUS_RASCUNHO = "rascunho"
STATUS_ENVIADO = "enviado"


def is_editable(bitin: dict[str, Any]) -> bool:
    return bitin.get("status", STATUS_RASCUNHO) != STATUS_ENVIADO


def require_editable(bitin: dict[str, Any]) -> None:
    """Guarda a ser chamada por qualquer função que vá mutar um BITin (adicionar/remover
    material, editar campo). Nenhuma edição deve contornar essa checagem."""
    if not is_editable(bitin):
        raise ValueError(f"BITin {bitin.get('bitin', '?')} já foi enviado — não pode ser editado")


def enviar_bitin(
    bitin: dict[str, Any],
    vba_mapping_config: dict[str, Any],
    document_config: dict[str, Any],
) -> tuple[bool, list[BitinError]]:
    """Roda toda a validação de uma vez. Se passar, marca status=enviado e carimba
    data_envio (muta o bitin recebido). Se falhar, bitin continua "rascunho"."""
    if bitin.get("status", STATUS_RASCUNHO) == STATUS_ENVIADO:
        return False, [make_error(
            "status", "already_sent",
            f"BITin {bitin.get('bitin', '?')} já foi enviado anteriormente",
        )]

    errors = list(bitin_model.validate_bitin(bitin, vba_mapping_config))
    errors += lista_tecnica_export.validate_lista_tecnica(bitin)
    errors += bitin_business_rules.validate_business_rules(bitin, document_config)

    if errors:
        return False, errors

    bitin["status"] = STATUS_ENVIADO
    bitin["data_envio"] = datetime.now().strftime("%Y-%m-%d")
    return True, []


def encaminhar_para_roteiro(bitin: dict[str, Any]) -> None:
    """Substitui o e-mail automático que o Módulo12.bas disparava ao enviar o BITin
    (romeu.maia/gustavo.goldshmith, "Segue BITin para cadastro/liberação") -- em vez de
    e-mail, o setor Cadastro tem uma fila própria (ver frontend CadastroPage.tsx) e marca
    aqui quando termina de processar e encaminha pro setor Roteiro (próxima etapa que já
    existia na macro original como aviso "REVISAR ROTEIRO", Módulo4.bas).

    Não é um terceiro status -- `encaminhado_roteiro` é um campo à parte que só faz sentido
    depois de `enviado` (mantém a checagem binária `is_editable` intacta em todo o resto do
    backend)."""
    if bitin.get("status", STATUS_RASCUNHO) != STATUS_ENVIADO:
        raise ValueError(f"BITin {bitin.get('bitin', '?')} ainda não foi enviado — nada para encaminhar")
    if bitin.get("encaminhado_roteiro", False):
        raise ValueError(f"BITin {bitin.get('bitin', '?')} já foi encaminhado para o roteiro")

    bitin["encaminhado_roteiro"] = True
    bitin["data_encaminhado_roteiro"] = datetime.now().strftime("%Y-%m-%d")


def concluir_processamento(bitin: dict[str, Any]) -> None:
    """Fecha o ciclo aberto por `encaminhar_para_roteiro` -- enquanto `encaminhado_roteiro`
    é True e isto ainda não rodou, o setor Processos pode reeditar o BITin (única exceção à
    regra geral de que "enviado" é travado pra sempre, ver
    backend/api/bitins.py::_pode_editar). Marcar como concluído tranca de novo, inclusive
    pra Processos -- ninguém edita depois disso."""
    if not bitin.get("encaminhado_roteiro", False):
        raise ValueError(f"BITin {bitin.get('bitin', '?')} ainda não foi encaminhado para o Processos")
    if bitin.get("processos_concluido", False):
        raise ValueError(f"BITin {bitin.get('bitin', '?')} já foi concluído pelo Processos")

    bitin["processos_concluido"] = True
    bitin["data_processos_concluido"] = datetime.now().strftime("%Y-%m-%d")


def concluir_sem_roteiro(bitin: dict[str, Any]) -> None:
    """Atalho pro Cadastro quando o BITin NÃO precisa passar pelo setor Processos (2026-07-17,
    pedido explícito: "coloca essa opção, do cadastro não precisar enviar pra processos,
    quando não houver: D/P, D/- ou -/P" -- ver bitin_document.precisa_roteiro pra regra
    exata). Chega direto no mesmo estado final de `concluir_processamento` (PDF liberado pro
    Cadastro baixar), sem passar pela janela de reedição do Processos -- `sem_necessidade_
    roteiro` só existe pra distinguir os dois caminhos na hora de auditar/exibir, não muda
    nenhum filtro (CadastroPage.tsx já lê só `processos_concluido`)."""
    if bitin.get("status", STATUS_RASCUNHO) != STATUS_ENVIADO:
        raise ValueError(f"BITin {bitin.get('bitin', '?')} ainda não foi enviado")
    if bitin.get("encaminhado_roteiro", False):
        raise ValueError(f"BITin {bitin.get('bitin', '?')} já foi encaminhado para o roteiro")

    agora = datetime.now().strftime("%Y-%m-%d")
    bitin["encaminhado_roteiro"] = True
    bitin["data_encaminhado_roteiro"] = agora
    bitin["processos_concluido"] = True
    bitin["data_processos_concluido"] = agora
    bitin["sem_necessidade_roteiro"] = True
