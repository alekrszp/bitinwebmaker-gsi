import { NavLink } from 'react-router-dom'
import AgenteSapStatus from './AgenteSapStatus'

// Barra fixa no canto inferior direito (decisão do usuário, 2026-07-14): "não deve atrapalhar
// pra ver informações do bitin". A aba "BITin" sempre aparece; "Automação" só aparece com o
// agente SAP conectado (2026-07-23) -- os COMANDOS do agente (buscar material, preencher
// campos etc.) ficam no sistema web, não na janela do agente (decisão explícita do usuário:
// "quero algo seguro e com validações" -- o sistema web já tem toda a validação/auth que a
// janela do agente não tem). A janela do próprio agente (sap-agent/agente_app.py) é só
// status/configuração, nunca comando. "Enviar" continua sempre na ponta direita.
//
// Badge do agente mora aqui, não no cabeçalho do BITin (2026-07-23, pedido explícito: "ali tem
// muitas informações juntas, coloca ele lá em baixo junto da automação e do bitin") -- fica
// junto das próprias abas que ele afeta.
export default function EdicaoBottomBar({
  mongoId,
  agenteConectado,
  onAgenteDesconectadoClick,
  enviando,
  onEnviar,
}: {
  mongoId: string
  agenteConectado: boolean
  onAgenteDesconectadoClick?: () => void
  enviando: boolean
  onEnviar: () => void
}) {
  return (
    <div className="fixed bottom-4 right-4 z-20 flex items-center gap-1 rounded-xl border border-line bg-surface p-1.5 shadow-lg">
      <AgenteSapStatus conectado={agenteConectado} onClickDesconectado={onAgenteDesconectadoClick} />
      <div className="mx-0.5 h-6 w-px bg-line" />
      <NavLink
        to={`/bitins/${mongoId}`}
        end
        className={({ isActive }) =>
          `rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
            isActive ? 'bg-brand-navy text-white' : 'text-ink-muted hover:bg-surface-alt hover:text-ink'
          }`
        }
      >
        BITin
      </NavLink>
      {agenteConectado && (
        <NavLink
          to={`/bitins/${mongoId}/automacao`}
          className={({ isActive }) =>
            `rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
              isActive ? 'bg-brand-navy text-white' : 'text-ink-muted hover:bg-surface-alt hover:text-ink'
            }`
          }
        >
          Automação
        </NavLink>
      )}
      <div className="mx-1 h-6 w-px bg-line" />
      <button
        type="button"
        onClick={() => {
          // Confirmação antes de enviar (2026-07-21, pedido explícito) -- depois de
          // "Enviar" o BITin fica travado pra sempre (só volta a mudar de mãos pelos fluxos
          // de Cadastro/Processos), então vale um clique a mais de segurança.
          if (window.confirm('Enviar BITin? Não vai mais conseguir alterá-lo.')) {
            onEnviar()
          }
        }}
        disabled={enviando}
        className="rounded-lg bg-brand-orange px-5 py-2 text-sm font-semibold text-white transition-colors hover:brightness-95 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {enviando ? 'Enviando...' : 'Enviar'}
      </button>
    </div>
  )
}
