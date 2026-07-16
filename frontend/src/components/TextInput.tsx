import { forwardRef, type InputHTMLAttributes } from 'react'

// Input de texto -- mesmo estilo repetido em Settings.tsx e DadosGeraisCard.tsx, extraído pra
// não divergir entre telas. forwardRef porque é um wrapper fino sobre <input>, mesmo padrão de
// qualquer componente que possa precisar expor a ref nativa a quem o usa.
const TextInput = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  function TextInput(props, ref) {
    return (
      <input
        ref={ref}
        {...props}
        className="w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink focus:border-brand-navy focus:outline-none focus:ring-2 focus:ring-brand-navy/20"
      />
    )
  },
)

export default TextInput
