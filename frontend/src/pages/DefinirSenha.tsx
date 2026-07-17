import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { usePasswordChangeForm } from '../hooks/usePasswordChangeForm'

// Tela obrigatória de primeiro login com senha temporária (2026-07-15, cadastro de usuário só
// por admin -- ver backend/api/users.py::create_user_by_admin e RequireAuth.tsx, que redireciona
// pra cá enquanto Usuario.senha_temporaria for True). Reusa a mesma chamada de
// POST /auth/change-password de Settings.tsx::TrocarSenhaForm (via usePasswordChangeForm) -- a
// senha temporária que o admin passou fora do sistema É a senha_atual dessa primeira troca; não
// existe endpoint separado pra "definir senha pela primeira vez". Tela standalone (sem
// sidebar/topbar), mesmo espírito "não dá pra pular" de Login.tsx.
export default function DefinirSenha() {
  const { refreshUser, logout } = useAuth()
  const navigate = useNavigate()
  const { senhaAtual, setSenhaAtual, senhaNova, setSenhaNova, confirmarSenha, setConfirmarSenha, erro, enviando, handleSubmit } =
    usePasswordChangeForm(async () => {
      // Servidor já zerou Usuario.senha_temporaria -- rebusca /users/me pra RequireAuth.tsx
      // parar de redirecionar pra cá, e só então navega pra home.
      await refreshUser()
      navigate('/', { replace: true })
    })

  return (
    <div className="flex min-h-screen items-center justify-center bg-app-bg px-4 py-12">
      <div className="w-full max-w-sm">
        <h1 className="text-2xl font-semibold text-ink">Defina sua senha</h1>
        <p className="mt-2 text-sm text-ink-muted">
          Você entrou com uma senha temporária. Defina agora uma senha só sua, que ninguém mais
          vai saber, antes de continuar.
        </p>

        <form onSubmit={handleSubmit} noValidate className="mt-8 space-y-4">
          <div>
            <label htmlFor="senha-atual" className="mb-1.5 block text-sm font-medium text-ink">
              Senha temporária (a que você recebeu)
            </label>
            <input
              id="senha-atual"
              type="password"
              autoComplete="current-password"
              required
              autoFocus
              value={senhaAtual}
              onChange={(e) => setSenhaAtual(e.target.value)}
              className="w-full rounded-lg border border-line bg-surface px-3 py-2.5 text-sm text-ink focus:border-brand-navy focus:outline-none focus:ring-2 focus:ring-brand-navy/20"
            />
          </div>
          {/* Regra explícita ANTES do campo, não só depois de um 400 (2026-07-16, pedido explícito:
              "mostrar a regra em palavras, antes de digitar"). Texto espelha exatamente
              backend/auth/security.py::validate_password_strength -- min 8 caracteres + pelo
              menos 3 dos 4 tipos de caractere. */}
          <p className="rounded-lg border border-line bg-surface px-3 py-2 text-xs text-ink-muted">
            A senha precisa ter pelo menos 8 caracteres e incluir pelo menos 3 destes 4 tipos:
            letra maiúscula, letra minúscula, número, caractere especial.
          </p>

          <div>
            <label htmlFor="senha-nova" className="mb-1.5 block text-sm font-medium text-ink">
              Nova senha
            </label>
            <input
              id="senha-nova"
              type="password"
              autoComplete="new-password"
              required
              value={senhaNova}
              onChange={(e) => setSenhaNova(e.target.value)}
              className="w-full rounded-lg border border-line bg-surface px-3 py-2.5 text-sm text-ink focus:border-brand-navy focus:outline-none focus:ring-2 focus:ring-brand-navy/20"
            />
          </div>
          <div>
            <label htmlFor="confirmar-senha" className="mb-1.5 block text-sm font-medium text-ink">
              Confirmar nova senha
            </label>
            <input
              id="confirmar-senha"
              type="password"
              autoComplete="new-password"
              required
              value={confirmarSenha}
              onChange={(e) => setConfirmarSenha(e.target.value)}
              className="w-full rounded-lg border border-line bg-surface px-3 py-2.5 text-sm text-ink focus:border-brand-navy focus:outline-none focus:ring-2 focus:ring-brand-navy/20"
            />
          </div>

          {erro && (
            <p role="alert" className="rounded-lg border border-red-200 bg-red-50 px-3 py-2.5 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
              {erro}
            </p>
          )}

          <button
            type="submit"
            disabled={enviando || !senhaAtual || !senhaNova || !confirmarSenha}
            className="w-full rounded-lg bg-brand-navy py-2.5 font-medium text-white transition-colors hover:bg-brand-navy-dark disabled:cursor-not-allowed disabled:opacity-60"
          >
            {enviando ? 'Salvando...' : 'Definir senha e continuar'}
          </button>

          <button
            type="button"
            onClick={logout}
            className="w-full text-center text-xs text-ink-muted hover:text-ink"
          >
            Sair
          </button>
        </form>
      </div>
    </div>
  )
}
