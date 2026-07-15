import { Navigate, useLocation } from 'react-router-dom'
import type { ReactNode } from 'react'
import { useAuth } from '../context/AuthContext'

// Rota pra onde quem está com senha temporária (Usuario.senha_temporaria, backend/auth/
// models.py) é forçado antes de conseguir usar o resto do app -- ver frontend/src/pages/
// DefinirSenha.tsx. Comparada aqui (não só montada dentro de RequireAuth) pra evitar loop de
// redirecionamento: sem essa exceção, /definir-senha redirecionaria pra ela mesma.
const ROTA_DEFINIR_SENHA = '/definir-senha'

export default function RequireAuth({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth()
  const location = useLocation()

  if (loading) return <div className="p-6 text-center text-ink-muted">Carregando...</div>
  if (!user) return <Navigate to="/login" state={{ from: location }} replace />

  // Gate de senha temporária (2026-07-15, cadastro de usuário só por admin -- ver
  // backend/api/users.py::create_user_by_admin): quem ainda está com a senha gerada pelo
  // admin não pode navegar pra mais nada até trocar por uma senha só dela/dele. Só o
  // servidor sabe a senha_atual de verdade pra validar a troca (POST /auth/change-password)
  // -- isso aqui é só roteamento, não um bloqueio de segurança de verdade (ver comentário em
  // backend/auth/models.py::Usuario.senha_temporaria sobre não bloquear outros endpoints).
  if (user.senha_temporaria && location.pathname !== ROTA_DEFINIR_SENHA) {
    return <Navigate to={ROTA_DEFINIR_SENHA} replace />
  }

  return children
}
