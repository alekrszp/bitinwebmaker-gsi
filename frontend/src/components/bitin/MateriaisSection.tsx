import type { MaterialResumo } from '../../lib/bitinTypes'
import type { MateriaisSchema, MaterialEditavel } from '../../lib/types'
import AlteracaoTable from './AlteracaoTable'
import MaterialEditorCard from './MaterialEditorCard'

// Bloco de materiais da aba BITin -- editável (um MaterialEditorCard por material + "+ Novo
// material") ou só-leitura (AlteracaoTable, quando enviado), extraído de BitinDetail.tsx pra
// isolar essa responsabilidade (decisão do usuário, 2026-07-15: "não ta nada componentizado
// o bitindetail, ajusta isso"). ZBPP009/Lista Técnica (páginas separadas) deixaram de existir
// no modo manual (2026-07-23) -- este bloco (+ a lista técnica inline em MaterialEditorCard) é
// o único jeito de cadastrar material sem o agente conectado.
export default function MateriaisSection({
  editavel,
  schema,
  materiais,
  onChangeMaterial,
  onAddMaterial,
  onRemoveMaterial,
  materiaisResumo,
}: {
  editavel: boolean
  schema: MateriaisSchema | null
  materiais: (MaterialEditavel & { _id: string })[]
  onChangeMaterial: (id: string, material: MaterialEditavel) => void
  onAddMaterial: () => void
  onRemoveMaterial: (id: string) => void
  materiaisResumo: MaterialResumo[] | null
}) {
  if (!editavel) {
    return materiaisResumo && <AlteracaoTable materiais={materiaisResumo} />
  }

  return (
    <>
      {/* key={material._id} + onChange/onRemove passados DIRETO (não embrulhados numa closure
          por índice, 2026-07-17) -- é o que permite o React.memo de MaterialEditorCard
          funcionar: uma closure nova a cada render (`(m) => onChangeMaterial(i, m)`) faria o
          memo achar que a prop "mudou" mesmo quando o card em si não mudou. */}
      {schema &&
        materiais.map((material) => {
          // "REVISAR ROTEIRO" (Módulo4.bas) -- aviso fixo quando o Alt declarado é "D/P" ou
          // "-/P" (revisão de desenho mudou sem troca de fornecedor). Não afeta checklist,
          // só lembra o engenheiro de revisar o roteiro de fabricação, como a macro original.
          const revisarRoteiro = materiaisResumo?.find(
            (r) => r.codigo_material === material.codigo_material,
          )?.revisar_roteiro
          return (
            <div key={material._id}>
              <MaterialEditorCard
                id={material._id}
                material={material}
                schema={schema}
                onChange={onChangeMaterial}
                onRemove={onRemoveMaterial}
              />
              {revisarRoteiro && (
                <p className="mb-4 mt-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
                  Revisar roteiro de fabricação: a revisão de desenho mudou sem troca de
                  fornecedor.
                </p>
              )}
            </div>
          )
        })}
      <div className="mt-6 flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={onAddMaterial}
          className="rounded-lg border border-dashed border-line px-4 py-2 text-sm font-medium text-ink-muted hover:bg-surface-alt"
        >
          + Novo material
        </button>
      </div>
    </>
  )
}
