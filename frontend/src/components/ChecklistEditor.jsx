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
    // Volta a ser uma tabela de verdade (não grade de cards): a print real mandada pelo
    // usuário mostra Documento/Afeta/Observação como 3 colunas de largura fixa, uma linha por
    // item, todas com a mesma altura -- exatamente o que <table> garante "de graça" e o que a
    // tentativa anterior (cards em grid, altura variável conforme Observação aparecia ou não)
    // quebrava ("colunas desiguais").
    <div className="overflow-hidden border-y border-line">
      <div className="bg-red-900 py-1.5 text-center text-sm font-bold uppercase tracking-widest text-white">
        Check list
      </div>
      <table className="w-full table-fixed text-sm">
        <thead>
          <tr className="bg-surface-header text-left text-xs font-semibold uppercase tracking-wide text-ink-muted">
            <th className="w-2/5 px-3 py-2">Documento</th>
            <th className="w-24 px-3 py-2 text-center">Afeta</th>
            <th className="px-3 py-2">Observação</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {items.map((item) => {
            const valor = checklist.find((c) => c.id === item.id) ?? { afeta: false, descricao: '' }
            return (
              <tr key={item.id} className="bg-surface">
                <td className="px-3 py-1.5 text-ink">{item.etapa}</td>
                <td className="px-3 py-1.5 text-center">
                  <select
                    value={valor.afeta ? 'SIM' : 'NÃO'}
                    disabled={disabled}
                    onChange={(e) => updateItem(item.id, 'afeta', e.target.value === 'SIM')}
                    className={`w-full rounded border bg-surface px-2 py-1 text-center text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-brand-navy ${
                      valor.afeta ? 'border-brand-orange text-brand-orange' : 'border-line text-ink-muted'
                    }`}
                  >
                    <option value="NÃO">NÃO</option>
                    <option value="SIM">SIM</option>
                  </select>
                </td>
                <td className="px-3 py-1.5">
                  <input
                    value={valor.descricao}
                    disabled={disabled}
                    onChange={(e) => updateItem(item.id, 'descricao', e.target.value)}
                    className="w-full rounded border border-line bg-surface px-2 py-1 text-ink focus:border-brand-navy focus:outline-none"
                  />
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
