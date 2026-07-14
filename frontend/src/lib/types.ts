// Espelha backend/auth/schemas.py::UserOut -- devolvido por GET /users/me.
export interface User {
  id: number
  email: string
  nome: string
  ativo: boolean
  permission_level: number
  network_id: string | null
  sector_id: number | null
  created_at: string
}
