import type { ReactNode } from 'react'

// Cartão com título -- mesmo padrão repetido em Settings.tsx ("Minha conta"/"Gestão de
// usuários"/"Sobre") e BitinDetail.tsx ("Dados gerais"/por material). Único lugar que decide
// o espaçamento/borda/tipografia do título, pra não divergir entre telas.
export default function Card({ title, children }: { title?: string; children: ReactNode }) {
  return (
    <section className="relative mt-6 rounded-lg border border-line bg-surface p-5">
      {title && <h2 className="text-sm font-semibold uppercase tracking-wide text-ink-muted">{title}</h2>}
      {children}
    </section>
  )
}
