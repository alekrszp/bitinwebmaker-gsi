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

    // trim() nas três (2026-07-17, mesmo motivo de Login.tsx) -- `senhaAtual` aqui é
    // tipicamente a senha temporária copiada/colada do popup de cadastro ou do e-mail; um
    // espaço/quebra de linha extra arrastado na seleção derrubava a troca com "senha atual
    // incorreta" mesmo copiando certinho o texto visível. Trima os três ANTES de comparar
    // nova/confirmação, senão um trim só de um lado faz a comparação falhar por engano.
    const atual = senhaAtual.trim()
    const nova = senhaNova.trim()
    const confirmar = confirmarSenha.trim()

    // Checagem client-side barata -- a validação de verdade (força da senha, senha atual
    // correta) é sempre do servidor, isso aqui só evita uma ida à API por engano de digitação.
    if (nova !== confirmar) {
      setErro('A confirmação não bate com a nova senha.')
      return
    }

    setEnviando(true)
    try {
      const body: ChangePasswordRequest = { senha_atual: atual, senha_nova: nova }
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
