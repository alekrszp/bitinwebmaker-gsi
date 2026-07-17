"""Exportação de um BITin em PDF (relatório interno, sem estilização elaborada) -- usado
por GET /bitins/{mongo_id}/pdf (ver backend/api/bitins.py). Reaproveita
bitin_view.render_bitin_summary (mesma função usada por GET /bitins/{mongo_id}/resumo) em
vez de reimplementar a leitura de materiais/checklist a partir do content bruto.

Usa reportlab.platypus (SimpleDocTemplate + Table/Paragraph) -- flowables de alto nível que
cuidam de quebra de página automaticamente, em vez de desenhar em canvas cru posição por
posição."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

import bitin_document
import bitin_model
import bitin_view
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

# Caminhos calculados relativos a este arquivo (scripts/ não depende de backend/ -- é o
# contrário: backend/api/bitins.py importa bitin_pdf, não o inverso. backend/scripts_path.py
# só cuida de colocar scripts/ no sys.path e é irrelevante aqui, já que este módulo já está
# dentro de scripts/).
_ROOT = Path(__file__).resolve().parents[1]
_VBA_MAPPING_CONFIG_PATH = _ROOT / "config" / "vba_mapping.json"
_DOCUMENT_CONFIG_PATH = _ROOT / "config" / "bitin_document_mapping.json"
_VBA_MAPPING_CONFIG = bitin_model.load_config(_VBA_MAPPING_CONFIG_PATH)
_DOCUMENT_CONFIG = bitin_document.load_config(_DOCUMENT_CONFIG_PATH)

_STYLES = getSampleStyleSheet()
_TITLE = ParagraphStyle("BitinTitle", parent=_STYLES["Title"], fontSize=16, spaceAfter=4)
_H2 = ParagraphStyle("BitinH2", parent=_STYLES["Heading2"], fontSize=12, spaceBefore=10, spaceAfter=4)
_NORMAL = _STYLES["Normal"]
_CELL = ParagraphStyle("BitinCell", parent=_STYLES["Normal"], fontSize=8, leading=10)

_TABLE_GRID = TableStyle([
    ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
    ("FONTSIZE", (0, 0), (-1, -1), 8),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
])


def _p(value: Any, style: ParagraphStyle = _CELL) -> Paragraph:
    """Envolve um valor em Paragraph pra permitir quebra de linha dentro de célula de
    tabela (uma string crua numa Table não quebra linha e pode estourar a página)."""
    text = "" if value is None else str(value)
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return Paragraph(text or "-", style)


def _header_block(summary: dict[str, Any]) -> list:
    codigo = summary.get("bitin") or ""
    titulo = f"BITin {codigo}" if codigo else "BITin (RASCUNHO -- sem código ainda)"
    rows = [
        ["Código", codigo or "RASCUNHO"],
        ["Produto", summary.get("produto", "")],
        ["Motivo", summary.get("motivo", "")],
        ["Solicitante", summary.get("solicitante", "")],
        ["Setor", summary.get("setor", "")],
        ["Data de solicitação", summary.get("data_solicitacao", "")],
        ["Data de envio", summary.get("data_envio") or "-"],
    ]
    table = Table([[_p(k, _NORMAL), _p(v, _NORMAL)] for k, v in rows], colWidths=[4 * cm, 12 * cm])
    table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return [Paragraph(titulo, _TITLE), Spacer(1, 6), table]


def _material_flowables(material: dict[str, Any], indice: int) -> list:
    flowables: list = [Paragraph(
        f"Material {indice}: {material.get('codigo_material', '')} "
        f"- {material.get('descricao_material', '') or '(sem descrição)'}",
        _H2,
    )]

    info_rows = [
        ["Centro", material.get("centro", "")],
        ["Tipo de material", material.get("tipo_material", "")],
    ]
    info_table = Table(
        [[_p(k, _NORMAL), _p(v, _NORMAL)] for k, v in info_rows], colWidths=[4 * cm, 12 * cm],
    )
    info_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
    ]))
    flowables.append(info_table)

    diffs = material.get("dados_basicos_alterados") or []
    if diffs:
        flowables.append(Spacer(1, 4))
        header = [_p("Campo", _NORMAL), _p("De", _NORMAL), _p("Para", _NORMAL)]
        body = [
            [_p(d.get("campo", "")), _p(d.get("de", "")), _p(d.get("para", ""))]
            for d in diffs
        ]
        diffs_table = Table([header] + body, colWidths=[6 * cm, 5 * cm, 5 * cm], repeatRows=1)
        diffs_table.setStyle(_TABLE_GRID)
        flowables.append(diffs_table)

    lista_tecnica = material.get("lista_tecnica") or []
    if lista_tecnica:
        flowables.append(Spacer(1, 4))
        flowables.append(Paragraph("Lista técnica", _NORMAL))
        header = [_p("Componente", _NORMAL), _p("Descrição", _NORMAL), _p("Quantidade", _NORMAL)]
        body = [
            [
                _p(item.get("codigo_material", "")),
                _p(item.get("descricao_material", "")),
                _p(item.get("quantidade", "")),
            ]
            for item in lista_tecnica
        ]
        lt_table = Table([header] + body, colWidths=[4 * cm, 8 * cm, 4 * cm], repeatRows=1)
        lt_table.setStyle(_TABLE_GRID)
        flowables.append(lt_table)

    return flowables


def _checklist_flowables(checklist: list[dict[str, Any]]) -> list:
    flowables: list = [Paragraph("Checklist", _H2)]
    header = [_p("", _NORMAL), _p("Etapa", _NORMAL), _p("Observação", _NORMAL)]
    body = []
    for item in checklist:
        marca = "[x]" if item.get("afeta") else "[ ]"
        body.append([_p(marca), _p(item.get("etapa", "")), _p(item.get("descricao", ""))])
    table = Table([header] + body, colWidths=[1.5 * cm, 8.5 * cm, 6 * cm], repeatRows=1)
    table.setStyle(_TABLE_GRID)
    flowables.append(table)
    return flowables


def build_bitin_pdf(bitin: dict[str, Any]) -> bytes:
    """Gera o PDF de um BITin a partir do `content` bruto salvo no Mongo (mesmo shape que
    `bitin_view.render_bitin_summary` espera). Funciona tanto pra um BITin enviado (com
    código) quanto pra um rascunho (sem código ainda) -- nunca levanta exceção por causa
    disso, só omite/anota o que não existe ainda."""
    summary = bitin_view.render_bitin_summary(bitin, _VBA_MAPPING_CONFIG, _DOCUMENT_CONFIG)

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        title=f"BITin {summary.get('bitin') or 'rascunho'}",
    )

    story: list = []
    story.extend(_header_block(summary))

    materiais = summary.get("materiais") or []
    if materiais:
        story.append(Spacer(1, 8))
        story.append(Paragraph("Materiais", _H2))
        for idx, material in enumerate(materiais, start=1):
            story.extend(_material_flowables(material, idx))
            story.append(Spacer(1, 6))

    checklist = summary.get("checklist") or []
    if checklist:
        story.extend(_checklist_flowables(checklist))

    doc.build(story)
    return buffer.getvalue()
