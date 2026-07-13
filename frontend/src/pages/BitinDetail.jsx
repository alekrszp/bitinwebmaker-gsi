import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import ChecklistEditor from '../components/ChecklistEditor'
import MaterialGrid from '../components/MaterialGrid'
import { api } from '../lib/api'

function blankForm() {
  return {
    setor: '',
    produto: '',
    motivo: '',
    solicitante: '',
    data_solicitacao: '',
    bitex: 'NÃO',
    checklist: [],
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

  function setChecklist(checklist) {
    setForm((atual) => ({ ...atual, checklist }))
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

  if (loading) return <p className="text-ink-muted">Carregando...</p>

  if (status === 'enviado') {
    return <BitinResumo codigo={codigo} resumo={resumo} />
  }

  return (
    <div>
      <div className="mx-auto max-w-6xl">
      {/* Cabeçalho -- réplica da aba "Template apresentação" da planilha real do BITin:
          logo/título/BITex/Setor na linha 1, Produto/Solicitante e Motivo/Data abaixo. */}
      <div className="mb-6 overflow-hidden rounded border border-line">
        <div className="grid grid-cols-12 border-b border-line">
          <div className="col-span-3 flex items-center justify-center bg-white px-2 py-2 text-center sm:col-span-2">
            <img src="/logo.svg" className="max-h-14 w-full object-contain" alt="Grain & Protein Technologies" />
          </div>
          <div className="col-span-9 flex items-center justify-center bg-brand-navy px-2 py-3 sm:col-span-5">
            <span className="text-center text-sm font-bold uppercase tracking-wide text-white">
              Boletim de Informações Técnicas Interno (BITIn)
            </span>
          </div>
          <div className="col-span-6 flex items-center justify-center gap-2 px-2 py-2 sm:col-span-2">
            <span className="text-xs font-medium text-ink-muted">BITex</span>
            <select
              value={form.bitex}
              onChange={(e) => updateHeader('bitex', e.target.value)}
              className="rounded border border-line bg-surface px-2 py-1 text-sm font-bold text-red-600 focus:outline-none focus:ring-2 focus:ring-brand-navy"
            >
              <option value="NÃO">NÃO</option>
              <option value="SIM">SIM</option>
            </select>
          </div>
          <div className="col-span-6 flex items-center justify-center bg-brand-gold px-2 py-3 sm:col-span-3">
            <select
              value={form.setor}
              onChange={(e) => updateHeader('setor', e.target.value)}
              className="w-full bg-transparent text-center text-sm font-bold text-brand-navy focus:outline-none"
            >
              <option value="">Selecione o setor...</option>
              {SETORES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="grid grid-cols-1 border-b border-line sm:grid-cols-2">
          <CampoInline label="Produto">
            <input
              value={form.produto}
              onChange={(e) => updateHeader('produto', e.target.value)}
              className="w-full bg-transparent px-2 py-2 text-sm text-ink focus:outline-none"
            />
          </CampoInline>
          <CampoInline label="Solicitante" borda>
            <input
              value={form.solicitante}
              onChange={(e) => updateHeader('solicitante', e.target.value)}
              className="w-full bg-transparent px-2 py-2 text-sm text-ink focus:outline-none"
            />
          </CampoInline>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2">
          <CampoInline label="Motivo">
            <input
              value={form.motivo}
              onChange={(e) => updateHeader('motivo', e.target.value)}
              className="w-full bg-transparent px-2 py-2 text-sm text-ink focus:outline-none"
            />
          </CampoInline>
          <CampoInline label="Data Solicitação" borda>
            <input
              type="date"
              value={form.data_solicitacao}
              onChange={(e) => updateHeader('data_solicitacao', e.target.value)}
              className="w-full bg-transparent px-2 py-2 text-sm text-ink focus:outline-none"
            />
          </CampoInline>
        </div>
      </div>

      <div className="mb-6">
        <ChecklistEditor checklist={form.checklist} onChange={setChecklist} />
      </div>
      </div>

      {/* Grade de materiais -- fora do container centralizado de propósito: "deve ser
          literalmente um excel", usando a largura inteira da tela (a diferença entre `main`
          ter `max-w-6xl` ou não é justamente pra isso, ver Layout.jsx), sem moldura de card. */}
      <div className="mb-6 -mx-4">
        <MaterialGrid materiais={form.materiais} onChange={setMateriais} errors={enviarErrors} />
      </div>

      <div className="mx-auto max-w-6xl">
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

      {saveMessage && <p className="mb-4 text-sm text-ink-muted">{saveMessage}</p>}

      <div className="flex gap-3">
        <button
          onClick={handleSalvar}
          disabled={saving}
          className="rounded border border-line bg-surface px-4 py-2 font-medium text-ink hover:bg-surface-alt disabled:opacity-50"
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
    </div>
  )
}

function CampoInline({ label, borda = false, children }) {
  return (
    <div className={`flex items-center ${borda ? 'sm:border-l sm:border-line' : ''}`}>
      <span className="w-36 shrink-0 border-r border-line bg-surface-alt px-3 py-2 text-sm font-medium text-brand-navy">
        {label}
      </span>
      <div className="flex-1">{children}</div>
    </div>
  )
}

function BitinResumo({ codigo, resumo }) {
  if (!resumo) return <p className="text-ink-muted">Carregando resumo...</p>
  return (
    <div>
      <h1 className="mb-1 text-2xl font-semibold text-ink">{codigo}</h1>
      <p className="mb-6 text-sm text-green-700">Enviado — travado, sem edição.</p>

      <div className="mb-6 grid grid-cols-1 gap-4 rounded border border-line bg-surface p-4 sm:grid-cols-2">
        <Info label="Setor" valor={resumo.setor} />
        <Info label="Produto" valor={resumo.produto} />
        <Info label="Motivo" valor={resumo.motivo} />
        <Info label="Solicitante" valor={resumo.solicitante} />
      </div>

      <div className="mb-6 rounded border border-line bg-surface p-4">
        <h2 className="mb-3 text-lg font-medium text-ink">Materiais</h2>
        <ul className="divide-y divide-line">
          {resumo.materiais.map((m, i) => (
            <li key={i} className="py-2 text-sm">
              <span className="font-medium">{m.codigo_material}</span> — {m.descricao_material} (centro{' '}
              {m.centro}, {m.tipo_material})
            </li>
          ))}
        </ul>
      </div>

      <div className="rounded border border-line bg-surface p-4">
        <h2 className="mb-3 text-lg font-medium text-ink">Checklist</h2>
        <ul className="grid grid-cols-1 gap-1 text-sm sm:grid-cols-2">
          {resumo.checklist.map((item) => (
            <li key={item.id} className={item.afeta ? 'text-ink' : 'text-ink-faint'}>
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
      <p className="text-xs uppercase tracking-wide text-ink-muted">{label}</p>
      <p className="text-ink">{valor || '—'}</p>
    </div>
  )
}
