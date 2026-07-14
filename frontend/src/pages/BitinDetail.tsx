import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../lib/api'

// Visualização mínima só-leitura (decidida com o usuário, ver docs/FRONTEND.md) -- usa
// GET /bitins/{mongo_id}/resumo (scripts/bitin_view.py::render_bitin_summary), que já monta
// os dados legíveis (diffs de campo, impactos operacionais) em vez de reimplementar essa
// lógica no frontend a partir do content bruto. Edição fica pra uma rodada futura.
interface CampoAlterado {
  campo: string
  de: string
  para: string
}

interface MaterialResumo {
  codigo_material: string
  descricao_material: string
  centro: string
  tipo_material: string
  impactos_operacionais: Record<string, unknown>
  dados_basicos_alterados: CampoAlterado[]
  lista_tecnica: unknown[]
}

interface BitinResumo {
  bitin: string
  status: string
  data_envio: string | null
  setor: string
  produto: string
  motivo: string
  solicitante: string
  data_solicitacao: string
  materiais: MaterialResumo[]
}

export default function BitinDetail() {
  const { mongoId } = useParams<{ mongoId: string }>()
  const [resumo, setResumo] = useState<BitinResumo | null>(null)
  const [erro, setErro] = useState<string | null>(null)

  useEffect(() => {
    let cancelado = false
    setResumo(null)
    setErro(null)
    api
      .get(`/bitins/${mongoId}/resumo`)
      .then((resp) => {
        if (!cancelado) setResumo(resp.data)
      })
      .catch(() => {
        if (!cancelado) setErro('Não foi possível carregar este BITin.')
      })
    return () => {
      cancelado = true
    }
  }, [mongoId])

  return (
    <div className="mx-auto max-w-3xl">
      <Link to="/bitins" className="text-sm text-ink-muted hover:text-ink hover:underline">
        ← Voltar pra Meus Bitins
      </Link>

      {erro && <p className="mt-4 text-sm text-red-600">{erro}</p>}
      {!resumo && !erro && <p className="mt-4 text-sm text-ink-muted">Carregando...</p>}

      {resumo && (
        <>
          <div className="mt-3 flex items-center gap-3">
            <h1 className="text-2xl font-semibold text-ink">{resumo.bitin || 'Rascunho sem código'}</h1>
            <StatusBadge status={resumo.status} />
          </div>

          <section className="mt-6 rounded-lg border border-line bg-surface p-5">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-ink-muted">Dados gerais</h2>
            <dl className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
              <InfoField label="Setor" value={resumo.setor} />
              <InfoField label="Produto" value={resumo.produto} />
              <InfoField label="Motivo" value={resumo.motivo} />
              <InfoField label="Solicitante" value={resumo.solicitante} />
              <InfoField label="Data da solicitação" value={resumo.data_solicitacao} />
              <InfoField label="Data de envio" value={resumo.data_envio ?? '—'} />
            </dl>
          </section>

          {resumo.materiais.map((material) => (
            <section key={material.codigo_material} className="mt-6 rounded-lg border border-line bg-surface p-5">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-ink-muted">
                Material {material.codigo_material}
              </h2>
              <dl className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
                <InfoField label="Descrição" value={material.descricao_material || '—'} />
                <InfoField label="Centro" value={material.centro} />
                <InfoField label="Tipo" value={material.tipo_material} />
              </dl>

              {material.dados_basicos_alterados.length > 0 && (
                <div className="mt-4 overflow-hidden rounded border border-line">
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr className="bg-surface-alt text-xs uppercase tracking-wide text-ink-muted">
                        <th className="px-3 py-2 font-medium">Campo alterado</th>
                        <th className="px-3 py-2 font-medium">De</th>
                        <th className="px-3 py-2 font-medium">Para</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-line">
                      {material.dados_basicos_alterados.map((diff) => (
                        <tr key={diff.campo}>
                          <td className="px-3 py-2 text-ink">{diff.campo}</td>
                          <td className="px-3 py-2 text-ink-muted">{diff.de || '—'}</td>
                          <td className="px-3 py-2 text-ink-muted">{diff.para}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          ))}
        </>
      )}
    </div>
  )
}

function InfoField({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-ink-muted">{label}</dt>
      <dd className="mt-0.5 text-sm text-ink">{value || '—'}</dd>
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
