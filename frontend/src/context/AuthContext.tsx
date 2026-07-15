import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { api, clearToken, getToken, setToken } from '../lib/api'
import type { User } from '../lib/types'

interface AuthContextValue {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  // Rebusca GET /users/me e atualiza o user em memória -- usado por DefinirSenha.tsx depois de
  // POST /auth/change-password zerar Usuario.senha_temporaria no servidor, pra RequireAuth.tsx
  // parar de redirecionar pra /definir-senha sem precisar de um reload de página inteiro.
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = getToken()
    if (!token) {
      setLoading(false)
      return
    }
    api
      .get('/users/me')
      .then((resp) => setUser(resp.data))
      .catch(() => clearToken())
      .finally(() => setLoading(false))
  }, [])

  async function login(email: string, password: string) {
    const form = new URLSearchParams()
    form.set('username', email)
    form.set('password', password)
    const resp = await api.post('/auth/login', form, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
    setToken(resp.data.access_token)
    const me = await api.get('/users/me')
    setUser(me.data)
  }

  function logout() {
    clearToken()
    setUser(null)
  }

  async function refreshUser() {
    const me = await api.get('/users/me')
    setUser(me.data)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth precisa estar dentro de <AuthProvider>')
  return ctx
}
