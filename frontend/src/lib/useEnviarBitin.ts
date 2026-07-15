import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from './api'

interface ErroEnvio {
  field: string
  code: string
  message: string
}

// Compartilhado entre a página principal de edição e as páginas de Códigos SAP/Lista
// Técnica (components/bitin/EdicaoBottomBar.tsx) -- o engenheiro pode clicar em "Enviar" de
// qualquer uma das 3 (é a mesma barra fixa nas três), então a lógica de enviar não pode viver
// só numa delas. Ver docs/FRONTEND.md, decisão de 2026-07-14 ("nova aba, outra página").
export function useEnviarBitin(mongoId: string | undefined) {
  const navigate = useNavigate()
  const [enviando, setEnviando] = useState(false)
  const [errosEnvio, setErrosEnvio] = useState<ErroEnvio[]>([])

  async function enviar() {
    if (!mongoId) return
    setErrosEnvio([])
    setEnviando(true)
    try {
      const resp = await api.post(`/bitins/${mongoId}/enviar`)
      if (resp.data.ok) {
        navigate(`/bitins/${mongoId}`)
      } else {
        setErrosEnvio(resp.data.errors ?? [])
      }
    } catch {
      setErrosEnvio([{ field: '', code: 'erro_rede', message: 'Não foi possível enviar. Tente novamente.' }])
    } finally {
      setEnviando(false)
    }
  }

  return { enviando, errosEnvio, enviar }
}
