import { useId, useState } from 'react'

// Logo do Agente SAP - BITin (2026-07-23, redesign v2 -- "remodela tudo isso, faz do 0 esse
// ícone do melhor jeito que tu achar"). Crachá com gradiente (mais volume que cor chapada),
// "visor" de vidro fosco no rosto (em vez do retângulo branco liso), olhos em cápsula que
// piscam achatando (scale), sorriso mantido (validado em rodadas anteriores, junto com "sem
// braço/emoji", crachá navy arredondado e antena de acento). Só na versão web -- estático
// (`sap-agent/logo_agente.py`) continua sem gradiente/animação nenhuma, ícone do `.exe`/
// bandeja/instalador não pode "respirar" nem piscar.
//
// `status` dá 3 leituras pro mesmo ícone, sem trocar de componente: 'conectado' (verde, halo
// pulsando na antena), 'desligado' (vermelho -- pedido explícito: "faz tbm pra ele vermelho
// desligado", mesma linguagem de cor já usada no anel/glow de AgenteSapStatus.tsx pra
// desconectado), ou omitido (laranja neutro -- usado onde ainda não se sabe/não importa o
// status, ex. branding genérico).
//
// Timing sorteado 1x por montagem (`useState(() => ...)`, nunca recalcula em re-render) --
// cada instância na tela pisca/respira fora de sincronia com as outras. Dois eventos de piscar
// por ciclo -- "solo" (só o olho direito) e "duplo" (os dois juntos) -- em posição E ordem
// aleatórias. `prefers-reduced-motion` desliga tudo (respiração via CSS + piscar/halo via JS).
function aleatorioEntre(min: number, max: number): number {
  return min + Math.random() * (max - min)
}

// Monta `values`/`keyTimes` de um `<animate>`/`<animateTransform>`: fica em `valorBase` o tempo
// todo, exceto durante os `intervalos` (frações de 0 a 1 do ciclo), onde salta pra `valorPico`
// -- entrada/saída bem próximas (epsilon) pra parecer um "snap", não uma transição suave.
function construirTrilha(
  valorBase: string,
  valorPico: string,
  intervalos: Array<[number, number]>,
): { values: string; keyTimes: string } {
  const eps = 0.004
  const pontos: Array<[number, string]> = [[0, valorBase]]
  for (const [inicio, fim] of [...intervalos].sort((a, b) => a[0] - b[0])) {
    const ultimoTempo = pontos[pontos.length - 1][0]
    pontos.push([Math.max(ultimoTempo + eps, inicio - eps), valorBase])
    pontos.push([inicio, valorPico])
    pontos.push([fim, valorPico])
    pontos.push([Math.min(1 - eps, fim + eps), valorBase])
  }
  pontos.push([1, valorBase])
  return {
    values: pontos.map((p) => p[1]).join(';'),
    keyTimes: pontos.map((p) => p[0].toFixed(4)).join(';'),
  }
}

function useAnimacaoAleatoria() {
  return useState(() => {
    const reduzida =
      typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches === true

    const duracaoOlhos = aleatorioEntre(6, 11)
    const duracaoRespiracao = aleatorioEntre(5, 9)
    const atrasoRespiracao = aleatorioEntre(0, 4)
    const duracaoAntena = aleatorioEntre(1.6, 2.6)

    // 2 eventos de ~3,5% do ciclo cada, separados por uma folga -- sorteia a posição dos 2 E
    // qual dos dois (solo ou duplo) cai em cada posição, pra ordem no tempo variar entre
    // instâncias.
    const janela = 0.035
    const gap = 0.15
    const inicioA = aleatorioEntre(0.08, 0.4)
    const inicioB = aleatorioEntre(inicioA + janela + gap, 0.92 - janela)
    const soloPrimeiro = Math.random() < 0.5
    const intervaloSolo: [number, number] = soloPrimeiro ? [inicioA, inicioA + janela] : [inicioB, inicioB + janela]
    const intervaloDuplo: [number, number] = soloPrimeiro ? [inicioB, inicioB + janela] : [inicioA, inicioA + janela]

    return {
      reduzida,
      duracaoOlhos,
      duracaoRespiracao,
      atrasoRespiracao,
      duracaoAntena,
      olhoDireito: construirTrilha('1 1', '1 0.12', [intervaloSolo, intervaloDuplo]),
      olhoEsquerdo: construirTrilha('1 1', '1 0.12', [intervaloDuplo]),
    }
  })[0]
}

const CORES_ACENTO: Record<'conectado' | 'desligado' | 'neutro', { de: string; para: string; halo: string }> = {
  conectado: { de: '#96c91a', para: '#79aa00', halo: '#79aa00' },
  desligado: { de: '#f0645a', para: '#dc2626', halo: '#dc2626' },
  // `halo` nunca é usado pro estado neutro (`mostrarHalo` só é true pra conectado/desligado).
  neutro: { de: '#f3902e', para: '#ea7603', halo: '' },
}

export default function AgenteLogoIcon({
  size = 52,
  status,
}: {
  size?: number
  status?: 'conectado' | 'desligado'
}) {
  const anim = useAnimacaoAleatoria()
  const idBase = useId()
  const cores = CORES_ACENTO[status ?? 'neutro']
  const mostrarHalo = status === 'conectado' || status === 'desligado'

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id={`${idBase}-cracha`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#3d545c" />
          <stop offset="100%" stopColor="#26343a" />
        </linearGradient>
        <linearGradient id={`${idBase}-visor`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#e7edf0" />
          <stop offset="100%" stopColor="#c7d2d6" />
        </linearGradient>
        <linearGradient id={`${idBase}-acento`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor={cores.de} />
          <stop offset="100%" stopColor={cores.para} />
        </linearGradient>
      </defs>

      <g
        style={
          anim.reduzida
            ? undefined
            : {
                transformBox: 'fill-box',
                transformOrigin: '50% 50%',
                animation: `agente-respirar ${anim.duracaoRespiracao}s ease-in-out ${anim.atrasoRespiracao}s infinite`,
              }
        }
      >
        {/* Crachá -- gradiente navy (mais volume que cor chapada) + contorno sutil mais escuro. */}
        <rect x="2" y="2" width="60" height="60" rx="18" fill={`url(#${idBase}-cracha)`} />
        <rect x="2.5" y="2.5" width="59" height="59" rx="17.5" stroke="#1c282c" strokeWidth="1" opacity="0.5" />

        {/* Antena -- gradiente de acento, cor conforme `status`. */}
        <line x1="32" y1="13" x2="32" y2="19" stroke={`url(#${idBase}-acento)`} strokeWidth="2.6" strokeLinecap="round" />
        {mostrarHalo && !anim.reduzida && (
          <circle cx="32" cy="10.5" r="6" fill={cores.halo} opacity="0">
            <animate attributeName="opacity" values="0;0.5;0" dur={`${anim.duracaoAntena}s`} repeatCount="indefinite" />
          </circle>
        )}
        <circle cx="32" cy="10.5" r="3.2" fill={`url(#${idBase}-acento)`} />

        {/* Visor -- vidro fosco com sombra sutil por baixo, pra parecer encaixado no crachá. */}
        <rect x="15" y="19" width="34" height="27" rx="12" fill="#1c282c" opacity="0.18" />
        <rect x="16" y="20" width="32" height="25" rx="11" fill={`url(#${idBase}-visor)`} />

        {/* Olhos em cápsula -- pisca achatando (scaleY), não sumindo com opacidade. */}
        <rect
          x="21.5"
          y="30.5"
          width="6"
          height="8"
          rx="3"
          fill="#243237"
          style={{ transformBox: 'fill-box', transformOrigin: '50% 50%' }}
        >
          {!anim.reduzida && (
            <animateTransform
              attributeName="transform"
              type="scale"
              values={anim.olhoEsquerdo.values}
              keyTimes={anim.olhoEsquerdo.keyTimes}
              dur={`${anim.duracaoOlhos}s`}
              repeatCount="indefinite"
            />
          )}
        </rect>
        <rect
          x="36.5"
          y="30.5"
          width="6"
          height="8"
          rx="3"
          fill="#243237"
          style={{ transformBox: 'fill-box', transformOrigin: '50% 50%' }}
        >
          {!anim.reduzida && (
            <animateTransform
              attributeName="transform"
              type="scale"
              values={anim.olhoDireito.values}
              keyTimes={anim.olhoDireito.keyTimes}
              dur={`${anim.duracaoOlhos}s`}
              repeatCount="indefinite"
            />
          )}
        </rect>

        {/* Sorriso -- mantido (validado em rodadas anteriores), levemente mais espesso. */}
        <path
          d="M 25 40.5 Q 29 43 32 43 Q 35 43 39 40.5"
          stroke="#243237"
          strokeWidth="2.4"
          strokeLinecap="round"
          fill="none"
        />
      </g>
    </svg>
  )
}
