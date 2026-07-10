"""Erro estruturado compartilhado por todas as funções validate_* do BITin.

Decisão registrada (docs/BITIN_MODEL.md, "Erros estruturados"): dict, não string solta --
'field' pro frontend destacar o campo exato, 'code' estável pra tratamento por tipo,
'message' pronto pra mostrar ao usuário.
"""

from typing import TypedDict


class BitinError(TypedDict):
    field: str
    code: str
    message: str


def make_error(field: str, code: str, message: str) -> BitinError:
    return {"field": field, "code": code, "message": message}
