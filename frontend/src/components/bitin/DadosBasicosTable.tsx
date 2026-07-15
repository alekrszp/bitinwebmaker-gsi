interface CampoAlterado {
  campo: string
  de: string
  para: string
}

// "Campo alterado / De / Para" -- inclui campos livres que o engenheiro escreveu fora do
// crosswalk SAP reconhecido (ex.: "Salvar DWG", "Alterado peso e IS"), exatamente como foram
// digitados. Ver scripts/bitin_document.py::build_campo_alterado_diffs.
//
// Título "Alteração de Dados Básicos no Centro: {centro}" -- mesmo texto literal usado no
// documento original (examples/A263326.xlsm, célula C34 etc.), centro incluído aqui em vez de
// como campo solto, pra seguir a mesma estrutura.
export default function DadosBasicosTable({ diffs, centro }: { diffs: CampoAlterado[]; centro: string }) {
  return (
    <div className="mt-4">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-muted">
        Alteração de Dados Básicos no Centro: {centro || '—'}
      </h3>
      <div className="mt-2 overflow-hidden rounded border border-line">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="bg-surface-alt text-xs uppercase tracking-wide text-ink-muted">
              <th className="px-3 py-2 font-medium">Campo alterado</th>
              <th className="px-3 py-2 font-medium">De</th>
              <th className="px-3 py-2 font-medium">Para</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {diffs.map((diff) => (
              <tr key={diff.campo}>
                <td className="px-3 py-2 text-ink">{diff.campo}</td>
                <td className="px-3 py-2 text-ink-muted">{diff.de || '—'}</td>
                <td className="px-3 py-2 text-ink-muted">{diff.para || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
