import { useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import AgenteConexaoToast from '../components/bitin/AgenteConexaoToast'
import AgenteLogoIcon from '../components/bitin/AgenteLogoIcon'
import EdicaoBottomBar from '../components/bitin/EdicaoBottomBar'
import { useAgenteSapConectado } from '../hooks/useAgenteSapConectado'
import { useFaviconAgente } from '../hooks/useFaviconAgente'
import { useEnviarBitin } from '../lib/useEnviarBitin'

// Aba "Automação" (2026-07-23) -- só existe com o agente SAP conectado, no lugar da antiga
// ZBPP009/Lista Técnica (removidas). Os COMANDOS do agente (buscar material, preencher campos
// etc.) ficam aqui, no sistema web -- decisão explícita do usuário: "quero algo seguro e com
// validações", a janela do próprio agente (sap-agent/agente_app.py) é só status/configuração,
// nunca comando. Stub por enquanto: só a casca (cabeçalho + barra inferior) -- o fluxo de
// verdade (colar códigos, o agente busca o "de", engenheiro declara o "para") vai ser
// construído do zero numa próxima rodada, ver mockup aprovado na conversa.
export default function AutomacaoPage() {
  const { mongoId } = useParams<{ mongoId: string }>()
  const navigate = useNavigate()
  const { conectado: agenteConectado, verificado } = useAgenteSapConectado()
  const { enviando, enviar } = useEnviarBitin(mongoId)
  useFaviconAgente(verificado ? (agenteConectado ? 'conectado' : 'desligado') : undefined)

  // Se o agente cair enquanto o engenheiro está nesta aba, não faz sentido continuar aqui --
  // volta pro BITin manual (mesma regra de fallback do gate, ver BitinDetail.tsx). Só decide
  // depois da 1ª checagem resolver (`verificado`), senão redirecionaria sempre de cara.
  useEffect(() => {
    if (verificado && !agenteConectado) navigate(`/bitins/${mongoId}`, { replace: true })
  }, [agenteConectado, verificado, mongoId, navigate])

  return (
    <div className="mx-auto max-w-[1600px] pb-24">
      <button
        type="button"
        onClick={() => navigate(`/bitins/${mongoId}`)}
        className="text-sm text-ink-muted hover:text-ink hover:underline"
      >
        ← Voltar pro BITin
      </button>

      <div className="mt-3 flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-semibold text-ink">Automação</h1>
      </div>

      {/* Logo grande preenchendo o vazio (2026-07-23, pedido explícito: "aplica nos lugares que
          você achar legal") -- em vez de só o texto "Em construção" sozinho na tela. */}
      <div className="mt-10 flex flex-col items-center gap-3 text-center">
        <AgenteLogoIcon size={112} status="conectado" />
        <p className="text-sm text-ink-muted">Em construção.</p>
      </div>

      {mongoId && (
        <EdicaoBottomBar mongoId={mongoId} agenteConectado={agenteConectado} enviando={enviando} onEnviar={enviar} />
      )}
      <AgenteConexaoToast conectado={agenteConectado} verificado={verificado} />
    </div>
  )
}
