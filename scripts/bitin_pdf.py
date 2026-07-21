"""Exportação de um BITin em PDF -- usado por GET /bitins/{mongo_id}/pdf (ver
backend/api/bitins.py). Reaproveita bitin_view.render_bitin_summary (mesma função usada por
GET /bitins/{mongo_id}/resumo) em vez de reimplementar a leitura de materiais/checklist a
partir do content bruto.

Usa reportlab.platypus (SimpleDocTemplate + Table/Paragraph) -- flowables de alto nível que
cuidam de quebra de página automaticamente, em vez de desenhar em canvas cru posição por
posição.

Layout (2026-07-21, restilizado -- pedido explícito: "colocar a logo seguir as cores da
marca... layout seguir o mesmo do bitin -> cabeçalho setores checklist e dai sim os códigos
com as alterações") segue a MESMA ordem da tela de edição (BitinDetail.tsx): cabeçalho
(DadosGeraisCard) -> setores acionados (SetoresBanner) -> checklist (ChecklistTable) -> só
depois os materiais com as alterações de código -- antes a ordem era cabeçalho -> materiais ->
checklist, sem seção de setores nenhuma."""

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
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

# Caminhos calculados relativos a este arquivo (scripts/ não depende de backend/ -- é o
# contrário: backend/api/bitins.py importa bitin_pdf, não o inverso. backend/scripts_path.py
# só cuida de colocar scripts/ no sys.path e é irrelevante aqui, já que este módulo já está
# dentro de scripts/).
_ROOT = Path(__file__).resolve().parents[1]
_VBA_MAPPING_CONFIG_PATH = _ROOT / "config" / "vba_mapping.json"
_DOCUMENT_CONFIG_PATH = _ROOT / "config" / "bitin_document_mapping.json"
_VBA_MAPPING_CONFIG = bitin_model.load_config(_VBA_MAPPING_CONFIG_PATH)
_DOCUMENT_CONFIG = bitin_document.load_config(_DOCUMENT_CONFIG_PATH)

# Mesmo arquivo usado pela topbar do frontend (Topbar.tsx) -- versão colorida (fundo claro do
# cabeçalho do PDF), não a mono-navy/mono-white (essas são pra fundo escuro/navy sólido, que o
# cabeçalho do PDF não usa). Se o arquivo não existir (ambiente sem o checkout completo do
# frontend), o PDF continua sendo gerado sem logo -- nunca falha por causa disso.
_LOGO_PATH = _ROOT / "frontend" / "public" / "brand" / "gpt-color.png"
_LOGO_ASPECT = 1549 / 4072  # altura/largura reais do PNG -- mantém proporção ao redimensionar.

# Paleta = EXATAMENTE os tokens de marca do frontend (frontend/src/index.css, tema claro) --
# antes eram cores calculadas à mão (#1c3a5e etc.) que não batiam com nenhuma cor real da marca
# nem do resto do sistema. Verde continua reservado pro semáforo do checklist (afeta=True),
# não é uma cor de marca aqui -- é o mesmo verde de brand-green, que também é dourado, laranja
# usados pela logo, então o significado semántico não colide com a paleta.
_NAVY = colors.HexColor("#32464d")
_NAVY_DARK = colors.HexColor("#243237")
_NAVY_LIGHT = colors.HexColor("#6c8899")
_GOLD = colors.HexColor("#f3d148")
_GREEN = colors.HexColor("#79aa00")
_LINE = colors.HexColor("#dfe3e8")
_SURFACE_ALT = colors.HexColor("#f5f6f8")
_INK = colors.HexColor("#16212a")
_INK_MUTED = colors.HexColor("#5b6b74")
_GREEN_BG = colors.HexColor("#eef4e0")  # brand-green a ~12% sobre branco, pro fundo de linha.

_STYLES = getSampleStyleSheet()
_TITLE = ParagraphStyle(
    "BitinTitle", parent=_STYLES["Title"], fontSize=20, leading=23, textColor=_NAVY_DARK, spaceAfter=2,
)
_SUBTITLE = ParagraphStyle(
    "BitinSubtitle", parent=_STYLES["Normal"], fontSize=10, textColor=_INK_MUTED, spaceAfter=0,
)
_H2 = ParagraphStyle(
    "BitinH2", parent=_STYLES["Heading2"], fontSize=12, textColor=_NAVY_DARK, spaceBefore=12, spaceAfter=5,
)
_NORMAL = _STYLES["Normal"]
_CELL = ParagraphStyle("BitinCell", parent=_STYLES["Normal"], fontSize=8, leading=10, textColor=_INK)
_CELL_MUTED = ParagraphStyle("BitinCellMuted", parent=_CELL, textColor=_INK_MUTED)
_CELL_GREEN = ParagraphStyle("BitinCellGreen", parent=_CELL, textColor=_GREEN, fontName="Helvetica-Bold")

_TABLE_GRID = TableStyle([
    ("GRID", (0, 0), (-1, -1), 0.5, _LINE),
    ("BACKGROUND", (0, 0), (-1, 0), _NAVY),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 8),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("TOPPADDING", (0, 0), (-1, -1), 4),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
])


def _com_zebra(style: TableStyle, linhas: int) -> TableStyle:
    """Linhas alternadas (a partir da 1, já que a 0 é o cabeçalho) -- só cosmético, ajuda a
    acompanhar uma linha em tabelas largas com muitos campos alterados."""
    comandos = list(style.getCommands())
    for i in range(1, linhas):
        if i % 2 == 0:
            comandos.append(("BACKGROUND", (0, i), (-1, i), _SURFACE_ALT))
    return TableStyle(comandos)


def _p(value: Any, style: ParagraphStyle = _CELL) -> Paragraph:
    """Envolve um valor em Paragraph pra permitir quebra de linha dentro de célula de
    tabela (uma string crua numa Table não quebra linha e pode estourar a página)."""
    text = "" if value is None else str(value)
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return Paragraph(text or "-", style)


def _logo_flowable(largura: float = 4.5 * cm) -> Any | None:
    """None se o PNG não existir (ex.: checkout parcial) -- o PDF continua sendo gerado, só
    sem logo, nunca falha por causa disso."""
    if not _LOGO_PATH.exists():
        return None
    return Image(str(_LOGO_PATH), width=largura, height=largura * _LOGO_ASPECT)


def _header_block(summary: dict[str, Any]) -> list:
    """Logo + código do BITin lado a lado (linha de topo), status logo abaixo como subtítulo,
    e o resto dos campos num grid 2x3 dentro de uma faixa com fundo leve -- mais fácil de
    escanear de relance do que uma lista vertical crua."""
    codigo = summary.get("bitin") or ""
    titulo = codigo or "RASCUNHO (sem código ainda)"
    status_label = {"enviado": "Enviado", "rascunho": "Rascunho"}.get(summary.get("status", ""), "")
    if summary.get("bitin_cadastrado"):
        status_label += " — Cadastrado"
    elif summary.get("processos_concluido"):
        status_label += " — Aguardando cadastro"

    titulo_bloco = [Paragraph(titulo, _TITLE), Paragraph(status_label, _SUBTITLE)]
    logo = _logo_flowable()
    if logo is not None:
        topo = Table([[logo, titulo_bloco]], colWidths=[4.5 * cm, 13.5 * cm])
        topo.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (0, 0), "LEFT"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))
        blocos: list = [topo, Spacer(1, 8)]
    else:
        blocos = titulo_bloco + [Spacer(1, 4)]

    grid = [
        ["Produto", summary.get("produto", ""), "Solicitante", summary.get("solicitante", "")],
        ["Motivo", summary.get("motivo", ""), "Setor", summary.get("setor", "")],
        [
            "Data de solicitação", summary.get("data_solicitacao", ""),
            "Data de envio", summary.get("data_envio") or "-",
        ],
    ]
    label_style = ParagraphStyle("BitinHeaderLabel", parent=_NORMAL, fontSize=8, textColor=_INK_MUTED)
    value_style = ParagraphStyle(
        "BitinHeaderValue", parent=_NORMAL, fontSize=10, fontName="Helvetica-Bold", textColor=_INK,
    )
    body = [
        [_p(l1, label_style), _p(v1, value_style), _p(l2, label_style), _p(v2, value_style)]
        for l1, v1, l2, v2 in grid
    ]
    table = Table(body, colWidths=[3 * cm, 5 * cm, 3 * cm, 5 * cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), _SURFACE_ALT),
        ("LINEABOVE", (0, 0), (-1, 0), 2, _GOLD),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    blocos.append(table)
    return blocos


def _setores_flowables(setores: list[str]) -> list:
    """Espelha SetoresBanner.tsx -- setores acionados conectados por "↔", numa faixa com fundo
    leve. Sem essa seção antes, o PDF pulava direto de cabeçalho pra materiais, sem mostrar
    quem é impactado pelo BITin."""
    flowables: list = [Paragraph("Setores acionados", _H2)]
    texto = " ↔ ".join(setores) if setores else "Nenhum setor acionado."
    estilo = ParagraphStyle(
        "BitinSetores", parent=_NORMAL, fontSize=9,
        fontName="Helvetica-Bold" if setores else "Helvetica",
        textColor=_INK if setores else _INK_MUTED,
    )
    faixa = Table([[Paragraph(texto, estilo)]], colWidths=[18 * cm])
    faixa.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), _SURFACE_ALT),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ]))
    flowables.append(faixa)
    return flowables


def _checklist_flowables(checklist: list[dict[str, Any]]) -> list:
    """Indicador visual por linha -- item que afeta vira ✓ verde (brand-green) com fundo
    levemente verde e etapa em negrito; item que não afeta fica cinza apagado, pra quem folheia
    rápido enxergar de cara só o que precisa de ação, sem ler linha por linha."""
    flowables: list = [Paragraph("Checklist", _H2)]
    # " " em vez de "" -- _p() troca string vazia por "-" (bom pra célula de dado vazia, ruim
    # num cabeçalho de coluna sem título).
    header = [_p(" ", _NORMAL), _p("Etapa", _NORMAL), _p("Observação", _NORMAL)]
    body = []
    extra_estilo: list[tuple] = []
    for i, item in enumerate(checklist, start=1):
        afeta = bool(item.get("afeta"))
        marca_style = _CELL_GREEN if afeta else _CELL_MUTED
        etapa_style = ParagraphStyle(
            f"BitinChecklistEtapa{i}", parent=_CELL,
            fontName="Helvetica-Bold" if afeta else "Helvetica",
            textColor=_INK if afeta else _INK_MUTED,
        )
        body.append([
            _p("✓" if afeta else "—", marca_style),
            _p(item.get("etapa", ""), etapa_style),
            _p(item.get("descricao", ""), _CELL if afeta else _CELL_MUTED),
        ])
        if afeta:
            extra_estilo.append(("BACKGROUND", (0, i), (-1, i), _GREEN_BG))
    table = Table([header] + body, colWidths=[1.5 * cm, 8.5 * cm, 6 * cm], repeatRows=1)
    comandos = list(_TABLE_GRID.getCommands()) + extra_estilo
    table.setStyle(TableStyle(comandos))
    flowables.append(table)
    return flowables


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
        ("TEXTCOLOR", (0, 0), (0, -1), _NAVY_DARK),
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
        diffs_table.setStyle(_com_zebra(_TABLE_GRID, len(body) + 1))
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
        lt_table.setStyle(_com_zebra(_TABLE_GRID, len(body) + 1))
        flowables.append(lt_table)

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

    # Ordem espelha BitinDetail.tsx (2026-07-21): cabeçalho -> setores acionados -> checklist
    # -> só depois os materiais com as alterações de código.
    story: list = []
    story.extend(_header_block(summary))

    story.append(Spacer(1, 6))
    story.extend(_setores_flowables(summary.get("setores_afetados") or []))

    checklist = summary.get("checklist") or []
    if checklist:
        story.extend(_checklist_flowables(checklist))

    materiais = summary.get("materiais") or []
    if materiais:
        story.append(Spacer(1, 8))
        story.append(Paragraph("Materiais", _H2))
        for idx, material in enumerate(materiais, start=1):
            story.extend(_material_flowables(material, idx))
            story.append(Spacer(1, 6))

    doc.build(story)
    return buffer.getvalue()
