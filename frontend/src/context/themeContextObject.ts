import { createContext } from 'react'

export type Theme = 'light' | 'dark'

export interface ThemeContextValue {
  theme: Theme
  toggleTheme: () => void
}

// Ver comentário equivalente em authContextObject.ts sobre o nome do arquivo (colisão de
// casing no Windows) e por que este objeto mora num arquivo à parte (Fast Refresh do Vite).
export const ThemeContext = createContext<ThemeContextValue | null>(null)
