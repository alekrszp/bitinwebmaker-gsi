import { Link, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'

export default function Layout() {
  const { user, logout } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-app-bg">
      <header className="bg-brand-navy">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <Link to="/bitins" className="flex items-center gap-2 text-lg font-bold tracking-tight text-white">
            {/* TODO: trocar por <img src="/logo.png" className="h-8" alt="Grain & Protein Technologies" />
                assim que o arquivo da logo estiver disponível (ver docs/FRONTEND.md, "Identidade visual"). */}
            BIT<span className="text-brand-gold">in</span>
          </Link>
          {user && (
            <div className="flex items-center gap-3 text-sm text-white/80">
              <span className="hidden sm:inline">{user.email}</span>
              <ThemeToggle theme={theme} onToggle={toggleTheme} />
              <button
                onClick={handleLogout}
                className="rounded border border-white/25 px-3 py-1 text-white hover:bg-white/10"
              >
                Sair
              </button>
            </div>
          )}
        </div>
        {/* Faixa de 3 cores -- referência discreta aos 3 hexágonos do logo (frango/grão/porco),
            sem tentar redesenhar o ícone em si. */}
        <div className="flex h-1">
          <div className="flex-1 bg-brand-gold" />
          <div className="flex-1 bg-brand-green" />
          <div className="flex-1 bg-brand-orange" />
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}

function ThemeToggle({ theme, onToggle }) {
  const escuro = theme === 'dark'
  return (
    <button
      onClick={onToggle}
      title={escuro ? 'Mudar pro tema claro' : 'Mudar pro tema escuro'}
      aria-label={escuro ? 'Mudar pro tema claro' : 'Mudar pro tema escuro'}
      className="flex h-8 w-8 items-center justify-center rounded border border-white/25 text-white hover:bg-white/10"
    >
      {escuro ? (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-4 w-4">
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
        </svg>
      ) : (
        <svg viewBox="0 0 24 24" fill="currentColor" className="h-4 w-4">
          <path d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 1020.354 15.354z" />
        </svg>
      )}
    </button>
  )
}
