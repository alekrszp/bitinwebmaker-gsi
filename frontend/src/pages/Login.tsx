import { useState, type FormEvent, type SVGProps } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import ThemeToggle from '../components/ThemeToggle'
import { useAuth } from '../hooks/useAuth'
import { version as appVersion } from '../../package.json'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [mostrarSenha, setMostrarSenha] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    // trim() na senha (2026-07-17) -- senha temporária normalmente vem de copiar/colar (popup
    // de cadastro ou e-mail), e é fácil arrastar um espaço/quebra de linha extra na seleção
    // sem notar; o servidor comparava o hash exato, então esse espaço sozinho já derrubava o
    // login com "e-mail ou senha incorretos" mesmo copiando certinho o texto visível.
    const senhaLimpa = password.trim()
    try {
      await login(email.trim(), senhaLimpa)
      // Credential Management API (2026-07-15): input com autoComplete já deixa o navegador
      // oferecer salvar a senha na maioria dos casos, mas o prompt é heurístico -- em SPA
      // (sem navegação de página cheia no submit) às vezes não dispara. Chamar
      // navigator.credentials.store() explicitamente após um login confirmado força o prompt
      // de forma confiável. Só existe em navegadores baseados em Chromium (não no Safari) --
      // checagem de feature antes de usar, e nunca falha o login se o navegador não suportar.
      if ('PasswordCredential' in window && navigator.credentials) {
        try {
          const cred = new (window as unknown as { PasswordCredential: new (data: { id: string; password: string; name?: string }) => Credential }).PasswordCredential({
            id: email,
            password: senhaLimpa,
            name: email,
          })
          await navigator.credentials.store(cred)
        } catch {
          // Prompt de salvar senha é conveniência, não deveria travar o fluxo de login se
          // falhar por qualquer motivo (navegador negou, API mudou, etc.).
        }
      }
      const from = (location.state as { from?: Location })?.from?.pathname || '/'
      navigate(from, { replace: true })
    } catch (err) {
      // Duck-typed em vez de axios.isAxiosError -- o teste (Login.test.tsx) mocka a API com um
      // objeto de erro simples, sem a marca isAxiosError; e o formato {response:{data:{detail}}}
      // já é a única forma de erro que este catch precisa tratar (erro de rede/CORS cai no
      // fallback genérico do lado direito do `||`, igual antes).
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(detail || 'Não foi possível entrar. Confira e-mail e senha.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-screen bg-app-bg">
      {/* Painel de marca -- só em telas médias+; no celular a logo aparece compacta em cima do
          formulário (ver abaixo), pra não gastar metade da tela com algo só decorativo.
          Fundo branco FIXO + logo colorida (2026-07-16, a pedido do usuário -- versão anterior
          com painel navy foi revertida por não ter ficado boa). Tentativa de trocar por
          `bg-surface` pra acompanhar o tema escuro (2026-07-17) foi revertida a pedido do
          usuário -- este painel é decorativo/de marca, sempre branco nos dois temas, não é
          "conteúdo" que precise se adaptar. Por isso as cores de texto aqui também são fixas
          (slate-*), não os tokens `text-ink*` (que mudam com o tema e ficariam claros demais
          sobre fundo branco no modo escuro) -- só o painel do formulário ao lado (`Painel do
          formulário` abaixo) usa os tokens de tema. */}
      <div className="relative hidden w-[42%] max-w-md flex-col overflow-hidden border-r border-line bg-white px-10 py-10 text-slate-900 md:flex lg:w-[38%]">
        <div className="flex flex-col pt-16">
          <img src="/brand/gpt-color.png" className="mb-6 h-20 w-fit" alt="Grain & Protein Technologies" />
          <div className="flex items-baseline gap-2">
            {/* Cor extraída direto do PNG da logo (rgb(5,70,96) / #054660, amostrado em
                public/brand/gpt-color.png -- ver docs/RELEASE_v0.8.4.md) em vez do token
                `brand-navy` (#32464d) -- os dois têm nomes parecidos mas hex diferentes, o que
                deixava "BITin" visivelmente destoando das letras da logo ao lado (2026-07-17,
                pedido explícito: "pega a cor a logo das letras e coloca em BITin também").
                Escopado só a esta tela -- não mexe no token `brand-navy` usado no resto do
                app, ver memória "logo/paleta pendente" (revisão de paleta fica pra quando o
                usuário mandar os arquivos oficiais por tema). */}
            <h1 className="text-3xl font-bold leading-none tracking-tight text-[#054660]">BITin</h1>
          </div>
          <p className="mt-2.5 text-sm text-slate-500">
            Sistema interno Grain &amp; Protein Technologies.
          </p>
        </div>

        <div className="flex-1" />

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

        <span className="mb-8 flex w-fit items-center md:hidden">
          <img src="/brand/gpt-color.png" className="h-10" alt="Grain & Protein Technologies" />
        </span>

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
                  name="email"
                  type="email"
                  required
                  autoFocus
                  autoComplete="email"
                  placeholder="voce@empresa.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full rounded-lg border border-line bg-surface py-2.5 pl-10 pr-3 text-ink placeholder:text-ink-faint focus:border-[#054660] focus:outline-none focus:ring-2 focus:ring-[#054660]/20"
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
                  name="password"
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
              <p role="alert" className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2.5 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
                <AlertIcon className="mt-0.5 h-4 w-4 shrink-0" />
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={submitting}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-[#054660] py-2.5 font-medium text-white transition-colors hover:bg-[#033349] disabled:cursor-not-allowed disabled:opacity-60"
            >
              {submitting && <SpinnerIcon className="h-4 w-4 animate-spin" />}
              {submitting ? 'Entrando...' : 'Entrar'}
            </button>
          </form>
        </div>

        <p className="mt-10 text-xs text-ink-faint">v{appVersion}</p>
      </div>
    </div>
  )
}

function MailIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <path d="m3 7 9 6 9-6" />
    </svg>
  )
}

function LockIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <rect x="4" y="10" width="16" height="10" rx="2" />
      <path d="M8 10V7a4 4 0 0 1 8 0v3" />
    </svg>
  )
}

function EyeIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  )
}

function EyeOffIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M3 3l18 18" />
      <path d="M10.58 10.58a2 2 0 0 0 2.83 2.83" />
      <path d="M9.88 5.09A10.7 10.7 0 0 1 12 5c6.5 0 10 7 10 7a13.2 13.2 0 0 1-3.17 3.88M6.6 6.6C3.94 8.32 2 12 2 12s3.5 7 10 7a10.6 10.6 0 0 0 4.24-.88" />
    </svg>
  )
}

function AlertIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <circle cx="12" cy="12" r="10" />
      <path d="M12 8v5M12 16h.01" />
    </svg>
  )
}

function SpinnerIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" {...props}>
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="3" opacity="0.25" />
      <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  )
}
