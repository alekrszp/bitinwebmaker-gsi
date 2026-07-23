// Client do agente SAP local (2026-07-22) -- roda no PC do próprio engenheiro
// (`sap-agent/servidor.py`), NÃO é o backend do BITin. Usa `fetch()` puro, separado do client
// axios compartilhado (`lib/api.ts`) de propósito: o interceptor de response de `api.ts`
// limpa a sessão do BITin em QUALQUER `401` que passe por ele, de qualquer origem -- reusar o
// mesmo client pro agente local (que roda em outra porta, outro processo, pode estar offline
// o tempo todo) arriscaria derrubar a sessão do usuário por causa do agente, não do backend.
const AGENTE_BASE_URL = import.meta.env.VITE_SAP_AGENT_URL || 'http://127.0.0.1:39217'

// Timeout curto (2026-07-22) -- se o agente não estiver rodando, `fetch` a `localhost` numa
// porta fechada geralmente falha rápido, mas um timeout explícito evita que o poll de status
// fique pendurado caso algo (firewall, antivírus corporativo) segure a conexão.
async function fetchComTimeout(url: string, opcoes: RequestInit, timeoutMs: number): Promise<Response> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  try {
    return await fetch(url, { ...opcoes, signal: controller.signal })
  } finally {
    clearTimeout(timer)
  }
}

export async function consultarStatusAgente(): Promise<boolean> {
  try {
    const resp = await fetchComTimeout(`${AGENTE_BASE_URL}/status`, {}, 2000)
    return resp.ok
  } catch {
    return false
  }
}

// "Com o agente aberto ele vai validar com o sistema... pegar a conta logada, todas as
// informações do usuário" (2026-07-23, pedido explícito) -- manda quem está logado assim que
// detecta o agente conectado, só pra exibir na janela do agente (ver
// sap-agent/estado_agente.py) -- não é autenticação nenhuma, best-effort (falha silenciosa se
// o agente cair no meio do caminho, não é crítico pro resto da tela funcionar).
export async function identificarUsuarioNoAgente(usuario: {
  nome: string
  email: string
  setor: string
}): Promise<void> {
  try {
    await fetchComTimeout(
      `${AGENTE_BASE_URL}/identificar-usuario`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(usuario),
      },
      3000,
    )
  } catch {
    // best-effort, ver comentário acima
  }
}

// Abre/foca o agente local via protocolo customizado registrado por
// `sap-agent/registrar_protocolo.ps1` -- decisão do usuário: "quando o usuário clicar no botão
// de abrir o scripting, ele roda um python" sem instalar/gerenciar um "programa" visível.
export function abrirAgenteViaProtocolo(): void {
  window.location.href = 'bitinsap://abrir'
}
