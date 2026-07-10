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
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
          <Link to="/bitins" className="text-lg font-semibold text-gray-900">
            BITin
          </Link>
          {user && (
            <div className="flex items-center gap-4 text-sm text-gray-600">
              <span>{user.email}</span>
              <button
                onClick={handleLogout}
                className="rounded border border-gray-300 px-3 py-1 hover:bg-gray-100"
              >
                Sair
              </button>
            </div>
          )}
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}
