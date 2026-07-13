import { Fragment, useEffect, useMemo, useState } from 'react'
import { api } from '../lib/api'
import { blankMaterial, getDadosBasico, getImpacto, materialFromSapPaste, setDadosBasico, setImpacto } from '../lib/bitinFields'
import { buildErrorIndex, cellKey } from '../lib/bitinErrors'

const IMPACTOS_CONDICIONAIS = [
  { key: 'centro_custo', label: 'Centro de custo' },
  { key: 'conta_razao', label: 'Conta razão' },
]

// Grid de materiais (linhas/colunas) -- ver docs/FRONTEND.md, "Grid de materiais". As
// colunas de identificação/snapshot/impactos são fixas; as de dados_basicos (De/Para) vêm
// do schema do backend e ficam ocultas por padrão (são ~30 campos -- mostrar todas de uma
// vez deixaria a planilha impraticável) até o usuário escolher quais quer editar.
export default function MaterialGrid({ materiais, onChange, errors = [], disabled = false }) {
  const [schema, setSchema] = useState(null)
  const [schemaError, setSchemaError] = useState(null)
  const [visibleFields, setVisibleFields] = useState([])
  const [showFieldPicker, setShowFieldPicker] = useState(false)
  const [showPaste, setShowPaste] = useState(false)

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

  // Só usa os erros com caminho materiais[idx]... pra destacar célula -- erros gerais
  // (cabeçalho, ordem_cliente) já aparecem na lista completa mostrada por quem usa este
  // componente (ver BitinDetail.jsx), não precisam de um painel duplicado aqui.
  const { byCell } = useMemo(() => buildErrorIndex(errors), [errors])

  function updateRow(idx, updater) {
    const novo = materiais.map((m, i) => (i === idx ? updater(m) : m))
    onChange(novo)
  }

  function addRow() {
    onChange([...materiais, blankMaterial()])
  }

  function removeRow(idx) {
    onChange(materiais.filter((_, i) => i !== idx))
  }

  function addFromPaste(novosMateriais) {
    onChange([...materiais, ...novosMateriais.map(materialFromSapPaste)])
  }

  function cellErrors(idx, group, key) {
    return byCell.get(cellKey(idx, group, key)) || []
  }

  const CELL_WIDTHS = { sm: 'w-20', md: 'w-32', lg: 'w-48' }

  function cellClass(idx, group, key, width = 'md') {
    const base = `${CELL_WIDTHS[width]} rounded border px-2 py-1.5 text-sm disabled:bg-gray-50 disabled:text-gray-500`
    return cellErrors(idx, group, key).length > 0
      ? `${base} border-red-400 bg-red-50 focus:border-red-500`
      : `${base} border-gray-300 focus:border-blue-500`
  }

  function cellTitle(idx, group, key) {
    const errs = cellErrors(idx, group, key)
    return errs.length > 0 ? errs.map((e) => e.message).join('\n') : undefined
  }

  return (
    <div className="rounded border border-gray-200 bg-white p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-medium text-gray-900">Materiais</h2>
        {!disabled && (
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={addRow}
              className="rounded border border-gray-300 px-3 py-1 text-sm hover:bg-gray-100"
            >
              + Adicionar material
            </button>
            <button
              type="button"
              onClick={() => setShowPaste((v) => !v)}
              className="rounded border border-gray-300 px-3 py-1 text-sm hover:bg-gray-100"
            >
              Colar do SAP
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

      {showPaste && !disabled && (
        <SapPastePanel onParsed={addFromPaste} onClose={() => setShowPaste(false)} />
      )}

      {materiais.length === 0 && <p className="text-sm text-gray-500">Nenhum material adicionado ainda.</p>}

      {materiais.length > 0 && (
        <div className="overflow-x-auto rounded border border-gray-100">
          <table className="min-w-full border-collapse text-sm">
            <thead>
              <tr className="bg-gray-50 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                <th className="sticky left-0 z-10 bg-gray-50 px-3 py-2">#</th>
                <th className="px-2 py-2">Código</th>
                <th className="px-2 py-2">Descrição</th>
                <th className="px-2 py-2">Centro</th>
                <th className="px-2 py-2">Tipo Material</th>
                <th className="px-2 py-2">Grupo Mercadorias (atual)</th>
                <th className="px-2 py-2 text-center">Tem desenho</th>
                <th className="px-2 py-2 text-center">Desenho aprovado</th>
                <th className="px-2 py-2 text-center">NCM aprovado (fiscal)</th>
                {visibleFields.map((campo) => (
                  <th key={campo} colSpan={2} className="border-l border-gray-200 px-2 py-2 text-center">
                    {schema?.dados_basicos.find((c) => c.key === campo)?.label || campo}
                  </th>
                ))}
                {(schema?.impactos_operacionais || []).map((col) => (
                  <th key={col.key} className="border-l border-gray-200 px-2 py-2 text-center">
                    {col.label}
                  </th>
                ))}
                {IMPACTOS_CONDICIONAIS.map((col) => (
                  <th key={col.key} className="px-2 py-2">
                    {col.label}
                  </th>
                ))}
                {!disabled && <th className="px-2 py-2 text-center">Ações</th>}
              </tr>
              {visibleFields.length > 0 && (
                <tr className="bg-gray-50 text-[10px] uppercase tracking-wide text-gray-400">
                  <th className="sticky left-0 z-10 bg-gray-50" colSpan={9} />
                  {visibleFields.map((campo) => (
                    <Fragment key={campo}>
                      <th className="border-l border-gray-200 px-2 py-1 font-normal">De</th>
                      <th className="px-2 py-1 font-normal">Para</th>
                    </Fragment>
                  ))}
                  <th colSpan={(schema?.impactos_operacionais.length || 0) + IMPACTOS_CONDICIONAIS.length + (disabled ? 0 : 1)} />
                </tr>
              )}
            </thead>
            <tbody>
              {materiais.map((material, idx) => (
                <tr key={idx} className="border-t border-gray-100 align-top hover:bg-gray-50/60">
                  <td className="sticky left-0 z-10 bg-white px-3 py-1.5 text-xs text-gray-500">{idx + 1}</td>
                  <td className="px-2 py-1.5">
                    <input
                      value={material.codigo_material || ''}
                      disabled={disabled}
                      onChange={(e) => updateRow(idx, (m) => ({ ...m, codigo_material: e.target.value }))}
                      className={cellClass(idx, 'campo', 'codigo_material', 'md')}
                      title={cellTitle(idx, 'campo', 'codigo_material')}
                    />
                  </td>
                  <td className="px-2 py-1.5">
                    <input
                      value={material.descricao_material || ''}
                      disabled={disabled}
                      onChange={(e) => updateRow(idx, (m) => ({ ...m, descricao_material: e.target.value }))}
                      className={cellClass(idx, 'campo', 'descricao_material', 'lg')}
                    />
                  </td>
                  <td className="px-2 py-1.5">
                    <input
                      value={material.centro || ''}
                      disabled={disabled}
                      onChange={(e) => updateRow(idx, (m) => ({ ...m, centro: e.target.value }))}
                      className={cellClass(idx, 'campo', 'centro', 'sm')}
                      title={cellTitle(idx, 'campo', 'centro')}
                    />
                  </td>
                  <td className="px-2 py-1.5">
                    <input
                      value={material.tipo_material || ''}
                      disabled={disabled}
                      onChange={(e) => updateRow(idx, (m) => ({ ...m, tipo_material: e.target.value }))}
                      className={cellClass(idx, 'campo', 'tipo_material', 'sm')}
                      title={cellTitle(idx, 'campo', 'tipo_material')}
                    />
                  </td>
                  <td className="px-2 py-1.5">
                    <input
                      value={material.grupo_mercadorias_atual || ''}
                      disabled={disabled}
                      onChange={(e) => updateRow(idx, (m) => ({ ...m, grupo_mercadorias_atual: e.target.value }))}
                      className={cellClass(idx, 'campo', 'grupo_mercadorias_atual', 'md')}
                    />
                  </td>
                  <td className="px-2 py-1.5 text-center">
                    <input
                      type="checkbox"
                      checked={!!material.tem_desenho}
                      disabled={disabled}
                      onChange={(e) => updateRow(idx, (m) => ({ ...m, tem_desenho: e.target.checked }))}
                    />
                  </td>
                  <td className="px-2 py-1.5 text-center">
                    <input
                      type="checkbox"
                      checked={!!material.desenho_aprovado}
                      disabled={disabled}
                      onChange={(e) => updateRow(idx, (m) => ({ ...m, desenho_aprovado: e.target.checked }))}
                      title={cellTitle(idx, 'campo', 'desenho_aprovado')}
                    />
                  </td>
                  <td className="px-2 py-1.5 text-center">
                    <input
                      type="checkbox"
                      checked={!!material.ncm_aprovado_fiscal}
                      disabled={disabled}
                      onChange={(e) => updateRow(idx, (m) => ({ ...m, ncm_aprovado_fiscal: e.target.checked }))}
                      title={cellTitle(idx, 'campo', 'ncm_aprovado_fiscal')}
                    />
                  </td>

                  {visibleFields.map((campo) => (
                    <Fragment key={campo}>
                      <td className="border-l border-gray-200 px-2 py-1.5">
                        <input
                          value={getDadosBasico(material, campo, 'de')}
                          disabled={disabled}
                          onChange={(e) => updateRow(idx, (m) => setDadosBasico(m, campo, 'de', e.target.value))}
                          className={cellClass(idx, 'dados_basicos', campo, 'md')}
                        />
                      </td>
                      <td className="px-2 py-1.5">
                        <input
                          value={getDadosBasico(material, campo, 'para')}
                          disabled={disabled}
                          onChange={(e) => updateRow(idx, (m) => setDadosBasico(m, campo, 'para', e.target.value))}
                          className={cellClass(idx, 'dados_basicos', campo, 'md')}
                          title={cellTitle(idx, 'dados_basicos', campo)}
                        />
                      </td>
                    </Fragment>
                  ))}

                  {(schema?.impactos_operacionais || []).map((col) => (
                    <td key={col.key} className="border-l border-gray-200 px-2 py-1.5">
                      <select
                        value={getImpacto(material, col.key) || '-'}
                        disabled={disabled}
                        onChange={(e) => updateRow(idx, (m) => setImpacto(m, col.key, e.target.value))}
                        className={cellClass(idx, 'impactos_operacionais', col.key, 'sm')}
                        title={cellTitle(idx, 'impactos_operacionais', col.key)}
                      >
                        {col.options.map((opt) => (
                          <option key={opt} value={opt}>
                            {opt}
                          </option>
                        ))}
                      </select>
                    </td>
                  ))}

                  {IMPACTOS_CONDICIONAIS.map((col) => (
                    <td key={col.key} className="px-2 py-1.5">
                      <input
                        value={getImpacto(material, col.key)}
                        disabled={disabled}
                        onChange={(e) => updateRow(idx, (m) => setImpacto(m, col.key, e.target.value))}
                        className={cellClass(idx, 'impactos_operacionais', col.key, 'md')}
                        title={cellTitle(idx, 'impactos_operacionais', col.key)}
                        placeholder={getImpacto(material, 'est') === 'S' ? 'obrigatório (Est=S)' : ''}
                      />
                    </td>
                  ))}

                  {!disabled && (
                    <td className="px-2 py-1.5 text-center">
                      <button
                        type="button"
                        onClick={() => removeRow(idx)}
                        className="rounded border border-red-300 px-2 py-1 text-xs text-red-700 hover:bg-red-50"
                      >
                        Remover
                      </button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function FieldPicker({ schema, visibleFields, setVisibleFields, open, setOpen }) {
  const [busca, setBusca] = useState('')

  const opcoes = useMemo(() => {
    if (!schema) return []
    const termo = busca.toLowerCase()
    return schema.dados_basicos.filter((c) => c.label.toLowerCase().includes(termo))
  }, [schema, busca])

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="rounded border border-gray-300 px-3 py-1 text-sm hover:bg-gray-100"
      >
        Campos de dados básicos ({visibleFields.length})
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-9 z-20 w-72 rounded border border-gray-200 bg-white p-3 shadow-lg">
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

function SapPastePanel({ onParsed, onClose }) {
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
        Cole aqui as linhas copiadas do SAP (ZBPP009 ou relatório equivalente). Cada linha vira um material novo.
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
        <button type="button" onClick={onClose} className="rounded border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-100">
          Cancelar
        </button>
      </div>
    </div>
  )
}
