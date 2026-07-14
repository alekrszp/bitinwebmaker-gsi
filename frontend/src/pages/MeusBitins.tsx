import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import type { Bitin } from '../lib/types'

// Escopo desta rodada (decidido com o usuário, ver docs/FRONTEND.md): listagem + clique na
// linha abre uma visualização só-leitura (BitinDetail.tsx) -- ainda sem edição nem botão
// "+ Novo BITin" (não existe tela de cadastro ainda). GET /bitins já vem escopado pro próprio
// usuário no backend ("só os meus", mesma decisão do resumo da Home).
type Aba = 'todos' | 'rascunho' | 'enviado'

const ABAS: { value: Aba; label: string }[] = [
  { value: 'todos', label: 'Todos' },
  { value: 'rascunho', label: 'Rascunhos' },
  { value: 'enviado', label: 'Enviados' },
]

export default function MeusBitins() {
  const [aba, setAba] = useState<Aba>('todos')
  const [bitins, setBitins] = useState<Bitin[] | null>(null)
  const [erro, setErro] = useState<string | null>(null)

  useEffect(() => {
    let cancelado = false
    setBitins(null)
    setErro(null)
    api
      .get('/bitins', { params: aba === 'todos' ? {} : { status: aba } })
      .then((resp) => {
        if (!cancelado) setBitins(resp.data)
      })
      .catch(() => {
        if (!cancelado) setErro('Não foi possível carregar os BITins.')
      })
    return () => {
      cancelado = true
    }
  }, [aba])

  return (
    <div>
      <h1 className="text-2xl font-semibold text-ink">Meus Bitins</h1>

      <div className="mt-4 flex gap-1 border-b border-line">
        {ABAS.map(({ value, label }) => (
          <button
            key={value}
            type="button"
            onClick={() => setAba(value)}
            className={`-mb-px border-b-2 px-3 py-2 text-sm font-medium transition-colors ${
              aba === value
                ? 'border-brand-navy text-ink'
                : 'border-transparent text-ink-muted hover:text-ink'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {erro && <p className="mt-4 text-sm text-red-600">{erro}</p>}
      {!bitins && !erro && <p className="mt-4 text-sm text-ink-muted">Carregando...</p>}
      {bitins && bitins.length === 0 && !erro && (
        <p className="mt-4 text-sm text-ink-muted">Nenhum BITin encontrado.</p>
      )}

      {bitins && bitins.length > 0 && (
        <div className="mt-4 overflow-hidden rounded-lg border border-line">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="bg-surface-alt text-xs uppercase tracking-wide text-ink-muted">
                <th className="px-4 py-2 font-medium">Código</th>
                <th className="px-4 py-2 font-medium">Motivo</th>
                <th className="px-4 py-2 font-medium">Solicitante</th>
                <th className="px-4 py-2 font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line bg-surface">
              {bitins.map((b) => (
                <tr key={b.mongo_id}>
                  <td className="px-4 py-2">
                    <Link to={`/bitins/${b.mongo_id}`} className="block text-ink hover:underline">
                      {b.codigo ?? '—'}
                    </Link>
                  </td>
                  <td className="px-4 py-2 text-ink-muted">
                    <Link to={`/bitins/${b.mongo_id}`} className="block">
                      {String(b.content?.motivo ?? '—')}
                    </Link>
                  </td>
                  <td className="px-4 py-2 text-ink-muted">
                    <Link to={`/bitins/${b.mongo_id}`} className="block">
                      {String(b.content?.solicitante ?? '—')}
                    </Link>
                  </td>
                  <td className="px-4 py-2">
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
  )
}

function StatusBadge({ status }: { status: string }) {
  const enviado = status === 'enviado'
  return (
    <span
      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${
        enviado ? 'bg-brand-green/15 text-brand-green' : 'bg-brand-gold/15 text-brand-gold'
      }`}
    >
      {enviado ? 'Enviado' : 'Rascunho'}
    </span>
  )
}
