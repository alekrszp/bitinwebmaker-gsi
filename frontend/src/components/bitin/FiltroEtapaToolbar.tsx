// Toolbar de filtro (select de etapa + busca), extraída da mesma marcação repetida em
// CadastroPage.tsx e ProcessosPage.tsx (mesmas classes Tailwind, mesmo placeholder) --
// 2026-07-21, revisão de componentização.
export default function FiltroEtapaToolbar<TEtapa extends string>({
  opcoes,
  valor,
  onChange,
  busca,
  onBuscaChange,
  placeholder = 'Buscar por motivo, solicitante ou número...',
}: {
  opcoes: { value: TEtapa; label: string }[]
  valor: TEtapa
  onChange: (v: TEtapa) => void
  busca: string
  onBuscaChange: (v: string) => void
  placeholder?: string
}) {
  return (
    <div className="mt-6 flex flex-wrap items-center gap-2 border-b border-line pb-3">
      <select
        value={valor}
        onChange={(e) => onChange(e.target.value as TEtapa)}
        className="rounded-lg border border-line bg-surface px-3 py-1.5 text-sm text-ink"
      >
        {opcoes.map(({ value, label }) => (
          <option key={value} value={value}>
            Etapa: {label}
          </option>
        ))}
      </select>
      <input
        type="text"
        value={busca}
        onChange={(e) => onBuscaChange(e.target.value)}
        placeholder={placeholder}
        className="w-64 rounded-lg border border-line bg-surface px-3 py-1.5 text-sm text-ink placeholder:text-ink-faint"
      />
    </div>
  )
}
