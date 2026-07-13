import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { blankChecklist } from '../lib/bitinFields'

// Checklist do BITin -- réplica da faixa "CHECK LIST" da planilha real (aba "Template
// apresentação"): banner vermelho escuro, tabela Documento/Afeta/Observação, 22 itens fixos
// do POP. "Afeta" fica livre pro engenheiro marcar aqui (SIM/NÃO) -- o cálculo automático a
// partir dos impactos declarados por material (Módulo4/build_checklist, usado na tela de
// resumo pós-envio) é um jeito diferente de preencher a mesma informação, não implementado
// aqui ainda (ver docs/FRONTEND.md).
export default function ChecklistEditor({ checklist, onChange, disabled = false }) {
  const [items, setItems] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelado = false
    api
      .get('/bitins/schema/checklist')
      .then((resp) => {
        if (cancelado) return
        setItems(resp.data.items)
        if (checklist.length === 0) onChange(blankChecklist(resp.data.items))
      })
      .catch(() => {
        if (!cancelado) setError('Não foi possível carregar o checklist.')
      })
    return () => {
      cancelado = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function updateItem(id, campo, valor) {
    onChange(checklist.map((item) => (item.id === id ? { ...item, [campo]: valor } : item)))
  }

  if (error) return <p className="text-sm text-red-600">{error}</p>
  if (!items) return null

  return (
    // Sem cantos arredondados/borda lateral de propósito -- a faixa encosta nas bordas reais
    // da tela, mesmo tratamento do cabeçalho e da grade de materiais (ver BitinDetail.jsx).
    <div className="overflow-hidden border-y border-line">
      <div className="bg-red-900 py-1.5 text-center text-sm font-bold uppercase tracking-widest text-white">
        Check list
      </div>
      {/* Grade em colunas (não lista de 22 linhas empilhadas) -- a faixa de checklist não pode
          "descer demais" a tela e empurrar a grade de materiais pra fora da dobra. Observação
          só aparece quando o item afeta (SIM): reduz ainda mais a altura já que a maioria dos
          itens tende a ficar "NÃO", e escrever observação sem afetar não faz sentido. */}
      <div className="grid grid-cols-1 gap-px bg-line sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
        {items.map((item) => {
          const valor = checklist.find((c) => c.id === item.id) ?? { afeta: false, descricao: '' }
          return (
            <div key={item.id} className="bg-surface px-3 py-2">
              <div className="flex items-center gap-2">
                <span className="flex-1 text-sm text-ink">{item.etapa}</span>
                <select
                  value={valor.afeta ? 'SIM' : 'NÃO'}
                  disabled={disabled}
                  onChange={(e) => updateItem(item.id, 'afeta', e.target.value === 'SIM')}
                  className={`shrink-0 rounded border bg-surface px-2 py-1 text-center text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-brand-navy ${
                    valor.afeta ? 'border-brand-orange text-brand-orange' : 'border-line text-ink-muted'
                  }`}
                >
                  <option value="NÃO">NÃO</option>
                  <option value="SIM">SIM</option>
                </select>
              </div>
              {valor.afeta && (
                <input
                  value={valor.descricao}
                  disabled={disabled}
                  placeholder="Observação..."
                  onChange={(e) => updateItem(item.id, 'descricao', e.target.value)}
                  className="mt-1.5 w-full rounded border border-line bg-surface px-2 py-1 text-xs text-ink focus:border-brand-navy focus:outline-none"
                />
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
