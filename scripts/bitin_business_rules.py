#!/usr/bin/env python3
"""Regras de negócio do POP_ENG_7.3.7_002 + regras gerais de consistência, aplicadas
como portão de envio do BITin.

Filosofia: o engenheiro tem liberdade total pra editar o BITin -- essas regras só rodam
no envio (mesmo espírito de bitin_model.validate_bitin), nunca bloqueiam a edição.

Alt/Esp são declarados pelo engenheiro (impactos_operacionais), não derivados de código
SAP (ver docs/BITIN_MODEL.md, seção "Alt/Esp declarados pelo engenheiro" — código de Grupo
Mercadorias é vasto e muda com o tempo, então não é uma base confiável pra automação).
As regras aqui validam CONSISTÊNCIA GERAL entre o que foi declarado e o que foi de fato
alterado, sem depender de conhecer nenhum código específico -- exceto os valores válidos
de impactos_operacionais em si, que vêm do ANEXO A do POP (não mudam com o catálogo SAP).
"""

from typing import Any

import bitin_document
from bitin_errors import BitinError, make_error


def _validar_enums(
    impactos: dict[str, Any],
    valores_validos: dict[str, list[str]],
    material_field: str,
) -> list[BitinError]:
    errors: list[BitinError] = []
    for campo, validos in valores_validos.items():
        if campo == "_comment":
            continue
        valor = impactos.get(campo, "-")
        if valor not in validos:
            errors.append(make_error(
                f"{material_field}.impactos_operacionais.{campo}",
                f"invalid_{campo}_value",
                f"{material_field}: {campo}={valor!r} inválido — valores aceitos: {', '.join(validos)}",
            ))
    return errors


def validate_business_rules(
    bitin: dict[str, Any],
    document_config: dict[str, Any],
) -> list[BitinError]:
    errors: list[BitinError] = []
    ordem_cliente_codigos = {
        item.get("codigo") for item in bitin.get("ordem_cliente", []) if item.get("codigo")
    }
    codigos_centros_vistos: set[tuple[str, str]] = set()
    valores_validos = document_config["valores_validos"]

    for idx, material in enumerate(bitin.get("materiais", [])):
        codigo = material.get("codigo_material", "?")
        centro = material.get("centro", "?")
        material_field = f"materiais[{idx}]"
        prefix = f"{material_field} ({codigo}, centro {centro})"
        alteracoes = material.get("alteracoes", {})
        dados_basicos = alteracoes.get("dados_basicos", {})
        impactos = bitin_document.read_impactos_operacionais(material)
        alt = impactos["alt"]

        # Enum: alt/est/esp/lp/pre/oc/of precisam ser um dos valores do ANEXO A do POP.
        errors.extend(_validar_enums(impactos, valores_validos, material_field))

        # Geral: (código de material, centro) duplicado no mesmo BITin. Um mesmo código
        # pode legitimamente precisar de alteração em vários centros (ex.: 2001/2003/2005);
        # o que não pode é a MESMA combinação código+centro aparecer duas vezes.
        chave = (codigo, centro)
        if codigo != "?" and chave in codigos_centros_vistos:
            errors.append(make_error(
                f"{material_field}.centro", "duplicate_codigo_centro",
                f"{prefix}: combinação código+centro duplicada neste BITin",
            ))
        codigos_centros_vistos.add(chave)

        # Geral: campo listado em dados_basicos mas 'de' == 'para' (mudança sem efeito).
        mudancas_reais = []
        for campo, entry in dados_basicos.items():
            de, para = entry.get("de", ""), entry.get("para", "")
            campo_field = f"{material_field}.alteracoes.dados_basicos.{campo}"
            if para != "" and de == para:
                errors.append(make_error(
                    campo_field, "no_effective_change",
                    f"{prefix}: campo '{campo}' listado em dados_basicos mas 'de' e 'para' são "
                    f"iguais ({de!r}) — remova se não há mudança real",
                ))
            elif para != "":
                mudancas_reais.append(campo)

        alt_field = f"{material_field}.alteracoes.impactos_operacionais.alt"

        # Geral: Alt="-" (sem alteração) mas há campos de dados_basicos realmente mudando.
        if alt == "-" and mudancas_reais:
            errors.append(make_error(
                alt_field, "alt_inconsistent_no_changes",
                f"{prefix}: Alt='-' (sem alteração) mas há mudança(s) em dados_basicos "
                f"({', '.join(mudancas_reais)}) — confira se o Alt declarado está correto",
            ))

        # Geral: Alt indica alteração de desenho, mas nenhuma mudança de Nível de Revisão
        # foi registrada — sinal de que o Alt declarado pode não corresponder ao que
        # realmente foi alterado.
        if alt.startswith("D") and "nivel_revisao" not in mudancas_reais:
            errors.append(make_error(
                alt_field, "alt_desenho_sem_revisao",
                f"{prefix}: Alt={alt} indica alteração de desenho, mas não há mudança de "
                f"'nivel_revisao' em dados_basicos — confira se o Alt declarado está correto",
            ))

        # Nota 2: alteração de desenho exige desenho já aprovado.
        if alt.startswith("D") and not material.get("desenho_aprovado"):
            errors.append(make_error(
                f"{material_field}.desenho_aprovado", "desenho_aprovado_required",
                f"{prefix}: alteração de desenho (Alt={alt}) requer 'desenho_aprovado=true' (POP Nota 2)",
            ))

        # Nota 17: alteração de NCM exige aprovação fiscal prévia.
        ncm_entry = dados_basicos.get("ncm")
        if ncm_entry and ncm_entry.get("para") and not material.get("ncm_aprovado_fiscal"):
            errors.append(make_error(
                f"{material_field}.ncm_aprovado_fiscal", "ncm_aprovado_fiscal_required",
                f"{prefix}: alteração de NCM requer 'ncm_aprovado_fiscal=true' (POP Nota 17)",
            ))

        # Nota 8: sucatear estoque exige centro de custo e conta razão.
        if impactos.get("est") == "S":
            if not impactos.get("centro_custo") or not impactos.get("conta_razao"):
                errors.append(make_error(
                    f"{material_field}.alteracoes.impactos_operacionais.centro_custo",
                    "sucateamento_centro_custo_required",
                    f"{prefix}: sucateamento de estoque (Est=S) requer 'centro_custo' e "
                    f"'conta_razao' em impactos_operacionais (POP Nota 8)",
                ))

        # Nota 10: afeta ordem de cliente exige entrada correspondente em ordem_cliente[].
        if impactos.get("oc") == "X" and codigo not in ordem_cliente_codigos:
            errors.append(make_error(
                "ordem_cliente", "ordem_cliente_required",
                f"{prefix}: Afeta Ordem de Cliente (OC=X) requer entrada correspondente em "
                f"'ordem_cliente[]' com codigo={codigo!r} (POP Nota 10)",
            ))

    return errors
