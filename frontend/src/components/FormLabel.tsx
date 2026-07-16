import type { LabelHTMLAttributes } from 'react'

// Rótulo de campo de formulário -- mesmo estilo repetido em Settings.tsx e DadosGeraisCard.tsx,
// extraído pra não divergir entre telas.
export default function FormLabel(props: LabelHTMLAttributes<HTMLLabelElement>) {
  return <label {...props} className="mb-1.5 block text-xs uppercase tracking-wide text-ink-muted" />
}
