import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'

const ABAS = [
  { id: 'todos', label: 'Todos', status: null },
  { id: 'rascunho', label: 'Rascunhos', status: 'rascunho' },
  { id: 'enviado', label: 'Enviados', status: 'enviado' },
]

export default function MeusBitins() {
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
        <h1 className="text-2xl font-semibold text-gray-900">Meus Bitins</h1>
        <Link
          to="/bitins/novo"
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
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
                aba === a.id ? 'bg-blue-600 text-white' : 'bg-white text-gray-700 border border-gray-300'
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
            className="rounded border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
          />
          <button type="submit" className="rounded border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-100">
            Buscar
          </button>
        </form>
      </div>

      {loading && <p className="text-gray-500">Carregando...</p>}
      {error && <p className="text-red-600">{error}</p>}

      {!loading && !error && bitins.length === 0 && (
        <p className="text-gray-500">Nenhum BITin encontrado.</p>
      )}

      <ul className="divide-y divide-gray-200 rounded border border-gray-200 bg-white">
        {bitins.map((b) => (
          <li key={b.mongo_id} className="flex items-center justify-between px-4 py-3">
            <div>
              <p className="font-medium text-gray-900">
                {b.codigo || b.titulo || 'Rascunho sem título'}
              </p>
              <p className="text-sm text-gray-500">
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
                className="rounded border border-gray-300 px-3 py-1 text-sm hover:bg-gray-100"
              >
                {b.status === 'enviado' ? 'Visualizar' : 'Editar'}
              </Link>
              {b.status === 'rascunho' && (
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
