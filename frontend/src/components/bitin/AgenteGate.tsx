import { useState } from 'react'
import AjudaPopover from './AjudaPopover'
import AgenteLogoIcon from './AgenteLogoIcon'
import { abrirAgenteViaProtocolo, consultarStatusAgente } from '../../lib/sapAgent'

// Tela exibida ao abrir um BITin novo (rascunho 100% vazio) sem o agente SAP identificado
// (2026-07-23, pedido explícito do usuário). Só pergunta uma vez -- clicar "Sim" libera o modo
// manual normal (BitinDetail sem nenhuma restrição, só sem a aba Automação na barra inferior).
//
// Layout horizontal (2026-07-23, revisão: "refaz o layout dela, mesma ideia mas UI diferente")
// -- logo ao lado do título (em vez de empilhado/centralizado), faixa de 3 cores no topo do
// card (mesmo acento decorativo do cabeçalho do app, ver docs/FRONTEND.md "Identidade
// visual"), e as 2 ações lado a lado numa faixa de rodapé em vez de empilhadas com um "ou".
//
// Hierarquia visual dos 2 botões invertida de propósito (2026-07-23, pedido explícito: "coloca
// o instalar o agente SAP com a cor cinza, e fazer manualmente apagada, para induzir o usuário
// a instalar") -- "Instalar" é o botão sólido/visível, "fazer manualmente" vira só texto,
// discreto, pra não competir visualmente.
export default function AgenteGate({
  onConfirmarManual,
  onAbrirInstalacao,
  onAcessarComAgente,
}: {
  onConfirmarManual: () => void
  onAbrirInstalacao: () => void
  // Separado de `onConfirmarManual` (2026-07-23, achado real corrigindo a persistência do modo
  // manual): os dois botões chamavam a MESMA função, então "Acessar bitin" (agente confirmado
  // conectado) marcava esta tela como "manual pra sempre" junto -- bug real, o BITin ficava
  // preso no modo manual mesmo com o agente funcionando. `onAcessarComAgente` só dispensa a
  // tela desta vez, sem persistir nada -- o agente conectado é quem decide o resto sozinho.
  onAcessarComAgente: () => void
}) {
  // "Verificar conexão" (2026-07-23, pedido explícito) -- pra quem já tem o agente instalado e
  // ativo mas caiu nesta tela (1ª checagem ainda não resolveu, ou o agente acabou de ser
  // ativado agora mesmo); evita ter que clicar em "Instalar o agente SAP" só pra confirmar que
  // já está tudo certo. Não decide nada sozinho -- `useAgenteSapConectado.ts` continua sendo a
  // fonte única de verdade que faz esta tela sumir sozinha (poll ~4s); isso aqui é só feedback
  // imediato pro clique, mesmo padrão já usado em InstalarAgenteCard.tsx.
  const [verificando, setVerificando] = useState(false)
  const [resultado, setResultado] = useState<'ok' | 'falhou' | null>(null)

  async function verificarConexao() {
    setVerificando(true)
    setResultado(null)
    const ok = await consultarStatusAgente()
    setResultado(ok ? 'ok' : 'falhou')
    setVerificando(false)
  }

  return (
    <div className="flex min-h-[60vh] items-center justify-center px-4 py-10">
      {/* Sem overflow-hidden no card inteiro (2026-07-23, achado real: cortava o popover de
          ajuda, que precisa "vazar" pra fora do card pra ser legível) -- só a faixa colorida no
          topo precisa dos cantos arredondados clipados, o resto do card não. */}
      <div className="w-full max-w-lg rounded-2xl border border-line bg-surface shadow-sm">
        <div className="h-1.5 w-full rounded-t-2xl bg-gradient-to-r from-brand-navy via-brand-green to-brand-gold" />

        <div className="flex items-center gap-5 p-7">
          <AgenteLogoIcon size={64} status={resultado === 'ok' ? 'conectado' : resultado === 'falhou' ? 'desligado' : undefined} />
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-semibold text-ink">Agente SAP não identificado</h1>
              <AjudaPopover titulo="O que é o Agente SAP?">
                <p>
                  Um programa pequeno que roda no seu computador e conversa com o SAP GUI que
                  você já tem aberto e logado -- ele confere se um código de material existe e
                  traz dados reais do SAP direto pro BITin, sem precisar copiar/colar na mão.
                </p>
                <p>É opcional: sem ele, o BITin continua funcionando 100% manual.</p>
              </AjudaPopover>
            </div>
            <p className="mt-1 text-sm text-ink-muted">Deseja realizar o BITin manualmente?</p>
          </div>
        </div>

        <div className="flex flex-col gap-2 border-t border-line bg-surface-alt p-5 sm:flex-row">
          <button
            type="button"
            onClick={onAbrirInstalacao}
            className="flex-1 rounded-lg bg-ink-muted px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:opacity-90"
          >
            Instalar o agente SAP
          </button>
          <button
            type="button"
            onClick={onConfirmarManual}
            className="flex-1 rounded-lg border border-line bg-transparent px-4 py-2.5 text-sm font-medium text-ink-faint transition-colors hover:bg-surface"
          >
            Sim, fazer manualmente
          </button>
        </div>

        <div className="px-7 pb-6 pt-3">
          <p className="text-xs text-ink-muted">
            Se não tiver instalado, clique em "Instalar o agente SAP". Caso já tenha instalado,
            clique em "Abrir agente", para ativá-lo. Com ele ativado pode verificar a conexão em
            "Verificar conexão", com ele validado, pode acessar o bitin no botão abaixo.
          </p>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={abrirAgenteViaProtocolo}
              className="rounded-lg border border-line px-3 py-1.5 text-xs font-medium text-ink transition-colors hover:bg-surface-alt"
            >
              Abrir agente
            </button>
            <button
              type="button"
              onClick={verificarConexao}
              disabled={verificando}
              className="rounded-lg border border-line px-3 py-1.5 text-xs font-medium text-ink transition-colors hover:bg-surface-alt disabled:cursor-not-allowed disabled:opacity-60"
            >
              {verificando ? 'Verificando...' : 'Verificar conexão'}
            </button>
            {resultado === 'falhou' && (
              <p className="text-xs text-red-600">Não encontrou o agente ainda.</p>
            )}
          </div>
          {/* "Acessar bitin" (2026-07-23, pedido explícito) -- só aparece depois de verificar
              com sucesso, pra não convidar a pular a checagem. */}
          {resultado === 'ok' && (
            <div className="mt-3 rounded-lg border border-brand-green/30 bg-brand-green/10 p-3">
              <p className="text-xs text-brand-green">Agente encontrado!</p>
              <button
                type="button"
                onClick={onAcessarComAgente}
                className="mt-2 rounded-lg bg-brand-green px-3 py-1.5 text-xs font-semibold text-white transition-colors hover:opacity-90"
              >
                Acessar bitin
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
