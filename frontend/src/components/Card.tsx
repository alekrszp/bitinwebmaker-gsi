import type { ReactNode } from 'react'

// Cartão com título -- mesmo padrão repetido em Settings.tsx ("Minha conta"/"Gestão de
// usuários"/"Sobre") e BitinDetail.tsx ("Dados gerais"/por material). Único lugar que decide
// o espaçamento/borda/tipografia do título, pra não divergir entre telas.
export default function Card({ id, title, children }: { id?: string; title?: ReactNode; children: ReactNode }) {
  return (
    <section id={id} className="relative mt-6 rounded-lg border border-line bg-surface p-5 scroll-mt-20">
      {title && <h2 className="text-sm font-semibold uppercase tracking-wide text-ink-muted">{title}</h2>}
      {children}
    </section>
  )
}
