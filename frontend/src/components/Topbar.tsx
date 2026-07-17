import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import ThemeToggle from './ThemeToggle'
import { LogoutIcon, MenuIcon, SettingsIcon } from './icons'

// Espelha backend/auth/deps.py::NIVEL_ADMIN (99) -- só duplicado aqui pra decidir o que
// mostrar; o backend continua sendo quem de fato garante a permissão em cada rota.
const NIVEL_ADMIN = 99

export default function Topbar({ onOpenSidebar }: { onOpenSidebar: () => void }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <header className="sticky top-0 z-20 flex h-14 items-center justify-between border-b border-line bg-surface px-4 sm:px-6">
      <button
        type="button"
        onClick={onOpenSidebar}
        aria-label="Abrir menu"
        className="rounded-lg p-2 text-ink-muted hover:bg-surface-alt md:hidden"
      >
        <MenuIcon className="h-5 w-5" />
      </button>

      {/* Selo "Admin" (2026-07-16, pedido explícito) -- mesma convenção visual de
          StatusBadge.tsx/SetorBadge.tsx (pill arredondada, cor de marca em 15-20% de opacidade
          de fundo + texto sólido), não uma cor nova inventada pra isso. Perto da borda
          esquerda (ao lado do botão de menu), só visível pra Admin (99). */}
      {user && user.permission_level === NIVEL_ADMIN && (
        <span className="ml-2 hidden rounded-full bg-brand-navy/15 px-4 py-1.5 text-sm font-semibold text-brand-navy dark:text-white sm:inline-block">
          Admin
        </span>
      )}

      {/* Espaço reservado pro celular (o menu fica à esquerda); em telas maiores o resto fica
          alinhado à direita porque o título da página já mora dentro do próprio conteúdo
          (mesma ideia do "Entrar" no login -- não duplicado aqui no chrome). */}
      <div className="flex flex-1 items-center justify-end gap-1.5 sm:gap-3">
        <ThemeToggle className="text-ink-muted hover:bg-surface-alt" />
        <Link
          to="/configuracoes"
          title="Configurações"
          aria-label="Configurações"
          className="flex h-9 w-9 items-center justify-center rounded-full text-ink-muted transition-colors hover:bg-surface-alt"
        >
          <SettingsIcon className="h-4 w-4" />
        </Link>
        <span className="hidden text-sm text-ink-muted sm:inline">{user?.email}</span>
        <button
          onClick={handleLogout}
          title="Sair"
          className="flex items-center gap-1.5 rounded-lg border border-line px-3 py-1.5 text-sm text-ink hover:bg-surface-alt"
        >
          <LogoutIcon className="h-4 w-4" />
          <span className="hidden sm:inline">Sair</span>
        </button>
      </div>
    </header>
  )
}
