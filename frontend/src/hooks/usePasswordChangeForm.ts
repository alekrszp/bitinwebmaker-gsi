import { useState, type FormEvent } from 'react'
import { api } from '../lib/api'
import { extrairErro } from '../lib/errors'
import type { ChangePasswordRequest } from '../lib/types'

// Estado/validação/submit compartilhados entre Settings.tsx::TrocarSenhaForm (seção dentro da
// página, com mensagem de sucesso inline) e DefinirSenha.tsx (tela cheia de primeiro login, que
// navega pra home no sucesso) -- extraído porque os dois implementavam os mesmos três campos +
// checagem de confirmação + POST /auth/change-password de forma verbatim. O que acontece no
// sucesso continua sendo decisão de cada tela: `onSucesso` é chamado depois do POST confirmar,
// cada chamador decide se mostra mensagem, navega, etc.
export function usePasswordChangeForm(onSucesso: () => void | Promise<void>) {
  const [senhaAtual, setSenhaAtual] = useState('')
  const [senhaNova, setSenhaNova] = useState('')
  const [confirmarSenha, setConfirmarSenha] = useState('')
  const [erro, setErro] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setErro(null)

    // Checagem client-side barata -- a validação de verdade (força da senha, senha atual
    // correta) é sempre do servidor, isso aqui só evita uma ida à API por engano de digitação.
    if (senhaNova !== confirmarSenha) {
      setErro('A confirmação não bate com a nova senha.')
      return
    }

    setEnviando(true)
    try {
      const body: ChangePasswordRequest = { senha_atual: senhaAtual, senha_nova: senhaNova }
      await api.post('/auth/change-password', body)
      setSenhaAtual('')
      setSenhaNova('')
      setConfirmarSenha('')
      await onSucesso()
    } catch (err) {
      setErro(extrairErro(err, 'Não foi possível trocar a senha. Tente novamente.'))
    } finally {
      setEnviando(false)
    }
  }

  return {
    senhaAtual,
    setSenhaAtual,
    senhaNova,
    setSenhaNova,
    confirmarSenha,
    setConfirmarSenha,
    erro,
    enviando,
    handleSubmit,
  }
}
