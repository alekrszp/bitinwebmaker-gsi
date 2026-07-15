import Card from '../Card'
import DetailField from '../DetailField'

interface ItemPedido {
  codigo_material: string
  quantidade: string
}

interface OrdemClienteItem {
  codigo: string
  descricao: string
  acrescentar_no_pedido: ItemPedido[]
  retira_do_pedido: ItemPedido[]
}

export default function OrdemClienteSection({ itens }: { itens: OrdemClienteItem[] }) {
  if (itens.length === 0) return null
  return (
    <Card title="Ordem de cliente">
      {itens.map((oc) => (
        <div key={oc.codigo} className="mt-4 first:mt-0">
          <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <DetailField label="Código" value={oc.codigo} />
            <DetailField label="Descrição" value={oc.descricao} />
          </dl>
          {oc.acrescentar_no_pedido.length > 0 && (
            <PedidoTable titulo="Acrescentar no pedido" itens={oc.acrescentar_no_pedido} />
          )}
          {oc.retira_do_pedido.length > 0 && <PedidoTable titulo="Retira do pedido" itens={oc.retira_do_pedido} />}
        </div>
      ))}
    </Card>
  )
}

function PedidoTable({ titulo, itens }: { titulo: string; itens: ItemPedido[] }) {
  return (
    <div className="mt-3">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-muted">{titulo}</h3>
      <div className="mt-2 overflow-hidden rounded border border-line">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="bg-surface-alt text-xs uppercase tracking-wide text-ink-muted">
              <th className="px-3 py-2 font-medium">Material</th>
              <th className="px-3 py-2 font-medium">Quantidade</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {itens.map((item, i) => (
              <tr key={`${item.codigo_material}-${i}`}>
                <td className="px-3 py-2 text-ink">{item.codigo_material}</td>
                <td className="px-3 py-2 text-ink-muted">{item.quantidade}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
