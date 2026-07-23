import { useState } from 'react'
import { abrirAgenteViaProtocolo, consultarStatusAgente } from '../../lib/sapAgent'

// URL de download do instalador -- endpoint público (sem login, ver
// backend/api/agente_sap.py) servido pelo próprio backend do BITin, então um <a> simples
// funciona sem precisar do client axios autenticado (mesma base de lib/api.ts, sem reusar o
// client em si).
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1'
const URL_DOWNLOAD_INSTALADOR = `${API_BASE_URL}/agente-sap/download`

// Instruções de instalação do agente SAP local (2026-07-23) -- 2 cards separados: "já
// instalado" (reabrir) vs. "instalar do zero", pedido explícito do usuário com o texto exato
// de cada um.
export default function InstalarAgenteCard({ onVoltar }: { onVoltar: () => void }) {
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
    <div className="mx-auto max-w-xl">
      <button
        type="button"
        onClick={onVoltar}
        className="mb-4 text-sm text-ink-muted hover:text-ink hover:underline"
      >
        ← Voltar pro BITin
      </button>

      {/* Card 1: já instalado antes, só precisa reabrir -- dispara o protocolo bitinsap://
          registrado na instalação, não baixa nem instala nada de novo. */}
      <div className="mb-4 rounded-xl border border-line bg-surface-alt p-6">
        <h1 className="text-base font-semibold text-ink">Já instalado?</h1>
        <p className="mt-1 text-sm text-ink-muted">
          Se o agente já foi instalado, abra novamente, que o sistema vai reconhecê-lo
          automaticamente.
        </p>
        <button
          type="button"
          onClick={abrirAgenteViaProtocolo}
          className="mt-3 rounded-lg border border-line bg-surface px-4 py-2 text-sm font-medium text-ink transition-colors hover:bg-surface-alt"
        >
          Abrir agente
        </button>
      </div>

      {/* Card 2: instalar do zero. */}
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
          <li className="py-3">
            <p className="text-sm font-medium text-ink">4. Verifique a conexão</p>
            <p className="mt-1 text-sm text-ink-muted">
              Com o agente rodando, o sistema detecta sozinho. Mas confirme sua conexão agora
              mesmo.
            </p>
            <button
              type="button"
              onClick={verificarConexao}
              disabled={verificando}
              className="mt-2 rounded-lg border border-line px-3 py-1.5 text-sm font-medium text-ink transition-colors hover:bg-surface-alt disabled:cursor-not-allowed disabled:opacity-60"
            >
              {verificando ? 'Verificando...' : 'Verificar conexão'}
            </button>
            {resultado === 'ok' && (
              <p className="mt-2 text-sm text-brand-green">Agente encontrado! Pode voltar pro BITin.</p>
            )}
            {resultado === 'falhou' && (
              <p className="mt-2 text-sm text-red-600">
                Não encontrou o agente ainda. Confira se ele está rodando e tente de novo.
              </p>
            )}
          </li>
        </ol>
      </div>
    </div>
  )
}
