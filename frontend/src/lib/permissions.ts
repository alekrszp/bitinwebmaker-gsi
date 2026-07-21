// 2ª revisão do modelo de permissões (2026-07-20, pedido explícito: "99 = ADMIN APENAS EU.
// 88 = GESTOR: pode existir gestor de cadastro, processos e engenharia. 77 = cadastro,
// processos, engenheiro.") -- espelha backend/auth/deps.py. Cadastro/Processos/Engenharia
// NÃO são mais níveis fixos (eram 88/89 antes) -- agora são valores de `User.setor`, cruzados
// com o rank (NIVEL_INDIVIDUAL/NIVEL_GESTOR/NIVEL_ADMIN). O backend continua sendo quem de
// fato garante a permissão em cada rota -- isto é só UX no cliente.
export const NIVEL_INDIVIDUAL = 77
export const NIVEL_GESTOR = 88
export const NIVEL_ADMIN = 99

export const SETOR_CADASTRO = 'cadastro'
export const SETOR_PROCESSOS = 'processos'
export const SETOR_ENGENHARIA = 'engenharia'

export function isAdmin(level: number | undefined | null): boolean {
  return level === NIVEL_ADMIN
}

export function isGestor(level: number | undefined | null): boolean {
  return level === NIVEL_GESTOR
}

// (rank, setor) combinados -- rank precisa ser INDIVIDUAL ou GESTOR, admin não "é" de setor
// nenhum pra fins de permissão (mesmo padrão de backend/auth/deps.py::eh_do_setor). Use isto
// pra checagens EXATAS (excluem admin de propósito) -- ex.: "esconder botão só pra quem é
// Cadastro puro, sem afetar admin".
export function ehDoSetor(
  level: number | undefined | null,
  setor: string | undefined | null,
  ...setoresPermitidos: string[]
): boolean {
  return (level === NIVEL_INDIVIDUAL || level === NIVEL_GESTOR) && !!setor && setoresPermitidos.includes(setor)
}

// Admin também enxerga/opera a fila de Cadastro/Processos (mesmo padrão do backend --
// check_setor(SETOR_CADASTRO) em POST /encaminhar-roteiro) -- use pra checagens de
// PERMISSÃO (admin sempre passa), diferente de ehDoSetor acima (checagem de identidade).
export function isCadastro(level: number | undefined | null, setor: string | undefined | null): boolean {
  return isAdmin(level) || ehDoSetor(level, setor, SETOR_CADASTRO)
}

export function isProcessos(level: number | undefined | null, setor: string | undefined | null): boolean {
  return isAdmin(level) || ehDoSetor(level, setor, SETOR_PROCESSOS)
}
