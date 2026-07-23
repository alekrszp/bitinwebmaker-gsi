import AgenteLogoIcon from './AgenteLogoIcon'

// URL de download do instalador -- endpoint público (sem login, ver
// backend/api/agente_sap.py) servido pelo próprio backend do BITin, então um <a> simples
// funciona sem precisar do client axios autenticado (mesma base de lib/api.ts, sem reusar o
// client em si).
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1'
const URL_DOWNLOAD_INSTALADOR = `${API_BASE_URL}/agente-sap/download`

// Instruções de instalação do agente SAP local (2026-07-23). Simplificado (achado real,
// pedido explícito: "retira a parte de verificar conexão deixa somente na outra. retira também
// a aba de já instalado pq tem na página antes") -- "Já instalado?"/"Abrir agente" e
// "Verificar conexão" ficaram DUPLICADOS depois que o gate (`AgenteGate.tsx`, a tela que
// aparece ANTES desta -- ver `BitinDetail.tsx`) ganhou os dois. Aqui fica só o fluxo de
// instalar do zero; verificar conexão/reabrir vivem só no gate.
export default function InstalarAgenteCard({ onVoltar }: { onVoltar: () => void }) {
  return (
    <div className="mx-auto max-w-xl">
      <button
        type="button"
        onClick={onVoltar}
        className="mb-4 text-sm text-ink-muted hover:text-ink hover:underline"
      >
        ← Voltar pro BITin
      </button>

      {/* Logo no topo (2026-07-23, pedido explícito: "aplica nos lugares que você achar
          legal") -- reforça a identidade visual do agente logo na tela onde ele é instalado. */}
      <div className="mb-4 flex justify-center">
        <AgenteLogoIcon size={72} />
      </div>

      <div className="rounded-xl border border-line bg-surface p-6">
        <h1 className="text-base font-semibold text-ink">Instalar o agente SAP</h1>
        <p className="mt-1 text-sm text-ink-muted">Não tem o agente instalado? Siga os passos abaixo.</p>

        <ol className="mt-4 divide-y divide-line">
          <li className="py-3">
            <p className="text-sm font-medium text-ink">1. Baixe o instalador</p>
            <a
              href={URL_DOWNLOAD_INSTALADOR}
              className="mt-2 inline-block rounded-lg bg-brand-navy px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-brand-navy-dark"
            >
              Baixar instalador (.exe)
            </a>
          </li>
          <li className="py-3">
            <p className="text-sm font-medium text-ink">2. Instale e ative</p>
            <p className="mt-1 text-sm text-ink-muted">
              Depois de feita a instalação, leia a aba "Leia-me" e ative o agente na aba
              "BITin".
            </p>
          </li>
          <li className="py-3">
            <p className="text-sm font-medium text-ink">3. Deixe o SAP aberto e logado</p>
            <p className="mt-1 text-sm text-ink-muted">
              O agente valida os códigos com o SAP GUI -- ele precisa estar aberto para o
              agente funcionar.
            </p>
          </li>
        </ol>
      </div>

      <p className="mt-4 text-center text-xs text-ink-muted">
        Já instalado? Procure "Agente SAP" no menu Iniciar do Windows pra abrir -- o sistema
        detecta a conexão sozinho, sem precisar verificar nada aqui.
      </p>
    </div>
  )
}
