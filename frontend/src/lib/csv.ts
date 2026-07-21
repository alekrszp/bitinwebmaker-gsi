// Espelha scripts/csv_safety.py (RFC 4180 + proteção contra CSV/formula injection) --
// mesmo motivo: campos vindos do BITin (motivo, solicitante...) podem começar com =/+/@ sem
// nenhuma intenção maliciosa, mas o Excel interpreta isso como fórmula ao abrir. "-" fica de
// fora de propósito, é valor de domínio legítimo no sistema (códigos de Alt).
const FORMULA_TRIGGER_CHARS = new Set(['=', '+', '@'])

function sanitizarCelula(valor: string): string {
  return valor && FORMULA_TRIGGER_CHARS.has(valor[0]) ? `'${valor}` : valor
}

function escaparCampo(valor: string): string {
  return `"${sanitizarCelula(valor).replace(/"/g, '""')}"`
}

// CRLF entre linhas (RFC 4180) -- sempre entre aspas (RFC 4180 permite omitir quando o campo
// não tem separador/aspas/quebra de linha, mas citar tudo é mais simples e já era o padrão
// anterior aqui).
export function montarCsv(linhas: string[][]): string {
  return linhas.map((linha) => linha.map(escaparCampo).join(';')).join('\r\n')
}

export function baixarCsv(nomeArquivo: string, linhas: string[][]) {
  const csv = montarCsv(linhas)
  const blob = new Blob([`﻿${csv}`], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = nomeArquivo
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
