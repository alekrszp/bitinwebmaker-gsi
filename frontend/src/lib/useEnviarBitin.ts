import { useState } from 'react'
import { api } from './api'
import type { Bitin } from './types'

interface ErroEnvio {
  field: string
  code: string
  message: string
}

// Compartilhado entre a página principal de edição e as páginas de Códigos SAP/Lista
// Técnica (components/bitin/EdicaoBottomBar.tsx) -- o engenheiro pode clicar em "Enviar" de
// qualquer uma das 3 (é a mesma barra fixa nas três), então a lógica de enviar não pode viver
// só numa delas. Ver docs/FRONTEND.md, decisão de 2026-07-14 ("nova aba, outra página").
//
// Não navega mais sozinho (2026-07-16, pedido do usuário: "coloque uma informação na tela de
// quando envia bitin de confirmação que atualize a pagina e vai direto no bitin já enviado").
// `navigate(mongoId)` era um no-op quando o clique já acontecia em BitinDetail (mesma URL, o
// React Router não remonta) -- a tela ficava com a UI editável desatualizada até um F5 manual.
// Agora o hook só expõe o BITin já enviado (resp.data.bitin, resposta de POST .../enviar já
// traz o código novo e o content atualizado) e cada página decide o que fazer: BitinDetail
// atualiza o próprio estado in-place (mesma URL, sem reload); Códigos SAP/Lista Técnica
// navegam pra `/bitins/:mongoId` (mesma ideia de "Importar pra BITin" que elas já tinham).
export function useEnviarBitin(mongoId: string | undefined) {
  const [enviando, setEnviando] = useState(false)
  const [errosEnvio, setErrosEnvio] = useState<ErroEnvio[]>([])
  const [bitinEnviado, setBitinEnviado] = useState<Bitin | null>(null)

  async function enviar() {
    if (!mongoId) return
    setErrosEnvio([])
    setEnviando(true)
    try {
      const resp = await api.post(`/bitins/${mongoId}/enviar`)
      if (resp.data.ok) {
        setBitinEnviado(resp.data.bitin ?? null)
      } else {
        setErrosEnvio(resp.data.errors ?? [])
      }
    } catch {
      setErrosEnvio([{ field: '', code: 'erro_rede', message: 'Não foi possível enviar. Tente novamente.' }])
    } finally {
      setEnviando(false)
    }
  }

  return { enviando, errosEnvio, bitinEnviado, enviar }
}
