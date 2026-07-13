import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import MaterialGrid from '../components/MaterialGrid'
import { api } from '../lib/api'

function blankForm() {
  return {
    setor: '',
    produto: '',
    motivo: '',
    solicitante: '',
    data_solicitacao: '',
    materiais: [],
  }
}

const SETORES = ['Proteína Animal', 'Armazenagem de Grãos']

export default function BitinDetail() {
  const { id } = useParams()
  const isNew = !id
  const navigate = useNavigate()

  const [mongoId, setMongoId] = useState(id)
  const [status, setStatus] = useState(isNew ? 'rascunho' : null)
  const [codigo, setCodigo] = useState(null)
  const [form, setForm] = useState(blankForm())
  const [resumo, setResumo] = useState(null)
  const [loading, setLoading] = useState(!isNew)
  const [saving, setSaving] = useState(false)
  const [enviarErrors, setEnviarErrors] = useState([])
  const [saveMessage, setSaveMessage] = useState(null)

  useEffect(() => {
    if (isNew) return
    let cancelado = false
    api
      .get(`/bitins/${id}`)
      .then((resp) => {
        if (cancelado) return
        setStatus(resp.data.status)
        setCodigo(resp.data.codigo)
        setForm({ ...blankForm(), ...resp.data.content })
        if (resp.data.status === 'enviado') {
          return api.get(`/bitins/${id}/resumo`).then((r) => setResumo(r.data))
        }
      })
      .finally(() => setLoading(false))
    return () => {
      cancelado = true
    }
  }, [id, isNew])

  function updateHeader(campo, valor) {
    setForm((atual) => ({ ...atual, [campo]: valor }))
  }

  function setMateriais(materiais) {
    setForm((atual) => ({ ...atual, materiais }))
  }

  async function handleSalvar() {
    setSaving(true)
    setSaveMessage(null)
    try {
      const resp = await api.post('/bitins/draft', {
        mongo_id: mongoId || undefined,
        content: form,
      })
      setMongoId(resp.data.mongo_id)
      setSaveMessage('Rascunho salvo.')
      if (isNew) navigate(`/bitins/${resp.data.mongo_id}`, { replace: true })
    } catch (err) {
      setSaveMessage(err.response?.data?.detail || 'Não foi possível salvar o rascunho.')
    } finally {
      setSaving(false)
    }
  }

  async function handleEnviar() {
    if (!mongoId) {
      setSaveMessage('Salve o rascunho antes de enviar.')
      return
    }
    setSaving(true)
    setEnviarErrors([])
    try {
      const resp = await api.post(`/bitins/${mongoId}/enviar`)
      if (resp.data.ok) {
        navigate(`/bitins/${mongoId}`, { replace: true })
        window.location.reload() // recarrega em modo visualização (enviado)
      } else {
        setEnviarErrors(resp.data.errors)
      }
    } catch {
      setEnviarErrors([{ field: '', message: 'Erro inesperado ao enviar.' }])
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <p className="text-gray-500">Carregando...</p>

  if (status === 'enviado') {
    return <BitinResumo codigo={codigo} resumo={resumo} />
  }

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold text-gray-900">
        {isNew ? 'Novo rascunho' : `Editar rascunho`}
      </h1>

      <div className="mb-6 grid grid-cols-1 gap-4 rounded border border-gray-200 bg-white p-4 sm:grid-cols-2">
        <Campo label="Setor">
          <select
            value={form.setor}
            onChange={(e) => updateHeader('setor', e.target.value)}
            className="w-full rounded border border-gray-300 px-3 py-2"
          >
            <option value="">Selecione...</option>
            {SETORES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </Campo>
        <Campo label="Produto">
          <input
            value={form.produto}
            onChange={(e) => updateHeader('produto', e.target.value)}
            className="w-full rounded border border-gray-300 px-3 py-2"
          />
        </Campo>
        <Campo label="Motivo">
          <input
            value={form.motivo}
            onChange={(e) => updateHeader('motivo', e.target.value)}
            className="w-full rounded border border-gray-300 px-3 py-2"
          />
        </Campo>
        <Campo label="Solicitante">
          <input
            value={form.solicitante}
            onChange={(e) => updateHeader('solicitante', e.target.value)}
            className="w-full rounded border border-gray-300 px-3 py-2"
          />
        </Campo>
        <Campo label="Data da solicitação">
          <input
            type="date"
            value={form.data_solicitacao}
            onChange={(e) => updateHeader('data_solicitacao', e.target.value)}
            className="w-full rounded border border-gray-300 px-3 py-2"
          />
        </Campo>
      </div>

      <div className="mb-6">
        <MaterialGrid materiais={form.materiais} onChange={setMateriais} errors={enviarErrors} />
      </div>

      {enviarErrors.length > 0 && (
        <div className="mb-4 rounded border border-red-300 bg-red-50 p-4">
          <p className="mb-2 font-medium text-red-800">
            Não foi possível enviar ({enviarErrors.length} erro{enviarErrors.length > 1 ? 's' : ''}) — as células com erro estão destacadas acima.
          </p>
          <ul className="list-inside list-disc text-sm text-red-700">
            {enviarErrors.map((e, i) => (
              <li key={i}>{e.message}</li>
            ))}
          </ul>
        </div>
      )}

      {saveMessage && <p className="mb-4 text-sm text-gray-600">{saveMessage}</p>}

      <div className="flex gap-3">
        <button
          onClick={handleSalvar}
          disabled={saving}
          className="rounded border border-gray-300 bg-white px-4 py-2 font-medium hover:bg-gray-100 disabled:opacity-50"
        >
          Salvar rascunho
        </button>
        <button
          onClick={handleEnviar}
          disabled={saving}
          className="rounded bg-brand-navy px-4 py-2 font-medium text-white hover:bg-brand-navy-dark disabled:opacity-50"
        >
          Enviar
        </button>
      </div>
    </div>
  )
}

function Campo({ label, children }) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-medium text-gray-700">{label}</span>
      {children}
    </label>
  )
}

function BitinResumo({ codigo, resumo }) {
  if (!resumo) return <p className="text-gray-500">Carregando resumo...</p>
  return (
    <div>
      <h1 className="mb-1 text-2xl font-semibold text-gray-900">{codigo}</h1>
      <p className="mb-6 text-sm text-green-700">Enviado — travado, sem edição.</p>

      <div className="mb-6 grid grid-cols-1 gap-4 rounded border border-gray-200 bg-white p-4 sm:grid-cols-2">
        <Info label="Setor" valor={resumo.setor} />
        <Info label="Produto" valor={resumo.produto} />
        <Info label="Motivo" valor={resumo.motivo} />
        <Info label="Solicitante" valor={resumo.solicitante} />
      </div>

      <div className="mb-6 rounded border border-gray-200 bg-white p-4">
        <h2 className="mb-3 text-lg font-medium text-gray-900">Materiais</h2>
        <ul className="divide-y divide-gray-100">
          {resumo.materiais.map((m, i) => (
            <li key={i} className="py-2 text-sm">
              <span className="font-medium">{m.codigo_material}</span> — {m.descricao_material} (centro{' '}
              {m.centro}, {m.tipo_material})
            </li>
          ))}
        </ul>
      </div>

      <div className="rounded border border-gray-200 bg-white p-4">
        <h2 className="mb-3 text-lg font-medium text-gray-900">Checklist</h2>
        <ul className="grid grid-cols-1 gap-1 text-sm sm:grid-cols-2">
          {resumo.checklist.map((item) => (
            <li key={item.id} className={item.afeta ? 'text-gray-900' : 'text-gray-400'}>
              {item.afeta ? '☑' : '☐'} {item.etapa}
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

function Info({ label, valor }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-gray-500">{label}</p>
      <p className="text-gray-900">{valor || '—'}</p>
    </div>
  )
}
