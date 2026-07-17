import { Link } from 'react-router-dom'
import type { MaterialResumo } from '../../lib/bitinTypes'
import type { MateriaisSchema, MaterialEditavel } from '../../lib/types'
import AlteracaoTable from './AlteracaoTable'
import MaterialEditorCard from './MaterialEditorCard'

// Bloco de materiais da aba BITin -- editável (um MaterialEditorCard por material + "+ Novo
// material") ou só-leitura (AlteracaoTable, quando enviado), extraído de BitinDetail.tsx pra
// isolar essa responsabilidade (decisão do usuário, 2026-07-15: "não ta nada componentizado
// o bitindetail, ajusta isso"). Códigos SAP é só outro jeito de chegar no mesmo materiais[] --
// o link abaixo do "+ Novo material" deixa isso explícito sem forçar o engenheiro a passar
// por lá.
export default function MateriaisSection({
  editavel,
  schema,
  materiais,
  onChangeMaterial,
  onAddMaterial,
  onRemoveMaterial,
  materiaisResumo,
  mongoId,
}: {
  editavel: boolean
  schema: MateriaisSchema | null
  materiais: MaterialEditavel[]
  onChangeMaterial: (index: number, material: MaterialEditavel) => void
  onAddMaterial: () => void
  onRemoveMaterial: (index: number) => void
  materiaisResumo: MaterialResumo[] | null
  mongoId: string | undefined
}) {
  if (!editavel) {
    return materiaisResumo && <AlteracaoTable materiais={materiaisResumo} />
  }

  return (
    <>
      {schema &&
        materiais.map((material, i) => (
          <MaterialEditorCard
            key={i}
            material={material}
            schema={schema}
            onChange={(m) => onChangeMaterial(i, m)}
            onRemove={() => onRemoveMaterial(i)}
          />
        ))}
      <div className="mt-6 flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={onAddMaterial}
          className="rounded-lg border border-dashed border-line px-4 py-2 text-sm font-medium text-ink-muted hover:bg-surface-alt"
        >
          + Novo material
        </button>
        {mongoId && (
          <span className="text-sm text-ink-muted">
            ou{' '}
            <Link to={`/bitins/${mongoId}/codigos-sap`} className="text-ink underline">
              cole/digite vários de uma vez em ZBPP009
            </Link>
          </span>
        )}
      </div>
    </>
  )
}
