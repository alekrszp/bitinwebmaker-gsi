import { useContext } from 'react'
import { ThemeContext } from '../context/themeContextObject'

// Separado de ThemeContext.tsx (2026-07-16) -- mesmo motivo de hooks/useAuth.ts (Fast Refresh).
export function useTheme() {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme precisa estar dentro de <ThemeProvider>')
  return ctx
}
