import { createContext } from 'react'
import type { User } from '../lib/types'

export interface AuthContextValue {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  // Rebusca GET /users/me e atualiza o user em memória -- usado por DefinirSenha.tsx depois de
  // POST /auth/change-password zerar Usuario.senha_temporaria no servidor, pra RequireAuth.tsx
  // parar de redirecionar pra /definir-senha sem precisar de um reload de página inteiro.
  refreshUser: () => Promise<void>
}

// Nome do arquivo evita colisão de maiúsculas/minúsculas com AuthContext.tsx em filesystems
// case-insensitive (Windows) -- TypeScript rejeita dois arquivos que só diferem em casing.
// Objeto de contexto isolado num arquivo à parte (2026-07-16) -- AuthContext.tsx exportar só o
// componente AuthProvider e hooks/useAuth.ts exportar só o hook não bastava pro Fast Refresh do
// Vite: o próprio objeto `createContext(...)` também precisa morar fora de um arquivo que
// exporta um componente.
export const AuthContext = createContext<AuthContextValue | null>(null)
