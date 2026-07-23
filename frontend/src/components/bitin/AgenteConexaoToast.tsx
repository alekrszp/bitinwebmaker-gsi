import { useEffect, useRef, useState } from 'react'
import AgenteLogoIcon from './AgenteLogoIcon'

// Toast curto quando o status do agente MUDA (2026-07-23, pedido explícito -- item que tinha
// ficado em aberto no redesign da logo). Não é um sistema de notificação genérico (o app ainda
// não tem um) -- é só este componente, de propósito único, escutando a transição do próprio
// `useAgenteSapConectado()`.
//
// Nunca dispara na 1ª resolução (`verificado` virando `true` pela primeira vez) -- só a partir
// da 2ª mudança de verdade. Isso evita 2 falsos positivos: (1) abrir a tela já com o agente
// conectado não deveria anunciar "conectado" como se tivesse acabado de acontecer; (2) navegar
// entre BITin/Automação/Preenchimento remonta este componente (são páginas diferentes), então
// sem essa guarda a 1ª resolução de CADA navegação disparia um toast, mesmo sem nada ter
// mudado de verdade.
export default function AgenteConexaoToast({ conectado, verificado }: { conectado: boolean; verificado: boolean }) {
  const anteriorRef = useRef<boolean | null>(null)
  const [mensagem, setMensagem] = useState<{ texto: string; status: 'conectado' | 'desligado' } | null>(null)

  useEffect(() => {
    if (!verificado) return
    if (anteriorRef.current === null) {
      anteriorRef.current = conectado
      return
    }
    if (anteriorRef.current === conectado) return
    anteriorRef.current = conectado
    setMensagem({
      texto: conectado ? 'Agente SAP conectado' : 'Agente SAP desconectado',
      status: conectado ? 'conectado' : 'desligado',
    })
    const timer = setTimeout(() => setMensagem(null), 4000)
    return () => clearTimeout(timer)
  }, [conectado, verificado])

  if (!mensagem) return null

  return (
    <div
      className="fixed bottom-20 right-4 z-30 flex items-center gap-2 rounded-xl border border-line bg-surface px-3 py-2 shadow-lg"
      style={{ animation: 'agente-toast-entrar 0.2s ease-out' }}
    >
      <AgenteLogoIcon size={28} status={mensagem.status} />
      <span className="text-sm font-medium text-ink">{mensagem.texto}</span>
    </div>
  )
}
