// Logo do Agente SAP - BITin (2026-07-23) -- crachá navy com um robô: antena, rosto branco,
// olho esquerdo sempre aberto + olho direito piscando (SMIL `<animate>`, roda nativamente no
// navegador) e um sorriso pequeno/simétrico. Piscar é só na versão web (pedido explícito: "o
// ícone estático só no python do agente, no front pode deixar ele piscando normalmente") --
// `sap-agent/logo_agente.py` (ícone da bandeja/instalador/executáveis) é estático, sem piscar.
export default function AgenteLogoIcon({ size = 52 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <rect x="2" y="2" width="60" height="60" rx="16" fill="#32464d" />
      <line x1="32" y1="14" x2="32" y2="20" stroke="#ea7603" strokeWidth="3" strokeLinecap="round" />
      <circle cx="32" cy="11" r="3.5" fill="#ea7603" />
      <rect x="16" y="20" width="32" height="26" rx="10" fill="#ffffff" />

      {/* Olho esquerdo -- sempre aberto. */}
      <circle cx="25" cy="33" r="3.5" fill="#32464d" />

      {/* Olho direito -- alterna entre aberto (círculo) e fechado (arco), nunca junto com o
          esquerdo -- é ELE que "pisca". */}
      <circle cx="39" cy="33" r="3.5" fill="#32464d">
        <animate attributeName="opacity" values="1;1;0;0;1" keyTimes="0;0.82;0.87;0.95;1" dur="4s" repeatCount="indefinite" />
      </circle>
      <path d="M 35 33.5 Q 39 37.5 43 33.5" stroke="#32464d" strokeWidth="2.4" strokeLinecap="round" fill="none" opacity="0">
        <animate attributeName="opacity" values="0;0;1;1;0" keyTimes="0;0.82;0.87;0.95;1" dur="4s" repeatCount="indefinite" />
      </path>

      {/* Sorriso pequeno e simétrico em torno de x=32. */}
      <path d="M 26 40 Q 29 42 32 42 Q 35 42 38 40" stroke="#32464d" strokeWidth="2.2" strokeLinecap="round" fill="none" />
    </svg>
  )
}
