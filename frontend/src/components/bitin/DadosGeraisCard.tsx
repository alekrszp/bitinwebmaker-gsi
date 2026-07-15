import Card from '../Card'
import DetailField from '../DetailField'
import type { BitinResumo } from '../../lib/bitinTypes'
import { formatarDataEnvio } from '../../lib/format'
import ChecklistTable from './ChecklistTable'
import SetorBadge from './SetorBadge'
import SetoresBanner from './SetoresBanner'

const SETORES = ['Proteína Animal', 'Armazenagem de Grãos']

// Card "Dados gerais" da aba BITin -- formulário (editável) ou campos travados (visualização)
// + banner de setores acionados + checklist, extraído de BitinDetail.tsx pra isolar essa
// responsabilidade (decisão do usuário, 2026-07-15: "não ta nada componentizado o
// bitindetail, ajusta isso").
export default function DadosGeraisCard({
  editavel,
  produto,
  motivo,
  solicitante,
  setor,
  onProdutoChange,
  onMotivoChange,
  onSolicitanteChange,
  onSetorChange,
  resumo,
  onToggleChecklist,
  onChecklistDescricaoChange,
}: {
  editavel: boolean
  produto: string
  motivo: string
  solicitante: string
  setor: string
  onProdutoChange: (v: string) => void
  onMotivoChange: (v: string) => void
  onSolicitanteChange: (v: string) => void
  onSetorChange: (v: string) => void
  resumo: BitinResumo | null
  onToggleChecklist?: (id: string, afeta: boolean) => void
  onChecklistDescricaoChange?: (id: string, descricao: string) => void
}) {
  return (
    <Card title="Dados gerais">
      {editavel ? (
        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <div>
            <label htmlFor="produto" className="mb-1.5 block text-xs uppercase tracking-wide text-ink-muted">
              Produto
            </label>
            <input
              id="produto"
              type="text"
              value={produto}
              onChange={(e) => onProdutoChange(e.target.value)}
              className="w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink focus:border-brand-navy focus:outline-none focus:ring-2 focus:ring-brand-navy/20"
            />
          </div>
          <div>
            <label htmlFor="motivo" className="mb-1.5 block text-xs uppercase tracking-wide text-ink-muted">
              Motivo
            </label>
            <input
              id="motivo"
              type="text"
              value={motivo}
              onChange={(e) => onMotivoChange(e.target.value)}
              className="w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink focus:border-brand-navy focus:outline-none focus:ring-2 focus:ring-brand-navy/20"
            />
          </div>
          <div>
            <label htmlFor="solicitante" className="mb-1.5 block text-xs uppercase tracking-wide text-ink-muted">
              Solicitante
            </label>
            <input
              id="solicitante"
              type="text"
              required
              value={solicitante}
              onChange={(e) => onSolicitanteChange(e.target.value)}
              className="w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink focus:border-brand-navy focus:outline-none focus:ring-2 focus:ring-brand-navy/20"
            />
          </div>
          <div>
            <label htmlFor="setor" className="mb-1.5 block text-xs uppercase tracking-wide text-ink-muted">
              Setor
            </label>
            <select
              id="setor"
              required
              value={setor}
              onChange={(e) => onSetorChange(e.target.value)}
              className="dark:[color-scheme:dark] [color-scheme:light] w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink focus:border-brand-navy focus:outline-none focus:ring-2 focus:ring-brand-navy/20"
            >
              <option value="" disabled>
                Selecione...
              </option>
              {SETORES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
          <DetailField label="Data de envio" value={formatarDataEnvio(resumo?.data_envio)} />
        </div>
      ) : (
        <dl className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <DetailField label="Produto" value={resumo?.produto} />
          <DetailField label="Motivo" value={resumo?.motivo} />
          <DetailField label="Solicitante" value={resumo?.solicitante} />
          <div>
            <dt className="text-xs uppercase tracking-wide text-ink-muted">Setor</dt>
            <dd className="mt-0.5">
              <SetorBadge setor={resumo?.setor ?? ''} />
            </dd>
          </div>
          <DetailField label="Data de envio" value={formatarDataEnvio(resumo?.data_envio)} />
        </dl>
      )}

      {resumo && (
        <>
          <div className="mt-6">
            <SetoresBanner setores={resumo.setores_afetados} />
          </div>
          <div className="mt-4">
            <ChecklistTable
              checklist={resumo.checklist}
              modo={editavel ? 'todas' : 'so-sim'}
              onToggle={editavel ? onToggleChecklist : undefined}
              onDescricaoChange={editavel ? onChecklistDescricaoChange : undefined}
            />
          </div>
        </>
      )}
    </Card>
  )
}
