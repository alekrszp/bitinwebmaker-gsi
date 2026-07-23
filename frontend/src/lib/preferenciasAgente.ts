// Preferência "fazer manualmente" por BITin, persistida no navegador (2026-07-23, pedido
// explícito: "quando a pessoa escolher fazer manualmente ele sempre vai abrir manual, não vai
// mais apitar a notificação") -- antes `manualConfirmado` era só estado de componente
// (`BitinDetail.tsx`), então voltar pra lista e abrir o MESMO BITin de novo perguntava tudo de
// novo (o componente remonta, o estado zera). `localStorage` (não o backend -- é preferência
// de navegador/máquina, não dado do BITin em si) resolve sem precisar de campo novo no modelo.
const PREFIXO = 'bitin_manual_'

export function bitinEscolheuManual(mongoId: string): boolean {
  try {
    return localStorage.getItem(PREFIXO + mongoId) === '1'
  } catch {
    // Storage bloqueado (modo privado restrito, política do navegador) -- degrada pra
    // "sempre pergunta de novo", nunca quebra a tela.
    return false
  }
}

export function marcarBitinManual(mongoId: string): void {
  try {
    localStorage.setItem(PREFIXO + mongoId, '1')
  } catch {
    // best-effort, ver comentário acima
  }
}
