import Card from '../Card'
import TextInput from '../TextInput'
import { ordemClienteVazia } from '../../lib/bitinDefaults'
import type { ItemPedidoEditavel, OrdemClienteEditavel } from '../../lib/types'

// Formulário editável de "Ordem de cliente" (2026-07-20, achado real: existia validação de
// envio pra isso -- POP Nota 10, material com OC="X" exige entrada correspondente aqui -- mas
// nenhum jeito de preencher pela tela, só a exibição só-leitura pós-envio
// (OrdemClienteSection.tsx). Sem esta tela, era impossível enviar um BITin com OC="X".
//
// Estrutura por entrada (mesma validação de scripts/bitin_model.py::validate_ordem_cliente):
// código obrigatório, e pelo menos 1 item em "acrescentar no pedido" OU "retira do pedido"
// (uma entrada sem nenhum dos dois é erro de envio -- "ordem_cliente_sem_itens").
//
// Poucas entradas/itens na prática (não é uma grade de centenas de linhas como Lista Técnica)
// -- inputs controlados direto, sem o padrão de estado-local-com-commit-no-blur usado em
// grades maiores (ListaTecnicaInline.tsx/CodigosSapPage.tsx), que existe pra evitar
// re-render de muitas linhas a cada tecla; aqui o custo é irrelevante.
export default function OrdemClienteEditor({
  itens,
  editavel,
  onChange,
}: {
  itens: OrdemClienteEditavel[]
  editavel: boolean
  onChange: (itens: OrdemClienteEditavel[]) => void
}) {
  if (!editavel) return null // versão só-leitura pós-envio é OrdemClienteSection.tsx

  function atualizarEntrada(idx: number, patch: Partial<OrdemClienteEditavel>) {
    onChange(itens.map((it, i) => (i === idx ? { ...it, ...patch } : it)))
  }

  function removerEntrada(idx: number) {
    onChange(itens.filter((_, i) => i !== idx))
  }

  function adicionarEntrada() {
    onChange([...itens, ordemClienteVazia()])
  }

  return (
    <Card title="Ordem de cliente">
      <p className="mt-1 text-xs text-ink-muted">
        Só preencher se algum material afeta Ordem de Cliente (OC = "X" na checklist de impactos). Cada entrada
        precisa de um código e pelo menos um item pra acrescentar ou retirar do pedido.
      </p>

      {itens.length === 0 && <p className="mt-3 text-sm text-ink-faint">Nenhuma entrada ainda.</p>}

      {itens.map((entrada, idx) => (
        <div key={idx} className="mt-4 rounded-lg border border-line p-4 first:mt-3">
          <div className="flex items-start justify-between gap-3">
            <div className="grid flex-1 grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-ink-muted">
                  Código *
                </label>
                <TextInput
                  value={entrada.codigo}
                  onChange={(e) => atualizarEntrada(idx, { codigo: e.target.value })}
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-ink-muted">
                  Descrição
                </label>
                <TextInput
                  value={entrada.descricao}
                  onChange={(e) => atualizarEntrada(idx, { descricao: e.target.value })}
                />
              </div>
            </div>
            <button
              type="button"
              onClick={() => removerEntrada(idx)}
              className="mt-6 text-ink-faint hover:text-red-600"
              aria-label="Remover entrada de ordem de cliente"
              title="Remover entrada"
            >
              ×
            </button>
          </div>

          <PedidoEditor
            titulo="Acrescentar no pedido"
            itens={entrada.acrescentar_no_pedido}
            onChange={(novosItens) => atualizarEntrada(idx, { acrescentar_no_pedido: novosItens })}
          />
          <PedidoEditor
            titulo="Retira do pedido"
            itens={entrada.retira_do_pedido}
            onChange={(novosItens) => atualizarEntrada(idx, { retira_do_pedido: novosItens })}
          />
        </div>
      ))}

      <button
        type="button"
        onClick={adicionarEntrada}
        className="mt-4 rounded-lg border border-dashed border-line px-4 py-2 text-sm font-medium text-ink-muted hover:bg-surface-alt"
      >
        + Nova entrada
      </button>
    </Card>
  )
}

function PedidoEditor({
  titulo,
  itens,
  onChange,
}: {
  titulo: string
  itens: ItemPedidoEditavel[]
  onChange: (itens: ItemPedidoEditavel[]) => void
}) {
  function atualizarItem(idx: number, patch: Partial<ItemPedidoEditavel>) {
    onChange(itens.map((it, i) => (i === idx ? { ...it, ...patch } : it)))
  }

  function removerItem(idx: number) {
    onChange(itens.filter((_, i) => i !== idx))
  }

  function adicionarItem() {
    onChange([...itens, { codigo_material: '', quantidade: '' }])
  }

  return (
    <div className="mt-3">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-muted">{titulo}</h3>
      <div className="mt-2 space-y-2">
        {itens.map((item, idx) => (
          <div key={idx} className="flex items-center gap-2">
            <div className="flex-1">
              <TextInput
                placeholder="Código material"
                value={item.codigo_material}
                onChange={(e) => atualizarItem(idx, { codigo_material: e.target.value })}
              />
            </div>
            <input
              type="text"
              inputMode="decimal"
              placeholder="Quantidade"
              value={item.quantidade}
              onChange={(e) => atualizarItem(idx, { quantidade: e.target.value.replace(/[^0-9.]/g, '') })}
              className="w-28 rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink focus:border-brand-navy focus:outline-none focus:ring-2 focus:ring-brand-navy/20"
            />
            <button
              type="button"
              onClick={() => removerItem(idx)}
              className="text-ink-faint hover:text-red-600"
              aria-label="Remover item"
            >
              ×
            </button>
          </div>
        ))}
      </div>
      <button
        type="button"
        onClick={adicionarItem}
        className="mt-2 text-xs font-medium text-ink-muted hover:text-ink hover:underline"
      >
        + Item
      </button>
    </div>
  )
}
