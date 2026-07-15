// Cores da própria identidade visual (hexágonos da logo, ver frontend/public/logo.svg):
// Armazenagem de Grãos = verde (hexágono da folha/grão), Proteína Animal = laranja (hexágono
// do porco) -- amarelo (galinha) ficou de fora de propósito pra não colidir com o destaque
// amarelo do checklist (ver ChecklistTable), que já usa esse tom na mesma tela.
export default function SetorBadge({ setor }: { setor: string }) {
  const armazenagem = setor === 'Armazenagem de Grãos'
  return (
    <span
      className={`inline-block rounded px-2 py-0.5 text-sm font-medium ${
        armazenagem ? 'bg-brand-green/20 text-brand-green' : 'bg-brand-orange/20 text-brand-orange'
      }`}
    >
      {setor || '—'}
    </span>
  )
}
