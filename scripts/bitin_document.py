#!/usr/bin/env python3
"""Documento do BITin (Alt/Esp/DWG-SAT/checklist), portado de Módulo4+Módulo10+Módulo13.

Diferente do Módulo1/Módulo2 (posições de coluna que o SAP/Winshuttle realmente lê, onde
qualquer divergência tem risco real de quebrar um upload), o checklist aqui é uma estrutura
de dados nova (não escreve em células de planilha legada) — por isso, quando os dados reais
de exemplo (bitin teste 2.xlsm) divergiram das linhas hardcoded no Módulo4.bas extraído, foi
usado o mapeamento semântico (por rótulo do item), que bateu com os dados reais, em vez da
posição de linha literal do .bas (ver docs/BITIN_MODEL.md, seção "Documento do BITin").
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


@lru_cache(maxsize=None)
def load_config(config_path: Path) -> dict[str, Any]:
    return json.loads(config_path.read_text(encoding="utf-8"))


def suggest_dwg_sat_action(plan2_row: dict[int, str], config: dict[str, Any]) -> str | None:
    """Sugestão opcional (não autoritativa) baseada em códigos SAP de Grupo Mercadorias.
    Frágil por natureza (catálogo de códigos é vasto e muda com o tempo) — não usar para
    validação; o campo autoritativo é materiais[].atualizar_dwg_sat, declarado pelo
    engenheiro. Ver docs/BITIN_MODEL.md, seção "Alt/Esp declarados pelo engenheiro"."""
    cols = config["plan2_columns"]
    dwg_sat_map = config["grupo_mercadorias_dwg_sat"]

    action = dwg_sat_map.get(plan2_row.get(cols["grupo_mercadorias_atual"], ""))
    novo = plan2_row.get(cols["grupo_mercadorias_novo"], "")
    if novo != "":
        action = dwg_sat_map.get(novo, action)
    return action


def suggest_alt(plan2_row: dict[int, str], config: dict[str, Any]) -> str:
    """Sugestão opcional (não autoritativa) — mesma ressalva de suggest_dwg_sat_action."""
    cols = config["plan2_columns"]
    fornecedor_code = config["grupo_mercadorias_fornecedor"]
    mp_prefix = config["mp_prefix"]

    atual = plan2_row.get(cols["grupo_mercadorias_atual"], "")
    novo = plan2_row.get(cols["grupo_mercadorias_novo"], "")
    tem_desenho = plan2_row.get(cols["desenho_atual"], "") == "SIM"
    revisao_mudou = plan2_row.get(cols["nivel_revisao_novo"], "") != ""

    def _por_grupo_mercadorias(alt_fornecedor: str, alt_default: str) -> str:
        if novo[:2] == mp_prefix or atual[:2] == mp_prefix:
            return alt_fornecedor
        if atual == fornecedor_code:
            return alt_fornecedor if novo == "" else alt_default
        # atual != fornecedor_code
        return alt_fornecedor if novo == fornecedor_code else alt_default

    if tem_desenho:
        if revisao_mudou:
            return _por_grupo_mercadorias("D/F", "D/P")
        return _por_grupo_mercadorias("-/F", "-")

    # Sem desenho: Módulo4 verifica "Texto Pedido Compras Novo" <> Empty, mas esse campo
    # é sempre pelo menos "N/A" (nunca Empty) — a checagem é sempre verdadeira na prática.
    # Replicado fielmente (ver docs/BITIN_MODEL.md).
    return _por_grupo_mercadorias("-/F", "-")


def suggest_esp(plan2_row: dict[int, str], config: dict[str, Any]) -> str:
    """Sugestão opcional (não autoritativa) — mesma ressalva de suggest_dwg_sat_action."""
    cols = config["plan2_columns"]
    fornecedor_code = config["grupo_mercadorias_fornecedor"]
    mp_prefix = config["mp_prefix"]

    texto_pedido = plan2_row.get(cols["texto_pedido_compras_novo"], "")
    if texto_pedido == "" or texto_pedido == "N/A":
        return "-"

    atual = plan2_row.get(cols["grupo_mercadorias_atual"], "")
    novo = plan2_row.get(cols["grupo_mercadorias_novo"], "")
    if atual[:2] == mp_prefix or novo[:2] == mp_prefix:
        return "X"
    if atual != fornecedor_code and novo == fornecedor_code:
        return "X"
    if atual == fornecedor_code:
        return "X"
    return "-"


def _plan2_row_from_material(material: dict[str, Any], document_config: dict[str, Any]) -> dict[int, str]:
    """Adapta `materiais[].alteracoes.dados_basicos` (nosso formato -- chaveado por nome de
    campo, ex. `dados_basicos["grupo_mercadorias"]["de"]`) pro formato `dict[coluna] -> valor`
    que `suggest_alt`/`suggest_esp`/`suggest_dwg_sat_action` esperam (o layout real da aba
    Plan2 que a macro original lia). NÃO é um adaptador genérico pra Plan2 inteira -- só os 4
    campos que essas 3 funções realmente usam (grupo_mercadorias, desenho, nivel_revisao,
    texto_pedidos_compras)."""
    dados_basicos = material.get("alteracoes", {}).get("dados_basicos", {})
    cols = document_config["plan2_columns"]

    def entry(campo: str) -> dict[str, str]:
        return dados_basicos.get(campo, {})

    grupo = entry("grupo_mercadorias")
    desenho = entry("desenho")
    nivel_revisao = entry("nivel_revisao")
    texto_pedido = entry("texto_pedidos_compras")

    return {
        cols["grupo_mercadorias_atual"]: grupo.get("de", ""),
        cols["grupo_mercadorias_novo"]: grupo.get("para", ""),
        cols["desenho_atual"]: desenho.get("de", ""),
        cols["nivel_revisao_novo"]: nivel_revisao.get("para", ""),
        cols["texto_pedido_compras_novo"]: texto_pedido.get("para", ""),
    }


def suggest_impactos(material: dict[str, Any], document_config: dict[str, Any]) -> dict[str, str | None]:
    """Sugestões automáticas de Alt/Esp/nota DWG-SAT a partir do código de Grupo de
    Mercadorias (2026-07-17, pedido explícito do usuário: "coloca os dois, códigos já
    existentes puxam mas o engenheiro pode mexer, mas tem que preencher automatico sozinho").

    Reabre PARCIALMENTE a decisão de 2026-07-10 (docs/BITIN_MODEL.md, "Alt/Esp declarados
    pelo engenheiro") -- aquela decisão vale ainda: o campo AUTORITATIVO continua sendo o que
    o engenheiro declarou em `impactos_operacionais` (nunca sobrescrito à força), e o risco
    documentado (catálogo de código SAP é vasto e muda) continua real. A diferença agora é só
    que a sugestão passou de "nunca usada" pra "usada como PONTO DE PARTIDA, só quando o campo
    ainda está em branco" (ver frontend/src/pages/BitinDetail.tsx, onde a sugestão só
    preenche `impactos_operacionais.alt`/`.esp` quando o valor ainda é "-", e só adiciona a
    nota DWG/SAT se ela ainda não existir) -- código SAP desconhecido/não mapeado não sugere
    nada (`suggest_dwg_sat_action` devolve `None`), o campo fica em branco esperando o
    engenheiro preencher, exatamente como já era antes; nunca quebra silenciosamente algo que
    o engenheiro já declarou."""
    row = _plan2_row_from_material(material, document_config)
    return {
        "alt": suggest_alt(row, document_config),
        "esp": suggest_esp(row, document_config),
        "dwg_sat_acao": suggest_dwg_sat_action(row, document_config),
    }


_ALTS_QUE_EXIGEM_REVISAR_ROTEIRO = {"D/P", "-/P"}


def revisar_roteiro(material: dict[str, Any]) -> bool:
    """Lembrete "REVISAR ROTEIRO" (Módulo4.bas linhas ~204-209): quando o Alt declarado é
    "D/P" ou "-/P" (revisão de desenho mudou sem troca de fornecedor), a macro original escrevia
    esse aviso fixo em Plan4. Não afeta checklist/setores -- é só um lembrete visual pro
    engenheiro revisar o roteiro de fabricação. Lê o Alt AUTORITATIVO (declarado pelo
    engenheiro em impactos_operacionais), não a sugestão -- mesmo raciocínio de
    read_impactos_operacionais: o campo que vale é sempre o que foi de fato preenchido."""
    return read_impactos_operacionais(material)["alt"] in _ALTS_QUE_EXIGEM_REVISAR_ROTEIRO


# Regra de negócio do setor Cadastro (2026-07-17, pedido explícito): decide se um BITin
# precisa passar pelo setor Roteiro/Processos antes de virar PDF final -- "quando não houver:
# D/P, D/- ou -/P... se tiver isso na alteração do código é roteiro, quando não tiver não é".
# Conjunto DIFERENTE de _ALTS_QUE_EXIGEM_REVISAR_ROTEIRO acima (inclui "D/-" também) --
# são duas regras distintas por natureza: aquela é um lembrete por material (herdado da macro
# VBA original), esta é a decisão de roteamento do BITin inteiro (nova, não existia na macro).
_ALTS_QUE_EXIGEM_ROTEIRO = {"D/P", "D/-", "-/P"}


def precisa_roteiro(bitin: dict[str, Any]) -> bool:
    """True se PELO MENOS UM material do BITin tem Alt em _ALTS_QUE_EXIGEM_ROTEIRO -- decide
    se o Cadastro precisa encaminhar pro setor Processos (roteiro) ou pode concluir direto
    (ver bitin_lifecycle.concluir_sem_roteiro / concluir_para_roteiro em
    backend/api/bitins.py)."""
    materiais = bitin.get("materiais", [])
    return any(
        read_impactos_operacionais(material)["alt"] in _ALTS_QUE_EXIGEM_ROTEIRO
        for material in materiais
    )


def read_impactos_operacionais(material: dict[str, Any]) -> dict[str, Any]:
    """Alt/Esp/Est/LP/Pre/OC/OF/atualizar_dwg_sat são declarados pelo engenheiro
    (impactos_operacionais), não derivados de código SAP — ver docs/BITIN_MODEL.md,
    seção "Alt/Esp declarados pelo engenheiro"."""
    impactos = material.get("alteracoes", {}).get("impactos_operacionais", {})
    return {
        "alt": impactos.get("alt", "-"),
        "esp": impactos.get("esp", "-"),
        "est": impactos.get("est", "-"),
        "lp": impactos.get("lp", "-"),
        "pre": impactos.get("pre", "-"),
        "oc": impactos.get("oc", "-"),
        "of": impactos.get("of", "-"),
        "atualizar_dwg_sat": bool(impactos.get("atualizar_dwg_sat", False)),
        "centro_custo": impactos.get("centro_custo", ""),
        "conta_razao": impactos.get("conta_razao", ""),
    }


def build_campo_alterado_diffs(material: dict[str, Any], vba_mapping_config: dict[str, Any]) -> list[dict[str, Any]]:
    """'Campo alterado / De: / Para:' por material, direto do JSON do BITin (não precisa
    reconsultar Plan2) — replica a tabela que Módulo4 monta em Plan4 por campo mudado.

    Campos livres (achado ao revisar um BITin real, A263326.xlsm): o engenheiro nem sempre
    preenche um campo SAP reconhecido — às vezes escreve uma nota solta ("Salvar DWG",
    "Alterado peso e IS") direto na coluna "Campo alterado". Se o texto não bate com nenhuma
    chave do crosswalk, mostra exatamente como foi escrito em vez de derrubar a requisição com
    KeyError — decisão registrada com o usuário: "tudo que for escrito deve ficar visível"."""
    crosswalk = vba_mapping_config["bitin_schema_crosswalk"]["dados_basicos"]
    headers = vba_mapping_config["plan2_column_headers"]
    dados_basicos = material.get("alteracoes", {}).get("dados_basicos", {})

    diffs: list[dict[str, Any]] = []
    for campo, entry in dados_basicos.items():
        de = entry.get("de", "")
        para = entry.get("para", "")
        plan2_col_novo = crosswalk.get(campo)
        livre = plan2_col_novo is None
        if not livre:
            # Campo SAP reconhecido: "para" vazio continua sem representar uma mudança real
            # (mesmo comportamento de sempre).
            if para == "":
                continue
            label = headers[plan2_col_novo - 2]  # coluna "atual" = Novo - 1; índice = col - 1
        else:
            # Campo livre (não está no crosswalk): a própria chave já é a informação escrita
            # pelo engenheiro -- nunca pula, mesmo sem de/para ("Salvar DWG" real,
            # A263326.xlsm, é só uma nota solta, sem par de/para). "livre" marca isso pro
            # frontend destacar visualmente (decisão do usuário, 2026-07-14).
            label = campo  # mostra exatamente como foi escrito
        diffs.append({"campo": label, "de": de, "para": para, "livre": livre})
    return diffs


def build_checklist_schema(config: dict[str, Any]) -> list[dict[str, str]]:
    """Os 22 itens fixos do checklist (Quadro 01 do POP), só id+etapa -- fonte única de
    verdade pro frontend montar a tabela de checklist editável na tela de cadastro (ver
    docs/BACKEND.md). Mesma lista usada por build_checklist, sem o cálculo de 'afeta'."""
    return [{"id": item["id"], "etapa": item["etapa"]} for item in config["checklist_items"]]


_DWG_SAT_NOTAS = {"SALVAR DWG", "SALVAR SAT"}


def _checklist_ids_auto_sugeridos(materiais: list[dict[str, Any]], config: dict[str, Any]) -> set[str]:
    """Regras de automação REAIS do checklist, confirmadas em auditoria da macro VBA original
    (2026-07-16): `Módulo4.bas`, `Sub Preencher_Bitin`, é o ÚNICO lugar em todos os 20 módulos
    que escreve "SIM" na coluna de checklist de `Plan4` -- grep exaustivo por `, 3) = "SIM"`
    em `artifacts/vba/*.bas` não achou mais nenhuma origem. Isso corrige uma decisão anterior
    (2026-07-15, "tirar esse autocomplete") que tinha removido a automação inteira por não ter
    sido verificada contra a macro real; o usuário then achou, na prática, que "quando colocado
    no campo nota salvar dwg ele marca sozinho a checklist" -- o que levou a essa reauditoria.

    As 8 regras herdadas da macro (linhas 144-202 de Módulo4.bas):
    1-5. Alt declarado -> id via `config['alt_to_checklist_id']` (D/- =1, D/P=2, D/F=3, -/P=4,
         -/F=5).
    6. Nota livre em dados_basicos igual (exato, case-sensitive, como a comparação VBA
       `= "SALVAR DWG"`) a "SALVAR DWG" ou "SALVAR SAT" -> id 18 ("Atualizar DWG / SAT"). Não é
       mais um checkbox (`impactos_operacionais.atualizar_dwg_sat` foi removido do frontend) --
       o único jeito de acionar isso é a nota de texto livre batendo exatamente com uma dessas
       duas strings.
    7. Est fora de {"", "-"} -> id 8 ("Retrabalhar ou descartar estoque").
    8. Est == "S" -> id 22 ("Centro de custo (se tem sucata)"), sucateamento (POP Nota 8).
    9. LP fora de {"", "-"} -> id 19 ("Lista de preço").
    10. PRE fora de {"", "-"} -> id 20 ("Precificação").
    11. OC fora de {"", "-"} -> id 10 ("Ordem de cliente").
    12. OF fora de {"", "-"} -> id 17 ("Atualizar ordem de fabricação").

    +2 regras NOVAS (2026-07-20, pedido explícito do usuário: "pegue a regra de negócio, e
    você mesmo coloque automático oq puder por com oq vc tem" -- iam além do que a macro
    original fazia, mas usam campo que já existe no schema, sem inventar heurística nova):
    13. Esp == "X" -> id 6 ("Especificações técnicas"). `impactos_operacionais.esp` já existe
        (ANEXO A do POP, valores {"X","-"}) e nunca tinha sido usado pra acionar checklist.
    14. `material.alteracoes.lista_tecnica` não vazia -> id 7 ("Alteração lista técnica"): a
        própria existência de itens na lista técnica do material já É o sinal de que ela foi
        alterada, não precisa de campo extra.

    As outras 8 etapas manuais (9, 11-16, 21) continuam SEM automação -- não existe nenhum
    campo no schema do BITin que sinalize DPO-PAN/BITex/manual/instrução de montagem/
    Elétrica/Estamparia/Madeira-Plástico/Atualizar custos; inventar uma regra sem lastro em
    dado real violaria o princípio já registrado no projeto (preferir regra robusta a
    heurística acoplada a algo instável, ver requirements.md)."""
    alt_to_id = config.get("alt_to_checklist_id", {})
    auto: set[str] = set()
    for material in materiais:
        impactos = read_impactos_operacionais(material)

        alt_id = alt_to_id.get(impactos["alt"])
        if alt_id:
            auto.add(alt_id)

        dados_basicos = material.get("alteracoes", {}).get("dados_basicos", {})
        if any(nota in _DWG_SAT_NOTAS for nota in dados_basicos.keys()):
            auto.add("18")

        if impactos["est"] not in ("", "-"):
            auto.add("8")
        if impactos["est"] == "S":
            auto.add("22")
        if impactos["lp"] not in ("", "-"):
            auto.add("19")
        if impactos["pre"] not in ("", "-"):
            auto.add("20")
        if impactos["oc"] not in ("", "-"):
            auto.add("10")
        if impactos["of"] not in ("", "-"):
            auto.add("17")
        if impactos["esp"] == "X":
            auto.add("6")
        if material.get("alteracoes", {}).get("lista_tecnica"):
            auto.add("7")
    return auto


def build_checklist(bitin: dict[str, Any], materiais: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    """'afeta' = sugestão automática (`_checklist_ids_auto_sugeridos`, regras 1-8 verificadas
    contra `Módulo4.bas`) a não ser que o engenheiro tenha clicado no item explicitamente
    (`bitin['checklist_overrides']`, dict id -> bool) -- o override sempre vence a sugestão,
    nos dois sentidos (liga um item que a sugestão não teria ligado, ou desliga um item que a
    sugestão ligaria). Restaurado em 2026-07-16: a versão 100% manual de 2026-07-15 tinha
    removido a automação inteira por desconfiar das regras antigas (não verificadas); a
    reauditoria da macro real (`Módulo4.bas`) confirmou que a automação existe e é bem mais
    restrita do que a versão antiga -- ver `_checklist_ids_auto_sugeridos` para a lista
    completa e a fonte de cada regra. Setores acionados (build_setores_afetados) sempre leem o
    resultado final daqui, então tanto a sugestão automática quanto um clique manual acionam
    os setores do mesmo jeito."""
    overrides = bitin.get("checklist_overrides", {})
    auto_sugeridos = _checklist_ids_auto_sugeridos(materiais, config)
    # Anotação livre por item (2026-07-15) -- ex.: "Centro de custo (se tem sucata)" (id 22)
    # usa isso pra registrar o centro de custo/conta razão do sucateamento (POP Nota 8), no
    # lugar de um campo estruturado por material (decisão do usuário: "isso é colocado no
    # campo de descrição lá em cima na checklist ao lado do campo da checklist referente").
    descricoes = bitin.get("checklist_descricoes", {})
    return [
        {
            **item,
            "afeta": overrides.get(item["id"], item["id"] in auto_sugeridos),
            "manual": item["id"] in overrides,
            "descricao": descricoes.get(item["id"], ""),
        }
        for item in config["checklist_items"]
    ]


def build_setores_afetados(checklist: list[dict[str, Any]], config: dict[str, Any]) -> list[str]:
    """Departamentos acionados pelas etapas marcadas 'afeta' -- crosswalk fixo
    (config['checklist_setores'], extraído de um BITin real, aba 'SETORES CHECKLIST' de
    A263326.xlsm). Uma etapa pode acionar mais de um setor; devolve a união, sem repetir,
    em ordem alfabética (não importa qual etapa acionou qual -- só quem precisa agir)."""
    setores_config = config.get("checklist_setores", {})
    setores: set[str] = set()
    for item in checklist:
        if item["afeta"]:
            setores.update(setores_config.get(item["id"], []))
    return sorted(setores)
