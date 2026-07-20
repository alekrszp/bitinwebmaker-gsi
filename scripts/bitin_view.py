#!/usr/bin/env python3
"""Modelo de visualização do BITin: um resumo estruturado (dict), não HTML/markdown --
a formatação visual fica a cargo do frontend. Serve tanto de prévia durante o rascunho
quanto de tela final depois de enviado. Ver docs/BITIN_MODEL.md, seção "Ciclo de vida".
"""

from typing import Any

import bitin_document
from bitin_lifecycle import STATUS_RASCUNHO


def render_material_summary(
    material: dict[str, Any], vba_mapping_config: dict[str, Any], document_config: dict[str, Any],
) -> dict[str, Any]:
    impactos = bitin_document.read_impactos_operacionais(material)
    return {
        "codigo_material": material.get("codigo_material", ""),
        "descricao_material": material.get("descricao_material", ""),
        "centro": material.get("centro", ""),
        "tipo_material": material.get("tipo_material", ""),
        "impactos_operacionais": impactos,
        "dados_basicos_alterados": bitin_document.build_campo_alterado_diffs(material, vba_mapping_config),
        "lista_tecnica": material.get("alteracoes", {}).get("lista_tecnica", []),
        # Sugestão automática (2026-07-17, ver bitin_document.suggest_impactos) -- ponto de
        # partida a partir do código de Grupo de Mercadorias, NUNCA autoritativo. O frontend
        # decide se/quando aplicar (só em campo ainda em branco); o backend só calcula.
        "sugestoes": bitin_document.suggest_impactos(material, document_config),
        # Lembrete "REVISAR ROTEIRO" (Módulo4.bas, ver bitin_document.revisar_roteiro) -- não é
        # sugestão de campo, é um aviso fixo baseado no Alt já declarado pelo engenheiro.
        "revisar_roteiro": bitin_document.revisar_roteiro(material),
    }


def render_bitin_summary(
    bitin: dict[str, Any],
    vba_mapping_config: dict[str, Any],
    document_config: dict[str, Any],
) -> dict[str, Any]:
    materiais = bitin.get("materiais", [])
    checklist = bitin_document.build_checklist(bitin, materiais, document_config)

    return {
        "bitin": bitin.get("bitin", ""),
        "status": bitin.get("status", STATUS_RASCUNHO),
        "data_envio": bitin.get("data_envio"),
        # Fila do setor Cadastro (2026-07-17) -- ver bitin_lifecycle.encaminhar_para_roteiro.
        "encaminhado_roteiro": bitin.get("encaminhado_roteiro", False),
        "data_encaminhado_roteiro": bitin.get("data_encaminhado_roteiro"),
        # Setor Processos (2026-07-17) -- ver bitin_lifecycle.concluir_processamento.
        "processos_concluido": bitin.get("processos_concluido", False),
        "data_processos_concluido": bitin.get("data_processos_concluido"),
        "setor": bitin.get("setor", ""),
        "produto": bitin.get("produto", ""),
        "motivo": bitin.get("motivo", ""),
        "solicitante": bitin.get("solicitante", ""),
        "data_solicitacao": bitin.get("data_solicitacao", ""),
        "materiais": [render_material_summary(m, vba_mapping_config, document_config) for m in materiais],
        "checklist": checklist,
        "checklist_pendencias": [item["etapa"] for item in checklist if item["afeta"]],
        "setores_afetados": bitin_document.build_setores_afetados(checklist, document_config),
        # Passthrough -- já validado estruturalmente em bitin_model.validate_ordem_cliente
        # (codigo obrigatório, itens de acrescentar/retira com codigo_material+quantidade), sem
        # transformação adicional necessária pra exibição. Ver docs/BITIN_MODEL.md.
        "ordem_cliente": bitin.get("ordem_cliente", []),
    }
