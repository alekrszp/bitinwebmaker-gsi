import Card from '../Card'

// Histórico/auditoria do BITin (2026-07-22, pedido explícito -- ideia de brainstorm: "quem
// mexeu, quando, o que mudou"). Nível de evento, não diff campo a campo (decisão do usuário:
// "só os eventos principais") -- ver backend/api/bitins.py::_evento_historico. Mais recente
// primeiro, igual a qualquer feed de atividade.

// Formato próprio com hora:minuto (2026-07-22) -- diferente de formatarDataEnvio (lib/format.ts,
// só data), num histórico a hora importa pra distinguir eventos do mesmo dia.
function formatarDataHora(iso: string): string {
  const data = new Date(iso)
  if (Number.isNaN(data.getTime())) return iso
  const dia = String(data.getDate()).padStart(2, '0')
  const mes = String(data.getMonth() + 1).padStart(2, '0')
  const hora = String(data.getHours()).padStart(2, '0')
  const min = String(data.getMinutes()).padStart(2, '0')
  return `${dia}.${mes}.${data.getFullYear()} ${hora}:${min}`
}

export default function HistoricoCard({ eventos }: { eventos: { usuario: string; data: string; acao: string }[] }) {
  if (eventos.length === 0) return null
  const ordenados = [...eventos].reverse()
  return (
    <Card title="Histórico">
      <ul className="mt-4 space-y-3">
        {ordenados.map((evento, i) => (
          <li key={i} className="flex flex-wrap items-baseline gap-x-2 text-sm">
            <span className="font-medium text-ink">{evento.usuario}</span>
            <span className="text-ink-muted">{evento.acao}</span>
            <span className="text-xs text-ink-faint">{formatarDataHora(evento.data)}</span>
          </li>
        ))}
      </ul>
    </Card>
  )
}
