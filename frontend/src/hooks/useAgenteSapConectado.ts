import { useEffect, useState } from 'react'
import { consultarStatusAgente } from '../lib/sapAgent'

// Estado de conexão do agente SAP local -- fonte única de verdade usada tanto pra decidir se o
// BITin abre no modo manual (gate) ou automação, quanto pro badge na barra inferior (ver
// EdicaoBottomBar.tsx, BitinDetail.tsx).
//
// Poll a cada ~4s (2026-07-23, pedido explícito: "quando é ativado ou desativado o agente, não
// precise recarregar a página para atualizar" -- os 15s de antes já atualizavam sozinhos, sem
// reload nenhum, mas a demora dava a impressão de que precisava recarregar). PLUS: checagem
// extra imediata sempre que a aba do navegador ganha foco de novo (`visibilitychange`) -- o
// caso mais comum é o engenheiro alternar pra janela do agente, ligar/desligar o checkbox "Agente
// ativo", e voltar pro navegador -- sem isso, dava pra esperar até 4s parado olhando pro badge
// desatualizado mesmo já tendo voltado.
//
// `verificado` distingue "ainda não checou" de "checou e não achou" -- sem isso, o gate de
// "agente não identificado" piscaria na tela por uma fração de segundo toda vez que o agente
// ESTÁ conectado (o estado inicial de `conectado` é `false` até a 1ª checagem resolver).
export function useAgenteSapConectado(): { conectado: boolean; verificado: boolean } {
  const [conectado, setConectado] = useState(false)
  const [verificado, setVerificado] = useState(false)

  useEffect(() => {
    let cancelado = false
    async function checar() {
      const ok = await consultarStatusAgente()
      if (!cancelado) {
        setConectado(ok)
        setVerificado(true)
      }
    }
    checar()
    const intervalo = setInterval(checar, 4000)

    function aoFocarAba() {
      if (document.visibilityState === 'visible') checar()
    }
    document.addEventListener('visibilitychange', aoFocarAba)
    window.addEventListener('focus', aoFocarAba)

    return () => {
      cancelado = true
      clearInterval(intervalo)
      document.removeEventListener('visibilitychange', aoFocarAba)
      window.removeEventListener('focus', aoFocarAba)
    }
  }, [])

  return { conectado, verificado }
}
