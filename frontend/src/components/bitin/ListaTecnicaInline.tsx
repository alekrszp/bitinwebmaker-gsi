import type { ItemListaTecnica, OperacaoListaTecnica } from '../../lib/types'

function linhaVazia(): ItemListaTecnica {
  return { operacao: 'alterar', codigo_filho: '', quantidade_de: '', quantidade_para: '' }
}

// Segunda entrada pra editar `material.alteracoes.lista_tecnica[]`, ao lado da página
// dedicada `ListaTecnicaPage.tsx` (2026-07-16, pedido do usuário: "coloque opção de fazer
// lista técnica na tela BITin, uma opção ao lado de campo alterado/nota"). Mesma ideia central
// já documentada em docs/FRONTEND.md ("as três telas não se complementam, fazem a mesma coisa
// de formas diferentes" -- aqui são QUATRO jeitos de chegar no mesmo `materiais[].alteracoes.
// lista_tecnica`, nenhum dependendo do outro): a página de Lista Técnica trabalha com todos os
// materiais numa grade plana com "código pai" livre; este componente já sabe qual material é
// (vem de dentro do `MaterialEditorCard`), então não precisa de código pai nem de agrupamento
// -- só a lista de componentes filhos deste material, com o mesmo formato de linha (operação/
// código filho/quantidade de/quantidade para).
//
// Propositalmente reaproveita o tipo `ItemListaTecnica` puro (sem o `codigo_pai` que
// `ListaTecnicaPage.tsx` adiciona só pra achatar a grade) -- aqui o "pai" já é implícito no
// material que contém este bloco.
export default function ListaTecnicaInline({
  itens,
  editavel,
  onChange,
}: {
  itens: ItemListaTecnica[]
  editavel: boolean
  onChange: (itens: ItemListaTecnica[]) => void
}) {
  // Sempre mostra uma linha em branco no final pra continuar preenchendo, igual ao padrão já
  // usado em ListaTecnicaPage.tsx/CodigosSapPage.tsx -- mas essa linha em branco nunca é
  // persistida (filtrada antes de chamar onChange, mesma regra de "linha fantasma" das outras
  // telas).
  const linhas = itens.length > 0 ? [...itens, linhaVazia()] : [linhaVazia()]

  function atualizarLinha(index: number, campo: keyof ItemListaTecnica, valor: string) {
    const copia = linhas.map((l, i) => (i === index ? { ...l, [campo]: valor } : l))
    onChange(copia.filter((l) => l.codigo_filho.trim() !== ''))
  }

  function removerLinha(index: number) {
    onChange(linhas.filter((_, i) => i !== index).filter((l) => l.codigo_filho.trim() !== ''))
  }

  if (!editavel) {
    if (itens.length === 0) return null
    return (
      <div className="mt-2 overflow-hidden rounded border border-line">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="bg-surface-alt text-xs uppercase tracking-wide text-ink-muted">
              <th className="px-3 py-2 font-medium">Operação</th>
              <th className="px-3 py-2 font-medium">Código filho</th>
              <th className="px-3 py-2 font-medium">Quantidade de</th>
              <th className="px-3 py-2 font-medium">Quantidade para</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {itens.map((item, i) => (
              <tr key={i}>
                <td className="px-3 py-2 capitalize text-ink">{item.operacao}</td>
                <td className="px-3 py-2 text-ink">{item.codigo_filho}</td>
                <td className="px-3 py-2 text-ink-muted">{item.quantidade_de || '—'}</td>
                <td className="px-3 py-2 text-ink-muted">{item.quantidade_para || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )
  }

  return (
    <div className="mt-2 overflow-x-auto rounded border border-line">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="bg-surface-alt text-xs uppercase tracking-wide text-ink-muted">
            <th className="whitespace-nowrap px-3 py-2 font-medium">Operação</th>
            <th className="whitespace-nowrap px-3 py-2 font-medium">Código filho</th>
            <th className="whitespace-nowrap px-3 py-2 font-medium">Quantidade de</th>
            <th className="whitespace-nowrap px-3 py-2 font-medium">Quantidade para</th>
            <th className="w-10" />
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {linhas.map((l, i) => (
            <tr key={i}>
              <td className="p-1.5">
                <select
                  value={l.operacao}
                  onChange={(e) => atualizarLinha(i, 'operacao', e.target.value as OperacaoListaTecnica)}
                  className="dark:[color-scheme:dark] [color-scheme:light] w-28 rounded border border-line bg-surface px-2 py-1.5 text-sm text-ink focus:border-brand-navy focus:outline-none"
                >
                  <option value="inserir">Inserir</option>
                  <option value="alterar">Alterar</option>
                  <option value="excluir">Excluir</option>
                </select>
              </td>
              <td className="p-1.5">
                <input
                  type="text"
                  value={l.codigo_filho}
                  onChange={(e) => atualizarLinha(i, 'codigo_filho', e.target.value)}
                  className="w-40 rounded border border-line bg-surface px-2 py-1.5 text-sm text-ink focus:border-brand-navy focus:outline-none"
                />
              </td>
              <td className="p-1.5">
                <input
                  type="text"
                  value={l.quantidade_de}
                  onChange={(e) => atualizarLinha(i, 'quantidade_de', e.target.value)}
                  disabled={l.operacao === 'inserir'}
                  className="w-28 rounded border border-line bg-surface px-2 py-1.5 text-sm text-ink focus:border-brand-navy focus:outline-none disabled:opacity-40"
                />
              </td>
              <td className="p-1.5">
                <input
                  type="text"
                  value={l.quantidade_para}
                  onChange={(e) => atualizarLinha(i, 'quantidade_para', e.target.value)}
                  disabled={l.operacao === 'excluir'}
                  className="w-28 rounded border border-line bg-surface px-2 py-1.5 text-sm text-ink focus:border-brand-navy focus:outline-none disabled:opacity-40"
                />
              </td>
              <td className="p-1.5 text-center">
                <button
                  type="button"
                  onClick={() => removerLinha(i)}
                  className="text-ink-faint hover:text-red-600"
                  aria-label="Remover linha"
                >
                  ×
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
