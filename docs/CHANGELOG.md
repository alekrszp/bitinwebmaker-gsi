# Changelog

All notable changes to this project will be documented in this file.

## [v0.8.0] - 2026-07-15

Rodada grande de três frentes: autenticação real (banco persistente + migrations, sessões
revogáveis, senha forte), reformulação completa das telas de cadastro/edição de BITin
(BITin/ZBPP009/Lista Técnica), e a paleta de cores oficial da marca. Escopo maior que os
incrementos anteriores — bump de minor (0.7.2 → 0.8.0) em vez de patch, decisão do usuário.

### Added — Autenticação

- **Migrations Alembic** (`migrations/`, `alembic.ini`, novos): antes o schema era criado via
  `Base.metadata.create_all()`, sem versionamento nenhum. Baseline + migration cobrindo os
  campos/tabelas novos abaixo.
- **`sessoes_usuario`**: sessão revogável por login — `POST /auth/logout` agora invalida o
  token de verdade (antes era JWT puro, stateless, sem jeito de derrubar antes de expirar).
- **`tentativas_login`**: rate limit de login persistido em banco (antes era um dict em
  memória do processo — não sobrevivia a restart nem funcionava com múltiplos workers).
- **`Usuario.numero_eng`, `email_verificado`, `updated_at`, `ultimo_acesso`** (colunas novas).
- **Política de senha forte** (`validate_password_strength`): mínimo 8 caracteres + 3 dos 4
  tipos de caractere, aplicada em registro e troca de senha (não retroativa).
- **`POST /auth/change-password`** (novo): antes não existia jeito de trocar a própria senha
  sem edição direta no banco. Revoga as outras sessões ativas ao trocar.
- **Normalização de e-mail** (sempre minúsculo, registro e login): corrige um bug real —
  e-mail cadastrado com maiúscula não conseguia logar se digitado diferente depois.

### Added — Telas de BITin (BITin / ZBPP009 / Lista Técnica)

- Cadastro e edição completos de um BITin: as três telas operam sobre o mesmo `materiais[]`,
  nenhuma dependendo da outra pra existir.
- **Checklist 100% manual** (`ChecklistTable.tsx`): tirada a sugestão automática a partir dos
  campos do material — todo item precisa ser clicado pelo engenheiro. Layout em grade
  responsiva (1–3 colunas) em vez de coluna única.
- **ZBPP009** (renomeada de "Códigos SAP"): bug de colagem corrigido (interceptador de colar
  agora funciona em qualquer célula da linha, não só a primeira).
- **Lista Técnica** virou página independente estilo planilha — não depende mais de materiais
  já cadastrados.
- **Bloco de material simplificado**: "Atualizar DWG/SAT" e "Centro de custo"/"Conta razão"
  saíram, viraram itens/anotação da checklist. Campo "Tipo" escondido no bloco (continua
  visível na ZBPP009, que é a réplica fiel da grade real do SAP).
- **`AjudaPopover.tsx`** (novo): ícone "?" com tutorial resumido nas três telas.
- **Excluir rascunho** direto na listagem "Meus Bitins", além de dentro do BITin.
- **Data de envio em `DD.MM.YYYY`**.

### Changed — Regras de negócio

- `scripts/bitin_business_rules.py` só bloqueia envio por regras verificáveis a partir do
  próprio BITin (Nota 8, Nota 10). Regras que dependem de confirmação externa (Nota 2 —
  desenho aprovado; Nota 17 — aprovação fiscal de NCM) não bloqueiam mais o envio — não havia
  (nem há) campo de UI pra satisfazê-las, travar nelas era travar pra sempre.

### Added — Interface

- **Configurações**: "Minha conta" ganhou troca de senha self-service; layout mais largo,
  campos longos (e-mail) não estouram mais o card, tabela de usuários rola em vez de cortar
  colunas.
- **Paleta de cores oficial da marca**: tokens de marca (`brand-navy`, `brand-gold`,
  `brand-green`, `brand-orange`, `brand-navy-light` novo) atualizados pros valores do guia
  oficial (hex/CMYK/Pantone), substituindo a aproximação anterior tirada dos arquivos de logo.

### Fixed

- `normalizarMaterial()`: material salvo antes de um campo existir no schema (ex.:
  `lista_tecnica`) quebrava a tela inteira (`Cannot read properties of undefined`), sem error
  boundary nenhum.

### Validação

- Backend: 192 testes (158 → 192), todos verdes.
- `npm run typecheck`/`lint`/`test`/`build` limpos.
- Migrations testadas contra uma cópia do `bitin_backend.db` real antes de aplicar no arquivo
  de verdade (nunca rodadas direto no original sem cópia primeiro).

## [v0.7.2] - 2026-07-14

Primeiro pedaço de verdade da tela de Bitins desde o reset da v0.5.0: listagem "Meus Bitins"
(escopada pro próprio usuário) + visualização só-leitura ao clicar numa linha. Escopo fechado
colaborativamente com o Alessandro.

### Added
- **`pages/MeusBitins.tsx`** (novo, rota `/bitins`): abas Todos/Rascunhos/Enviados, colunas
  Código/Motivo/Solicitante/Status.
- **`pages/BitinDetail.tsx`** (novo, rota `/bitins/:mongoId`): visualização só-leitura via
  `GET /bitins/{mongo_id}/resumo`, sem edição ainda.
- Novo item "Meus Bitins" na sidebar.

### Changed
- **`GET /bitins`** agora filtra por `criado_por` — cada usuário só vê os próprios BITins
  ("só os meus", mesma decisão já usada em `resumo-usuario`/Home). Antes listava o sistema
  inteiro.

### Validação
- Backend: 172 testes (3 novos, cobrindo isolamento entre usuários).
- `npm run typecheck`/`lint`/`test`/`build` limpos. Sem verificação visual ao vivo (sem
  MongoDB real nesta máquina, credenciais de teste locais desconhecidas).

## [v0.7.1] - 2026-07-14

Primeira mudança de UI visível pro engenheiro desde a v0.5.0 (a v0.6.0 e a v0.7.0 eram só
robustez/infra interna). Ainda pequena de propósito — o shell sozinho, sem a listagem de
Bitins atrás dele ainda.

### Added
- **Shell autenticado** (`Sidebar.tsx`, `Topbar.tsx`, novos): a área logada deixou de ser só
  um cabeçalho horizontal com logo/e-mail/sair — agora tem sidebar de navegação (off-canvas
  no celular) e topbar (menu mobile, tema, configurações, usuário, sair). Segue exatamente o
  padrão visual da tela de login (painel navy, logo em pílula branca, faixa de 3 cores) —
  pedido direto: "nunca fugir daquilo".
- **`pages/Home.tsx` reescrita**: de placeholder de texto ("Login funcionando.") pra uma
  página de boas-vindas de verdade, usando o primeiro nome do usuário.
- **`pages/Settings.tsx`** (novo, placeholder): o botão de configurações no topbar precisa
  levar a algum lugar real — ainda não há nada configurável de fato, mas não é mais um link
  morto.
- **`components/icons.tsx`** (novo): ícones SVG inline compartilhados entre Sidebar/Topbar.

### Validação
- Playwright ad-hoc: desktop/mobile, tema claro/escuro, navegação, configurações, logout —
  zero erro de console.
- `npm run typecheck`/`lint`/`test`/`build` limpos.

## [v0.7.0] - 2026-07-14

Continuação direta da avaliação geral do projeto (v0.6.0): CI, TypeScript no frontend, e
início de RBAC mais completo. Pendências que dependem de acesso a um Postgres real (rate
limiting compartilhado, migrations, transação distribuída) ficaram documentadas em
`requirements.md`, não implementadas ainda — aguardando o Alessandro passar a URL de acesso.

### Added
- **CI** (`.github/workflows/ci.yml`, novo): roda em todo push/PR pra `main` — suíte Python
  (`unittest discover`) e suíte de frontend (`typecheck` + `lint` + `test` + `build`). Antes
  disso nada rodava os testes automaticamente. Sem serviço de banco no workflow — os testes já
  usam SQLite + mongomock-motor.
- **TypeScript no frontend inteiro** (migração completa, não incremental — só 11 arquivos
  existiam, já que a tela de Bitins foi apagada no reset da v0.5.0): `tsconfig.app.json`/
  `tsconfig.node.json` com `strict: true`. `npm run typecheck` novo; `npm run build` agora
  typecheca antes de gerar o bundle.
- **`pode_editar` no `BitinResponse`** (`backend/api/bitins.py`, achado de auditoria "RBAC
  incompleto"): campo calculado por requisição — `false` quando quem vê não é dono/admin, ou
  quando o BITin já foi enviado. Prepara o backend pra tela de Bitins (quando reconstruída)
  abrir em modo leitura pra quem não pode editar, em vez de só descobrir com um `403` ao tentar
  salvar. 4 novos testes cobrindo dono/outro usuário/admin/já enviado.
- **`requirements.md` atualizado** com uma seção nova de "Pendências conhecidas" — itens já
  mapeados mas bloqueados por dependerem de acesso a infraestrutura externa (Postgres real),
  registrados pra não repetir a pergunta a cada rodada.

### Validação
- 164 → **168 testes automatizados Python** (4 novos cobrindo `pode_editar`).
- Frontend: `npm run typecheck` limpo, `npx oxlint src` sem warning novo, 4/4 testes (Vitest),
  `npm run build` sem erro — tudo reverificado depois da migração TypeScript completa.

## [v0.6.0] - 2026-07-13

Auditoria de segurança/arquitetura do backend (pedida diretamente) + primeira suíte de testes
automatizada do frontend. Sem mudança de UI visível pro engenheiro — tudo aqui é robustez.

### Security
- **`SECRET_KEY` padrão não deixa mais o app subir em produção**: antes, um deploy sem `.env`
  configurado subia silenciosamente com a chave JWT padrão (`backend/config.py`) — qualquer um
  forjaria um token de admin válido, sem aviso nenhum. Agora, `backend/main.py::lifespan`
  recusa subir (`RuntimeError`) se `ENVIRONMENT=production` e a `SECRET_KEY` continua no
  default. Dev local/testes nunca setam `ENVIRONMENT`, então nada muda pra eles.
- **Limite de tentativas de login** (`backend/auth/rate_limit.py`, novo): `/auth/login` não
  tinha limite nenhum — força bruta contra senha fraca só era limitada pelo custo do hash. 5
  tentativas erradas pro mesmo e-mail em 5 minutos bloqueiam com `429`. Em memória (processo
  único) de propósito — registrado como limitação conhecida se um dia rodar com múltiplos
  workers.
- **Busca (`termo`) escapada antes de virar `$regex` do Mongo**: metacaracteres de regex
  digitados pelo usuário podiam causar matches inesperados ou custo de busca patológico —
  `re.escape` aplicado em `backend/api/bitins.py::list_bitins`.

### Fixed
- **Corrida no envio (double-submit) não vaza mais como `500` puro**: se
  `gerar_e_salvar_bitin_sql` esgotasse as tentativas (quase sempre porque o mesmo BITin já
  tinha sido enviado por uma requisição concorrente — 2 cliques, 2 abas), o `RuntimeError`
  subia sem tratamento. `enviar_bitin_endpoint` agora distingue "já enviado por outra
  requisição" (erro estruturado, explicando) de um erro genuíno e raro (`503` com log).
- **Falha do Mongo depois do commit no Postgres não deixa mais número "fantasma"**: sem
  transação real cobrindo os 2 bancos, se `collection.update_one` falhasse depois do Postgres
  já ter reservado o número sequencial, sobrava um `BitinSQL` órfão. Agora desfaz o lado
  Postgres (best-effort) e loga `CRITICAL` se até isso falhar — reduz bastante a janela de
  inconsistência (não é uma solução de transação distribuída completa, ver `docs/BACKEND.md`).

### Added
- **Logging básico no backend** (`backend/main.py`): zero `logging` existia antes — uma falha
  em produção não deixava rastro nenhum além da resposta HTTP.
- **Dependências do backend com versão fixada** (`backend/requirements.txt`): antes sem
  nenhuma versão fixa (reprodutibilidade frágil); fixadas nas versões que rodam os 164 testes
  nesta máquina. `psycopg2-binary` descomentado, mas deliberadamente sem versão fixa (não
  instalado neste ambiente de dev).
- **Primeira suíte de testes de frontend commitada** (Vitest + Testing Library,
  `frontend/src/pages/Login.test.jsx`): até aqui toda validação de frontend vivia só em
  scripts Playwright ad-hoc fora do repo. `npm run test` roda smoke tests da tela de login
  (campos, mostrar/esconder senha, erro estruturado, tema).
- **3 novos testes Python** cobrindo a checagem de `SECRET_KEY` na subida
  (`tests/test_backend_main.py`), a corrida no envio e a falha do Mongo pós-commit
  (`tests/test_backend_bitins.py`), e o limite de tentativas de login
  (`tests/test_backend_auth.py`) — 164 testes automatizados no total (era 158).

## [v0.5.0] - 2026-07-13

### Removed
- **Reset da tela de Bitins**: depois de 8 rodadas de ajuste visual (ver "Added" abaixo — todo
  esse histórico fica registrado como referência do que já foi tentado), o resultado ainda
  estava "muito confuso" — decisão explícita: apagar `BitinDetail.jsx`, `MeusBitins.jsx`,
  `MaterialGrid.jsx`, `MaterialDetailModal.jsx`, `ChecklistEditor.jsx`,
  `lib/bitinFields.js`/`bitinErrors.js`/`textSearch.js` e reconstruir do zero, incrementalmente
  — login/autenticação primeiro, depois a parte de Bitins de novo, uma tela de cada vez. Lógica
  de negócio do backend (`scripts/`, `backend/api/`) não foi tocada — só a UI que consumia esses
  endpoints saiu. Ver `docs/FRONTEND.md`, seção "Reset da tela de Bitins".

### Added
- **Tela de login redesenhada** (pós-reset, foco 100% em UI/UX, backend real desde já — não
  mock): layout dividido (painel de marca navy + formulário), logo/título/subtítulo agrupados
  num bloco centralizado (1ª versão prendia a logo isolada no topo, "meio perdida"), campos com
  ícone, botão de mostrar/esconder senha, erro com `role="alert"`, spinner de carregamento,
  tema claro/escuro disponível já no login (`ThemeToggle.jsx` extraído de `Layout.jsx`),
  responsivo, versão da aplicação no rodapé lida de `frontend/package.json` (sincronizado de
  `0.0.0` pra `0.5.0`) em vez de texto fixo.
- **Tela de cadastro reconstruída como a aba "Template apresentação" real** (5ª rodada,
  correção de rota — as rodadas 1-4 tinham usado a aba `ZBPP009 + ALTERACAO`, mas o print
  enviado era do documento formatado): cabeçalho em faixas (logo/título/BITex/Setor dourado +
  Produto/Solicitante + Motivo/Data), campo `bitex` agora editável, **checklist de 22 itens
  editável de verdade** (`ChecklistEditor.jsx`, novo — antes só existia read-only no resumo
  pós-envio) via `GET /bitins/schema/checklist` (`bitin_document.build_checklist_schema`,
  novo), e cabeçalho da tabela de materiais em amarelo/dourado com "Novo" de volta pra
  vermelho (igual ao Excel real — cabeçalho dourado já separa visualmente do vermelho de erro
  de validação, que fica nas células de dado). `afeta` do checklist é 100% manual nesta
  rodada — a lógica de auto-cálculo que já existe em `build_checklist` (usada no resumo) ainda
  não roda ao vivo no formulário, ver `docs/FRONTEND.md`.
- **Grid de materiais dirigido por schema, com navegação e visual de planilha real**
  (`frontend/src/components/MaterialGrid.jsx`, `MaterialDetailModal.jsx`, `docs/FRONTEND.md`):
  substitui a lista simples de identificação por uma planilha completa (linha = material,
  colunas = campos), refeita em 3 rodadas de feedback direto até ficar de verdade "tipo
  Excel":
  - Navegação por teclado nas 4 setas (não depende de Tab) + `Enter`/`Shift+Enter`.
  - Colar em qualquer célula (`Ctrl+V`, bloco copiado do Excel), criando linhas novas
    automaticamente, além de "Importar relatório do SAP" (formato fixo, sempre linha nova).
  - Colunas "#"/"Código" congeladas ao rolar (como "congelar painéis" do Excel).
  - Painel de "Detalhes" por material (`MaterialDetailModal.jsx`) com todos os ~30 campos de
    `dados_basicos` (De/Para, com busca) e `impactos_operacionais` num layout espaçoso — a
    grade em si só fixa como coluna os campos que o usuário escolher (ideal pra colar em
    massa), evitando o problema de "muitos campos, pouco espaço".
  - **Cabeçalho "Novo" destacado**: convenção extraída da planilha real do BITin
    (`examples/bitin teste 2.xlsm`, aba `ZBPP009 + ALTERACAO`, inspecionada via `openpyxl`) —
    toda coluna de valor novo/editável tem o rótulo destacado (laranja da marca, não vermelho
    como no Excel original — vermelho já é erro de validação nesta tela).
  - **Todos os ~30 campos de `dados_basicos` visíveis por padrão** (não escondidos atrás de um
    seletor) — pedido direto: "a tela deve ser um excel enorme, com a mesma estrutura". A grade
    tem ~70 colunas contando identificação/impactos, com rolagem horizontal, igual a abrir a
    planilha real. Rótulos ajustados pra bater literalmente com o texto do Plan2 (ex.:
    "Unidade Peso", não "Unidade de Peso").
  - Modelado no `CodeForm.jsx` do projeto irmão `GPT_Engineering_BITIN`, mas reconstruído:
    colunas vêm do backend (não hardcoded), colar do SAP reaproveita o parser Python já
    testado, erros de envio destacam a célula exata (na grade ou no painel de Detalhes,
    dependendo de onde o campo está sendo editado) em vez de só listar texto solto.
- **Logo real e grade de materiais ocupando a tela inteira** (6ª rodada): logo enviado pelo
  usuário (`frontend/public/logo.svg`) substitui o placeholder de texto no cabeçalho, login e
  tela de cadastro; `<main>` (`Layout.jsx`) perdeu o `max-w-6xl` global, e a grade de materiais
  agora quebra pra fora do container centralizado (`-mx-4` em `BitinDetail.jsx`) e perdeu a
  moldura de card (`MaterialGrid.jsx`) — encosta nas bordas reais da tela, "literalmente um
  excel" em vez de uma tabela dentro de um formulário. Padding/fonte de células, cabeçalho e
  botões de ação aumentados; cálculo de largura de coluna unificado num único helper.
- **Checklist em grade de colunas, cabeçalho+checklist+grade em largura total** (7ª rodada,
  a partir de um wireframe de estrutura enviado pelo usuário): `ChecklistEditor.jsx` trocou a
  lista de 22 linhas empilhadas (`<table>`) por uma grade de 2-4 colunas (conforme a largura da
  tela), com o campo Observação só aparecendo quando o item está marcado "SIM" — a faixa caiu
  de ~750px pra ~280px de altura. Cabeçalho e checklist passaram a compartilhar o mesmo
  `-mx-4` de largura total que só a grade de materiais tinha, então as 3 faixas (cabeçalho,
  checklist, tabela) encostam nas bordas reais da tela.
- **Checklist volta a ser tabela even; grade de materiais vira "10 colunas + 300 linhas
  prontas"** (8ª rodada, correção de rota sobre a print real): a grade de cards da 7ª rodada
  deixava os 22 itens do checklist com altura desigual (Observação condicional) — voltou a ser
  uma `<table>` de verdade, que garante linhas parelhas de graça. A grade de materiais reduziu
  de ~70 colunas visíveis por padrão pra 10 (Código/Descrição/Centro + os 7 impactos
  operacionais, igual à print da aba "Template apresentação") — Tipo Material, Grupo
  Mercadorias e os 3 checkboxes de snapshot saíram da grade, mas continuam editáveis via novo
  painel "Identificação" em `MaterialDetailModal.jsx`. A grade nasce com 300 linhas em branco
  (`BitinDetail.jsx`), como uma planilha nova do Excel; linhas em branco são filtradas antes de
  salvar/enviar (`compactMateriais`/`hasContent`) já que o backend valida
  código/centro/tipo_material como obrigatórios em toda linha de `materiais[]`, sem exceção —
  os índices de erro do envio são traduzidos de volta pra célula certa da grade
  (`remapMaterialErrorIndices`). Texto explicativo acima da grade removido, só a barra de
  ferramentas.
  - Busca insensível a acento (`lib/textSearch.js`) no seletor de campos e no painel de
    Detalhes — achado testando: buscar "liquido" não encontrava "Peso Líquido".
- **Identidade visual da marca (Grain & Protein Technologies) + tema claro/escuro**
  (`frontend/src/index.css`, `ThemeContext.jsx`): paleta extraída do logo como tokens Tailwind
  v4, cabeçalho navy com faixa de 3 cores, tokens semânticos (`app-bg`/`surface`/`line`/`ink`)
  usados em todo componente pra que os dois temas fiquem consistentes num só lugar. Toggle
  claro/escuro no cabeçalho, padrão claro (não detecta o tema do sistema operacional de
  propósito), escolha persiste no navegador. Logo real ainda não está no repositório — usa
  wordmark em texto como placeholder.
- **`GET /bitins/schema/materiais`** (`bitin_model.build_materiais_schema`): fonte única de
  colunas do grid — identificação, snapshot, `dados_basicos` (na mesma ordem do crosswalk) e
  `impactos_operacionais` com os valores válidos do POP (`config/bitin_document_mapping.json`).
- **`POST /bitins/parse-sap-paste`**: expõe `sap_paste_parser.parse_sap_paste_to_materiais` pro
  frontend — colar linhas do SAP na planilha vira materiais novos direto no grid.
- **Erro de envio → célula do grid**: `frontend/src/lib/bitinErrors.js` faz o parse do `field`
  estruturado (`materiais[0].alteracoes.dados_basicos.ncm`, etc.) pra destacar a célula exata,
  além da lista completa de erros já existente.
- **RBAC visível em "Meus Bitins"**: o botão "Excluir" some quando o usuário não é dono nem
  admin (o backend já recusava com `403`; a UI agora não oferece a ação de antemão).

### Notes
- 8 testes novos (Python): `build_materiais_schema` (`tests/test_bitin_model.py`) + os dois
  endpoints novos (`tests/test_backend_bitins.py`) — 154 testes automatizados no total.
- Validado com um roteiro de 25 checagens via Playwright ad-hoc cobrindo as 10 áreas do grid
  (edição básica, navegação por teclado, colunas congeladas, colar em bloco, importar SAP,
  colunas visíveis, painel de Detalhes, validação de envio, tema claro/escuro) — mesma
  limitação de ambiente já documentada (sem MongoDB real, backend testado com
  `mongomock-motor`/rotas mockadas onde necessário). 2 bugs reais encontrados durante o teste e
  corrigidos antes de fechar: coluna congelada sobrepondo a seguinte (`position: sticky` não é
  confiável com `border-collapse`, nem `table-layout: fixed` sozinho sem largura total
  explícita — ver `docs/FRONTEND.md`) e busca de campo sem suporte a acento.
- Ainda não incluído (ver `docs/FRONTEND.md`, "O que NÃO está nesta fatia ainda"):
  `ordem_cliente[]`, `lista_tecnica[]`, checklist editável, modo de leitura explícito pra quem
  abre o rascunho de outra pessoa sem ser dono/admin, mesclar (em vez de sempre duplicar) ao
  colar do SAP em cima de um material já existente no grid.

## [v0.4.0] - 2026-07-10

### Added
- **Esqueleto do frontend** (`frontend/`, `docs/FRONTEND.md`): React 19 + Vite + Tailwind 4 +
  react-router-dom + axios, sem lib de estado global (Context API para autenticação). Primeira
  fatia funcional, validada ponta a ponta com Playwright contra o backend real: login → "Meus
  Bitins" (abas Todos/Rascunhos/Enviados + busca por termo) → criar rascunho → salvar → reabrir
  (confirma persistência) → enviar → tela travada com número gerado e checklist de 22 itens.
- `BitinDetail.jsx`: componente único cobrindo criação e edição (evita a duplicação
  `BitinForm`/`BitinEdit` vista no projeto de referência `GPT_Engineering_BITIN`).
- Rota protegida (`RequireAuth`) redireciona pro login sem token; interceptor axios limpa o
  token guardado ao receber `401`.

### Notes
- Ainda não incluído nesta fatia (documentado em `docs/FRONTEND.md`): colar do SAP, edição de
  `dados_basicos`/`impactos_operacionais` por material, `lista_tecnica[]`, `ordem_cliente[]`,
  RBAC visível na UI. Sem esses campos, o formulário ainda não cria um BITin realmente útil —
  esse é o próximo incremento.
- 147 testes automatizados (Python, sem mudança nesta versão) + verificação manual do
  frontend via Playwright (não faz parte da suíte automatizada ainda).
- Descoberta durante o teste: sem MongoDB real disponível no ambiente de desenvolvimento,
  qualquer ação de `/bitins` falha com `500` (limitação já documentada, não é bug) — o teste
  E2E rodou o backend com `mongomock-motor` no lugar do Mongo real, mesma estratégia da suíte
  de testes automatizados.

## [v0.3.0] - 2026-07-10

### Added
- **Autenticação unificada no backend** (`backend/auth/`: `models.py`, `security.py`,
  `schemas.py`, `deps.py`, `routes.py`): `Usuario`/`Setor` no mesmo Postgres do resto do
  backend, hash de senha `pbkdf2_sha256`, JWT emitido e validado localmente (sem serviço
  externo, sem segredo compartilhado entre processos). RBAC simples de 3 níveis
  (`0` usuário, `1` gestor, `99` admin). Primeiro usuário registrado (`POST /auth/register`)
  vira admin automaticamente (bootstrap); promoções depois só via
  `PATCH /users/{id}/permission`, restrito a admin.
- **Endpoints `/users` e `/sectors`** (`backend/api/users.py`, `backend/api/sectors.py`):
  perfil próprio, listagem/busca (gestor+), promoção de permissão (admin), setores (listagem
  pública, criação restrita a admin).
- **Reforço de dono nos rascunhos**: só quem criou o rascunho (ou um admin) pode editar
  (`POST /bitins/draft` com `mongo_id`) ou excluir (`DELETE /bitins/{mongo_id}`) — qualquer
  outro usuário autenticado recebe `403`. Edição por admin não reatribui `criado_por`.
- **`criado_por`** (Postgres `bitins` e Mongo `bitin_contents`): passa a ser preenchido de
  verdade com o e-mail do usuário autenticado (coluna já existia nullable desde antes).
- **Validação estrutural de `ordem_cliente[]`** (`bitin_model.validate_ordem_cliente`):
  `codigo` obrigatório por entrada, itens de `acrescentar_no_pedido[]`/`retira_do_pedido[]`
  exigem `codigo_material`+`quantidade`, entrada sem nenhum item é sinalizada
  (`ordem_cliente_sem_itens`). O schema já suportava essa forma aninhada; só o conteúdo não
  era validado ainda.
- **Todos os endpoints de `/bitins` agora exigem autenticação** (`Authorization: Bearer
  <token>`) — sem token válido, `401`.
- 13 testes novos de robustez em `tests/test_backend_bitins.py` (filtros de listagem,
  paginação, entrada degenerada em `/enviar`, lista técnica inválida via API) e um arquivo
  novo `tests/test_backend_auth.py` (registro/bootstrap-admin/login/RBAC/promoção/setores).

### Fixed (achados corrigindo o `GPT_Engineering_authAPI`, usado só como referência)
- **Escalonamento de privilégio**: no serviço de referência, `POST /auth/register` aceitava
  `permission_level` direto do corpo da requisição — qualquer um podia se registrar como
  admin. Aqui, `UserCreate` nem tem esse campo; o nível é sempre decidido no servidor.
- **CORS inválido**: `allow_origins=["*"]` + `allow_credentials=True` (combinação insegura) —
  trocado por lista explícita de origens.
- Rotas `/bitins` próprias do serviço de referência (numeração e persistência
  redundantes/incompatíveis com este sistema) não foram trazidas.

### Changed
- Reorganização de pastas: scripts/saídas do PoC leve original movidos para
  `scripts/legacy_poc/` e `scripts/legacy_poc/output/`; arquivos de exemplo/dados reais
  (`.xlsm`, `.pdf`, `exported_winshuttle.csv`) movidos para `examples/`.
- `backend/models_sql.py`: coluna `criado_por` (String, nullable) adicionada em `BitinSQL`.
- `backend/config.py`: `SECRET_KEY`/`ALGORITHM`/`ACCESS_TOKEN_EXPIRE_MINUTES` substituem as
  variáveis do design anterior de serviço de auth separado (abandonado antes de ser
  publicado); `VERSION` atualizado para `0.3.0`.

### Notes
- 147 testes automatizados no total (era 114 na v0.2.0).
- Decisão de arquitetura registrada e depois revisada no mesmo dia: cogitamos rodar a
  autenticação como serviço separado (JWT validado por segredo compartilhado entre dois
  `.env`), mas optamos por unificar no mesmo processo/banco — evita sincronizar segredo entre
  dois arquivos `.env` e resolve RBAC/reforço de dono sem exigir chamada de rede por
  requisição. Ver `docs/BACKEND.md`, seção "Autenticação", para o histórico completo da decisão.

## [v0.2.0] - 2026-07-10

### Added
- **Port fiel `Módulo1`/`Módulo2`/`Módulo11`** (`scripts/vba_port_export.py`): fluxo real
  `Plan1` (`ZBPP009`) → `Plan2` (`ZBPP009 + ALTERACAO`) → `Plan3` (`Formulário Winshuttle`),
  orientado por mapeamento declarativo (`config/vba_mapping.json`), com dois subcomandos
  (`sync`/`export`) que refletem o passo humano real entre eles. Validado contra dois BITins
  reais fornecidos como exemplo.
- **Modelo de dados do BITin** (`scripts/bitin_model.py`, `docs/BITIN_MODEL.md`): valida
  cabeçalho/materiais e converte `materiais[]` em linhas de `Plan2`, com geração do `.xlsx`
  real da aba.
- **Export de lista técnica / CS02-BOM** (`scripts/lista_tecnica_export.py`): automação nova
  (nunca existiu em VBA), cobrindo alteração de quantidade e troca de componente
  (`operacao: inserir/alterar/excluir`). Validado contra caso real de troca de componente.
- **Documento do BITin** (`scripts/bitin_document.py`, port de `Módulo4`+`Módulo10`+`Módulo13`):
  determina Alt/Esp/ação de desenho como sugestão, monta checklist de 22 itens e diffs
  "campo alterado / de / para". Validado contra BITin real (8 materiais com revisão de
  desenho alterada).
- **Regras de negócio** (`scripts/bitin_business_rules.py`): 4 regras do `POP_ENG_7.3.7_002`
  (desenho aprovado, NCM/fiscal, sucateamento/centro de custo, ordem de cliente) + regras
  gerais de consistência (duplicidade código+centro, campo sem efeito, Alt inconsistente).
  `Alt`/`Esp`/`Est`/`LP`/`Pre`/`OC`/`OF` são **declarados pelo engenheiro**, não derivados de
  código SAP (decisão registrada: código de Grupo Mercadorias é vasto demais pra confiar).
- **Ciclo de vida rascunho → enviado** (`scripts/bitin_lifecycle.py`): edição livre em
  rascunho, toda a validação roda de uma vez só no envio; BITin enviado fica travado.
- **Visualização** (`scripts/bitin_view.py`): resumo estruturado do BITin (prévia e tela final).
- **Erros estruturados** (`scripts/bitin_errors.py`): todas as validações devolvem
  `{field, code, message}` em vez de string solta.
- **Parser de colar do SAP** (`scripts/sap_paste_parser.py`): separa por TAB (não espaço),
  preservando a liberdade do engenheiro de copiar do SAP e colar direto.
- **Sanitização de exports** (`scripts/csv_safety.py`): proteção contra CSV/formula injection.
- **Backend/API** (`backend/`, `docs/BACKEND.md`): FastAPI + Postgres (metadado) + MongoDB
  (conteúdo), sem autenticação por enquanto. Endpoint de envio roda toda a validação antes de
  travar o BITin e gerar o número sequencial (com proteção contra corrida).

### Fixed
- `pd.read_excel` tratava a string `"N/A"` (valor de negócio real neste domínio) como célula
  vazia — corrigido com `keep_default_na=False`.
- `scripts/winshuttle_export.py`: `build_plan3_rows` não normalizava `"N/A"` → `""` como o
  teste já esperava.
- Regra de duplicidade validava só `codigo_material`, travando por engano quando o mesmo
  material precisa de alteração em centros diferentes (caso real).

### Changed
- `bitin_model.validate_bitin`: número do BITin (`bitin`) deixou de ser obrigatório no
  cabeçalho — agora é **gerado pelo sistema no momento do envio**, não digitado pelo
  engenheiro. `setor` passou a ser obrigatório (define o prefixo P/A do número gerado).

### Removed
- `.pyc` compilado rastreado por engano em `scripts/__pycache__/`.
- 3 arquivos `.xlsx` de PoC antigo sem nenhuma referência no repositório
  (`poc_winshuttle_export.xlsx`, `_aligned.xlsx`, `_robust.xlsx`).

### Notes
- 114 testes automatizados cobrindo motor Python + backend, vários validados contra BITins
  reais fornecidos como exemplo durante o desenvolvimento.
- Documentação completa das decisões e achados em `docs/BITIN_MODEL.md`,
  `docs/VBA_EXPORT_MAPPING.md`, `docs/VBA_MIGRATION_GUIDE.md`, `docs/BACKEND.md`.

## [v0.1.0] - 2026-07-09
### Added
- Public release `v0.1.0` published on GitHub.
- Release notes sourced from `docs/RELEASE_v0.1.0.md`.
- Documentation updated in `README.md` and `docs/README_HANDOFF.md` with release URL.

### Notes
- Release was created manually via GitHub UI.
- Release automation script removed from repository.
