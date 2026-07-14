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

// Espelha backend/api/bitins.py::ResumoUsuarioResponse -- devolvido por
// GET /bitins/resumo-usuario. Escopado por criado_por ("só os meus", não o sistema
// inteiro) -- decisão registrada, ver docs/FRONTEND.md.
export interface ResumoUsuario {
  rascunhos: number
  enviados: number
}
