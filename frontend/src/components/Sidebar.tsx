import { NavLink } from 'react-router-dom'
import { HomeIcon, ListIcon } from './icons'

// Lista extensível de propósito -- o próximo item entra aqui sem mexer no resto do componente.
const NAV_ITEMS = [
  { to: '/', label: 'Início', icon: HomeIcon, end: true },
  { to: '/bitins', label: 'Meus Bitins', icon: ListIcon, end: false },
]

export default function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <>
      {/* Fundo escurecido atrás da sidebar no celular -- só existe quando ela está aberta,
          fecha ao clicar fora (mesma ideia de qualquer off-canvas menu). */}
      {open && (
        <div className="fixed inset-0 z-30 bg-black/40 md:hidden" onClick={onClose} aria-hidden="true" />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-60 shrink-0 flex-col bg-brand-navy px-4 py-6 text-white transition-transform md:sticky md:top-0 md:h-screen md:translate-x-0 ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <span className="flex w-fit items-center rounded bg-white px-2.5 py-1.5 shadow-sm">
          <img src="/logo.svg" className="h-8" alt="Grain & Protein Technologies" />
        </span>

        <nav className="mt-8 flex flex-1 flex-col gap-1">
          {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              onClick={onClose}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  isActive ? 'bg-white/15 text-white' : 'text-white/70 hover:bg-white/10 hover:text-white'
                }`
              }
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Faixa de 3 cores -- mesma assinatura visual do login (painel de marca) e do
            cabeçalho antigo, pra dar continuidade entre as telas. */}
        <div className="flex gap-1.5">
          <span className="h-1.5 w-8 rounded-full bg-brand-gold" />
          <span className="h-1.5 w-8 rounded-full bg-brand-green" />
          <span className="h-1.5 w-8 rounded-full bg-brand-orange" />
        </div>
      </aside>
    </>
  )
}
