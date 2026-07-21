import { memo, useEffect, useState, type ChangeEvent } from 'react'
import type { ItemListaTecnica, OperacaoListaTecnica } from '../../lib/types'

function linhaVazia(): ItemListaTecnica {
  return { operacao: 'alterar', codigo_filho: '', quantidade_de: '', quantidade_para: '' }
}

// Campo "Operação" removido da UI (2026-07-17, pedido explícito: "tira o campo operação é
// desnecessário", mesma mudança em ListaTecnicaPage.tsx) -- mas o backend/export
// (scripts/lista_tecnica_export.py) ainda precisa dele pra validar e marcar a coluna certa
// (X) na planilha Winshuttle. Deriva sozinho a partir de qual quantidade foi preenchida:
// - só "para" preenchido (De vazio) -- item novo, ainda não existia -- Inserir.
// - só "de" preenchido (Para vazio) -- item removido -- Excluir.
// - os dois preenchidos (ou nenhum, linha em branco filtrada antes) -- Alterar.
function derivarOperacao(item: ItemListaTecnica): OperacaoListaTecnica {
  const temDe = item.quantidade_de.trim() !== ''
  const temPara = item.quantidade_para.trim() !== ''
  if (!temDe && temPara) return 'inserir'
  if (temDe && !temPara) return 'excluir'
  return 'alterar'
}

// `_id` client-side estável por linha (2026-07-17, otimização de performance -- mesmo padrão
// de CodigosSapPage.tsx/BitinDetail.tsx) -- `key={i}` perdia a identidade da linha ao remover
// uma no meio da lista.
type LinhaComId = ItemListaTecnica & { _id: string }

// Célula de texto memoizada com estado local (2026-07-17, mesmo padrão de CodigosSapPage.tsx/
// CodeTableCell do frontend antigo) -- digitar só propaga pro estado no blur, não a cada tecla.
const CelulaTexto = memo(function CelulaTexto({
  valor,
  onCommit,
  numerico,
  className,
}: {
  valor: string
  onCommit: (novoValor: string) => void
  // Quantidade aceita só número (2026-07-17, pedido explícito: "deixa o campo aberto
  // aceitando só números"). `type="number"` (tentativa anterior) foi revertido -- pedido
  // explícito: "esse seletor aí ficou um lixo" (as setinhas de incremento/decremento do
  // input nativo). `type="text"` + filtro no onChange (só dígitos, um "." opcional) +
  // `inputMode="decimal"` -- mantém teclado numérico no celular sem o visual de spinner.
  numerico?: boolean
  className: string
}) {
  const [local, setLocal] = useState(valor)
  useEffect(() => setLocal(valor), [valor])
  return (
    <input
      type="text"
      inputMode={numerico ? 'decimal' : undefined}
      value={local}
      onChange={(e: ChangeEvent<HTMLInputElement>) =>
        setLocal(numerico ? e.target.value.replace(/[^0-9.]/g, '') : e.target.value)
      }
      onBlur={() => {
        if (local !== valor) onCommit(local)
      }}
      className={className}
    />
  )
})

// Linha memoizada (2026-07-17) -- `linha` só muda de referência quando ela mesma é editada
// (atualizarLinha usa `.map` que preserva a referência das linhas não tocadas).
const LinhaItem = memo(function LinhaItem({
  linha,
  onCampoCommit,
  onRemover,
}: {
  linha: LinhaComId
  onCampoCommit: (id: string, campo: keyof ItemListaTecnica, valor: string) => void
  onRemover: (id: string) => void
}) {
  const classeInput =
    'w-40 rounded border border-line bg-surface px-2 py-1.5 text-sm text-ink focus:border-brand-navy focus:outline-none'
  return (
    <tr>
      <td className="p-1.5">
        <CelulaTexto
          valor={linha.codigo_filho}
          onCommit={(valor) => onCampoCommit(linha._id, 'codigo_filho', valor)}
          className={classeInput}
        />
      </td>
      <td className="p-1.5">
        <CelulaTexto
          valor={linha.quantidade_de}
          onCommit={(valor) => onCampoCommit(linha._id, 'quantidade_de', valor)}
          numerico
          className="w-28 rounded border border-line bg-surface px-2 py-1.5 text-sm text-ink focus:border-brand-navy focus:outline-none"
        />
      </td>
      <td className="p-1.5">
        <CelulaTexto
          valor={linha.quantidade_para}
          onCommit={(valor) => onCampoCommit(linha._id, 'quantidade_para', valor)}
          numerico
          className="w-28 rounded border border-line bg-surface px-2 py-1.5 text-sm text-ink focus:border-brand-navy focus:outline-none"
        />
      </td>
      <td className="p-1.5 text-center">
        <button
          type="button"
          onClick={() => onRemover(linha._id)}
          className="text-ink-faint hover:text-red-600"
          aria-label="Remover linha"
        >
          ×
        </button>
      </td>
    </tr>
  )
})

// Segunda entrada pra editar `material.alteracoes.lista_tecnica[]`, ao lado da página
// dedicada `ListaTecnicaPage.tsx` (2026-07-16, pedido do usuário: "coloque opção de fazer
// lista técnica na tela BITin, uma opção ao lado de campo alterado/nota"). Mesma ideia central
// já documentada em docs/FRONTEND.md ("as três telas não se complementam, fazem a mesma coisa
// de formas diferentes" -- aqui são QUATRO jeitos de chegar no mesmo `materiais[].alteracoes.
// lista_tecnica`, nenhum dependendo do outro): a página de Lista Técnica trabalha com todos os
// materiais numa grade plana com "código pai" livre; este componente já sabe qual material é
// (vem de dentro do `MaterialEditorCard`), então não precisa de código pai nem de agrupamento
// -- só a lista de componentes filhos deste material, com o mesmo formato de linha (código
// filho/quantidade de/quantidade para -- "operação" é derivada, ver derivarOperacao acima).
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
  // `linhas` (com `_id`) é estado LOCAL, inicializado uma vez de `itens` (2026-07-17) -- não
  // ressincroniza a cada mudança de `itens`, de propósito: esta instância do componente é a
  // ÚNICA origem de mudanças em `itens` enquanto estiver montada (MateriaisSection já dá um
  // ListaTecnicaInline por material, remontado do zero se o material trocar -- ver `key`
  // em MateriaisSection.tsx), então o valor que volta via prop depois de `onChange` é sempre
  // eco do que este componente acabou de mandar. Gerar um `_id` NOVO a cada render a partir de
  // `itens` (useMemo com `itens` como dep) quebraria a memoização de LinhaItem -- toda linha
  // ganharia um id novo (e um remount) a cada commit, mesmo as não tocadas.
  const [linhas, setLinhas] = useState<LinhaComId[]>(() =>
    itens.map((l) => ({ ...l, _id: crypto.randomUUID() })),
  )

  // SEM linha em branco automática (removido em 2026-07-20 -- bug real: a linha em branco do
  // final era recriada a cada commit, então clicar "×" nela não tinha efeito nenhum visível,
  // parecia "impossível excluir"). Agora só existe a linha que o próprio engenheiro pediu
  // ("+ Nova linha", abaixo) -- excluir remove de verdade.
  function commit(novasLinhas: LinhaComId[]) {
    setLinhas(novasLinhas)
    const semVazias = novasLinhas.filter((l) => l.codigo_filho.trim() !== '')
    // Operação derivada aqui (2026-07-17, campo removido da UI) -- ver derivarOperacao.
    onChange(semVazias.map(({ _id, ...resto }) => ({ ...resto, operacao: derivarOperacao(resto) })))
  }

  function atualizarCampo(id: string, campo: keyof ItemListaTecnica, valor: string) {
    commit(linhas.map((l) => (l._id === id ? { ...l, [campo]: valor } : l)))
  }

  function removerLinha(id: string) {
    commit(linhas.filter((l) => l._id !== id))
  }

  function adicionarLinha() {
    setLinhas([...linhas, { ...linhaVazia(), _id: crypto.randomUUID() }])
  }

  if (!editavel) {
    if (itens.length === 0) return null
    return (
      <div className="mt-2 overflow-hidden rounded border border-line">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="bg-surface-alt text-xs uppercase tracking-wide text-ink-muted">
              <th className="px-3 py-2 font-medium">Código filho</th>
              <th className="px-3 py-2 font-medium">Quantidade de</th>
              <th className="px-3 py-2 font-medium">Quantidade para</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {itens.map((item, i) => (
              <tr key={i}>
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
            <th className="whitespace-nowrap px-3 py-2 font-medium">Código filho</th>
            <th className="whitespace-nowrap px-3 py-2 font-medium">Quantidade de</th>
            <th className="whitespace-nowrap px-3 py-2 font-medium">Quantidade para</th>
            <th className="w-10" />
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {linhas.map((l) => (
            <LinhaItem key={l._id} linha={l} onCampoCommit={atualizarCampo} onRemover={removerLinha} />
          ))}
        </tbody>
      </table>
      <button
        type="button"
        onClick={adicionarLinha}
        className="w-full border-t border-line px-3 py-1.5 text-left text-xs font-medium text-ink-muted hover:bg-surface-alt"
      >
        + Nova linha
      </button>
    </div>
  )
}
