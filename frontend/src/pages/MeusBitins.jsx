import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { api } from '../lib/api'

const ABAS = [
  { id: 'todos', label: 'Todos', status: null },
  { id: 'rascunho', label: 'Rascunhos', status: 'rascunho' },
  { id: 'enviado', label: 'Enviados', status: 'enviado' },
]

// Espelha backend/api/bitins.py::ADMIN_LEVEL -- só usado aqui pra esconder a ação de
// excluir que o backend já recusaria com 403 (reforço de dono, ver docs/BACKEND.md).
const ADMIN_LEVEL = 99

function podeExcluir(bitin, user) {
  if (!user) return false
  if (user.permission_level >= ADMIN_LEVEL) return true
  // criado_por nulo = rascunho sem dono registrado (formato antigo) -- backend não bloqueia.
  return !bitin.criado_por || bitin.criado_por === user.email
}

export default function MeusBitins() {
  const { user } = useAuth()
  const [aba, setAba] = useState('todos')
  const [termo, setTermo] = useState('')
  const [bitins, setBitins] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  async function carregar() {
    setLoading(true)
    setError(null)
    try {
      const abaAtiva = ABAS.find((a) => a.id === aba)
      const params = {}
      if (abaAtiva.status) params.status = abaAtiva.status
      if (termo) params.termo = termo
      const resp = await api.get('/bitins', { params })
      setBitins(resp.data)
    } catch {
      setError('Não foi possível carregar os BITins.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    carregar()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [aba])

  async function handleExcluir(mongoId) {
    if (!window.confirm('Excluir este rascunho?')) return
    try {
      await api.delete(`/bitins/${mongoId}`)
      setBitins((atual) => atual.filter((b) => b.mongo_id !== mongoId))
    } catch {
      window.alert('Não foi possível excluir (só o dono ou um admin pode).')
    }
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-ink">Meus Bitins</h1>
        <Link
          to="/bitins/novo"
          className="rounded bg-brand-navy px-4 py-2 text-sm font-medium text-white hover:bg-brand-navy-dark"
        >
          + Novo rascunho
        </Link>
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-4">
        <div className="flex gap-2">
          {ABAS.map((a) => (
            <button
              key={a.id}
              onClick={() => setAba(a.id)}
              className={`rounded px-3 py-1.5 text-sm font-medium ${
                aba === a.id ? 'bg-brand-navy text-white' : 'bg-surface text-ink border border-line'
              }`}
            >
              {a.label}
            </button>
          ))}
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            carregar()
          }}
          className="flex gap-2"
        >
          <input
            type="search"
            placeholder="Buscar por motivo, solicitante, número..."
            value={termo}
            onChange={(e) => setTermo(e.target.value)}
            className="rounded border border-line bg-surface px-3 py-1.5 text-sm text-ink focus:border-brand-navy focus:outline-none"
          />
          <button type="submit" className="rounded border border-line px-3 py-1.5 text-sm text-ink hover:bg-surface-alt">
            Buscar
          </button>
        </form>
      </div>

      {loading && <p className="text-ink-muted">Carregando...</p>}
      {error && <p className="text-red-600">{error}</p>}

      {!loading && !error && bitins.length === 0 && (
        <p className="text-ink-muted">Nenhum BITin encontrado.</p>
      )}

      <ul className="divide-y divide-line rounded border border-line bg-surface">
        {bitins.map((b) => (
          <li key={b.mongo_id} className="flex items-center justify-between px-4 py-3">
            <div>
              <p className="font-medium text-ink">
                {b.codigo || b.titulo || 'Rascunho sem título'}
              </p>
              <p className="text-sm text-ink-muted">
                {b.content?.motivo || '—'} · {b.content?.solicitante || '—'} ·{' '}
                <span
                  className={
                    b.status === 'enviado' ? 'text-green-700' : 'text-amber-700'
                  }
                >
                  {b.status}
                </span>
              </p>
            </div>
            <div className="flex gap-2">
              <Link
                to={`/bitins/${b.mongo_id}`}
                className="rounded border border-line px-3 py-1 text-sm text-ink hover:bg-surface-alt"
              >
                {b.status === 'enviado' ? 'Visualizar' : 'Editar'}
              </Link>
              {b.status === 'rascunho' && podeExcluir(b, user) && (
                <button
                  onClick={() => handleExcluir(b.mongo_id)}
                  className="rounded border border-red-300 px-3 py-1 text-sm text-red-700 hover:bg-red-50"
                >
                  Excluir
                </button>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}
