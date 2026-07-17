import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import StatusBadge from '../components/bitin/StatusBadge'
import { useAuth } from '../hooks/useAuth'
import { api } from '../lib/api'
import { criarRascunhoENavegar } from '../lib/criarBitin'
import type { Bitin, ResumoUsuario } from '../lib/types'

// Upgrade da Home (2026-07-14): "Meus Bitins" (listagem + detalhe + cadastro) já existe agora,
// então os dois motivos que antes seguravam recentes/ação rápida (nenhum lugar útil pra
// linkar) não valem mais -- ver docs/FRONTEND.md, decisão original da v0.7.1. Cartões de
// resumo viraram links pra listagem já filtrada por status; ganhou lista de recentes e botão
// "+ Novo BITin". Sem a faixa de 3 cores aqui -- fica só na sidebar e no login por enquanto
// (decisão do usuário, 2026-07-14).
export default function Home() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const primeiroNome = user?.nome?.split(' ')[0]
  const [resumo, setResumo] = useState<ResumoUsuario | null>(null)
  const [recentes, setRecentes] = useState<Bitin[] | null>(null)
  const [erroNovo, setErroNovo] = useState<string | null>(null)

  // "+ Novo BITin" cria o rascunho na hora e navega direto pro editor completo -- sem tela
  // intermediária em branco (ver lib/criarBitin.ts).
  async function novoBitin() {
    setErroNovo(null)
    try {
      await criarRascunhoENavegar(navigate)
    } catch {
      setErroNovo('Não foi possível criar um novo BITin. Tente novamente.')
    }
  }

  useEffect(() => {
    let cancelado = false
    api
      .get('/bitins/resumo-usuario')
      .then((resp) => {
        if (!cancelado) setResumo(resp.data)
      })
      .catch(() => {}) // falha silenciosa -- não é crítico o bastante pra mostrar erro numa tela de boas-vindas
    api
      .get('/bitins', { params: { limit: 5 } })
      .then((resp) => {
        if (!cancelado) setRecentes(resp.data)
      })
      .catch(() => {})
    return () => {
      cancelado = true
    }
  }, [])

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-ink text-balance sm:text-3xl">
            {primeiroNome ? `Bem-vindo, ${primeiroNome}` : 'Bem-vindo'}
          </h1>
          <p className="mt-1 text-sm text-ink-muted">Seu resumo de BITins e atividade recente.</p>
        </div>
        <button
          type="button"
          onClick={novoBitin}
          className="whitespace-nowrap rounded-lg bg-brand-navy px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-brand-navy-dark"
        >
          + Novo BITin
        </button>
      </div>

      {erroNovo && <p className="mt-2 text-sm text-red-600">{erroNovo}</p>}

      <div className="mt-6 flex flex-wrap gap-4">
        <StatCard label="Rascunhos" value={resumo?.rascunhos} to="/bitins?status=rascunho" />
        <StatCard label="Enviados" value={resumo?.enviados} to="/bitins?status=enviado" />
      </div>

      <div className="mt-8">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-ink-muted">Recentes</h2>
          <Link to="/bitins" className="text-sm text-ink-muted hover:text-ink hover:underline">
            Ver todos
          </Link>
        </div>

        {!recentes && <p className="mt-3 text-sm text-ink-muted">Carregando...</p>}
        {recentes && recentes.length === 0 && (
          <p className="mt-3 text-sm text-ink-muted">Nenhum BITin ainda -- crie o primeiro.</p>
        )}
        {recentes && recentes.length > 0 && (
          <div className="mt-3 overflow-hidden rounded-lg border border-line">
            <table className="w-full text-left text-sm">
              <tbody className="divide-y divide-line bg-surface">
                {recentes.map((b) => (
                  <tr key={b.mongo_id} className="hover:bg-surface-alt">
                    <td className="w-24 px-4 py-2.5 text-ink-muted">
                      <Link to={`/bitins/${b.mongo_id}`} className="block">
                        {b.codigo ?? '—'}
                      </Link>
                    </td>
                    <td className="px-4 py-2.5">
                      <Link to={`/bitins/${b.mongo_id}`} className="block text-ink hover:underline">
                        {String(b.content?.motivo ?? '—')}
                      </Link>
                    </td>
                    <td className="w-28 px-4 py-2.5">
                      <Link to={`/bitins/${b.mongo_id}`} className="block">
                        <StatusBadge status={b.status} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

function StatCard({ label, value, to }: { label: string; value: number | undefined; to: string }) {
  return (
    <Link
      to={to}
      className="min-w-[140px] rounded-lg border border-line bg-surface px-6 py-4 transition-colors hover:border-brand-navy/30 hover:bg-surface-alt"
    >
      <p className="text-3xl font-semibold text-ink">{value ?? '—'}</p>
      <p className="mt-1 text-xs font-medium uppercase tracking-wide text-ink-muted">{label}</p>
    </Link>
  )
}
