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

**React 19 + Vite + Tailwind 4 + react-router-dom + axios, sem lib de estado global**
(Redux/Zustand). O estado de tela é local — Context API (`AuthContext`, `ThemeContext`) +
`useState` bastam nesse estágio.

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
    lib/api.js              - cliente axios (token via localStorage, interceptor 401)
    context/
      AuthContext.jsx        - login/logout/estado do usuário (Context API, sem lib externa)
      ThemeContext.jsx        - tema claro/escuro, padrão claro, persiste em localStorage
    components/
      RequireAuth.jsx        - guarda de rota (redireciona pro /login sem token)
      Layout.jsx              - shell: cabeçalho (logo, e-mail, toggle de tema, sair)
      ThemeToggle.jsx          - botão sol/lua (extraído de Layout.jsx pra reaproveitar no login)
    pages/
      Login.jsx                - tela de login (design completo, ver seção própria abaixo)
      Home.jsx                - placeholder da área autenticada (ver "Reset" acima)
    App.jsx                   - rotas
```

## Tela de login (design completo, 2026-07-13)

Primeira tela reconstruída depois do reset — pedido direto: "focar 100% no design UI/UX",
usando o backend real (não mock) desde já, já que Postgres já está rodando e testado nesta
máquina.

- **Layout dividido** (`Login.jsx`): painel de marca à esquerda (`bg-brand-navy`, logo, título
  "Boletim de Informações Técnicas Interno", subtítulo, faixa de 3 cores — mesma referência
  visual do cabeçalho pós-login) + formulário à direita, só em telas médias+
  (`hidden md:flex`). No celular o painel de marca colapsa pra só a logo centralizada acima do
  formulário, em vez de gastar metade da tela vertical com algo decorativo.
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
