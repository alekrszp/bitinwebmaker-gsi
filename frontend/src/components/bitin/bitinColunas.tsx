import type { ReactNode } from 'react'
import StatusBadge from './StatusBadge'
import { inicioDaEtapa, paradoHaMuitoTempo, tempoDecorrido } from '../../lib/tempoParado'
import type { Bitin } from '../../lib/types'

// Tipo/constante de coluna separados de BitinTableSection.tsx (2026-07-21) -- arquivo só de
// componente evita o aviso de fast-refresh do oxlint (react/only-export-components) por
// misturar componente + constante/tipo no mesmo módulo.
export interface BitinColuna {
  header: string
  /** Célula da linha para este BITin. */
  render: (b: Bitin) => ReactNode
  /** false pra célula que não deve virar link pro BITin (raro -- default é sempre linkar). */
  link?: boolean
  className?: string
}

// Colunas padrão (Número/Motivo/Solicitante/Status) repetidas em quase toda tela de listagem
// -- páginas com necessidade extra (ex.: Etapa em ProcessosPage) compõem a partir daqui.
export const COLUNAS_PADRAO_BITIN: BitinColuna[] = [
  { header: 'Número', render: (b) => b.codigo ?? '—', className: 'text-ink hover:underline' },
  { header: 'Motivo', render: (b) => String(b.content?.motivo ?? '—'), className: 'text-ink-muted' },
  { header: 'Solicitante', render: (b) => String(b.content?.solicitante ?? '—'), className: 'text-ink-muted' },
  { header: 'Status', render: (b) => <StatusBadge status={b.status} windchillEnviado={b.windchill_enviado} /> },
]

// "Parado há" (2026-07-22, pedido explícito -- ideia de brainstorm: "não dá pra saber se um
// BITin está há 2 horas ou 2 semanas esperando"). Opcional, não faz parte de
// COLUNAS_PADRAO_BITIN porque só faz sentido nas filas de trabalho (Cadastro/Processos) --
// Meus Bitins/Painel geral não tem essa noção de "parado esperando alguém". Destaque em
// vermelho (2+ dias) pra chamar atenção de relance numa lista longa.
export const COLUNA_TEMPO_ETAPA: BitinColuna = {
  header: 'Parado há',
  render: (b) => {
    const inicio = inicioDaEtapa(b)
    const texto = tempoDecorrido(inicio)
    if (!texto) return '—'
    return <span className={paradoHaMuitoTempo(inicio) ? 'font-medium text-red-600' : 'text-ink-muted'}>{texto}</span>
  },
}
