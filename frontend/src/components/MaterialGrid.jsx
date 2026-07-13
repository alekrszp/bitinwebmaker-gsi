import { useEffect, useMemo, useRef, useState } from 'react'
import { api } from '../lib/api'
import { blankMaterial, coerceBoolean, getCellValue, materialFromSapPaste, setCellValue } from '../lib/bitinFields'
import { buildErrorIndex, cellKey } from '../lib/bitinErrors'
import { matchesSearch } from '../lib/textSearch'
import MaterialDetailModal from './MaterialDetailModal'

const IMPACTOS_CONDICIONAIS = [
  { key: 'centro_custo', label: 'Centro de custo' },
  { key: 'conta_razao', label: 'Conta razão' },
]

// Colunas maiores que a primeira versão -- feedback direto: células pequenas demais pra
// campos com valores reais (código de material, descrição, texto de dados_basicos).
const CELL_WIDTHS = { sm: 'w-24', md: 'w-40', lg: 'w-60' }
// Mesmos valores de CELL_WIDTHS em px -- table-layout:fixed só respeita a largura declarada
// de cada coluna se a <table> tiver uma largura total explícita (senão o navegador encolhe
// tudo proporcionalmente pra caber no container, ignorando os valores declarados por célula
// -- foi exatamente o bug visto: a coluna "#" de 48px renderizava a 25px, e a coluna
// congelada "Código" ficava com o offset errado, sobrepondo "Descrição"). Por isso o total é
// somado em JS e aplicado como `width` da <table> abaixo.
const CELL_WIDTH_PX = { sm: 96, md: 160, lg: 240 }
const ROW_NUMBER_WIDTH = 48 // px -- usado pra calcular o offset da 2ª coluna congelada
const ACTIONS_WIDTH = 168 // px -- table-fixed exige largura explícita em toda coluna

const FIXED_COLUMNS = [
  { group: 'campo', field: 'codigo_material', label: 'Código', type: 'text', width: 'md', required: true, freeze: true },
  { group: 'campo', field: 'descricao_material', label: 'Descrição', type: 'text', width: 'lg' },
  { group: 'campo', field: 'centro', label: 'Centro', type: 'text', width: 'sm', required: true },
  { group: 'campo', field: 'tipo_material', label: 'Tipo Material', type: 'text', width: 'sm', required: true },
  { group: 'campo', field: 'grupo_mercadorias_atual', label: 'Grupo Mercadorias (atual)', type: 'text', width: 'md' },
  { group: 'campo', field: 'tem_desenho', label: 'Tem desenho', type: 'checkbox' },
  { group: 'campo', field: 'desenho_aprovado', label: 'Desenho aprovado', type: 'checkbox' },
  { group: 'campo', field: 'ncm_aprovado_fiscal', label: 'NCM aprovado (fiscal)', type: 'checkbox' },
]

// Uma lista única e "achatada" de colunas (em vez de identificação/dados_basicos/impactos
// renderizados em blocos separados) -- é o que permite a navegação por teclado e o colar em
// bloco tratarem o grid inteiro como uma única planilha contígua, com (linha, coluna) simples.
function buildColumns(schema, visibleFields) {
  if (!schema) return FIXED_COLUMNS

  // "para" pintado como "Novo" em vermelho no cabeçalho -- convenção da própria planilha real
  // do BITin (aba "ZBPP009 + ALTERACAO"): toda coluna "Novo"/editável tem o rótulo em
  // vermelho negrito, diferente das colunas de valor atual. Mantido aqui de propósito.
  const dadosBasicosCols = visibleFields.flatMap((campo) => {
    const label = schema.dados_basicos.find((c) => c.key === campo)?.label || campo
    return [
      { group: 'dados_basicos', field: campo, sub: 'de', label, subLabel: 'Atual', type: 'text', width: 'md' },
      { group: 'dados_basicos', field: campo, sub: 'para', label, subLabel: 'Novo', variant: 'novo', type: 'text', width: 'md' },
    ]
  })
  const impactosCols = schema.impactos_operacionais.map((col) => ({
    group: 'impactos_operacionais',
    field: col.key,
    label: col.label,
    type: 'select',
    options: col.options,
    width: 'sm',
  }))
  const impactosCondicionaisCols = IMPACTOS_CONDICIONAIS.map((col) => ({
    group: 'impactos_operacionais',
    field: col.key,
    label: col.label,
    type: 'text',
    width: 'md',
    dynamicPlaceholder: (material) => (getCellValue(material, impactosCols.find((c) => c.field === 'est')) === 'S' ? 'obrigatório (Est=S)' : ''),
  }))

  return [...FIXED_COLUMNS, ...dadosBasicosCols, ...impactosCols, ...impactosCondicionaisCols]
}

// Grid de materiais em formato planilha -- ver docs/FRONTEND.md, "Grid de materiais". Navega
// como Excel nas 4 setas (não depende de Tab, que pula pros botões de ação no fim da linha),
// Enter confirma e desce, e aceita colar um bloco de células a partir de qualquer célula. Os
// ~30 campos de dados_basicos ficam ocultos da grade por padrão (pouco espaço útil numa
// célula de planilha pra rótulo+valor) -- o botão "Detalhes" por linha abre um painel grande
// com todos eles, um por linha, pra edição sem aperto.
export default function MaterialGrid({ materiais, onChange, errors = [], disabled = false }) {
  const [schema, setSchema] = useState(null)
  const [schemaError, setSchemaError] = useState(null)
  const [visibleFields, setVisibleFields] = useState([])
  const [showFieldPicker, setShowFieldPicker] = useState(false)
  const [showSapImport, setShowSapImport] = useState(false)
  const [detailRowIndex, setDetailRowIndex] = useState(null)
  const cellRefs = useRef({})

  useEffect(() => {
    let cancelado = false
    api
      .get('/bitins/schema/materiais')
      .then((resp) => {
        if (!cancelado) setSchema(resp.data)
      })
      .catch(() => {
        if (!cancelado) setSchemaError('Não foi possível carregar as colunas de materiais.')
      })
    return () => {
      cancelado = true
    }
  }, [])

  const columns = useMemo(() => buildColumns(schema, visibleFields), [schema, visibleFields])
  const tableWidth =
    ROW_NUMBER_WIDTH +
    columns.reduce((soma, col) => soma + CELL_WIDTH_PX[col.width || 'md'], 0) +
    (disabled ? 0 : ACTIONS_WIDTH)

  // Só usa os erros com caminho materiais[idx]... pra destacar célula -- erros gerais
  // (cabeçalho, ordem_cliente) já aparecem na lista completa mostrada por quem usa este
  // componente (ver BitinDetail.jsx), não precisam de um painel duplicado aqui.
  const { byCell } = useMemo(() => buildErrorIndex(errors), [errors])

  function cellErrors(rowIndex, col) {
    return byCell.get(cellKey(rowIndex, col.group, col.field)) || []
  }

  function registerRef(rowIndex, colIndex, el) {
    const key = `${rowIndex}-${colIndex}`
    if (el) cellRefs.current[key] = el
    else delete cellRefs.current[key]
  }

  function focusCell(rowIndex, colIndex) {
    const el = cellRefs.current[`${rowIndex}-${colIndex}`]
    if (!el) return
    el.focus()
    if (el.select) el.select()
  }

  // Navegação nas 4 setas -- deliberadamente não depende de Tab (a ordem do DOM inclui os
  // botões "Detalhes"/"Remover" no fim de cada linha, o que quebraria o fluxo horizontal).
  // As 4 setas SEMPRE pulam de célula (sem meio-termo tipo "só pula na borda do texto") --
  // mais previsível pra digitação rápida, e cada célula já seleciona o conteúdo inteiro ao
  // chegar (foco programático em focusCell), então digitar direto substitui o valor. Pra
  // editar o meio de um texto longo, clique com o mouse ou use Home/End (não afetados aqui).
  function handleCellKeyDown(e, rowIndex, colIndex) {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      focusCell(rowIndex + 1, colIndex)
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      focusCell(rowIndex - 1, colIndex)
    } else if (e.key === 'Enter') {
      e.preventDefault()
      focusCell(e.shiftKey ? rowIndex - 1 : rowIndex + 1, colIndex)
    } else if (e.key === 'ArrowLeft') {
      e.preventDefault()
      focusCell(rowIndex, colIndex - 1)
    } else if (e.key === 'ArrowRight') {
      e.preventDefault()
      focusCell(rowIndex, colIndex + 1)
    }
  }

  function commitCell(rowIndex, col, value) {
    onChange(materiais.map((m, i) => (i === rowIndex ? setCellValue(m, col, value) : m)))
  }

  // Cola um bloco de células (copiado do Excel ou de outra parte do grid) a partir da célula
  // focada -- preenche linhas/colunas seguintes, criando materiais novos se o bloco for maior
  // que o grid atual. Um valor único colado (sem tab/quebra de linha) não entra aqui -- usa o
  // paste nativo do input, sem interferência.
  function handleCellPaste(e, rowIndex, colIndex) {
    const text = e.clipboardData?.getData('text')
    if (!text || (!text.includes('\t') && !text.includes('\n'))) return
    e.preventDefault()

    const linhas = text.replace(/\r/g, '').split('\n')
    if (linhas[linhas.length - 1] === '') linhas.pop()
    const bloco = linhas.map((linha) => linha.split('\t'))

    const novo = [...materiais]
    bloco.forEach((valores, r) => {
      const targetRow = rowIndex + r
      while (novo.length <= targetRow) novo.push(blankMaterial())
      valores.forEach((valor, c) => {
        const col = columns[colIndex + c]
        if (!col) return
        const valorFinal = col.type === 'checkbox' ? coerceBoolean(valor) : valor.trim()
        novo[targetRow] = setCellValue(novo[targetRow], col, valorFinal)
      })
    })
    onChange(novo)
  }

  function addRow() {
    onChange([...materiais, blankMaterial()])
  }

  function removeRow(idx) {
    onChange(materiais.filter((_, i) => i !== idx))
  }

  function addFromSapImport(novosMateriais) {
    onChange([...materiais, ...novosMateriais.map(materialFromSapPaste)])
  }

  return (
    <div className="rounded border border-gray-200 bg-white p-4">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-medium text-gray-900">Materiais</h2>
          {!disabled && (
            <p className="mt-0.5 text-xs text-gray-400">
              Clique numa célula e use as setas ↑↓←→ ou Enter pra navegar. Cole um bloco copiado do Excel em
              qualquer célula (Ctrl+V) — linhas novas são criadas automaticamente se precisar. Use "Detalhes"
              pra editar os campos de dados básicos com mais espaço.
            </p>
          )}
        </div>
        {!disabled && (
          <div className="flex flex-wrap gap-2">
            <button type="button" onClick={addRow} className="rounded border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-100">
              + Adicionar material
            </button>
            <button
              type="button"
              onClick={() => setShowSapImport((v) => !v)}
              className="rounded border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-100"
            >
              Importar relatório do SAP
            </button>
            <FieldPicker
              schema={schema}
              visibleFields={visibleFields}
              setVisibleFields={setVisibleFields}
              open={showFieldPicker}
              setOpen={setShowFieldPicker}
            />
          </div>
        )}
      </div>

      {schemaError && <p className="mb-3 text-sm text-red-600">{schemaError}</p>}

      {showSapImport && !disabled && (
        <SapImportPanel onParsed={addFromSapImport} onClose={() => setShowSapImport(false)} />
      )}

      {materiais.length === 0 && <p className="text-sm text-gray-500">Nenhum material adicionado ainda.</p>}

      {materiais.length > 0 && (
        <div className="max-h-[75vh] overflow-auto rounded border border-gray-200">
          {/* table-fixed é essencial aqui: com table-layout:auto (padrão), o navegador
              encolhe colunas com pouco conteúdo (ex.: "#" com só "1"/"2") abaixo da largura
              declarada, o que quebra a matemática do offset das colunas congeladas (a coluna
              "Código" ficava sobrepondo "Descrição"). Com table-fixed, a largura do cabeçalho
              manda de verdade. border-separate (não border-collapse) porque position:sticky
              em <td>/<th> não funciona de forma confiável com border-collapse. */}
          <table style={{ width: tableWidth }} className="table-fixed border-separate border-spacing-0 text-sm">
            <thead>
              <tr>
                <th
                  style={{ width: ROW_NUMBER_WIDTH }}
                  className="sticky top-0 left-0 z-30 border border-gray-200 bg-gray-100 px-2 py-2.5 text-xs font-semibold text-gray-500"
                >
                  #
                </th>
                {columns.map((col, colIndex) => (
                  <th
                    key={colIndex}
                    style={col.freeze ? { left: ROW_NUMBER_WIDTH } : undefined}
                    className={`${CELL_WIDTHS[col.width || 'md']} sticky top-0 border border-gray-200 bg-gray-100 px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide ${
                      col.variant === 'novo' ? 'text-red-600' : 'text-gray-600'
                    } ${col.freeze ? 'z-30' : 'z-20'}`}
                  >
                    {col.label}
                    {col.required && <span className="text-red-500"> *</span>}
                    {col.subLabel && (
                      <span className={`block text-[10px] font-normal normal-case tracking-normal ${col.variant === 'novo' ? 'text-red-500' : 'text-gray-400'}`}>
                        {col.subLabel}
                      </span>
                    )}
                  </th>
                ))}
                {!disabled && (
                  <th
                    style={{ width: ACTIONS_WIDTH }}
                    className="sticky top-0 z-20 border border-gray-200 bg-gray-100 px-3 py-2.5 text-center text-xs font-semibold text-gray-600"
                  >
                    Ações
                  </th>
                )}
              </tr>
            </thead>
            <tbody>
              {materiais.map((material, rowIndex) => (
                <tr key={rowIndex} className={`group ${rowIndex % 2 === 1 ? 'bg-gray-50' : 'bg-white'} hover:bg-blue-50`}>
                  <td
                    style={{ width: ROW_NUMBER_WIDTH }}
                    className="sticky left-0 z-10 border border-gray-200 bg-inherit px-2 py-2 text-center text-xs text-gray-400"
                  >
                    {rowIndex + 1}
                  </td>
                  {columns.map((col, colIndex) => {
                    const errs = cellErrors(rowIndex, col)
                    return (
                      <GridCell
                        key={colIndex}
                        col={col}
                        rowIndex={rowIndex}
                        colIndex={colIndex}
                        value={getCellValue(material, col)}
                        disabled={disabled}
                        hasError={errs.length > 0}
                        errorMessage={errs.length > 0 ? errs.map((e) => e.message).join('\n') : undefined}
                        placeholder={col.dynamicPlaceholder ? col.dynamicPlaceholder(material) : undefined}
                        registerRef={registerRef}
                        onCellKeyDown={handleCellKeyDown}
                        onCellPaste={handleCellPaste}
                        onCommit={(value) => commitCell(rowIndex, col, value)}
                        freezeOffset={col.freeze ? ROW_NUMBER_WIDTH : undefined}
                      />
                    )
                  })}
                  {!disabled && (
                    <td style={{ width: ACTIONS_WIDTH }} className="border border-gray-200 bg-inherit px-2 py-2 text-center">
                      <div className="flex justify-center gap-1.5">
                        <button
                          type="button"
                          onClick={() => setDetailRowIndex(rowIndex)}
                          className="rounded border border-gray-300 px-2 py-1 text-xs text-gray-700 hover:bg-gray-100"
                        >
                          Detalhes
                        </button>
                        <button
                          type="button"
                          onClick={() => removeRow(rowIndex)}
                          className="rounded border border-red-300 px-2 py-1 text-xs text-red-700 hover:bg-red-50"
                        >
                          Remover
                        </button>
                      </div>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {detailRowIndex !== null && materiais[detailRowIndex] && (
        <MaterialDetailModal
          material={materiais[detailRowIndex]}
          schema={schema}
          errors={errors}
          rowIndex={detailRowIndex}
          disabled={disabled}
          onChange={(atualizado) => onChange(materiais.map((m, i) => (i === detailRowIndex ? atualizado : m)))}
          onClose={() => setDetailRowIndex(null)}
        />
      )}
    </div>
  )
}

function GridCell({ col, rowIndex, colIndex, value, disabled, hasError, errorMessage, placeholder, registerRef, onCellKeyDown, onCellPaste, onCommit, freezeOffset }) {
  // Erro de envio: borda vermelha sempre visível (não só bg sutil) + anel vermelho por
  // cima do azul de foco -- precisa continuar óbvio mesmo quando a célula está selecionada.
  const cellBg = hasError
    ? 'border-red-400 bg-red-50 ring-1 ring-inset ring-red-400'
    : 'border-gray-200 bg-inherit'
  const inputClass = `h-full w-full bg-transparent px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-inset ${
    hasError ? 'focus:ring-red-500' : 'focus:ring-blue-500'
  } disabled:text-gray-400`
  const stickyStyle = freezeOffset !== undefined ? { left: freezeOffset } : undefined
  const stickyClass = freezeOffset !== undefined ? 'sticky z-10' : ''

  if (col.type === 'checkbox') {
    return (
      <td style={stickyStyle} className={`${CELL_WIDTHS[col.width || 'md']} border p-0 text-center ${cellBg} ${stickyClass}`}>
        <input
          ref={(el) => registerRef(rowIndex, colIndex, el)}
          type="checkbox"
          checked={!!value}
          disabled={disabled}
          onChange={(e) => onCommit(e.target.checked)}
          onKeyDown={(e) => onCellKeyDown(e, rowIndex, colIndex)}
          onPaste={(e) => onCellPaste(e, rowIndex, colIndex)}
          title={errorMessage}
          className="h-4 w-4 my-2.5"
        />
      </td>
    )
  }

  if (col.type === 'select') {
    return (
      <td style={stickyStyle} className={`${CELL_WIDTHS[col.width || 'md']} border p-0 ${cellBg} ${stickyClass}`}>
        <select
          ref={(el) => registerRef(rowIndex, colIndex, el)}
          value={value || '-'}
          disabled={disabled}
          onChange={(e) => onCommit(e.target.value)}
          onKeyDown={(e) => onCellKeyDown(e, rowIndex, colIndex)}
          onPaste={(e) => onCellPaste(e, rowIndex, colIndex)}
          title={errorMessage}
          className={inputClass}
        >
          {col.options.map((opt) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>
      </td>
    )
  }

  return (
    <td style={stickyStyle} className={`${CELL_WIDTHS[col.width || 'md']} border p-0 ${cellBg} ${stickyClass}`}>
      <input
        ref={(el) => registerRef(rowIndex, colIndex, el)}
        value={value || ''}
        disabled={disabled}
        onChange={(e) => onCommit(e.target.value)}
        onKeyDown={(e) => onCellKeyDown(e, rowIndex, colIndex)}
        onPaste={(e) => onCellPaste(e, rowIndex, colIndex)}
        title={errorMessage}
        placeholder={placeholder}
        className={inputClass}
      />
    </td>
  )
}

function FieldPicker({ schema, visibleFields, setVisibleFields, open, setOpen }) {
  const [busca, setBusca] = useState('')

  const opcoes = useMemo(() => {
    if (!schema) return []
    return schema.dados_basicos.filter((c) => matchesSearch(c.label, busca))
  }, [schema, busca])

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="rounded border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-100"
      >
        Fixar campos na grade ({visibleFields.length})
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-10 z-20 w-72 rounded border border-gray-200 bg-white p-3 shadow-lg">
            <p className="mb-2 text-xs text-gray-500">
              Campos de dados básicos mostrados como coluna na grade (útil pra colar em bloco). Pra editar
              qualquer campo com mais espaço, use "Detalhes" na linha do material.
            </p>
            <input
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              placeholder="Buscar campo..."
              className="mb-2 w-full rounded border border-gray-300 px-2 py-1 text-sm"
            />
            <div className="mb-2 flex gap-2 text-xs">
              <button
                type="button"
                onClick={() => setVisibleFields(schema.dados_basicos.map((c) => c.key))}
                className="text-blue-600 hover:underline"
              >
                Selecionar tudo
              </button>
              <button type="button" onClick={() => setVisibleFields([])} className="text-gray-500 hover:underline">
                Limpar
              </button>
            </div>
            <div className="max-h-64 overflow-y-auto">
              {opcoes.map((campo) => (
                <label key={campo.key} className="flex items-center gap-2 px-1 py-1 text-sm hover:bg-gray-50">
                  <input
                    type="checkbox"
                    checked={visibleFields.includes(campo.key)}
                    onChange={() =>
                      setVisibleFields((prev) =>
                        prev.includes(campo.key) ? prev.filter((k) => k !== campo.key) : [...prev, campo.key],
                      )
                    }
                  />
                  {campo.label}
                </label>
              ))}
              {opcoes.length === 0 && <p className="px-1 py-2 text-sm text-gray-400">Nenhum campo encontrado.</p>}
            </div>
          </div>
        </>
      )}
    </div>
  )
}

function SapImportPanel({ onParsed, onClose }) {
  const [texto, setTexto] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  async function processar() {
    setLoading(true)
    setError(null)
    try {
      const resp = await api.post('/bitins/parse-sap-paste', { raw_text: texto })
      onParsed(resp.data.materiais)
      setTexto('')
      onClose()
    } catch {
      setError('Não foi possível processar o texto colado.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mb-3 rounded border border-gray-200 bg-gray-50 p-3">
      <p className="mb-2 text-sm text-gray-600">
        Cole aqui as linhas copiadas do relatório do SAP (ZBPP009 ou equivalente). Cada linha vira um material
        novo, com identificação e snapshot atual já preenchidos — diferente de colar direto numa célula do grid
        (que edita o que já existe), isto sempre adiciona linhas novas.
      </p>
      <textarea
        value={texto}
        onChange={(e) => setTexto(e.target.value)}
        rows={5}
        className="mb-2 w-full rounded border border-gray-300 p-2 font-mono text-xs"
        placeholder="Cole aqui (Ctrl+V)..."
      />
      {error && <p className="mb-2 text-sm text-red-600">{error}</p>}
      <div className="flex gap-2">
        <button
          type="button"
          onClick={processar}
          disabled={loading || !texto.trim()}
          className="rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? 'Processando...' : 'Adicionar materiais'}
        </button>
        <button
          type="button"
          onClick={onClose}
          className="rounded border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-100"
        >
          Cancelar
        </button>
      </div>
    </div>
  )
}
