import { Link, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import ThemeToggle from './ThemeToggle'

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-app-bg">
      <header className="bg-brand-navy">
        <div className="flex items-center justify-between px-4 py-2">
          <Link to="/" className="flex items-center gap-2">
            {/* Fundo branco de propósito: a logo é um JPEG com fundo branco sólido (não
                transparente) -- sem isso, apareceria uma caixa branca "solta" sobre o navy. */}
            <span className="flex items-center rounded bg-white px-2 py-1">
              <img src="/logo.svg" className="h-8" alt="Grain & Protein Technologies" />
            </span>
          </Link>
          {user && (
            <div className="flex items-center gap-3 text-sm text-white/80">
              <span className="hidden sm:inline">{user.email}</span>
              <ThemeToggle className="border border-white/25 text-white hover:bg-white/10" />
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
      {/* Sem max-width aqui de propósito -- páginas que querem largura limitada decidem isso
          sozinhas, dentro do próprio conteúdo (ver docs/FRONTEND.md). */}
      <main className="px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}
