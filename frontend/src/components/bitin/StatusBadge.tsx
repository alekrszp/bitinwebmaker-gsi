// Selo de status de um BITin -- usado em MeusBitins.tsx (coluna Status) e BitinDetail.tsx
// (cabeçalho). Único lugar que decide as cores rascunho/enviado, pra não divergir entre telas.
export default function StatusBadge({ status }: { status: string }) {
  const enviado = status === 'enviado'
  return (
    <span
      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${
        enviado ? 'bg-brand-green/15 text-brand-green' : 'bg-brand-gold/15 text-brand-gold'
      }`}
    >
      {enviado ? 'Enviado' : 'Rascunho'}
    </span>
  )
}
