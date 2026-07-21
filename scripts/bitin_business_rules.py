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

Split entre regras bloqueantes e regras "de confiança" (decisão do usuário, 2026-07-15):
regras inferíveis só a partir de dados que já estão no sistema (ex.: alt_desenho_sem_revisao,
que compara Alt declarado com nivel_revisao realmente mudado em dados_basicos) continuam
bloqueando o envio aqui. Regras que dependem de uma confirmação externa que o sistema não
tem como saber (POP Nota 2: desenho já aprovado; POP Nota 17: NCM já aprovado pelo fiscal)
NÃO são mais aplicadas aqui -- não existe controle na UI pra marcar esses campos como
verdadeiros, então bloquear o envio nessas condições tornaria o envio permanentemente
impossível sempre que a condição de gatilho ocorresse. Ficam só como lembrete no popover de
ajuda ("?") da tela do BITin -- responsabilidade do engenheiro confirmar antes de enviar.
"""

import re
from typing import Any

import bitin_document
from bitin_errors import BitinError, make_error

# Domínio de valores válidos por campo de dados_basicos (2026-07-21, pedido explícito: "pega
# as informações de campo que tu já tem, e aplica essa validação em cima dos campos") -- só
# roda no envio, igual ao resto deste módulo (nunca bloqueia a edição). Campo vazio nunca é
# erro (ainda não foi preenchido). Espelha frontend/src/lib/dadosBasicosValidacao.ts -- QUALQUER
# mudança de domínio precisa ser replicada nos dois lados.
_NIVEL_REVISAO_RE = re.compile(r"^[A-Z]$")
_CAMPOS_BOOLEAN_X_TRACO = {"producao_interna", "marcacao_eliminar_nivel_mandante", "marcacao_eliminar_nivel_centro"}


def _validar_dominio_dados_basicos(dados_basicos: dict[str, Any], material_field: str, prefix: str) -> list[BitinError]:
    errors: list[BitinError] = []
    for campo, entry in dados_basicos.items():
        for lado in ("de", "para"):
            valor = entry.get(lado, "")
            if valor == "":
                continue
            campo_field = f"{material_field}.alteracoes.dados_basicos.{campo}.{lado}"
            if campo == "nivel_revisao" and not _NIVEL_REVISAO_RE.match(valor):
                errors.append(make_error(
                    campo_field, "invalid_nivel_revisao_value",
                    f"{prefix}: nivel_revisao ({lado})={valor!r} inválido — precisa ser 1 letra maiúscula (A-Z)",
                ))
            elif campo in _CAMPOS_BOOLEAN_X_TRACO and valor not in ("X", "-"):
                errors.append(make_error(
                    campo_field, f"invalid_{campo}_value",
                    f"{prefix}: {campo} ({lado})={valor!r} inválido — valores aceitos: X, -",
                ))
    return errors


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
    # Nenhuma alteração de verdade em nenhum material (2026-07-21, pedido explícito: "o
    # sistema deixa enviar bitin sem nenhuma alteração") -- `validate_bitin` (bitin_model.py)
    # já garante que existe PELO MENOS 1 material com os campos de identificação obrigatórios
    # (codigo_material/centro/tipo_material), mas isso sozinho não significa que algo foi
    # realmente alterado -- um material "vazio" (Alt/Esp/etc todos no valor padrão "-", sem
    # dados_basicos, sem lista_tecnica) passava por essa checagem e virava um BITin enviado
    # sem propósito nenhum. Aqui embaixo cada material contribui pra esse flag junto com o
    # resto das regras (não duplica leitura de `impactos`/`mudancas_reais`/`dados_basicos`).
    algum_material_alterado = False

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

        # Domínio: nivel_revisao (letra A-Z) e os 3 campos booleanos X/- de dados_basicos.
        errors.extend(_validar_dominio_dados_basicos(dados_basicos, material_field, prefix))

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

        # Alteração de verdade neste material: algum de/para efetivo em dados_basicos, algum
        # impacto operacional fora do padrão "-", "Atualizar DWG/SAT" marcado, ou componente
        # em lista_tecnica -- qualquer um já basta pra este material "contar".
        if (
            mudancas_reais
            or any(impactos.get(campo, "-") != "-" for campo in ("alt", "est", "esp", "lp", "pre", "oc", "of"))
            or impactos.get("atualizar_dwg_sat")
            or alteracoes.get("lista_tecnica")
        ):
            algum_material_alterado = True

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

        # Nota 2 (desenho já aprovado) e Nota 17 (NCM aprovado pelo fiscal) não são validadas
        # aqui -- exigem confirmação externa que o sistema não tem como conferir e não há
        # controle na UI pra marcá-las (ver docstring do módulo). Ficam só como lembrete no
        # popover de ajuda da tela do BITin.

        # Nota 10: afeta ordem de cliente exige entrada correspondente em ordem_cliente[].
        if impactos.get("oc") == "X" and codigo not in ordem_cliente_codigos:
            errors.append(make_error(
                "ordem_cliente", "ordem_cliente_required",
                f"{prefix}: Afeta Ordem de Cliente (OC=X) requer entrada correspondente em "
                f"'ordem_cliente[]' com codigo={codigo!r} (POP Nota 10)",
            ))

    # Nenhum material teve alteração de verdade (ver flag acima) -- BITin sem propósito.
    if bitin.get("materiais") and not algum_material_alterado:
        errors.append(make_error(
            "materiais", "nenhuma_alteracao_real",
            "Nenhum material tem alteração de verdade (Alt/Est/Esp/LP/Pré/OC/OF, dados básicos "
            "ou lista técnica) -- preencha ao menos uma antes de enviar",
        ))

    # Nota 8: sucatear estoque exige registrar centro de custo e conta razão -- não é mais um
    # campo por material, é a descrição do item 22 da checklist ("Centro de custo (se tem
    # sucata)"), que fica "afeta" automaticamente quando algum material declara Est=S (ou por
    # override manual, ver bitin_document.build_checklist). Decisão do usuário, 2026-07-15.
    checklist = bitin_document.build_checklist(bitin, bitin.get("materiais", []), document_config)
    item_centro_custo = next((item for item in checklist if item["id"] == "22"), None)
    if item_centro_custo and item_centro_custo["afeta"] and not item_centro_custo.get("descricao", "").strip():
        errors.append(make_error(
            "checklist_descricoes.22", "sucateamento_centro_custo_required",
            "Sucateamento de estoque ('Centro de custo (se tem sucata)' na checklist) requer uma "
            "descrição com o centro de custo e a conta razão (POP Nota 8)",
        ))

    return errors
