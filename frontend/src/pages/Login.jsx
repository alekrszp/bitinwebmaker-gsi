import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await login(email, password)
      const from = location.state?.from?.pathname || '/bitins'
      navigate(from, { replace: true })
    } catch (err) {
      setError(err.response?.data?.detail || 'Não foi possível entrar. Confira e-mail e senha.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-app-bg">
      <div className="flex flex-1 flex-col items-center justify-center px-4">
        <img src="/logo.svg" className="mb-6 h-16" alt="Grain & Protein Technologies" />
        <div className="w-full max-w-sm rounded-lg border border-line bg-surface p-6 shadow-sm">
          <h1 className="mb-1 text-lg font-semibold text-ink">Entrar</h1>
          <p className="mb-5 text-sm text-ink-muted">Boletim de Informações Técnicas — Grain &amp; Protein Technologies</p>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-ink-muted">E-mail</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded border border-line bg-surface px-3 py-2 text-ink focus:border-brand-navy focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-ink-muted">Senha</label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded border border-line bg-surface px-3 py-2 text-ink focus:border-brand-navy focus:outline-none"
              />
            </div>
            {error && <p className="text-sm text-red-600">{error}</p>}
            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded bg-brand-navy px-4 py-2 font-medium text-white hover:bg-brand-navy-dark disabled:opacity-50"
            >
              {submitting ? 'Entrando...' : 'Entrar'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
