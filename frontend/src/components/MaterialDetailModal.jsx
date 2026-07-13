import { useMemo, useState } from 'react'
import { getDadosBasico, getImpacto, setDadosBasico, setImpacto } from '../lib/bitinFields'
import { buildErrorIndex, cellKey } from '../lib/bitinErrors'
import { matchesSearch } from '../lib/textSearch'

const IMPACTOS_ORDEM = ['alt', 'est', 'esp', 'lp', 'pre', 'oc', 'of']

// Painel de detalhes de um material -- existe porque a grade (MaterialGrid) fica
// impraticável se tentar mostrar os ~30 campos de dados_basicos ao mesmo tempo (célula de
// planilha é ruim pra texto longo e rótulo). Aqui cada campo tem uma linha inteira, com
// espaço de sobra -- é o lugar recomendado pra edição cuidadosa; a grade continua útil pra
// visão geral e colar em bloco dos campos que o usuário decidir fixar como coluna.
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
    'w-full rounded border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-inset disabled:bg-gray-50 disabled:text-gray-400'

  function fieldClass(errMsg) {
    return errMsg ? `${inputClass} border-red-400 bg-red-50 focus:ring-red-500` : `${inputClass} border-gray-300 focus:ring-brand-navy`
  }

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div
        className="flex max-h-[90vh] w-full max-w-4xl flex-col rounded-lg bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        <div className="flex items-start justify-between border-b border-gray-200 px-6 py-4">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-gray-400">Detalhes do material {rowIndex + 1}</p>
            <h3 className="text-lg font-semibold text-gray-900">
              {material.codigo_material || '(sem código)'}
              {material.descricao_material && <span className="font-normal text-gray-500"> — {material.descricao_material}</span>}
            </h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-700"
            aria-label="Fechar"
          >
            ✕
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-5">
          <section className="mb-8">
            <h4 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">Impactos operacionais</h4>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
              {IMPACTOS_ORDEM.map((key) => {
                const col = impactosPorChave[key]
                if (!col) return null
                const errMsg = errorMessageFor('impactos_operacionais', key)
                return (
                  <label key={key} className="block">
                    <span className="mb-1 block text-xs font-medium text-gray-600">{col.label}</span>
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
                    <span className="mb-1 block text-xs font-medium text-gray-600">
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
              <h4 className="text-sm font-semibold uppercase tracking-wide text-gray-500">Dados básicos (De → Para)</h4>
              <input
                value={busca}
                onChange={(e) => setBusca(e.target.value)}
                placeholder="Buscar campo..."
                className="w-56 rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-brand-navy focus:outline-none"
              />
            </div>
            <div className="overflow-hidden rounded border border-gray-200">
              {/* "Novo"/Para em laranja da marca -- mesma ideia da planilha real do BITin (aba
                  "ZBPP009 + ALTERACAO", onde é vermelho), mas laranja aqui pra não se confundir
                  com o vermelho de erro de validação usado nesta mesma tela. */}
              <div className="grid grid-cols-[1.2fr_1fr_1fr] gap-3 bg-brand-navy-50 px-3 py-2 text-xs font-medium uppercase tracking-wide">
                <span className="text-brand-navy/60">Campo</span>
                <span className="text-brand-navy/60">Atual</span>
                <span className="text-brand-orange">Novo</span>
              </div>
              <div className="divide-y divide-gray-100">
                {camposFiltrados.map((campo) => {
                  const errMsg = errorMessageFor('dados_basicos', campo.key)
                  return (
                    <div key={campo.key} className={`grid grid-cols-[1.2fr_1fr_1fr] items-center gap-3 px-3 py-2 ${errMsg ? 'bg-red-50' : ''}`}>
                      <span className="text-sm text-gray-700">{campo.label}</span>
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
                {camposFiltrados.length === 0 && <p className="px-3 py-4 text-sm text-gray-400">Nenhum campo encontrado.</p>}
              </div>
            </div>
          </section>
        </div>

        <div className="flex justify-end border-t border-gray-200 px-6 py-3">
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
