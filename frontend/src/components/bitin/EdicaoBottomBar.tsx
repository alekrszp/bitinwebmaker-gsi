import { NavLink } from 'react-router-dom'

// Barra fixa no canto inferior direito (decisão do usuário, 2026-07-14): "não deve atrapalhar
// pra ver informações do bitin". Códigos SAP e Lista Técnica são páginas de verdade (rotas
// próprias, não um bloco que abre dentro da mesma tela) -- assim o engenheiro pode abrir uma
// delas numa aba nova do navegador e editar dados gerais numa aba e lista técnica na outra ao
// mesmo tempo, os dois olhando pro mesmo BITin. A barra aparece nas 3 páginas (dados gerais,
// Códigos SAP, Lista Técnica), sempre com "Enviar" na ponta direita.
export default function EdicaoBottomBar({
  mongoId,
  enviando,
  onEnviar,
}: {
  mongoId: string
  enviando: boolean
  onEnviar: () => void
}) {
  return (
    <div className="fixed bottom-4 right-4 z-20 flex items-center gap-1 rounded-xl border border-line bg-surface p-1.5 shadow-lg">
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
      <NavLink
        to={`/bitins/${mongoId}/codigos-sap`}
        className={({ isActive }) =>
          `rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
            isActive ? 'bg-brand-navy text-white' : 'text-ink-muted hover:bg-surface-alt hover:text-ink'
          }`
        }
      >
        ZBPP009
      </NavLink>
      <NavLink
        to={`/bitins/${mongoId}/lista-tecnica`}
        className={({ isActive }) =>
          `rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
            isActive ? 'bg-brand-navy text-white' : 'text-ink-muted hover:bg-surface-alt hover:text-ink'
          }`
        }
      >
        Lista Técnica
      </NavLink>
      <div className="mx-1 h-6 w-px bg-line" />
      <button
        type="button"
        onClick={onEnviar}
        disabled={enviando}
        className="rounded-lg bg-brand-orange px-5 py-2 text-sm font-semibold text-white transition-colors hover:brightness-95 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {enviando ? 'Enviando...' : 'Enviar'}
      </button>
    </div>
  )
}
