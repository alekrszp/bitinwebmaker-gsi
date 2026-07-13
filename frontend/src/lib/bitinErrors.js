// Faz o parse do 'field' estruturado que o backend devolve no envio (ver
// docs/BITIN_MODEL.md, "Erros estruturados") pra localizar a célula exata do grid de
// materiais (linha + grupo de coluna). Formatos reais emitidos por
// scripts/bitin_model.py e scripts/bitin_business_rules.py:
//   materiais[0].codigo_material
//   materiais[0].desenho_aprovado
//   materiais[0].alteracoes.dados_basicos.ncm
//   materiais[0].alteracoes.impactos_operacionais.alt
const MATERIAL_FIELD_RE = /^materiais\[(\d+)\]\.(.+)$/
const DADOS_BASICOS_RE = /^alteracoes\.dados_basicos\.([a-zA-Z0-9_]+)/
const IMPACTOS_RE = /^alteracoes\.impactos_operacionais\.([a-zA-Z0-9_]+)/

export function parseFieldPath(field) {
  const materialMatch = MATERIAL_FIELD_RE.exec(field || '')
  if (!materialMatch) return null
  const rowIndex = Number(materialMatch[1])
  const rest = materialMatch[2]

  const dadosBasicos = DADOS_BASICOS_RE.exec(rest)
  if (dadosBasicos) return { rowIndex, group: 'dados_basicos', key: dadosBasicos[1] }

  const impactos = IMPACTOS_RE.exec(rest)
  if (impactos) return { rowIndex, group: 'impactos_operacionais', key: impactos[1] }

  return { rowIndex, group: 'campo', key: rest }
}

export function cellKey(rowIndex, group, key) {
  return `${rowIndex}|${group}|${key}`
}

// Agrupa os erros do envio em: erros por célula (pra destacar no grid) + erros gerais
// (sem material associado -- cabeçalho, ordem_cliente, etc. -- mostrados como lista).
export function buildErrorIndex(errors) {
  const byCell = new Map()
  const general = []
  for (const err of errors || []) {
    const parsed = parseFieldPath(err.field)
    if (!parsed) {
      general.push(err)
      continue
    }
    const key = cellKey(parsed.rowIndex, parsed.group, parsed.key)
    if (!byCell.has(key)) byCell.set(key, [])
    byCell.get(key).push(err)
  }
  return { byCell, general }
}
