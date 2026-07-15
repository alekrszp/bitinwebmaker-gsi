// Departamentos acionados pelas etapas do checklist marcadas "afeta" -- crosswalk fixo
// (scripts/bitin_document.py::build_setores_afetados, extraído de um BITin real, aba
// "SETORES CHECKLIST"). Banner com flechas conectando cada setor -- mesmo formato do
// documento original ("QUALIDADE ↔ PCP ↔ ENG INDUS ↔ ..."), em vez de badges soltas
// (decisão do usuário, 2026-07-14). Usa os tokens de superfície de sempre (bg-surface-alt/
// text-ink), que já se adaptam nos dois temas, em vez de tentar acertar opacidade de brand-navy
// na mão.
export default function SetoresBanner({ setores }: { setores: string[] }) {
  if (setores.length === 0) {
    return <p className="text-sm text-ink-muted">Nenhum setor acionado.</p>
  }
  return (
    <div className="rounded-lg border border-line bg-surface-alt px-4 py-3">
      <p className="flex flex-wrap items-center gap-x-2 gap-y-1">
        {setores.map((setor, i) => (
          <span key={setor} className="flex items-center gap-2">
            {i > 0 && <span className="text-ink-faint">↔</span>}
            <span className="text-sm font-semibold tracking-wide text-ink">{setor}</span>
          </span>
        ))}
      </p>
    </div>
  )
}
