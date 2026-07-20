import Card from '../Card'
import DetailField from '../DetailField'
import FormLabel from '../FormLabel'
import TextInput from '../TextInput'
import type { BitinResumo } from '../../lib/bitinTypes'
import { formatarDataEnvio } from '../../lib/format'
import ChecklistTable from './ChecklistTable'
import SetorBadge from './SetorBadge'
import SetoresBanner from './SetoresBanner'

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
  setoresPermitidos,
  onProdutoChange,
  onMotivoChange,
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
  // Restrito ao(s) Subgrupo(s) do usuário logado (2026-07-17, pedido explícito, ver
  // BitinDetail.tsx) -- não é mais uma lista fixa. Só 1 subgrupo = trava sozinho (o pai já
  // preenche `setor` e o <select> fica desabilitado abaixo); admin sem subgrupo nenhum vê
  // todos.
  setoresPermitidos: string[]
  onProdutoChange: (v: string) => void
  onMotivoChange: (v: string) => void
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
            <FormLabel htmlFor="produto">Produto</FormLabel>
            <TextInput id="produto" type="text" value={produto} onChange={(e) => onProdutoChange(e.target.value)} />
          </div>
          <div>
            <FormLabel htmlFor="motivo">Motivo</FormLabel>
            <TextInput id="motivo" type="text" value={motivo} onChange={(e) => onMotivoChange(e.target.value)} />
          </div>
          {/* Solicitante travado (2026-07-16) -- deixou de ser input editável: o backend
              carimba automaticamente a partir do usuário logado que criou o rascunho
              (create_or_update_draft, backend/api/bitins.py), mesmo padrão de campo
              não-editável já usado aqui pra "Data de envio" (DetailField). */}
          <DetailField label="Solicitante" value={solicitante} />
          <div>
            <FormLabel htmlFor="setor">Setor</FormLabel>
            {/* Desabilitado com 1 opção só (2026-07-17, pedido explícito: "se ela tiver só 1
                setor vinculado só o do setor vinculado dela") -- BitinDetail.tsx já preenche
                sozinho quando só há 1 subgrupo permitido; aqui só trava o campo pra não dar a
                impressão de que dá pra trocar. Quem tem os dois (ou é admin, sem subgrupo
                nenhum) continua escolhendo livremente. */}
            <select
              id="setor"
              required
              disabled={setoresPermitidos.length <= 1}
              value={setor}
              onChange={(e) => onSetorChange(e.target.value)}
              className="dark:[color-scheme:dark] [color-scheme:light] w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink focus:border-brand-navy focus:outline-none focus:ring-2 focus:ring-brand-navy/20 disabled:opacity-60"
            >
              <option value="" disabled>
                Selecione...
              </option>
              {setoresPermitidos.map((s) => (
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
