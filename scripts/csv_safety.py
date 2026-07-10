"""Sanitização contra CSV/formula injection (OWASP): células que começam com
=, + ou @ podem ser interpretadas como fórmula quando o arquivo é aberto no
Excel. Como os exports escrevem texto vindo do BITin (descrição, motivo, etc.),
qualquer um desses campos pode conter esse prefixo sem intenção maliciosa
nenhuma -- ainda assim, sanitizamos antes de gravar.

Nota: "-" (hífen) foi DELIBERADAMENTE excluído da lista clássica OWASP (que
também inclui "-"), porque é um valor de domínio legítimo e onipresente neste
sistema -- os códigos de Alt são literalmente "-", "-/P", "-/F" (ver
docs/BITIN_MODEL.md). Sanitizar "-" quebraria esses valores no export real que
o Winshuttle/Central lê. TAB/CR não precisam de tratamento aqui porque o
csv.writer já os trata corretamente via quoting (RFC 4180)."""

FORMULA_TRIGGER_CHARS = ("=", "+", "@")


def sanitize_cell(value: str) -> str:
    if value and value[0] in FORMULA_TRIGGER_CHARS:
        return "'" + value
    return value


def sanitize_row(row: list[str]) -> list[str]:
    return [sanitize_cell(value) for value in row]
