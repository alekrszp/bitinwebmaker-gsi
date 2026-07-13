import { Link, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-brand-navy">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
          <Link to="/bitins" className="flex items-center gap-2 text-lg font-bold tracking-tight text-white">
            BIT<span className="text-brand-gold">in</span>
          </Link>
          {user && (
            <div className="flex items-center gap-4 text-sm text-white/80">
              <span>{user.email}</span>
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
      <main className="mx-auto max-w-5xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}
