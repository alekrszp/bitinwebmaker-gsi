// Par rótulo/valor só-leitura -- mesmo padrão usado em Settings.tsx ("Minha conta") e
// BitinDetail.tsx (dados gerais, dados do material). Único lugar que decide a tipografia
// desse par, pra não divergir entre telas.
export default function DetailField({ label, value }: { label: string; value: string | undefined }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-ink-muted">{label}</dt>
      <dd className="mt-0.5 break-words text-sm text-ink">{value || '—'}</dd>
    </div>
  )
}
