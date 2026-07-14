import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
  },
  // Vitest lê a mesma config -- não existia nenhuma suíte de teste de frontend commitada no
  // repo (toda a validação E2E desta sessão viveu só em scripts Playwright fora do repo).
  // jsdom simula o DOM sem precisar de browser real, suficiente pra smoke test de componente.
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.js',
    globals: true,
  },
  // Achado: sob Vitest (não sob `vite build`/`vite dev`), o JSX de todo o app -- não só dos
  // arquivos de teste -- falhava com "React is not defined", mesmo com @vitejs/plugin-react
  // registrado e o runtime automático funcionando normalmente fora de teste. `jsxInject`
  // injeta o import em toda transformação esbuild, contornando o problema sem mudar nada do
  // build/dev real (que já funciona sem isso -- só afeta como o esbuild processa o arquivo).
  esbuild: { jsxInject: "import React from 'react'" },
})
