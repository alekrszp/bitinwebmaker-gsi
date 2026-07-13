// Helpers de leitura/escrita imutável do formato materiais[] do BITin (ver
// docs/BITIN_MODEL.md). Mantidos separados do componente de grid porque o mesmo formato
// também é usado pela tela de resumo/visualização.

export function blankMaterial() {
  return {
    codigo_material: '',
    descricao_material: '',
    centro: '',
    tipo_material: '',
    grupo_mercadorias_atual: '',
    tem_desenho: false,
    desenho_aprovado: false,
    ncm_aprovado_fiscal: false,
    alteracoes: { dados_basicos: {}, impactos_operacionais: {} },
  }
}

// Um material "tem conteúdo" quando o código foi preenchido -- critério usado pra filtrar as
// linhas em branco da grade (ver MaterialGrid.jsx, "tabela pré-feita" com 300 linhas) antes de
// salvar/enviar, já que o backend valida codigo_material/centro/tipo_material como obrigatórios
// em TODA linha de materiais[] sem distinguir linha em branco de linha real preenchida
// (scripts/bitin_model.py, REQUIRED_MATERIAL_FIELDS) -- sem esse filtro, 300 linhas em branco
// virariam ~900 erros de campo obrigatório vazio no envio.
export function hasContent(material) {
  return !!material.codigo_material?.trim()
}

// Campos de identificação que a grade (MaterialGrid) não mostra por padrão (a print real da
// aba "Template apresentação" só tem 10 colunas: 3 de identificação + os 7 impactos) mas que
// continuam editáveis pelo painel de Detalhes (MaterialDetailModal, seção "Identificação"),
// reaproveitando getCellValue/setCellValue abaixo.
export const MODAL_ONLY_FIELDS = [
  { group: 'campo', field: 'tipo_material', label: 'Tipo Material', type: 'text', required: true },
  { group: 'campo', field: 'grupo_mercadorias_atual', label: 'Grupo Mercadorias (atual)', type: 'text' },
  { group: 'campo', field: 'tem_desenho', label: 'Tem desenho', type: 'checkbox' },
  { group: 'campo', field: 'desenho_aprovado', label: 'Desenho aprovado', type: 'checkbox' },
  { group: 'campo', field: 'ncm_aprovado_fiscal', label: 'NCM aprovado (fiscal)', type: 'checkbox' },
]

export function getDadosBasico(material, campo, sub) {
  return material.alteracoes?.dados_basicos?.[campo]?.[sub] ?? ''
}

export function setDadosBasico(material, campo, sub, valor) {
  const atual = material.alteracoes?.dados_basicos?.[campo] ?? { de: '', para: '' }
  return {
    ...material,
    alteracoes: {
      ...material.alteracoes,
      dados_basicos: {
        ...material.alteracoes?.dados_basicos,
        [campo]: { ...atual, [sub]: valor },
      },
    },
  }
}

export function getImpacto(material, campo) {
  return material.alteracoes?.impactos_operacionais?.[campo] ?? ''
}

export function setImpacto(material, campo, valor) {
  return {
    ...material,
    alteracoes: {
      ...material.alteracoes,
      impactos_operacionais: {
        ...material.alteracoes?.impactos_operacionais,
        [campo]: valor,
      },
    },
  }
}

// Colar do SAP devolve só identificação + snapshot atual (ver sap_paste_parser.py) --
// completa com a estrutura de alteracoes vazia pra virar uma linha editável do grid.
export function materialFromSapPaste(parsed) {
  return { ...blankMaterial(), ...parsed }
}

// checklist[] em branco a partir do schema (GET /bitins/schema/checklist) -- os 22 itens
// fixos do POP, todos com afeta=false até o engenheiro marcar. Ver ChecklistEditor.jsx.
export function blankChecklist(items) {
  return items.map((item) => ({ id: item.id, etapa: item.etapa, afeta: false, descricao: '' }))
}

// Interpreta texto colado (de uma célula tipo checkbox) do jeito que o Excel/SAP
// normalmente representa booleano em texto -- usado só ao colar um bloco de células
// (ver handleCellPaste em MaterialGrid.jsx); digitação normal usa o próprio <input type=checkbox>.
export function coerceBoolean(value) {
  if (typeof value === 'boolean') return value
  const v = String(value ?? '').trim().toUpperCase()
  return v === 'SIM' || v === 'TRUE' || v === 'X' || v === '1'
}

// Dispatch genérico get/set por coluna -- usado pela navegação por teclado e pelo colar
// de bloco (estilo Excel) do grid, que precisam ler/escrever uma célula sem saber de
// antemão se ela pertence a identificação/snapshot, dados_basicos ou impactos_operacionais.
export function getCellValue(material, col) {
  if (col.group === 'campo') {
    return col.type === 'checkbox' ? !!material[col.field] : material[col.field] || ''
  }
  if (col.group === 'dados_basicos') return getDadosBasico(material, col.field, col.sub)
  if (col.group === 'impactos_operacionais') return getImpacto(material, col.field)
  return ''
}

export function setCellValue(material, col, value) {
  if (col.group === 'campo') {
    if (col.type === 'checkbox') return { ...material, [col.field]: coerceBoolean(value) }
    return { ...material, [col.field]: value }
  }
  if (col.group === 'dados_basicos') return setDadosBasico(material, col.field, col.sub, value)
  if (col.group === 'impactos_operacionais') return setImpacto(material, col.field, value)
  return material
}
