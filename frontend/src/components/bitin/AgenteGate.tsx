import AjudaPopover from './AjudaPopover'
import AgenteLogoIcon from './AgenteLogoIcon'

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
}: {
  onConfirmarManual: () => void
  onAbrirInstalacao: () => void
}) {
  return (
    <div className="flex min-h-[60vh] items-center justify-center px-4 py-10">
      {/* Sem overflow-hidden no card inteiro (2026-07-23, achado real: cortava o popover de
          ajuda, que precisa "vazar" pra fora do card pra ser legível) -- só a faixa colorida no
          topo precisa dos cantos arredondados clipados, o resto do card não. */}
      <div className="w-full max-w-lg rounded-2xl border border-line bg-surface shadow-sm">
        <div className="h-1.5 w-full rounded-t-2xl bg-gradient-to-r from-brand-navy via-brand-green to-brand-gold" />

        <div className="flex items-center gap-5 p-7">
          <AgenteLogoIcon size={64} />
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

        <p className="px-7 pb-6 pt-3 text-xs text-ink-muted">
          Se não tiver instalado, clique em "Instalar o agente SAP". Com o agente rodando, o
          preenchimento dos materiais e da lista técnica é automático.
        </p>
      </div>
    </div>
  )
}
