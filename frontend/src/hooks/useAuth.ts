import { useContext } from 'react'
import { AuthContext } from '../context/authContextObject'

// Separado de AuthContext.tsx (2026-07-16) -- oxlint react(only-export-components): um arquivo
// que exporta componente (AuthProvider) e não-componente (este hook) desativa o Fast Refresh
// do Vite pra esse arquivo.
export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth precisa estar dentro de <AuthProvider>')
  return ctx
}
