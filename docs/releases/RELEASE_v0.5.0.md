# Release v0.5.0 — Autenticação consolidada; reset da tela de Bitins pra reconstrução incremental

Release criado a partir da tag `v0.5.0`.

## Resumo

- Objetivo original: reconstruir a tela de cadastro de Bitins como réplica da planilha Excel
  real, em cima da v0.4.0. Isso foi tentado em 8 rodadas de feedback direto (cabeçalho em
  faixas, checklist de 22 itens, grid de materiais estilo Excel, identidade visual da marca,
  tema claro/escuro) — histórico completo em `docs/CHANGELOG.md`.
- **Decisão de fechamento desta versão**: depois da 8ª rodada, o resultado ainda estava "muito
  confuso". Em vez de continuar iterando em cima de uma base que não estava funcionando, a
  tela de cadastro/listagem inteira foi apagada, e a reconstrução vai ser incremental —
  login/autenticação primeiro, Bitins depois, parte por parte.
- Status: o que sobrevive e fecha esta versão é a base de autenticação e identidade visual —
  não o formulário de Bitins (que volta a não ter UI, só backend). Próxima versão cobre o que
  for reconstruído da parte de Bitins.

## O que fecha nesta versão

- **Login/autenticação**: `POST /auth/login`, rota protegida (`RequireAuth`) redireciona pro
  login sem token, logout, interceptor axios limpa token em `401`.
- **Tela de login com design completo** (`Login.jsx`, foco 100% em UI/UX): layout dividido
  (painel de marca navy + formulário), campos com ícone, botão de mostrar/esconder senha, erro
  estruturado com `role="alert"`, spinner de carregamento no botão, tema claro/escuro
  disponível já no login (`ThemeToggle.jsx` extraído de `Layout.jsx` pra reaproveitar),
  responsivo (painel de marca colapsa no celular), versão da aplicação no rodapé lida de
  `package.json` (não texto fixo).
- **Identidade visual da marca** (Grain & Protein Technologies): paleta como tokens Tailwind
  v4, logo real (`frontend/public/logo.svg`) no cabeçalho e na tela de login, tema claro/escuro
  (toggle, padrão claro, persiste no navegador).
- **Shell autenticado** (`Layout.jsx`): cabeçalho com logo, e-mail do usuário, toggle de tema,
  botão sair — base pras próximas telas.

## O que foi tentado e revertido nesta mesma versão (histórico, não entra no release)

8 rodadas de tela de cadastro/listagem de Bitins (grid de materiais estilo Excel dirigido por
schema, checklist editável, colar do SAP, navegação por teclado, painel de Detalhes) — todas
revertidas no reset final. Detalhes completos em `docs/CHANGELOG.md`, seção `[v0.5.0]`. Vale
ler antes de reconstruir, pra não repetir os mesmos becos sem saída (ex.: grid de checklist em
cards de altura variável ficou desigual; grade de materiais com ~70 colunas visíveis por
padrão ficou confusa demais).

## Validação

- **158 testes automatizados Python** (era 147 na v0.4.0) — backend inalterado durante toda
  essa versão, incluindo o reset (só a UI que consumia os endpoints de materiais/checklist foi
  apagada, os endpoints continuam de pé e testados).
- Login → rota protegida → logout validado com Playwright ad-hoc; zero erro de console.

## Como reproduzir

```powershell
# backend
.venv/Scripts/python.exe -m uvicorn backend.main:app --reload

# frontend (outro terminal)
cd frontend
npm install
npm run dev
```

## Notas

- Próximo incremento: reconstrução incremental da tela de Bitins (listagem, depois cadastro),
  a partir da base de autenticação/identidade visual que fechou aqui. Ver `docs/FRONTEND.md`,
  seção "Reset da tela de Bitins" e "O que NÃO está nesta fatia ainda".
- Ver `CHANGELOG.md` para a lista completa (incluindo o histórico das 8 rodadas revertidas) e
  `docs/FRONTEND.md`/`docs/BACKEND.md` para arquitetura e decisões registradas.
