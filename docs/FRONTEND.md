# Frontend do BITin (`frontend/`)

Primeira fatia do frontend web que substitui o Excel/VBA — construída depois do backend
(`backend/`) já estar validado com 147 testes. Ver `docs/BACKEND.md` para a API que este
frontend consome.

## Reset da tela de Bitins (2026-07-13)

Depois de 8 rodadas de feedback direto tentando acertar o design da tela de cadastro
(`BitinDetail.jsx`, `MaterialGrid.jsx`, `MaterialDetailModal.jsx`, `ChecklistEditor.jsx`) e da
listagem (`MeusBitins.jsx`), o resultado ainda não estava bom o suficiente ("tá muito
confuso") — decisão explícita do usuário: **apagar tudo dessa parte e reconstruir do zero,
incrementalmente**, começando pelo login/autenticação e só depois voltando pra parte de
Bitins, uma tela de cada vez.

- **Apagados**: `pages/BitinDetail.jsx`, `pages/MeusBitins.jsx`, `components/MaterialGrid.jsx`,
  `components/MaterialDetailModal.jsx`, `components/ChecklistEditor.jsx`, `lib/bitinFields.js`,
  `lib/bitinErrors.js`, `lib/textSearch.js`.
- **Mantidos de propósito**: `pages/Login.jsx`, `context/AuthContext.jsx`,
  `context/ThemeContext.jsx`, `components/RequireAuth.jsx`, `components/Layout.jsx` (shell —
  cabeçalho, logo, toggle de tema, sair), `lib/api.js`. Nenhuma lógica de negócio do backend
  foi tocada (`scripts/`, `backend/api/`) — os endpoints de materiais/checklist continuam de
  pé e testados, só não têm UI consumindo ainda.
- **Rota autenticada temporária**: `pages/Home.jsx`, um placeholder vazio em `/` só pra rota
  protegida ter algo pra mostrar enquanto a tela de Bitins não é reconstruída.
- O histórico completo do que foi tentado (e por quê cada rodada mudou de direção) continua em
  `docs/CHANGELOG.md` — vale ler antes de reconstruir, pra não repetir os mesmos becos sem
  saída (ex.: grid de checklist em cards de altura variável ficou desigual; grade de materiais
  com ~70 colunas visíveis por padrão ficou confusa demais).

## Stack e por quê

**React 19 + TypeScript + Vite + Tailwind 4 + react-router-dom + axios, sem lib de estado
global** (Redux/Zustand). O estado de tela é local — Context API (`AuthContext`,
`ThemeContext`) + `useState` bastam nesse estágio.

**TypeScript (migração completa, 2026-07-14)**: todo o frontend (11 arquivos — pequeno o
suficiente pra migrar de uma vez, já que a tela de Bitins foi apagada no reset) converteu de
`.jsx`/`.js` pra `.tsx`/`.ts`. `tsconfig.app.json`/`tsconfig.node.json` com `strict: true`,
`noUnusedLocals`/`noUnusedParameters`. `npm run typecheck` (`tsc -b --noEmit`) roda separado
do `build` (que também typecheca antes de gerar o bundle: `"build": "tsc -b && vite build"`).

**Achado técnico registrado**: `vitest/config` empacota sua própria cópia interna de `vite`,
com um tipo `Plugin`/`PluginOption` estruturalmente diferente do `vite` de nível superior que
`@vitejs/plugin-react` usa — puramente um conflito de tipos entre as duas cópias aninhadas
(build/dev/test já funcionavam certinho antes de mexer nisso; só o `tsc` reclamava). Contornado
com um cast pontual (`as any[]`) só no array de `plugins` de `vite.config.ts`, comentado no
próprio arquivo.

## Identidade visual (adicionado em 2026-07-13, revisado no mesmo dia — tema claro/escuro)

Paleta extraída do logo da empresa (Grain & Protein Technologies — hexágonos
frango/grão/porco em volta do texto, cada um numa cor), definida como tokens Tailwind v4
(`@theme` em `frontend/src/index.css`, não hardcoded em cada componente). Dois grupos de
token:

**Marca** (não mudam entre os temas claro/escuro):

| Token | Uso |
|---|---|
| `brand-navy` / `brand-navy-dark` | Cor primária — cabeçalho do app, botões primários, links, foco de campo, `accent-color` de checkbox/select. Escolhida pra tudo que precisa de bom contraste (é escura). |
| `brand-gold` | Só decorativo (faixa de 3 cores no cabeçalho) — **nunca como cor de texto**: contraste ruim contra fundo claro E contra fundo escuro (é uma cor clara). |
| `brand-green` | Faixa decorativa do cabeçalho; status "positivo" continua usando os tons semânticos do Tailwind (`green-700` etc.) onde precisa de contraste de texto pequeno. |
| `brand-orange` | Acento reservado pra indicar "campo editável"/"Novo" em telas de dados tabulares, sem confundir com vermelho de erro de validação. |

**Semânticos** (mudam entre os temas — todo componente usa estes nomes, nunca `gray-*`
direto, pra que os dois temas fiquem consistentes num só lugar):

| Token | Uso |
|---|---|
| `app-bg` | Fundo da página (fora dos cards). |
| `surface` / `surface-alt` | Fundo de card/tabela/modal / fundo de zebra e painéis sutis. |
| `surface-header` | Tom sólido (não translúcido) — cabeçalho de tabela e hover de linha. Precisa ser sólido, não com opacidade, se algum dia houver coluna congelada (`position: sticky`) de novo — ver "Achado técnico registrado" no histórico do `CHANGELOG.md`. |
| `line` | Toda borda/divisória. |
| `ink` / `ink-muted` / `ink-faint` | Texto primário / secundário / terciário-desabilitado. |

Erros de validação continuam em vermelho puro (Tailwind `red-*`) — cor semântica de erro não
muda com a marca nem com o tema, em nenhuma tela.

**Tema claro/escuro** (`ThemeContext.jsx`): toggle no cabeçalho (ícone sol/lua), classe `.dark`
na raiz (`@custom-variant dark` em `index.css`, não `prefers-color-scheme` — decisão explícita:
**padrão é sempre claro**, não detecta o tema do sistema operacional). Escolha do usuário
persiste em `localStorage`. Os tokens semânticos acima são redefinidos sob `.dark` — como o
Tailwind gera variáveis CSS de verdade a partir de `@theme`, a troca de tema não precisa de
`dark:` em cada classe usada nos componentes.

**Logo**: `frontend/public/logo.svg`, arquivo real da empresa (enviado pelo usuário) — usado no
cabeçalho (`Layout.jsx`, dentro de um `bg-white` porque o arquivo é um JPEG embutido em SVG com
fundo branco sólido, não transparente) e na tela de login (`Login.jsx`).

## Estrutura

```text
frontend/
  src/
    lib/
      api.ts                  - cliente axios (token via localStorage, interceptor 401)
      types.ts                 - tipos compartilhados (User, espelha UserOut do backend)
    context/
      AuthContext.tsx         - login/logout/estado do usuário (Context API, sem lib externa)
      ThemeContext.tsx         - tema claro/escuro, padrão claro, persiste em localStorage
    components/
      RequireAuth.tsx         - guarda de rota (redireciona pro /login sem token)
      Layout.tsx               - shell: cabeçalho (logo, e-mail, toggle de tema, sair)
      ThemeToggle.tsx           - botão sol/lua (extraído de Layout.jsx pra reaproveitar no login)
    pages/
      Login.tsx                 - tela de login (design completo, ver seção própria abaixo)
      Login.test.tsx             - smoke test (Vitest + Testing Library, ver "Testes" abaixo)
      Home.tsx                 - placeholder da área autenticada (ver "Reset" acima)
    test/setup.ts               - matchers do jest-dom, carregado antes de cada suíte
    vite-env.d.ts               - referência aos tipos do cliente Vite (import.meta.env)
    App.tsx                    - rotas
```

## Testes (Vitest, adicionado em 2026-07-13)

Até esta rodada, toda a validação de frontend desta reconstrução (login, tema, navegação por
teclado da grade apagada no reset, etc.) viveu só em scripts Playwright ad-hoc fora do repo —
zero suíte automatizada commitada. Achado de auditoria: se alguém mexer no frontend sem esse
histórico de scratchpad, não tem `npm test` pra rodar. Vitest + Testing Library escolhidos por
já virem prontos pro ecossistema Vite (mesma config, `vite.config.js`), sem precisar de um
bundler/transform separado como Jest exigiria.

- `frontend/vite.config.js`: bloco `test` (`environment: 'jsdom'`, carrega
  `src/test/setup.js`).
- `Login.test.jsx`: smoke test da tela de login — campos renderizam, alternar
  mostrar/esconder senha, erro estruturado aparece quando o login falha (mock de `lib/api.js`,
  não bate no backend real — isso continua coberto pelos testes Python + validação manual),
  toggle de tema aplica `.dark` na raiz.
- `npm run test` (`vitest run`) — roda uma vez e sai (CI-friendly), não fica observando
  arquivos.
- Escopo deliberadamente pequeno por enquanto: só a única tela que existe (Login). Cresce
  junto com a reconstrução incremental da parte de Bitins.

**Achado técnico registrado**: sob Vitest (não sob `vite build`/`vite dev`, que sempre
funcionaram normalmente), todo componente com JSX — não só os arquivos de teste — falhava com
`ReferenceError: React is not defined`, mesmo com `@vitejs/plugin-react` registrado e o runtime
automático de JSX funcionando fora de teste. Corrigido com `esbuild: { jsxInject: "import React
from 'react'" }` em `vite.config.js` — injeta o import em toda transformação esbuild, sem afetar
o build/dev real (o `vite build` já usa outro transform, `oxc`, e ignora essa opção — confirmado
pelo aviso "Both esbuild and oxc options were set" no log de build, inofensivo).

## Tela de login (design completo, 2026-07-13)

Primeira tela reconstruída depois do reset — pedido direto: "focar 100% no design UI/UX",
usando o backend real (não mock) desde já, já que Postgres já está rodando e testado nesta
máquina.

- **Layout dividido** (`Login.jsx`): painel de marca à esquerda (`bg-brand-navy`, logo, título,
  subtítulo, faixa de 3 cores — mesma referência visual do cabeçalho pós-login) + formulário à
  direita, só em telas médias+ (`hidden md:flex`). No celular o painel de marca colapsa pra só
  a logo centralizada acima do formulário, em vez de gastar metade da tela vertical com algo
  decorativo. Logo + título + subtítulo formam um único bloco vertical centralizado
  (`justify-center`, não `justify-between`) — a 1ª versão prendia a logo isolada no topo do
  painel, com um vão vazio grande até o texto lá embaixo ("a logo ficou meio perdida"),
  corrigido agrupando os três num bloco só.
- **Versão da aplicação no rodapé** (não texto fixo): `Login.jsx` importa `version` direto de
  `frontend/package.json` (suportado nativamente pelo Vite, sem config extra — confirmado com
  `npm run build`). `package.json` estava com o placeholder padrão do Vite (`0.0.0`),
  sincronizado pra `0.5.0` — mesma versão rastreada em `backend/config.py` e nas releases.
- **`ThemeToggle.jsx` extraído de `Layout.jsx`**: antes só existia dentro do cabeçalho
  pós-login; agora é um componente próprio (`className` ajustável pra contraste claro/escuro
  em fundos diferentes) — o login também tem o toggle (canto superior direito), porque a
  escolha de tema deve valer antes de autenticar, não só depois.
- **Campos com ícone + validação visual**: e-mail e senha com ícone à esquerda (SVG inline,
  sem lib de ícones externa), foco com anel navy. Senha tem botão de mostrar/esconder (ícone
  de olho) — comum em formulário de login, evita erro de digitação silencioso.
- **Erro estruturado com ícone + `role="alert"`**: banner vermelho claro com ícone de alerta,
  em vez de só texto vermelho solto — mais visível e acessível (leitor de tela anuncia).
- **Estado de carregamento com spinner**: botão mostra um spinner SVG girando + "Entrando..."
  enquanto a requisição está em voo, em vez de só trocar o texto.
- **Sem "esqueci minha senha"/"criar conta" de propósito**: o backend só tem `POST
  /auth/login` e `POST /auth/register` — não existe fluxo de reset de senha. Não construí um
  link que levaria a lugar nenhum; registro de usuário é decisão de admin/bootstrap, não
  self-service (ver `docs/BACKEND.md`, seção "Autenticação"), então também não tem link aqui.

## O que já funciona

Validado com Playwright ad-hoc contra o backend real nesta máquina (sem MongoDB real, ver
"Rodando localmente" abaixo).

- Login (`POST /auth/login`) → redireciona pra `/`, com validação visual de erro (credencial
  errada) e estado de carregamento.
- Rota protegida: sem token, qualquer rota redireciona pro login.
- Logout: volta pro login.
- Tema claro/escuro (toggle no cabeçalho pós-login E na tela de login, padrão claro, escolha
  persiste no navegador) — testado nos dois temas, desktop e mobile.

## O que NÃO está nesta fatia ainda (próximos incrementos)

- **Toda a tela de Bitins** (listagem "Meus Bitins", criar/editar rascunho, grid de materiais,
  checklist, visualização de enviado) — apagada de propósito, ver "Reset" acima. Reconstrução
  incremental, começando pela listagem depois que o login estiver "100%".
- **RBAC visível na UI** — o backend já recusa (`403`) quem tenta editar/excluir algo sem
  permissão; a versão anterior escondia alguns botões preventivamente, mas essa UI foi apagada
  no reset. Refazer quando a listagem voltar.

## Rodando localmente

```powershell
# backend (outro terminal, ver docs/BACKEND.md)
.venv/Scripts/python.exe -m uvicorn backend.main:app --reload

# frontend
cd frontend
npm install
npm run dev
```

Copie `frontend/.env.example` para `frontend/.env` se a API não estiver em
`http://127.0.0.1:8000/api/v1` (`VITE_API_BASE_URL`).

**Sem MongoDB real configurado**: o backend sobe e login/registro funcionam (Postgres/SQLite),
mas qualquer ação de `/bitins` (que depende do Mongo) devolve `500`. Isso não é um bug do
frontend — é a mesma limitação documentada em `docs/BACKEND.md`. Pra testar o fluxo de BITin
sem MongoDB real, é preciso rodar o backend com `mongomock-motor` no lugar do cliente Mongo
real (mesma estratégia dos testes automatizados).
