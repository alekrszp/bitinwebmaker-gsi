// Nível admin -- espelha backend/auth/deps.py::NIVEL_ADMIN e backend/api/bitins.py::ADMIN_LEVEL
// (99). Centralizado aqui (2026-07-16) pra não duplicar a mesma constante em cada componente
// que precisa decidir o que mostrar; o backend continua sendo quem de fato garante a permissão
// em cada rota -- isto é só UX no cliente.
export const NIVEL_ADMIN = 99

// Espelha backend/auth/deps.py::NIVEL_CADASTRO (88) -- fila do setor Cadastro
// (CadastroPage.tsx), mesmo raciocínio de NIVEL_ADMIN acima.
export const NIVEL_CADASTRO = 88

export function isAdmin(level: number | undefined | null): boolean {
  return level === NIVEL_ADMIN
}

// Admin também enxerga/opera a fila do Cadastro (mesmo padrão do backend --
// check_permission(NIVEL_CADASTRO, NIVEL_ADMIN) em POST /encaminhar-roteiro).
export function isCadastro(level: number | undefined | null): boolean {
  return level === NIVEL_CADASTRO || level === NIVEL_ADMIN
}

// Espelha backend/auth/deps.py::NIVEL_PROCESSOS (89) -- reedita BITins já enviados enquanto
// estiverem na fila do Cadastro (encaminhado_roteiro=true), ver BitinDetail.tsx.
export const NIVEL_PROCESSOS = 89

export function isProcessos(level: number | undefined | null): boolean {
  return level === NIVEL_PROCESSOS || level === NIVEL_ADMIN
}
