import { useMemo, useState } from 'react'
import { MODAL_ONLY_FIELDS, getCellValue, getDadosBasico, getImpacto, setCellValue, setDadosBasico, setImpacto } from '../lib/bitinFields'
import { buildErrorIndex, cellKey } from '../lib/bitinErrors'
import { matchesSearch } from '../lib/textSearch'

const IMPACTOS_ORDEM = ['alt', 'est', 'esp', 'lp', 'pre', 'oc', 'of']

// Painel de detalhes de um material -- atalho opcional, não obrigatório: a grade
// (MaterialGrid) já mostra todos os ~30 campos de dados_basicos como coluna por padrão (igual
// à planilha real do BITin). Aqui cada campo vira uma linha inteira com espaço de sobra e
// busca, útil pra revisar/editar um material sem precisar rolar a grade inteira.
export default function MaterialDetailModal({ material, schema, errors = [], rowIndex, onChange, onClose, disabled = false }) {
  const [busca, setBusca] = useState('')

  const { byCell } = useMemo(() => buildErrorIndex(errors), [errors])

  function errorMessageFor(group, field) {
    const errs = byCell.get(cellKey(rowIndex, group, field))
    return errs && errs.length > 0 ? errs.map((e) => e.message).join(' ') : null
  }

  const camposFiltrados = useMemo(() => {
    if (!schema) return []
    return schema.dados_basicos.filter((c) => matchesSearch(c.label, busca))
  }, [schema, busca])

  const impactosPorChave = useMemo(() => {
    const map = {}
    ;(schema?.impactos_operacionais || []).forEach((c) => {
      map[c.key] = c
    })
    return map
  }, [schema])

  const inputClass =
    'w-full rounded border bg-surface px-3 py-2 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-inset disabled:bg-surface-alt disabled:text-ink-faint'

  function fieldClass(errMsg) {
    return errMsg ? `${inputClass} border-red-400 bg-red-50 focus:ring-red-500` : `${inputClass} border-line focus:ring-brand-navy`
  }

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/50 p-4" onClick={onClose}>
      <div
        className="flex max-h-[90vh] w-full max-w-4xl flex-col rounded-lg bg-surface shadow-2xl"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        <div className="flex items-start justify-between border-b border-line px-6 py-4">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-ink-faint">Detalhes do material {rowIndex + 1}</p>
            <h3 className="text-lg font-semibold text-ink">
              {material.codigo_material || '(sem código)'}
              {material.descricao_material && <span className="font-normal text-ink-muted"> — {material.descricao_material}</span>}
            </h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded p-1.5 text-ink-faint hover:bg-surface-alt hover:text-ink"
            aria-label="Fechar"
          >
            ✕
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-5">
          <section className="mb-8">
            <h4 className="mb-3 text-sm font-semibold uppercase tracking-wide text-ink-muted">Identificação</h4>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
              {MODAL_ONLY_FIELDS.map((col) => {
                const errMsg = errorMessageFor('campo', col.field)
                if (col.type === 'checkbox') {
                  return (
                    <label key={col.field} className="flex items-center gap-2 pt-5">
                      <input
                        type="checkbox"
                        checked={!!getCellValue(material, col)}
                        disabled={disabled}
                        onChange={(e) => onChange(setCellValue(material, col, e.target.checked))}
                        className="h-4 w-4"
                      />
                      <span className="text-sm text-ink">{col.label}</span>
                    </label>
                  )
                }
                return (
                  <label key={col.field} className="block">
                    <span className="mb-1 block text-xs font-medium text-ink-muted">
                      {col.label}
                      {col.required && <span className="text-red-500"> *</span>}
                    </span>
                    <input
                      value={getCellValue(material, col)}
                      disabled={disabled}
                      onChange={(e) => onChange(setCellValue(material, col, e.target.value))}
                      className={fieldClass(errMsg)}
                      title={errMsg || undefined}
                    />
                    {errMsg && <p className="mt-1 text-xs text-red-600">{errMsg}</p>}
                  </label>
                )
              })}
            </div>
          </section>

          <section className="mb-8">
            <h4 className="mb-3 text-sm font-semibold uppercase tracking-wide text-ink-muted">Impactos operacionais</h4>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
              {IMPACTOS_ORDEM.map((key) => {
                const col = impactosPorChave[key]
                if (!col) return null
                const errMsg = errorMessageFor('impactos_operacionais', key)
                return (
                  <label key={key} className="block">
                    <span className="mb-1 block text-xs font-medium text-ink-muted">{col.label}</span>
                    <select
                      value={getImpacto(material, key) || '-'}
                      disabled={disabled}
                      onChange={(e) => onChange(setImpacto(material, key, e.target.value))}
                      className={fieldClass(errMsg)}
                      title={errMsg || undefined}
                    >
                      {col.options.map((opt) => (
                        <option key={opt} value={opt}>
                          {opt}
                        </option>
                      ))}
                    </select>
                    {errMsg && <p className="mt-1 text-xs text-red-600">{errMsg}</p>}
                  </label>
                )
              })}
              {['centro_custo', 'conta_razao'].map((key) => {
                const errMsg = errorMessageFor('impactos_operacionais', key)
                return (
                  <label key={key} className="block">
                    <span className="mb-1 block text-xs font-medium text-ink-muted">
                      {key === 'centro_custo' ? 'Centro de custo' : 'Conta razão'}
                      {getImpacto(material, 'est') === 'S' && <span className="text-red-500"> *</span>}
                    </span>
                    <input
                      value={getImpacto(material, key)}
                      disabled={disabled}
                      onChange={(e) => onChange(setImpacto(material, key, e.target.value))}
                      className={fieldClass(errMsg)}
                      title={errMsg || undefined}
                    />
                    {errMsg && <p className="mt-1 text-xs text-red-600">{errMsg}</p>}
                  </label>
                )
              })}
            </div>
          </section>

          <section>
            <div className="mb-3 flex items-center justify-between gap-3">
              <h4 className="text-sm font-semibold uppercase tracking-wide text-ink-muted">Dados básicos (Atual → Novo)</h4>
              <input
                value={busca}
                onChange={(e) => setBusca(e.target.value)}
                placeholder="Buscar campo..."
                className="w-56 rounded border border-line bg-surface px-2 py-1.5 text-sm text-ink focus:border-brand-navy focus:outline-none"
              />
            </div>
            <div className="overflow-hidden rounded border border-line">
              {/* "Novo"/Para em laranja da marca -- mesma ideia da planilha real do BITin (aba
                  "ZBPP009 + ALTERACAO", onde é vermelho), mas laranja aqui pra não se confundir
                  com o vermelho de erro de validação usado nesta mesma tela. */}
              <div className="grid grid-cols-[1.2fr_1fr_1fr] gap-3 bg-surface-header px-3 py-2 text-xs font-medium uppercase tracking-wide">
                <span className="text-ink-muted">Campo</span>
                <span className="text-ink-muted">Atual</span>
                <span className="text-brand-orange">Novo</span>
              </div>
              <div className="divide-y divide-line">
                {camposFiltrados.map((campo) => {
                  const errMsg = errorMessageFor('dados_basicos', campo.key)
                  return (
                    <div key={campo.key} className={`grid grid-cols-[1.2fr_1fr_1fr] items-center gap-3 px-3 py-2 ${errMsg ? 'bg-red-50' : ''}`}>
                      <span className="text-sm text-ink">{campo.label}</span>
                      <input
                        value={getDadosBasico(material, campo.key, 'de')}
                        disabled={disabled}
                        onChange={(e) => onChange(setDadosBasico(material, campo.key, 'de', e.target.value))}
                        className={fieldClass(errMsg)}
                        title={errMsg || undefined}
                      />
                      <input
                        value={getDadosBasico(material, campo.key, 'para')}
                        disabled={disabled}
                        onChange={(e) => onChange(setDadosBasico(material, campo.key, 'para', e.target.value))}
                        className={fieldClass(errMsg)}
                        title={errMsg || undefined}
                      />
                    </div>
                  )
                })}
                {camposFiltrados.length === 0 && <p className="px-3 py-4 text-sm text-ink-faint">Nenhum campo encontrado.</p>}
              </div>
            </div>
          </section>
        </div>

        <div className="flex justify-end border-t border-line px-6 py-3">
          <button
            type="button"
            onClick={onClose}
            className="rounded bg-brand-navy px-4 py-2 text-sm font-medium text-white hover:bg-brand-navy-dark"
          >
            Fechar
          </button>
        </div>
      </div>
    </div>
  )
}
