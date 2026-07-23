import { useEffect, useRef } from 'react'

// Favicon da aba do navegador reflete o status do agente SAP enquanto o engenheiro está numa
// tela que depende disso (2026-07-23, pedido explícito -- item que tinha ficado em aberto no
// redesign da logo). Verde/vermelho igual ao badge/logo; sem `status` (undefined), volta pro
// favicon padrão do sistema (`originalRef`, capturado do próprio <link> -- ver hook abaixo) --
// nunca fica "preso" num estado depois de sair da tela.
const CORES: Record<'conectado' | 'desligado', string> = {
  conectado: '#79aa00',
  desligado: '#dc2626',
}

// SVG estático simplificado (sem gradiente/animação -- favicon é pequeno demais pra notar a
// diferença, e trocar um `data:` URI a cada frame seria desperdício) espelhando
// AgenteLogoIcon.tsx.
function faviconAgenteSvg(cor: string): string {
  const svg =
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">` +
    `<rect x="2" y="2" width="60" height="60" rx="18" fill="#32464d"/>` +
    `<line x1="32" y1="13" x2="32" y2="19" stroke="${cor}" stroke-width="3" stroke-linecap="round"/>` +
    `<circle cx="32" cy="10.5" r="3.5" fill="${cor}"/>` +
    `<rect x="16" y="20" width="32" height="25" rx="11" fill="#e7edf0"/>` +
    `<rect x="21.5" y="30.5" width="6" height="8" rx="3" fill="#243237"/>` +
    `<rect x="36.5" y="30.5" width="6" height="8" rx="3" fill="#243237"/>` +
    `<path d="M 25 40.5 Q 29 43 32 43 Q 35 43 39 40.5" stroke="#243237" stroke-width="2.4" stroke-linecap="round" fill="none"/>` +
    `</svg>`
  return `data:image/svg+xml,${encodeURIComponent(svg)}`
}

export function useFaviconAgente(status?: 'conectado' | 'desligado') {
  // Guarda o favicon ORIGINAL 1x só (não a cada troca de status) -- senão trocar de conectado
  // pra desligado e voltar restauraria pro ícone do status anterior no unmount, nunca pro
  // favicon.svg de verdade (achado ao revisar: `link.href` já estaria sobrescrito pelo próprio
  // hook na 2ª chamada em diante).
  const originalRef = useRef<string | null>(null)

  useEffect(() => {
    const link = document.querySelector<HTMLLinkElement>('link[rel="icon"]')
    if (!link) return
    if (originalRef.current === null) originalRef.current = link.href
    link.href = status ? faviconAgenteSvg(CORES[status]) : originalRef.current
    return () => {
      if (originalRef.current !== null) link.href = originalRef.current
    }
  }, [status])
}
