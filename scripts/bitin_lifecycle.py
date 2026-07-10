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
