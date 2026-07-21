import { useEffect, useRef, useState, type ReactNode } from 'react'
import { CloseIcon } from '../icons'

// Ícone "?" com tutorial em popover -- usado nas telas de edição (ZBPP009, BITin) no lugar de
// um parágrafo de instrução sempre visível (decisão do usuário, 2026-07-15: "aquela descrição
// muda, só deixa um icone de '?' com um tutorial mais completo"). Fecha ao clicar fora ou no
// "×"; conteúdo (children) é livre, cada tela escreve o próprio tutorial.
export default function AjudaPopover({ titulo, children }: { titulo: string; children: ReactNode }) {
  const [aberto, setAberto] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!aberto) return
    function aoClicarFora(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) setAberto(false)
    }
    document.addEventListener('mousedown', aoClicarFora)
    return () => document.removeEventListener('mousedown', aoClicarFora)
  }, [aberto])

  return (
    <div ref={containerRef} className="relative inline-block">
      <button
        type="button"
        onClick={() => setAberto((v) => !v)}
        aria-label={`Ajuda: ${titulo}`}
        aria-expanded={aberto}
        className="flex h-5 w-5 items-center justify-center rounded-full border border-line text-[0.7rem] font-semibold text-ink-muted hover:border-brand-navy hover:text-brand-navy"
      >
        ?
      </button>

      {aberto && (
        // normal-case (2026-07-21): Settings.tsx usa este componente dentro do título
        // uppercase do Card -- sem isso o texto do popover herdava o uppercase do ancestral.
        <div className="absolute left-0 top-7 z-30 w-80 rounded-lg border border-line bg-surface p-4 text-left normal-case shadow-lg sm:w-96">
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-sm font-semibold text-ink">{titulo}</h3>
            <button
              type="button"
              onClick={() => setAberto(false)}
              aria-label="Fechar ajuda"
              className="text-ink-faint hover:text-ink"
            >
              <CloseIcon className="h-4 w-4" />
            </button>
          </div>
          <div className="mt-2 space-y-2 text-xs leading-relaxed text-ink-muted">{children}</div>
        </div>
      )}
    </div>
  )
}
