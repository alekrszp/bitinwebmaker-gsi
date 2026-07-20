// Modal de "alterações não salvas" (2026-07-17) -- ver useAvisoSairSemSalvar.ts. 3 ações
// (não um confirm() nativo de 2 botões só) porque "salvar e sair" é uma opção de verdade, não
// só confirmar/cancelar.
export default function AvisoSairModal({
  onSalvarESair,
  onSairSemSalvar,
  onCancelar,
  salvando,
}: {
  onSalvarESair: () => void
  onSairSemSalvar: () => void
  onCancelar: () => void
  salvando: boolean
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <div className="w-full max-w-sm rounded-lg border border-line bg-surface p-5 shadow-xl">
        <h2 className="text-base font-semibold text-ink">Alterações não salvas</h2>
        <p className="mt-1.5 text-sm text-ink-muted">
          Você tem alterações que ainda não foram salvas. O que deseja fazer antes de sair?
        </p>
        <div className="mt-4 flex flex-col gap-2">
          <button
            type="button"
            onClick={onSalvarESair}
            disabled={salvando}
            className="rounded-lg bg-brand-navy px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-navy-dark disabled:cursor-not-allowed disabled:opacity-60"
          >
            {salvando ? 'Salvando...' : 'Salvar e sair'}
          </button>
          <button
            type="button"
            onClick={onSairSemSalvar}
            disabled={salvando}
            className="rounded-lg border border-red-600/40 px-4 py-2 text-sm font-medium text-red-600 transition-colors hover:bg-red-600/10 disabled:cursor-not-allowed disabled:opacity-60"
          >
            Sair sem salvar
          </button>
          <button
            type="button"
            onClick={onCancelar}
            disabled={salvando}
            className="rounded-lg px-4 py-2 text-sm font-medium text-ink-muted transition-colors hover:bg-surface-alt disabled:cursor-not-allowed disabled:opacity-60"
          >
            Cancelar
          </button>
        </div>
      </div>
    </div>
  )
}
