// Nível admin -- espelha backend/auth/deps.py::NIVEL_ADMIN e backend/api/bitins.py::ADMIN_LEVEL
// (99). Centralizado aqui (2026-07-16) pra não duplicar a mesma constante em cada componente
// que precisa decidir o que mostrar; o backend continua sendo quem de fato garante a permissão
// em cada rota -- isto é só UX no cliente.
export const NIVEL_ADMIN = 99

export function isAdmin(level: number | undefined | null): boolean {
  return level === NIVEL_ADMIN
}
