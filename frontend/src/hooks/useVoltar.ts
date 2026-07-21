import { useCallback } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

// "Voltar" correto por tela (2026-07-21, revisão de navegação): antes, BitinDetail.tsx tinha
// o alvo do botão "Voltar" fixo em "/bitins", então chegar nele a partir de CadastroPage,
// ProcessosPage, PainelGeral ou da aba "Bitins Concluídos" de Settings.tsx sempre te devolvia
// pra "Meus Bitins", perdendo o filtro/aba de onde você realmente veio. `location.key` do
// react-router é "default" só na primeira entrada da sessão (sem histórico de navegação
// dentro do app pra voltar -- ex.: link direto/nova aba); qualquer outra navegação já tem uma
// entrada anterior própria, então `navigate(-1)` volta pra tela certa. `fallback` só é usado
// nesse caso raro de não ter pra onde voltar.
export function useVoltar(fallback: string) {
  const navigate = useNavigate()
  const location = useLocation()
  const podeVoltarNoHistorico = location.key !== 'default'

  return useCallback(() => {
    if (podeVoltarNoHistorico) navigate(-1)
    else navigate(fallback)
  }, [navigate, podeVoltarNoHistorico, fallback])
}
