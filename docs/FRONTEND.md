# Frontend do BITin (`frontend/`)

Primeira fatia do frontend web que substitui o Excel/VBA — construída depois do backend
(`backend/`) já estar validado com 147 testes. Ver `docs/BACKEND.md` para a API que este
frontend consome.

> **Como ler este documento**: as seções abaixo são um diário cronológico de construção (cada
> `##`/`###` é datado) — registram a decisão e o PORQUÊ de cada rodada, não necessariamente o
> estado atual (uma rodada seguinte muda o que uma anterior descreveu, sem voltar a editar o
> texto antigo). Pra estado ATUAL: a árvore de arquivos em "## Estrutura" e as seções mais
> recentes (maior data no título) são as mais confiáveis; qualquer coisa sobre nível de
> permissão numérico (`66`/`77`/`88`/`89`/`99`) fora da seção "Revisão do modelo de permissões"
> mais recente é quase certamente de um esquema anterior — a fonte de verdade viva do modelo de
> permissões é sempre `docs/BACKEND.md`/`docs/BITIN_MODEL.md`, nunca este histórico.

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

## Identidade visual (adicionado em 2026-07-13, revisado em 2026-07-15 — paleta oficial)

Tokens Tailwind v4 (`@theme` em `frontend/src/index.css`, não hardcoded em cada componente).
**Paleta atualizada em 2026-07-15** com os valores do guia de marca oficial (print com
HEX/RGB/CMYK/Pantone enviado pelo usuário) — substitui a aproximação anterior tirada pixel a
pixel dos arquivos de logo (frontend/public/brand/), que era só uma leitura visual. Dois
grupos de token:

**Marca** (não mudam entre os temas claro/escuro):

| Token | Hex | Uso |
|---|---|---|
| `brand-navy` | `#32464d` ("GPT Dark Blue") | Cor primária — cabeçalho do app, botões primários, links, foco de campo, `accent-color` de checkbox/select. |
| `brand-navy-light` | `#6c8899` ("GPT Light Blue") | Cor oficial da marca, reaproveitada pro papel de variante clara do navy (já existia esse papel no sistema; antes era um tom calculado à mão, agora é uma cor real do guia). |
| `brand-navy-dark` | `#243237` | Sem "GPT Dark Blue escuro" oficial no guia — calculado a partir do novo `brand-navy` (mesmo tom, ~28% mais escuro), usado em hover de botões primários. |
| `brand-gold` | `#f3d148` ("GPT Yellow") | Só decorativo (faixa de 3 cores no cabeçalho) — **nunca como cor de texto**: contraste ruim contra fundo claro E contra fundo escuro (é uma cor clara). |
| `brand-green` | `#79aa00` ("GPT Green") | Faixa decorativa do cabeçalho; status "positivo" continua usando os tons semânticos do Tailwind (`green-700` etc.) onde precisa de contraste de texto pequeno. |
| `brand-orange` | `#ea7603` ("GPT Orange") | Acento reservado pra indicar "campo editável"/"Novo" em telas de dados tabulares, sem confundir com vermelho de erro de validação. |

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

Atualizada em 2026-07-21 (Cadastro/Processos reformulados, Painel geral, aba "Bitins
Concluídos" em Configurações, componentização — ver seção própria abaixo):

```text
frontend/
  src/
    lib/
      api.ts                  - cliente axios (token via localStorage, interceptor 401)
      types.ts                - tipos compartilhados (User, ChangePasswordRequest, ResumoUsuario, ...)
      bitinTypes.ts            - tipos do domínio BITin (BitinResumo, ChecklistItem, MaterialResumo, ...)
      bitinDefaults.ts         - materialVazio(), normalizarMaterial() (defensivo contra material
                                  salvo antes de um campo novo existir no schema)
      bitinEtapa.ts             - Status x Etapa (fonte única, ver PainelGeral.tsx/BITIN_MODEL.md)
      format.ts                - formatarDataEnvio() (DD.MM.YYYY)
      permissions.ts            - NIVEL_*/SETOR_*, isAdmin/isGestor/ehDoSetor/isCadastro/isProcessos
      criarBitin.ts             - criarRascunhoENavegar() (cria rascunho + navega, sem tela em branco)
      useEnviarBitin.ts        - hook compartilhado pelo fluxo de envio (BitinDetail/CodigosSapPage/
                                  ListaTecnicaPage chamam a mesma lógica de envio + erros)
    hooks/
      useAuth.ts                - contexto de autenticação
      useAvisoSairSemSalvar.ts  - modal "sair sem salvar" (BitinDetail)
      useDebouncedValue.ts      - debounce genérico (busca em CadastroPage/ProcessosPage/MeusBitins)
      useVoltar.ts              - "voltar" pra tela de origem (navigate(-1) com fallback)
    context/
      AuthContext.tsx          - login/logout/estado do usuário (Context API, sem lib externa)
      ThemeContext.tsx         - tema claro/escuro, padrão claro, persiste em localStorage
    components/
      RequireAuth.tsx          - guarda de rota (redireciona pro /login sem token)
      Layout.tsx                - compõe Sidebar + Topbar + <Outlet/> (ver seção própria abaixo)
      Sidebar.tsx                - navegação lateral (logo, nav extensível, off-canvas no mobile)
      Topbar.tsx                 - menu mobile, tema, configurações, usuário, sair
      ThemeToggle.tsx            - botão sol/lua (reaproveitado no login e no topbar)
      icons.tsx                  - ícones SVG inline compartilhados (Home/Configurações/Sair/Menu)
      Card.tsx                   - card com título (aceita string ou JSX), base visual de várias telas
      DetailField.tsx            - par rótulo/valor só-leitura (Settings, visualização de BITin)
      bitin/
        AjudaPopover.tsx         - ícone "?" com tutorial em popover (uma por tela principal)
        BitinTableSection.tsx    - tabela de listagem de BITins compartilhada (Cadastro/Processos/
                                    Meus Bitins/Bitins Concluídos)
        bitinColunas.tsx          - tipo BitinColuna + COLUNAS_PADRAO_BITIN (Número/Motivo/
                                    Solicitante/Status)
        FiltroEtapaToolbar.tsx    - select de etapa + busca compartilhado (Cadastro/Processos)
        ChecklistTable.tsx       - checklist 100% manual, grade responsiva (1-3 colunas)
        DadosGeraisCard.tsx      - card "Dados gerais" (produto/motivo/solicitante/setor + checklist)
        MaterialEditorCard.tsx   - bloco editável de um material na aba BITin
        MateriaisSection.tsx     - lista de MaterialEditorCard + "+ Novo material"
        AlteracaoTable.tsx       - visualização só-leitura de um material (BITin enviado)
        DadosBasicosTable.tsx    - tabela De/Para de um material (dados básicos SAP)
        OrdemClienteSection.tsx / OrdemClienteEditor.tsx - bloco de ordem_cliente[] (POP Nota 10)
        SetorBadge.tsx / StatusBadge.tsx / SetoresBanner.tsx - badges/banners de status e setor
        EdicaoBottomBar.tsx      - barra fixa (BITin/ZBPP009/Lista Técnica + Enviar, com
                                    confirmação antes de enviar de verdade, 2026-07-21)
        ErrosEnvioBanner.tsx     - lista de erros de validação ao tentar enviar
        AvisoSairModal.tsx       - modal "sair sem salvar"
      settings/
        CriarUsuarioForm.tsx / GestaoUsuarios.tsx / TrocarSenhaForm.tsx
    pages/
      Login.tsx                  - tela de login (design completo, ver seção própria abaixo)
      Login.test.tsx              - smoke test (Vitest + Testing Library, ver "Testes" abaixo)
      Home.tsx                   - boas-vindas + resumo (fila do setor ou próprios BITins) + recentes
      Settings.tsx                - Minha conta (+ troca de senha); admin ganha aba "Bitins
                                     Concluídos" (lista travada, "Voltar bitin" reverte o Windchill)
      GestaoUsuariosPage.tsx      - só super-admin (ver `security.py::CONTAS_SUPER_ADMIN`)
      MeusBitins.tsx               - listagem escopada por permissão (próprio/setor/sistema) +
                                       excluir rascunho (ou enviado, se admin)
      CadastroPage.tsx             - fila do setor Cadastro (etapas Aguardando cadastro/
                                       Pendência de envio, ver BITIN_MODEL.md)
      ProcessosPage.tsx            - fila do setor Processos (etapas Pendente/Revisado)
      PainelGeral.tsx              - visão de leitura pra Gestor/Admin (Status x Etapa, sem ações)
      BitinDetail.tsx               - aba "BITin": mesma estrutura de edição e de visualização
                                       enviada, só trava os campos quando não é mais editável
      CodigosSapPage.tsx            - aba "ZBPP009": grade estilo planilha, cola/digita direto
      ListaTecnicaPage.tsx          - aba "Lista Técnica": grade independente, não depende de
                                       materiais pré-cadastrados
    test/setup.ts                - matchers do jest-dom, carregado antes de cada suíte
    vite-env.d.ts                - referência aos tipos do cliente Vite (import.meta.env)
    App.tsx                     - rotas
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

> **Nota (2026-07-21)**: o histórico abaixo é da PRIMEIRA versão de "Gestão de usuários"
> (ainda dentro de `Settings.tsx`, esquema de 4 níveis fixos `66`/`77`/`88`/`99` =
> Usuário/Gestor/Cadastro/Admin). Hoje "Gestão de usuários" é uma página própria
> (`GestaoUsuariosPage.tsx`, rota `/usuarios`), visível só pra `Settings.tsx` (aba "Minha
> conta" + "Bitins Concluídos" pra admin, ver seção "Etapa final «Concluído»" mais abaixo), e
> restrita à conta super-admin fixa — não a qualquer `99` (ver "Super-admin oculto" em
> `docs/BACKEND.md`). Os números `77`/`88`/`99` também mudaram de sentido: hoje são RANK
> (Individual/Gestor/Admin), cruzado com `Usuario.setor` — ver "Revisão do modelo de
> permissões (2ª revisão)" em `docs/BACKEND.md`/`docs/BITIN_MODEL.md`. O texto abaixo fica só
> como registro de como cada decisão foi tomada, não como referência do esquema atual.

- **"Minha conta"** (somente leitura): nome, e-mail, setor(es) (nomes resolvidos via `GET
  /sectors`, público — desde 2026-07-15 um usuário pode ter vários `Setor` ao mesmo tempo,
  ver abaixo; nomes juntados por vírgula) e nível de permissão (rótulo amigável —
  `Usuário`/`Gestor`/`Cadastro`/`Admin` desde 2026-07-16, ver `docs/BACKEND.md` "Revisão do
  modelo de permissões" — em vez do número cru). Trocar senha via `POST /auth/change-password`
  (adicionado nesta mesma rodada); editar o próprio perfil fica pra uma rodada futura.
- **Setores múltiplos por usuário (2026-07-15)**: pedido explícito, "um usuário poder ser
  tanto armazenagem tanto quanto proteina" — `Usuario.sector_id` (FK única) virou
  `sector_ids: number[]` (many-to-many, `Setor[]` via `usuario_setores` no backend). No
  formulário "Cadastrar usuário", o `<select>` de setor único virou um grupo de checkboxes
  (uma por `Setor` existente, sem hardcode de quantidade); a tabela de "Gestão de usuários" e
  o `DetailField` de "Minha conta" juntam os nomes com vírgula em vez de resolver um id só.
- **"Gestão de usuários"** (só visível se `user.permission_level === NIVEL_ADMIN` (99),
  decisão explícita do usuário — "só pra admin"): tabela com todos os usuários (`GET /users`,
  exige Gestor/Admin no backend — a UI é mais restritiva que o mínimo do backend de propósito).
  Desde 2026-07-15, um **gestor** (não só admin) também acessa `GET /users`, mas escopado: só
  vê usuários que compartilham ao menos um `Setor` com ele (pedido explícito: "se um usuário
  for gestor, ele consegue só ver listagem de usuários do setor que ele é gestor"). Essa tela
  em si continua visível só pra admin (`Settings.tsx` não muda essa checagem de UI); o escopo
  por setor do gestor vale pra quem consumir `GET /users` diretamente, não pra esta tela hoje.
  Um `<select>` por linha pra trocar o nível (`PATCH /users/{id}/permission`, backend exige
  Admin). **Proteção contra auto-rebaixamento**: o `<select>` da própria linha do usuário
  logado fica desabilitado — evita um admin se rebaixar sem querer e ficar trancado fora da
  própria gestão. **Proteção contra rebaixar admin (2026-07-16)**: o `<select>` de qualquer
  linha cujo nível atual seja Admin (99) também fica desabilitado, pra QUALQUER usuário logado
  (não só pra si mesmo) — "ninguém pode tirar permissão dele", com o mesmo padrão de `title` de
  tooltip explicativo já usado pro auto-rebaixamento; o backend rejeita com 400
  independentemente do frontend.
- **"Sobre"**: versão do app, mesma fonte que o rodapé do login (`package.json`).
- **Achado ao validar**: para testar a seção de admin de verdade (nenhum usuário de teste
  local era admin), o usuário autorizou explicitamente promover `teste@example.com` pra nível
  99 direto no SQLite local só pra essa verificação — revertido pra `0` logo depois, e
  confirmado por leitura direta do banco que os dois usuários (`demo@example.com`,
  `teste@example.com`) voltaram exatamente ao estado original.

**Troca de senha self-service (2026-07-15)**: "Minha conta" deixou de ser só-leitura em uma
parte — ganhou um formulário "Trocar senha" (senha atual/nova/confirmar), postando pra
`POST /auth/change-password` (ver `docs/BACKEND.md`). Confirmação de senha é checada no
cliente antes de enviar (evita uma ida à API por erro de digitação — a validação de força de
verdade é sempre do servidor). Erro do servidor (senha atual errada, senha nova fraca)
aparece verbatim, via o mesmo padrão de extração de erro (`extrairErro`, duck-typing igual ao
já usado em `Login.tsx`) que lida com as duas formas de resposta da API: `{detail: string}` e
`{detail: [{msg}]}` (erro de validação do Pydantic).

**Cadastro de usuário só por admin + primeiro login forçado (2026-07-15)**: pedido explícito
do usuário — "tela de cadastro de usuário SÓ PARA ADMIN para não ter que cadastrar no banco" —
substitui a nota acima ("Gestão de usuários só lista e muda nível, não cria").

- **`CriarUsuarioForm`** (`Settings.tsx`, dentro de `GestaoUsuarios`): E-mail, Nome, ID/Número
  de engenharia (opcional), Setor (grupo de checkboxes do `sectors` já carregado), Permissão
  (mesmo mapeamento 66/77/88/99 -- Usuário/Gestor/Cadastro/Admin -- do `<select>` de nível já
  existente na tabela, ver `docs/BACKEND.md` "Revisão do modelo de permissões"). **Setor
  obrigatório pra 66/77/88 (2026-07-16)**: submit fica desabilitado e aparece erro inline se
  nenhum setor for marcado pra esses 3 níveis — só Admin (99) pode ficar sem setor; validação
  client-side é só UX, o backend (`AdminUserCreate`) segue sendo quem garante a regra de
  verdade. Sem campo de senha — o backend gera (`POST /users`, ver `docs/BACKEND.md`). Sucesso
  mostra a senha gerada num callout persistente (não um toast que some): "Essa senha só aparece
  agora — anote e repasse pra [nome] antes de sair desta tela." O usuário novo entra direto na
  tabela abaixo via atualização local (mesmo padrão otimista de `alterarNivel`, sem refetch de
  `GET /users`).
- **Gate de senha temporária** (`RequireAuth.tsx`): se `user.senha_temporaria` (espelha
  `Usuario.senha_temporaria`) for `true`, redireciona pra `/definir-senha` em vez de renderizar
  a rota pedida — exceto quando já está em `/definir-senha` (evita loop de redirecionamento).
  Checado depois do gate de "tem token" já existente, não substitui ele.
- **`DefinirSenha.tsx`** (rota `/definir-senha`, nova, tela standalone sem sidebar/topbar,
  mesmo espírito de `Login.tsx`): formulário senha temporária/nova/confirmar, reusa a mesma
  chamada `POST /auth/change-password` de `TrocarSenhaForm` (duplicação pequena e deliberada —
  o app não tinha um padrão pra compartilhar lógica de formulário entre páginas, e não valia a
  pena criar um só pra isso). Sucesso chama `AuthContext.refreshUser()` (novo — rebusca `GET
  /users/me`) e navega pra `/`; como o servidor já zerou `senha_temporaria`, o gate acima para
  de redirecionar.

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
- **Escopo por nível, revisto em 2026-07-15** (era "só os meus" pra todo mundo, incl. admin):
  `GET /bitins` filtra por `criado_por` no backend, mas o que entra nesse filtro agora depende
  do nível de quem pergunta — usuário comum continua só os próprios; gestor vê os de quem
  compartilha ao menos um `Setor` com ele (mesma lógica de "Gestão de usuários"); admin vê o
  **sistema inteiro, sem filtro nenhum** (pedido explícito do usuário, "Admin vê tudo" —
  reverte a decisão anterior de 2026-07-14 que também prendia admin a "só os meus" aqui). O
  título da tela e o rótulo de busca "Solicitante" se ajustam pra quem vê um escopo mais amplo
  (gestor/admin) — ver abaixo.
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

### Aba BITin, ZBPP009 e Lista Técnica — cadastro/edição (2026-07-15)

Rodada grande de feedback direto sobre as três telas de edição de um BITin (aba "BITin",
ZBPP009 e Lista Técnica), fechando o ciclo começado em "Meus Bitins": agora dá pra criar e
editar um BITin de verdade, não só visualizar. Decisão central do usuário: **as três telas não
se complementam, fazem a mesma coisa de formas diferentes** — o mesmo `materiais[]` do JSON do
BITin, editável em qualquer uma das três, nenhuma dependendo da outra pra existir.

- **`BitinDetail.tsx`** vira editável quando o BITin é rascunho: mesma estrutura da
  visualização enviada (`AlteracaoTable`), só destrava os campos. Um material pode ser criado
  inteiramente aqui, sem nunca abrir a ZBPP009 ("`+ Novo material`").
- **Checklist 100% manual (`ChecklistTable.tsx`)**: antes o sistema sugeria "Sim/Não"
  automaticamente a partir dos campos de cada material (Alt/Est/Esp/etc.) — decisão do usuário:
  "checklist é marcada manualmente", tirou completamente a derivação automática
  (`scripts/bitin_document.py::build_checklist`, ver `docs/BACKEND.md`). Cada item vira
  "Sim" só quando o engenheiro clica nele. Item com anotação de texto livre (usado no item 22,
  "Centro de custo (se tem sucata)", pra registrar a Nota 8 do POP) — campo aparece quando o
  item está "Sim" e a tela é editável. Layout em **grade responsiva** (1 coluna no celular, até
  3 em telas largas) em vez de uma coluna só empilhada, reduzindo o scroll.
- **Bloco de material simplificado (`MaterialEditorCard.tsx`)**: "Atualizar DWG/SAT" e "Centro
  de custo"/"Conta razão" saíram do bloco — a primeira agora é só clicar no item 18 da
  checklist, a segunda virou a anotação do item 22 (ver acima). Campo "Tipo" fica escondido
  aqui (continua obrigatório pro envio — `materialVazio()` preenche um valor padrão), mas
  **continua visível na ZBPP009**, porque lá é a réplica fiel da grade real do SAP (é a
  primeira coluna de verdade do relatório, e a âncora de onde o parser de colagem espera o
  texto colado).
- **ZBPP009 renomeada** (de "Códigos SAP" — "vai ajudar o pessoal" a reconhecer): rota
  (`/bitins/:mongoId/codigos-sap`) não mudou, só o rótulo em toda a UI.
- **Bug de colagem corrigido**: o interceptador de colar só ficava na primeira coluna da
  grade, mas a primeira coluna visual (Código) não é mais a primeira coluna real do SAP (Tipo
  Material) — colar numa célula "errada" jogava o texto inteiro, cru, num campo só. Corrigido
  colocando o mesmo interceptador em toda célula da linha (identificação + dados básicos);
  colar em qualquer célula da linha, se tiver TAB/quebra de linha, dispara o parser
  (`POST /bitins/parse-sap-paste`) igual antes.
- **Lista Técnica virou página independente**: antes dependia de materiais já cadastrados
  (`materiais[]` não vazio) pra mostrar qualquer coisa. Agora é uma grade estilo planilha,
  igual à ZBPP009, com uma coluna "Código pai" livre (texto, não precisa já existir) — ao
  salvar, agrupa as linhas por código pai e cria um material novo (mesmo formato de
  `materialVazio()`) pra qualquer código pai digitado que ainda não exista.
- **`AjudaPopover.tsx`** (novo): ícone "?" com tutorial em popover, substitui parágrafo de
  instrução fixo nas três telas (BITin/ZBPP009/Lista Técnica). Revisado pra ficar resumido —
  só o que é específico do sistema (como colar, Salvar vs. Importar, checklist manual) e os
  lembretes de regra de negócio que importam pro envio; não repete o que o engenheiro já sabe
  do processo do POP.
- **Botão "Importar pra BITin"** (ZBPP009 e Lista Técnica): salva e leva direto pra aba BITin,
  onde a checklist/setores recalculam automaticamente a partir do que foi preenchido.
- **Regras de negócio automatizáveis vs. confirmação externa**: `scripts/bitin_business_rules.py`
  só bloqueia envio por regras que o sistema consegue verificar sozinho a partir do que já está
  no BITin (Nota 8 — descrição do item 22 da checklist; Nota 10 — `ordem_cliente[]`). Regras que
  dependem de confirmação de alguém fora do sistema (Nota 2 — desenho aprovado; Nota 17 —
  aprovação fiscal de NCM) **não bloqueiam mais o envio** — não existia (e não existe) campo na
  UI pra marcar isso como "aprovado", então travar o envio nelas era travar pra sempre. Viraram
  lembrete no `AjudaPopover` da aba BITin.
- **Excluir rascunho**: botão dentro do BITin (`BitinDetail.tsx`) e agora também direto na
  listagem (`MeusBitins.tsx`), sem precisar abrir o BITin primeiro — mesmo endpoint
  (`DELETE /bitins/{mongo_id}`), só reaproveitado dos dois lugares.
- **Data de envio em `DD.MM.YYYY`** (`lib/format.ts::formatarDataEnvio`) — convenção de data do
  POP/SAP, aplicada só ao campo `data_envio`, não aos campos de data dentro do snapshot de
  dados básicos (esses são texto livre do SAP, não datas parseadas).
- **`normalizarMaterial()` (`lib/bitinDefaults.ts`)**: correção de um bug real — material salvo
  antes de um campo existir no schema (ex.: `lista_tecnica`) vinha `undefined` do backend,
  quebrando a tela inteira com `Cannot read properties of undefined (reading 'map')` sem
  nenhum error boundary. Aplicado em toda tela que carrega materiais do backend
  (BitinDetail/CodigosSapPage/ListaTecnicaPage).

## Automações VBA, fila Cadastro/Processos e polish geral (2026-07-16 a 2026-07-20)

Sessão longa, três frentes principais — auditoria das automações do VBA original (checklist,
Alt/Esp/DWG-SAT), o fluxo novo de roteamento pós-envio (setores Cadastro e Processos) e uma
rodada de performance/polish nas telas de edição. Regra de negócio e ciclo de vida completos
em `docs/BITIN_MODEL.md`/`docs/BACKEND.md` — aqui só o que muda na UI.

- **Checklist/setores ao vivo (`POST /bitins/preview-resumo`)**: antes só recalculava depois
  de "Salvar"; agora `BitinDetail.tsx` chama esse endpoint com debounce (500ms) a cada
  alteração de campo, sem persistir rascunho — reaproveita 100% da lógica Python de
  `bitin_view.render_bitin_summary`, não duplica regra de negócio em TypeScript.
- **Sugestão automática de Alt/Esp/nota DWG-SAT** (`aplicarSugestoes` em `BitinDetail.tsx`):
  a partir do código de Grupo de Mercadorias, só preenche campo ainda em branco (`"-"`) —
  nunca sobrescreve o que o engenheiro já declarou. Código SAP desconhecido não sugere nada,
  não trava.
- **Aviso "Revisar roteiro de fabricação"** (`MateriaisSection.tsx`): banner por material
  quando o Alt declarado é `"D/P"` ou `"-/P"` — mesmo lembrete que a macro original escrevia,
  não afeta checklist/setores.
- **Aviso de alterações não salvas** (`AvisoSairModal.tsx` + `hooks/useAvisoSairSemSalvar.ts`):
  intercepta navegação (troca de rota ou fechar aba) com alteração pendente em `BitinDetail`,
  oferece Salvar e sair / Sair sem salvar / Cancelar.
- **Fila do setor Cadastro** (`CadastroPage.tsx`, rota `/cadastro`) — substitui de vez o
  e-mail/PDF manual que existia antes. Roteamento automático (`enviar_bitin` já decide
  sozinho se precisa de roteiro): Cadastro só vê o BITin nas etapas "Aguardando cadastro"
  (liberar no SAP, botão "Concluir BITIN") e "Pendência de envio" (botão "Baixar PDF", que
  baixa o PDF e chama `enviar-windchill` na mesma ação, com confirmação antes). BITins
  concluídos (Status="Concluído") saem desta tela — vivem só na aba "Bitins Concluídos" de
  `Settings.tsx`.
- **Setor Processos** (`ProcessosPage.tsx`, rota `/processos`, `isProcessos()` em
  `lib/permissions.ts`): recebe da fila do Cadastro (`encaminhado_roteiro=true`), reedita um
  BITin já `"enviado"` (única exceção do sistema a "enviado é travado pra sempre") e conclui
  ("Concluir" em `BitinDetail.tsx`). Não cria BITin. Etapas "Pendente"/"Revisado" — BITins que
  nunca precisaram de roteiro (`sem_necessidade_roteiro=true`) são excluídos das duas, porque
  Processos nunca teve contato real com eles.
- **Painel geral** (`PainelGeral.tsx`, rota `/painel-geral`, Gestor/Admin): visão de leitura
  sem ações, todo BITin com Status/Etapa (`lib/bitinEtapa.ts`) + com quem está, filtros de
  Setor/Usuário/Status/Etapa + export CSV.
- **Gestão de usuários**: `CriarUsuarioForm.tsx`/`GestaoUsuarios.tsx` usam os seletores de
  Nível (77/88/99) e Setor (Cadastro/Processos/Engenharia) do modelo atual — só Engenharia
  exige Subgrupo.
- **Performance** (pedido explícito, "usa como base o frontend antigo que tinha uma
  otimização feita"): `React.memo` + padrão de estado local/commit-on-blur em
  `MaterialEditorCard.tsx`, ids estáveis por material (`crypto.randomUUID()` client-side em
  vez de índice de array), code-splitting por rota (`lazy`) em `App.tsx`.
- **Polish de UI**: dropdown de Centro removido de onde não fazia sentido, default `HALB`
  removido, colunas De/Para em `CodigosSapPage.tsx` (ZBPP009) com rótulo `"{campo}"`/`"{campo}
  nova"` por coluna, campo Operação removido (auto-derivado), campos de quantidade da Lista
  Técnica voltaram a ser `type="text"` + `inputMode="decimal"` (o seletor nativo de
  `type="number"` tinha ficado ruim visualmente).

## O que já funciona (estado atual, não histórico — atualizado 2026-07-21)

Diferente das seções acima (diário cronológico), esta lista é mantida como resumo do estado
ATUAL — atualizar aqui sempre que algo mudar de verdade, não só quando uma seção nova for
adicionada. Validado por `python -m unittest discover -s tests` (358 testes, inclui
`test_bitin_workflow_e2e.py` ponta a ponta) + `tsc`/`lint`/`build` do frontend + testes ao vivo
com Playwright nas contas reais (ver `docs/RELEASE_v0.10.0.md`/`v0.10.1.md`).

- Login (`POST /auth/login`) → redireciona pra `/`, com validação visual de erro (credencial
  errada), estado de carregamento, e gate de senha temporária (`/definir-senha`) no primeiro
  acesso de uma conta criada pelo admin.
- Rota protegida: sem token, qualquer rota redireciona pro login.
- Shell autenticado: sidebar de navegação (off-canvas no celular), itens condicionais pelo
  modelo de permissões atual (rank 77/88/99 cruzado com `Usuario.setor` — "Cadastro"/
  "Processos" pra quem é desses setores ou admin; "Painel geral" pra Gestor/Admin; "Gestão de
  usuários" só pro super-admin fixo), topbar com tema/configurações/usuário/sair, Home com
  boas-vindas + resumo (fila do setor ou próprios BITins) + recentes.
- "Meus Bitins" (`/bitins`): listagem escopada por permissão (próprio/Subgrupo/setor/sistema
  inteiro conforme o papel, ver `docs/BACKEND.md`), abas Todos/Rascunhos/Enviados, excluir
  rascunho (ou enviado, se admin) direto na linha, clique na linha abre o BITin.
- **BITin/ZBPP009/Lista Técnica** (`/bitins/:mongoId`, `/bitins/:mongoId/codigos-sap`,
  `/bitins/:mongoId/lista-tecnica`): as três telas de edição de um rascunho — cadastro completo
  de material, colar do SAP em qualquer célula, checklist com sugestão automática e recálculo
  ao vivo, lista técnica independente (com autocompletar de Código pai e Centro/Descrição pra
  material novo), aviso de alterações não salvas, confirmação antes de enviar, envio com
  validação de regras de negócio (inclui bloqueio se nenhum material tem alteração real).
- **Fila do setor Cadastro** (`/cadastro`): recebe todo BITin enviado, decide se precisa de
  roteiro (regra automática) ou conclui direto. Etapas "Aguardando cadastro" (botão "Concluir
  BITIN") e "Pendência de envio" (botão "Baixar PDF", que baixa e já manda pro Windchill na
  mesma ação) — ver `docs/BITIN_MODEL.md`, seção "Roteamento pós-envio".
- **Setor Processos** (`/processos`): reedita um BITin já enviado enquanto está na fila do
  Cadastro (única exceção do sistema a "enviado é travado pra sempre"), conclui quando termina.
  Etapas "Pendente"/"Revisado" — BITins que nunca precisaram de roteiro não aparecem aqui.
- **Painel geral** (`/painel-geral`, Gestor/Admin): visão de leitura de todo BITin visível pro
  usuário, Status x Etapa, filtros de Setor/Usuário/Status/Etapa, export CSV.
- **Configurações**: "Minha conta" (+ troca de senha) pra qualquer nível; aba "Bitins
  Concluídos" (admin-only) — lista de BITins com Status="Concluído", botão "Voltar bitin"
  reverte o envio ao Windchill.
- **Gestão de usuários** (`/usuarios`, só super-admin fixo): cadastro/reativação com senha
  temporária, promover/rebaixar nível, atribuir setor/Subgrupo, soft-delete.
- Logout: volta pro login.
- Tema claro/escuro (toggle no login E no topbar pós-login, padrão claro, escolha persiste no
  navegador).

## O que NÃO está nesta fatia ainda (próximos incrementos)

- **"Esqueci minha senha"** — só existe troca de senha sabendo a senha atual
  (`POST /auth/change-password`); sem fluxo de reset pra quem esqueceu.
- **RBAC visível na UI** além do que já existe — o backend recusa (`403`) quem tenta
  editar/excluir sem permissão; a UI não esconde botões preventivamente pra ações que vão
  falhar no backend.
- **Painel geral sem paginação de verdade** — busca tudo em lotes de 500 (`PainelGeral.tsx`)
  até esgotar; funciona, mas não escala indefinidamente. Filtros são todos client-side sobre a
  lista carregada, não passados pro backend.

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

**Se `MONGO_URL` não estiver configurado no `.env` desta máquina**: o backend sobe e
login/registro funcionam (Postgres/SQLite), mas qualquer ação de `/bitins` (que depende do
Mongo) devolve `500`. Desde a v0.8.2 o projeto já roda com **MongoDB Atlas real** em produção
(ver `docs/RELEASE_v0.8.2.md`) — essa nota vale só pra uma máquina de dev sem esse `.env`
configurado localmente. Pra testar o fluxo de BITin sem MongoDB real disponível, é preciso
rodar o backend com `mongomock-motor` no lugar do cliente Mongo (mesma estratégia dos testes
automatizados).
