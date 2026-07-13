# Changelog

All notable changes to this project will be documented in this file.

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
