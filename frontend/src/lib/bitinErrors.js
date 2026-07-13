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

const MATERIAL_INDEX_RE = /^materiais\[(\d+)\]/

// A grade de materiais tem 300 linhas, mas só as preenchidas são de fato enviadas ao backend
// (ver BitinDetail.jsx, compactMateriais) -- os erros do envio vêm indexados nesse array
// compactado, não na posição real da grade. `indexMap[i]` é a posição na grade de onde a
// i-ésima linha enviada veio; sem essa tradução, o erro destacaria a célula errada (ou uma
// linha em branco) sempre que existir alguma linha em branco antes da com erro.
export function remapMaterialErrorIndices(errors, indexMap) {
  if (!indexMap) return errors
  return (errors || []).map((err) => {
    const match = MATERIAL_INDEX_RE.exec(err.field || '')
    if (!match) return err
    const gridIndex = indexMap[Number(match[1])]
    if (gridIndex === undefined) return err
    return { ...err, field: err.field.replace(MATERIAL_INDEX_RE, `materiais[${gridIndex}]`) }
  })
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
