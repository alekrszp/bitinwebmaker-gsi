import { memo, useEffect, useState } from 'react'

// Célula de descrição memoizada com estado local (2026-07-17, corrige bug real: o input
// mostrava `item.descricao` (vem de `resumo.checklist`, só atualizado depois de um save+
// refetch), mas `onDescricaoChange` só gravava num estado LOCAL separado
// (`checklistDescricoes` em BitinDetail.tsx) que nunca realimentava `resumo` -- ou seja, o
// valor exibido nunca refletia o que era digitado, fazendo o campo parecer travado/brigando
// consigo mesmo a cada tecla ("não tá sendo instantâneo"). Estado local aqui resolve os dois
// problemas de uma vez: exibe o que foi digitado imediatamente (sem depender de `resumo`
// estar sincronizado) e só propaga pro estado do pai no blur (não a cada tecla, mesmo padrão
// de CodigosSapPage.tsx/ListaTecnicaPage.tsx).
const DescricaoInput = memo(function DescricaoInput({
  valor,
  onCommit,
}: {
  valor: string
  onCommit: (novoValor: string) => void
}) {
  const [local, setLocal] = useState(valor)
  useEffect(() => setLocal(valor), [valor])
  return (
    <input
      type="text"
      value={local}
      onChange={(e) => setLocal(e.target.value)}
      onBlur={() => {
        if (local !== valor) onCommit(local)
      }}
      placeholder="Anotação (ex.: centro de custo, conta razão)..."
      className="mt-1.5 w-full rounded border border-line bg-surface px-2 py-1 text-xs text-ink placeholder:text-ink-faint focus:border-brand-navy focus:outline-none"
    />
  )
})

interface ChecklistItem {
  id: string
  etapa: string
  afeta: boolean
  manual: boolean
  descricao: string
}

// Os 22 itens fixos do checklist (Quadro 01 do POP). Na visualização (rascunho ou enviado),
// mostra só as etapas afetadas (afeta=true) -- na edição, mostra as 22 (o engenheiro precisa
// ver o efeito de cada campo preenchido em todo o checklist, não só no que já ficou "sim"),
// decisão do usuário, 2026-07-14. Coluna única no canto esquerdo, com espaço à direita de cada
// linha -- no documento original essa área fica livre pra anotação manual. Usa os tokens
// highlight-* (index.css), pensados pra funcionar bem nos dois temas.
//
// Clicável em edição (2026-07-15): checklist 100% manual -- nenhum item é sugerido a partir
// dos materiais, o engenheiro precisa clicar em cada item que se aplica pra marcar "Sim" (decisão
// do usuário, 2026-07-15: "checklist é marcada manualmente"). Os setores acionados sempre
// refletem o estado marcado manualmente, ver scripts/bitin_document.py::build_checklist. Item
// já clicado ganha um marcador "•" (mesmo que o clique tenha voltado pra "Não" -- indica que o
// engenheiro já revisou aquele item, distinto de "nunca tocado").
//
// Descrição por item (2026-07-15): quando um item está "Sim" e a tela é editável, aparece um
// campo de anotação livre abaixo -- usado principalmente no item 22 ("Centro de custo (se tem
// sucata)") pra registrar centro de custo/conta razão (POP Nota 8, que saiu do bloco do
// material e virou anotação aqui, decisão do usuário). Fica fora do <button> de toggle (dois
// elementos interativos separados), senão clicar no campo de texto also alternaria o item.
//
// Grade lado a lado (2026-07-15, decisão do usuário: "pode mudar o layout deles, colocar um
// do lado do outro, assim diminui o scroll da tela") -- itens em grid responsivo (1 coluna no
// mobile, 2 no tablet, 3 em telas largas) em vez de empilhados numa coluna só. Cada item é uma
// célula independente (`self-start`), então um item com descrição aberta não estica a altura
// dos vizinhos na mesma linha.
export default function ChecklistTable({
  checklist,
  modo = 'so-sim',
  onToggle,
  onDescricaoChange,
}: {
  checklist: ChecklistItem[]
  modo?: 'so-sim' | 'todas'
  onToggle?: (id: string, afeta: boolean) => void
  onDescricaoChange?: (id: string, descricao: string) => void
}) {
  const itens = modo === 'todas' ? checklist : checklist.filter((item) => item.afeta)

  if (itens.length === 0) {
    return <p className="text-sm text-ink-muted">Nenhuma etapa afetada.</p>
  }

  return (
    <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-2 xl:grid-cols-3">
      {itens.map((item) => {
        const conteudo = (
          <>
            <span className={`text-sm font-medium ${item.afeta ? 'text-highlight-text' : 'text-ink-muted'}`}>
              {item.manual && <span title="Definido manualmente">• </span>}
              {item.etapa}
            </span>
            <span
              className={`text-[0.65rem] font-bold uppercase tracking-wide ${
                item.afeta ? 'text-highlight-text/70' : 'text-ink-faint'
              }`}
            >
              {item.afeta ? 'Sim' : 'Não'}
            </span>
          </>
        )
        const classes = `self-start rounded border px-3 py-2 ${item.afeta ? 'border-highlight-border bg-highlight-bg' : 'border-line'}`
        const mostrarDescricao = item.afeta && (onDescricaoChange ? true : item.descricao !== '')

        return (
          <div key={item.id} className={classes}>
            {onToggle ? (
              <button
                type="button"
                onClick={() => onToggle(item.id, !item.afeta)}
                className="flex w-full cursor-pointer items-center justify-between text-left transition-colors hover:brightness-95"
              >
                {conteudo}
              </button>
            ) : (
              <div className="flex w-full items-center justify-between">{conteudo}</div>
            )}
            {mostrarDescricao &&
              (onDescricaoChange ? (
                <DescricaoInput valor={item.descricao} onCommit={(valor) => onDescricaoChange(item.id, valor)} />
              ) : (
                <p className="mt-1.5 text-xs text-ink-muted">{item.descricao}</p>
              ))}
          </div>
        )
      })}
    </div>
  )
}
