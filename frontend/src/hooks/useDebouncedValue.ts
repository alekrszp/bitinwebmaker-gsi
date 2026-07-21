import { useEffect, useState } from 'react'

// Extraído de 3 cópias idênticas (CadastroPage.tsx/ProcessosPage.tsx/MeusBitins.tsx, cada
// uma com seu próprio `useEffect(() => setTimeout(...), [busca])` pra esperar o usuário parar
// de digitar antes de bater na API) -- 2026-07-21, revisão de componentização.
export function useDebouncedValue<T>(valor: T, delayMs = 300): T {
  const [debounced, setDebounced] = useState(valor)

  useEffect(() => {
    const id = setTimeout(() => setDebounced(valor), delayMs)
    return () => clearTimeout(id)
  }, [valor, delayMs])

  return debounced
}
