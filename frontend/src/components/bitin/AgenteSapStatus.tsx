import AgenteLogoIcon from './AgenteLogoIcon'

// Badge de status do agente SAP -- só o ícone, com um anel fino + um brilho suave atrás
// indicando o estado. Verde = conectado, vermelho = desconectado (clicável nesse caso, abre a
// tela de instalação). Mora na barra inferior (`EdicaoBottomBar.tsx`), junto das abas
// BITin/Automação que ele afeta.
//
// Tons diferentes por tema (2026-07-23, achado real: "ainda ta um verde muito escuro" -- o
// mesmo `brand-green/X%` de opacidade fica ilegível sobre o fundo escuro do tema dark, porque
// a cor da marca não muda entre temas (ver index.css) mas o fundo por trás sim; sem `dark:`
// mais forte, o verde quase desaparece no fundo preto). `dark:` funciona aqui porque o tema
// troca via classe `.dark` na raiz (`@custom-variant dark`, ver index.css), não media query.
export default function AgenteSapStatus({
  conectado,
  onClickDesconectado,
  size = 36,
}: {
  conectado: boolean
  onClickDesconectado?: () => void
  size?: number
}) {
  const titulo = conectado ? 'Agente SAP conectado' : 'Agente SAP desconectado — clique para ativar'
  // Classes completas e literais de propósito (nunca montadas por interpolação de string) --
  // o Tailwind precisa achar a classe inteira no código-fonte pra gerar o CSS dela; um
  // `from-${cor}/25` construído em runtime não aparece no CSS final.
  const gradienteAnel = conectado
    ? 'from-brand-green/25 to-brand-green/5 dark:from-brand-green/70 dark:to-brand-green/20'
    : 'from-red-500/25 to-red-500/5 dark:from-red-500/70 dark:to-red-500/20'

  const anel = (
    <span title={titulo} className="relative inline-flex">
      {/* Brilho atrás (2026-07-23, pedido explícito: "coloca alguma coisa por trás ali...
          algo sutil mas visível") -- disco desfocado, mais forte no tema escuro pro fundo
          preto não engolir a cor. */}
      <span
        className={`absolute inset-0 -z-10 rounded-xl blur-md ${
          conectado ? 'bg-brand-green/30 dark:bg-brand-green/50' : 'bg-red-500/30 dark:bg-red-500/50'
        }`}
      />
      <span className={`inline-flex rounded-xl bg-gradient-to-br p-[3px] ${gradienteAnel}`}>
        <span className="flex items-center justify-center rounded-lg bg-surface p-0.5">
          <AgenteLogoIcon size={size} status={conectado ? 'conectado' : 'desligado'} />
        </span>
      </span>
    </span>
  )

  if (conectado) return anel

  return (
    <button type="button" onClick={onClickDesconectado} aria-label={titulo}>
      {anel}
    </button>
  )
}
