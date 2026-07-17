import { NavLink } from 'react-router-dom'
import { version as appVersion } from '../../package.json'
import { useAuth } from '../hooks/useAuth'
import { isAdmin } from '../lib/permissions'
import { HomeIcon, ListIcon, UsersIcon } from './icons'

// Lista extensível de propósito -- o próximo item entra aqui sem mexer no resto do componente.
const NAV_ITEMS = [
  { to: '/', label: 'Início', icon: HomeIcon, end: true },
  { to: '/bitins', label: 'Meus Bitins', icon: ListIcon, end: false },
]

// Item só-admin (2026-07-16, revisado: "gestão de usuários e criar usuário devem ser
// desvinculadas de Configurações, páginas juntas" -- GestaoUsuarios já renderiza
// CriarUsuarioForm dentro de si, então uma rota dedicada só, não duas com âncora). Ver
// GestaoUsuariosPage.tsx / rota /usuarios.
const NAV_ITEMS_ADMIN = [{ to: '/usuarios', label: 'Gestão de usuários', icon: UsersIcon, end: true }]

export default function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { user } = useAuth()
  // Identidade visual por papel (2026-07-16, ajustado depois que a 1ª versão -- cinza pro admin,
  // Light Blue pros outros -- ficou ruim visualmente. Decisão final do usuário: admin fica
  // exatamente como sempre foi (navy + logo.svg); só Gestor/Cadastro/Usuário mudam, pra branco
  // com a logo colorida. Ver Topbar.tsx (mesmo par cor/logo, pro cabeçalho combinar).
  const admin = isAdmin(user?.permission_level)
  const logoSrc = admin ? '/logo.svg' : '/brand/gpt-color.png'
  const surfaceClass = admin ? 'bg-brand-navy' : 'bg-white border-r border-line'
  const textClass = admin ? 'text-white' : 'text-ink'
  const navActiveClass = admin ? 'bg-white/15 text-white' : 'bg-brand-navy/10 text-brand-navy'
  const navInactiveClass = admin
    ? 'text-white/70 hover:bg-white/10 hover:text-white'
    : 'text-ink-muted hover:bg-surface-alt hover:text-ink'
  const dividerClass = admin ? 'border-white/10' : 'border-line'
  const groupLabelClass = admin ? 'text-white/40' : 'text-ink-faint'
  const versionClass = admin ? 'text-white/50' : 'text-ink-faint'
  return (
    <>
      {/* Fundo escurecido atrás da sidebar no celular -- só existe quando ela está aberta,
          fecha ao clicar fora (mesma ideia de qualquer off-canvas menu). */}
      {open && (
        <div className="fixed inset-0 z-30 bg-black/40 md:hidden" onClick={onClose} aria-hidden="true" />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-60 shrink-0 flex-col ${surfaceClass} px-4 py-6 ${textClass} transition-transform md:sticky md:top-0 md:h-screen md:translate-x-0 ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* h-16 pro logo.svg original (admin); os PNGs de marca (gpt-color) são um lockup mais
            largo (~2.6:1), h-12 evita que fiquem colados nas bordas do menu de 240px. */}
        <div className="flex justify-center py-2">
          <img src={logoSrc} className={admin ? 'h-16 w-auto' : 'h-12 w-auto'} alt="Grain & Protein Technologies" />
        </div>

        <nav className="mt-8 flex flex-1 flex-col gap-1">
          {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              onClick={onClose}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  isActive ? navActiveClass : navInactiveClass
                }`
              }
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </NavLink>
          ))}

          {admin && (
            <>
              <div className={`mt-3 border-t ${dividerClass} pt-3 text-xs font-semibold uppercase tracking-wide ${groupLabelClass}`}>
                Administração
              </div>
              {NAV_ITEMS_ADMIN.map(({ to, label, icon: Icon, end }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={end}
                  onClick={onClose}
                  className={({ isActive }) =>
                    `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                      isActive ? navActiveClass : navInactiveClass
                    }`
                  }
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  {label}
                </NavLink>
              ))}
            </>
          )}
        </nav>

        {/* Faixa de 3 cores -- mesma assinatura visual do login (painel de marca) e do
            cabeçalho antigo, pra dar continuidade entre as telas. Versão centralizada abaixo,
            com borda separando do resto (tirada de Configurações -- decisão do usuário,
            2026-07-14: um lugar só, não duplicado). */}
        <div className={`flex flex-col items-center gap-2 border-t ${dividerClass} pt-3`}>
          <div className="flex gap-1.5">
            <span className="h-1.5 w-8 rounded-full bg-brand-gold" />
            <span className="h-1.5 w-8 rounded-full bg-brand-green" />
            <span className="h-1.5 w-8 rounded-full bg-brand-orange" />
          </div>
          <span className={`text-xs ${versionClass}`}>v{appVersion}</span>
        </div>
      </aside>
    </>
  )
}
