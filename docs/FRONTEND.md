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

**Achado técnico registrado (CI, 2026-07-14)**: o primeiro run do CI (`.github/workflows/ci.yml`)
falhou no job de frontend com `npm ci` reclamando de `package-lock.json` fora de sincronia
(faltando `@emnapi/core`/`@emnapi/runtime`) — o lockfile tinha sido gerado só no Windows local
(`npm install`), e ficou sem as entradas de dependências opcionais específicas de Linux (o CI
roda em `ubuntu-latest`). `npm ci` local (Windows) não pegava o problema, porque validava
contra o mesmo lockfile que ele mesmo tinha gerado. Corrigido apagando `node_modules` +
`package-lock.json` e rodando `npm install` do zero, o que recapturou as entradas de todas as
plataformas — **lição**: `npm ci` local só garante que o lockfile bate com o `package.json`,
não que ele tem as entradas de todas as plataformas que o CI vai rodar.

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
      Layout.tsx               - compõe Sidebar + Topbar + <Outlet/> (ver seção própria abaixo)
      Sidebar.tsx               - navegação lateral (logo, nav extensível, off-canvas no mobile)
      Topbar.tsx                - menu mobile, tema, configurações, usuário, sair
      ThemeToggle.tsx           - botão sol/lua (reaproveitado no login e no topbar)
      icons.tsx                 - ícones SVG inline compartilhados (Home/Configurações/Sair/Menu)
    pages/
      Login.tsx                 - tela de login (design completo, ver seção própria abaixo)
      Login.test.tsx             - smoke test (Vitest + Testing Library, ver "Testes" abaixo)
      Home.tsx                 - página de boas-vindas da área autenticada
      Settings.tsx              - placeholder de configurações (link do topbar precisa ir a algum lugar)
    test/setup.ts               - matchers do jest-dom, carregado antes de cada suíte
    vite-env.d.ts               - referência aos tipos do cliente Vite (import.meta.env)
    App.tsx                    - rotas
```

## Testes (Vitest, adicionado em 2026-07-13)

Até esta rodada, toda a validação de frontend desta reconstrução (login, tema, navegação por
teclado da grade apagada no reset, etc.) viveu só em scripts Playwright ad-hoc fora do repo —
zero suíte automatizada commitada. Achado de auditoria: se alguém mexer no frontend sem esse
histórico de scratchpad, não tem `npm test` pra rodar. Vitest + Testing Library escolhidos por
já virem prontos pro ecossistema Vite (mesma config, `vite.config.ts`), sem precisar de um
bundler/transform separado como Jest exigiria.

- `frontend/vite.config.ts`: bloco `test` (`environment: 'jsdom'`, carrega
  `src/test/setup.ts`).
- `Login.test.tsx`: smoke test da tela de login — campos renderizam, alternar
  mostrar/esconder senha, erro estruturado aparece quando o login falha (mock de `lib/api.ts`,
  não bate no backend real — isso continua coberto pelos testes Python + validação manual),
  toggle de tema aplica `.dark` na raiz.
- `npm run test` (`vitest run`) — roda uma vez e sai (CI-friendly), não fica observando
  arquivos.
- **Escopo ainda pequeno de propósito**: só `Login.tsx` tem teste automatizado. O shell
  autenticado (Sidebar/Topbar/Home/Settings, adicionado em 2026-07-14) foi validado só com
  Playwright ad-hoc (desktop/mobile, claro/escuro, navegação, logout) — sem suíte commitada
  ainda. Cresce junto com a reconstrução incremental da parte de Bitins.

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

## Shell autenticado — Sidebar + Topbar + Home (2026-07-14)

Antes disso, a área autenticada era só um cabeçalho horizontal (`Layout.jsx` original) com a
logo, e-mail e sair, e `Home.tsx` era um placeholder de texto ("Login funcionando."). Pedido
direto: montar a "página principal" de verdade — sidebar de navegação, topbar (logo/nome,
usuário, tema, configurações), e uma Home com boas-vindas — **seguindo exatamente o padrão
visual já estabelecido no login, sem inventar uma linguagem nova** ("nunca fugir daquilo").

- **`Sidebar.tsx`**: painel fixo à esquerda (`bg-brand-navy`, igual ao painel de marca do
  login), logo em pílula branca no topo, faixa de 3 cores no rodapé (mesma assinatura visual
  do login e do cabeçalho antigo). Navegação vem de um array `NAV_ITEMS` extensível — só
  "Início" existe hoje (a tela de Bitins ainda não foi reconstruída); o próximo item entra
  ali sem mexer no resto do componente. Vira off-canvas no celular (`-translate-x-full` por
  padrão, `translate-x-0` quando aberta via hambúrguer no topbar), com um overlay escurecido
  atrás que fecha ao clicar fora.
- **`Topbar.tsx`**: barra fixa no topo do conteúdo (não da tela inteira — a sidebar já ocupa a
  largura própria em telas médias+). Da esquerda pra direita: botão de menu (só no celular),
  toggle de tema (`ThemeToggle.tsx`, já existia), botão de configurações (ícone de engrenagem,
  leva pra `/configuracoes`), e-mail do usuário, botão sair.
- **`pages/Settings.tsx`** (novo, placeholder): o botão de configurações no topbar precisa
  levar a algum lugar real, não um link morto — mas ainda não existe nada de fato
  configurável. Mesma lógica do `Home.tsx` original: placeholder honesto, cresce quando
  houver conteúdo.
- **`pages/Home.tsx`** reescrita: mensagem de boas-vindas usando o primeiro nome do usuário
  (`useAuth().user.nome`), título grande + subtítulo discreto + faixa de 3 cores — mesma
  hierarquia tipográfica do "Entrar" da tela de login, não uma composição nova.
- **Tema claro por padrão, escolha do usuário persiste** — comportamento que já existia
  (`ThemeContext.jsx`, `localStorage`), só confirmado/preservado nesta rodada, não alterado.
- **`components/icons.tsx`** (novo): ícones SVG inline compartilhados entre Sidebar/Topbar
  (Home, Configurações, Sair, Menu, Fechar) — mesmo padrão inline sem lib externa já usado em
  `Login.tsx`, só que num módulo próprio porque mais de um componente do shell usa os mesmos
  ícones (`Login.tsx` continua com os seus próprios, específicos da tela).

### Cartões de resumo pessoal na Home (2026-07-14)

Pedido direto: "deixar a Home simples mas útil". Decisão registrada com o usuário — dois
cartões (Rascunhos/Enviados), contando **só os BITins do próprio usuário logado**, sem lista
de recentes nem botão de ação rápida ("+ Novo BITin") nesta rodada: a tela de
detalhe/cadastro de BITin ainda não existe, e um link/botão pra lugar nenhum seria pior que
não ter nada.

- `GET /bitins/resumo-usuario` (novo, ver `docs/BACKEND.md`) — `{rascunhos, enviados}`
  escopado por `criado_por`, não o sistema inteiro.
- `Home.tsx`: busca o resumo ao montar (`useEffect`), mostra `—` enquanto carrega ou se a
  chamada falhar — **falha silenciosa de propósito**, não é crítico o bastante pra estampar um
  erro vermelho numa tela de boas-vindas.
- `lib/types.ts`: `ResumoUsuario` novo, espelhando `ResumoUsuarioResponse` do backend (mesmo
  padrão do tipo `User`).
- **Achado ao validar**: não há MongoDB real rodando nesta máquina (mesma limitação já
  documentada em "Rodando localmente" abaixo) — a chamada trava esperando conexão e os
  cartões ficam permanentemente em `—` ao testar contra o servidor de dev real. A correção do
  cálculo em si (2 rascunhos + 1 enviado → `{rascunhos: 2, enviados: 1}`, e isolamento por
  usuário) foi validada pelos 3 testes automatizados novos (`mongomock-motor`), não pela
  UI ao vivo — registrado com transparência, não sonegado.

### Tela de Configurações (2026-07-14)

Antes era só um placeholder ("Nada configurável ainda por aqui."). Escopo fechado com o
usuário: o que já dá pra fazer sem endpoint novo (Postgres/SQLite já funciona nesta máquina,
diferente do Mongo — validado ao vivo de verdade, não só por teste automatizado).

- **"Minha conta"** (somente leitura): nome, e-mail, setor (nome resolvido via `GET
  /sectors`, público) e nível de permissão (rótulo amigável — `Usuário`/`Gestor`/`Admin` — em
  vez do número cru). Trocar senha e editar o próprio perfil ficam pra uma rodada futura,
  quando os endpoints existirem (o backend hoje só tem `POST /auth/register`/`login`, nada de
  "trocar minha senha").
- **"Gestão de usuários"** (só visível se `user.permission_level >= 99`, decisão explícita do
  usuário — "só pra admin"): tabela com todos os usuários (`GET /users`, já exigia nível ≥ 1
  no backend — a UI é mais restritiva que o mínimo do backend de propósito) e um `<select>`
  por linha pra trocar o nível (`PATCH /users/{id}/permission`, backend já exigia nível 99).
  **Proteção contra auto-rebaixamento**: o `<select>` da própria linha do usuário logado fica
  desabilitado — evita um admin se rebaixar sem querer e ficar trancado fora da própria
  gestão.
- **"Sobre"**: versão do app, mesma fonte que o rodapé do login (`package.json`).
- **Achado ao validar**: para testar a seção de admin de verdade (nenhum usuário de teste
  local era admin), o usuário autorizou explicitamente promover `teste@example.com` pra nível
  99 direto no SQLite local só pra essa verificação — revertido pra `0` logo depois, e
  confirmado por leitura direta do banco que os dois usuários (`demo@example.com`,
  `teste@example.com`) voltaram exatamente ao estado original.

### "Meus Bitins" — listagem + visualização só-leitura (2026-07-14)

Escopo fechado colaborativamente com o usuário via `AskUserQuestion` (pedido explícito: "quero
decidir junto com você"). A primeira formulação da pergunta de escopo ("listagem só, ou
listagem + visualização mínima?") não ficou clara o suficiente e precisou ser reexplicada em
termos mais concretos antes de fechar.

- **`MeusBitins.tsx`** (rota `/bitins`): tabela com abas Todos/Rascunhos/Enviados (`GET /bitins`
  com `?status=`), colunas Código/Motivo/Solicitante/Status. Motivo e Solicitante são
  obrigatórios na lista (não só Código) porque rascunhos ainda não têm código — só é gerado no
  envio (`gerar_e_salvar_bitin_sql`) — e sem eles a linha de um rascunho ficaria em branco, sem
  nada pra identificar do que se trata.
- **Escopo "só os meus"**: `GET /bitins` passou a filtrar por `criado_por` no backend (mesma
  decisão já registrada em `resumo-usuario`/Home) — mudança de comportamento do endpoint
  existente, não só um filtro novo no frontend, pra não vazar motivo/solicitante de BITins de
  outros usuários pra quem só deveria ver os próprios. Nem admins veem a lista do sistema
  inteiro aqui (diferente de "Gestão de usuários" em Configurações, que é uma função
  administrativa separada).
- **`BitinDetail.tsx`** (rota `/bitins/:mongoId`, clique na linha): visualização só-leitura,
  ainda sem edição. Usa `GET /bitins/{mongo_id}/resumo` (`bitin_view.render_bitin_summary`) em
  vez do `content` bruto — reaproveita a lógica de diffs de campo (`dados_basicos_alterados`) e
  impactos operacionais que o backend já monta pra pré-visualização/tela final, em vez de
  reimplementar essa transformação no frontend.
- **Nota de acesso direto por URL**: `GET /bitins/{mongo_id}` e `/resumo` não checam dono (só
  `POST /draft`, `DELETE` e `/enviar` checam, via `_require_owner_or_admin`) — comportamento
  pré-existente do backend (leitura de um BITin específico por id é aberta a qualquer usuário
  autenticado, só a escrita é restrita). A listagem "Meus Bitins" não expõe outros ids pra
  descobrir, mas navegar direto pra uma URL `/bitins/{id}` de outra pessoa ainda funciona —
  não é uma regressão desta rodada, é o mesmo modelo de permissão que já existia.
- **Fora de escopo nesta rodada** (decidido com o usuário): botão "+ Novo BITin" (não existe
  tela de cadastro ainda) e edição no `BitinDetail` (fica travado, só leitura).
- **Ambiente**: não foi possível validar ao vivo com Playwright (sem MongoDB real nesta
  máquina, e as credenciais dos usuários de teste locais não são conhecidas por mim — foram
  criadas pelo próprio usuário via `POST /auth/register`, não seedadas). Coberto pela suíte
  automatizada (172 testes de backend com `mongomock-motor`, incluindo o novo escopo por
  `criado_por`) e por `typecheck`/`lint`/`test`/`build` limpos no frontend.

## O que já funciona

Validado com Playwright ad-hoc contra o backend real nesta máquina (sem MongoDB real, ver
"Rodando localmente" abaixo).

- Login (`POST /auth/login`) → redireciona pra `/`, com validação visual de erro (credencial
  errada) e estado de carregamento.
- Rota protegida: sem token, qualquer rota redireciona pro login.
- Shell autenticado: sidebar de navegação (off-canvas no celular, agora com "Início" e "Meus
  Bitins"), topbar com tema/configurações/usuário/sair, Home com boas-vindas + cartões de
  resumo pessoal (rascunhos/enviados, `GET /bitins/resumo-usuario`), página de Configurações
  ("Minha conta" + "Sobre" pra todo mundo, "Gestão de usuários" só pra admin).
- "Meus Bitins" (`/bitins`): listagem escopada pro próprio usuário, abas por status, clique na
  linha abre visualização só-leitura (`/bitins/:mongoId`) — ver seção acima. Validado pela
  suíte automatizada (sem verificação visual ao vivo nesta rodada, ver nota de ambiente acima).
- Logout: volta pro login.
- Tema claro/escuro (toggle no login E no topbar pós-login, padrão claro, escolha persiste no
  navegador) — testado nos dois temas, desktop e mobile.

## O que NÃO está nesta fatia ainda (próximos incrementos)

- **Criar/editar rascunho, grid de materiais, checklist, botão "+ Novo BITin"** — a listagem e
  a visualização só-leitura já existem (`MeusBitins.tsx`/`BitinDetail.tsx`, 2026-07-14), mas
  cadastro/edição de verdade ainda não. Apagados de propósito no reset, ver "Reset" acima.
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
