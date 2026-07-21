import { statusDoBitin } from '../../lib/bitinEtapa'

// Selo de STATUS de um BITin -- usado em MeusBitins.tsx/CadastroPage.tsx/ProcessosPage.tsx/
// PainelGeral.tsx (coluna Status) e BitinDetail.tsx (cabeçalho). Único lugar que decide as
// cores rascunho/enviado/concluído, pra não divergir entre telas (2026-07-20, pedido
// explícito: "painel geral e a tela de cadastro e processos devem conversar na mesma
// língua"). "Concluído" (2026-07-20, ver lib/bitinEtapa.ts::statusDoBitin) é status, não
// etapa -- `windchillEnviado` é opcional só pra não quebrar call sites que ainda não têm o
// BITin inteiro à mão (ex.: cabeçalhos que só sabem o `status` bruto).
export default function StatusBadge({ status, windchillEnviado }: { status: string; windchillEnviado?: boolean }) {
  const rotulo = statusDoBitin({ status, windchill_enviado: windchillEnviado ?? false })
  const classesPorRotulo: Record<string, string> = {
    Rascunho: 'bg-brand-gold/15 text-brand-gold',
    Enviado: 'bg-brand-green/15 text-brand-green',
    Concluído: 'bg-brand-navy/15 text-brand-navy',
  }
  return (
    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${classesPorRotulo[rotulo]}`}>
      {rotulo}
    </span>
  )
}
