import { useState } from 'react'
import FormLabel from '../FormLabel'
import TextInput from '../TextInput'
import { usePasswordChangeForm } from '../../hooks/usePasswordChangeForm'

// Autoatendimento de troca de senha (2026-07-15, pedido explícito do usuário: "wired into the
// Settings screen") -- antes disso não existia nenhum jeito de trocar a própria senha sem
// edição direta no banco. POST /auth/change-password (backend/auth/routes.py) valida a senha
// atual e a força da nova (mesma regra de UserCreate.password no registro). Estado/validação
// compartilhados com DefinirSenha.tsx via usePasswordChangeForm -- só o que acontece no sucesso
// (mensagem inline aqui, navegação lá) é próprio desta tela.
export default function TrocarSenhaForm() {
  const [sucesso, setSucesso] = useState(false)
  const { senhaAtual, setSenhaAtual, senhaNova, setSenhaNova, confirmarSenha, setConfirmarSenha, erro, enviando, handleSubmit: handleSubmitBase } =
    usePasswordChangeForm(() => setSucesso(true))

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    setSucesso(false)
    await handleSubmitBase(event)
  }

  return (
    <form onSubmit={handleSubmit} className="mt-6 max-w-sm border-t border-line pt-5">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-muted">Trocar senha</h3>

      <div className="mt-3 space-y-3">
        <div>
          <FormLabel htmlFor="senha-atual">Senha atual</FormLabel>
          <TextInput
            id="senha-atual"
            type="password"
            autoComplete="current-password"
            value={senhaAtual}
            onChange={(e) => setSenhaAtual(e.target.value)}
          />
        </div>
        <div>
          <FormLabel htmlFor="senha-nova">Nova senha</FormLabel>
          <TextInput
            id="senha-nova"
            type="password"
            autoComplete="new-password"
            value={senhaNova}
            onChange={(e) => setSenhaNova(e.target.value)}
          />
          {/* Regra explícita ANTES de errar (2026-07-16), mesma redação de DefinirSenha.tsx --
              espelha backend/auth/security.py::validate_password_strength. */}
          <p className="mt-1 text-xs text-ink-muted">
            Pelo menos 8 caracteres e 3 destes 4 tipos: maiúscula, minúscula, número, caractere
            especial.
          </p>
        </div>
        <div>
          <FormLabel htmlFor="confirmar-senha">Confirmar nova senha</FormLabel>
          <TextInput
            id="confirmar-senha"
            type="password"
            autoComplete="new-password"
            value={confirmarSenha}
            onChange={(e) => setConfirmarSenha(e.target.value)}
          />
        </div>
      </div>

      {erro && <p className="mt-3 text-sm text-red-600">{erro}</p>}
      {sucesso && <p className="mt-3 text-sm text-green-600">Senha alterada com sucesso.</p>}

      <button
        type="submit"
        disabled={enviando || !senhaAtual || !senhaNova || !confirmarSenha}
        className="mt-4 rounded-lg bg-brand-navy px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-navy-dark disabled:cursor-not-allowed disabled:opacity-60"
      >
        {enviando ? 'Salvando...' : 'Salvar nova senha'}
      </button>
    </form>
  )
}
