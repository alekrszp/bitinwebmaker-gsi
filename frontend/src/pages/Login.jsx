import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import ThemeToggle from '../components/ThemeToggle'
import { useAuth } from '../context/AuthContext'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [mostrarSenha, setMostrarSenha] = useState(false)
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await login(email, password)
      const from = location.state?.from?.pathname || '/'
      navigate(from, { replace: true })
    } catch (err) {
      setError(err.response?.data?.detail || 'Não foi possível entrar. Confira e-mail e senha.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-screen bg-app-bg">
      {/* Painel de marca -- só em telas médias+; no celular a logo aparece compacta em cima do
          formulário (ver abaixo), pra não gastar metade da tela com algo só decorativo. */}
      <div className="relative hidden w-[42%] max-w-md flex-col overflow-hidden bg-brand-navy px-10 py-10 text-white md:flex lg:w-[38%]">
        {/* Logo + título + subtítulo formam um único bloco centralizado -- antes a logo ficava
            presa no topo, isolada, com um vão vazio grande até o texto lá embaixo; agrupados e
            centralizados, o painel lê como uma composição, não como dois elementos soltos. */}
        <div className="flex flex-1 flex-col justify-center">
          <span className="mb-8 flex w-fit items-center rounded bg-white px-2.5 py-1.5 shadow-sm">
            <img src="/logo.svg" className="h-9" alt="Grain & Protein Technologies" />
          </span>

          <p className="text-2xl font-semibold leading-snug text-balance">
            BITin - Sistema de manuseamento de BITins.
          </p>
          <p className="mt-3 text-sm text-white/70">
            Sistema interno da Grain &amp; Protein Technologies.
          </p>
        </div>

        {/* Faixa de 3 cores -- mesma referência discreta aos 3 hexágonos do logo usada no
            cabeçalho pós-login (Layout.jsx), pra dar continuidade visual entre as duas telas. */}
        <div className="flex gap-1.5">
          <span className="h-1.5 w-10 rounded-full bg-brand-gold" />
          <span className="h-1.5 w-10 rounded-full bg-brand-green" />
          <span className="h-1.5 w-10 rounded-full bg-brand-orange" />
        </div>
      </div>

      {/* Painel do formulário */}
      <div className="relative flex flex-1 flex-col items-center justify-center px-4 py-12">
        <div className="absolute right-4 top-4">
          <ThemeToggle className="text-ink-muted hover:bg-surface-alt" />
        </div>

        <img src="/logo.svg" className="mb-8 h-14 md:hidden" alt="Grain & Protein Technologies" />

        <div className="w-full max-w-sm">
          <h1 className="text-2xl font-semibold text-ink">Entrar</h1>
          <p className="mt-1 text-sm text-ink-muted">
            Acesse sua conta.
          </p>

          <form onSubmit={handleSubmit} noValidate className="mt-8 space-y-5">
            <div>
              <label htmlFor="email" className="mb-1.5 block text-sm font-medium text-ink">
                E-mail
              </label>
              <div className="relative">
                <MailIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-faint" />
                <input
                  id="email"
                  type="email"
                  required
                  autoFocus
                  autoComplete="email"
                  placeholder="voce@empresa.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full rounded-lg border border-line bg-surface py-2.5 pl-10 pr-3 text-ink placeholder:text-ink-faint focus:border-brand-navy focus:outline-none focus:ring-2 focus:ring-brand-navy/20"
                />
              </div>
            </div>

            <div>
              <label htmlFor="password" className="mb-1.5 block text-sm font-medium text-ink">
                Senha
              </label>
              <div className="relative">
                <LockIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-faint" />
                <input
                  id="password"
                  type={mostrarSenha ? 'text' : 'password'}
                  required
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-lg border border-line bg-surface py-2.5 pl-10 pr-10 text-ink focus:border-brand-navy focus:outline-none focus:ring-2 focus:ring-brand-navy/20"
                />
                <button
                  type="button"
                  onClick={() => setMostrarSenha((v) => !v)}
                  aria-label={mostrarSenha ? 'Esconder senha' : 'Mostrar senha'}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-faint hover:text-ink-muted"
                >
                  {mostrarSenha ? <EyeOffIcon className="h-4 w-4" /> : <EyeIcon className="h-4 w-4" />}
                </button>
              </div>
            </div>

            {error && (
              <p role="alert" className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2.5 text-sm text-red-700">
                <AlertIcon className="mt-0.5 h-4 w-4 shrink-0" />
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={submitting}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand-navy py-2.5 font-medium text-white transition-colors hover:bg-brand-navy-dark disabled:cursor-not-allowed disabled:opacity-60"
            >
              {submitting && <SpinnerIcon className="h-4 w-4 animate-spin" />}
              {submitting ? 'Entrando...' : 'Entrar'}
            </button>
          </form>
        </div>

        <p className="mt-10 text-xs text-ink-faint">Grain &amp; Protein Technologies — Central de Cadastro/Engenheria</p>
      </div>
    </div>
  )
}

function MailIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <path d="m3 7 9 6 9-6" />
    </svg>
  )
}

function LockIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <rect x="4" y="10" width="16" height="10" rx="2" />
      <path d="M8 10V7a4 4 0 0 1 8 0v3" />
    </svg>
  )
}

function EyeIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  )
}

function EyeOffIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M3 3l18 18" />
      <path d="M10.58 10.58a2 2 0 0 0 2.83 2.83" />
      <path d="M9.88 5.09A10.7 10.7 0 0 1 12 5c6.5 0 10 7 10 7a13.2 13.2 0 0 1-3.17 3.88M6.6 6.6C3.94 8.32 2 12 2 12s3.5 7 10 7a10.6 10.6 0 0 0 4.24-.88" />
    </svg>
  )
}

function AlertIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <circle cx="12" cy="12" r="10" />
      <path d="M12 8v5M12 16h.01" />
    </svg>
  )
}

function SpinnerIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" {...props}>
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="3" opacity="0.25" />
      <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  )
}
