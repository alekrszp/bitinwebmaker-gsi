# Frontend do BITin (`frontend/`)

Primeira fatia do frontend web que substitui o Excel/VBA — construída depois do backend
(`backend/`) já estar validado com 147 testes. Ver `docs/BACKEND.md` para a API que este
frontend consome.

## Stack e por quê

**React 19 + Vite + Tailwind 4 + react-router-dom + axios, sem lib de estado global**
(Redux/Zustand). Decisão baseada na revisão do `GPT_Engineering_BITIN` (projeto irmão mais
antigo, usado só como referência de padrões, não copiado): essa mesma combinação de stack já
tinha se mostrado proporcional ao problema — o estado de um formulário de BITin é local,
Context API (`AuthContext`) + `useState` já bastam, e trazer Redux seria complexidade sem
benefício claro nesse estágio.

**Um único componente para criar/editar** (`BitinDetail.jsx`, com `mode` implícito por
`useParams`), não dois componentes separados como o projeto de referência tinha
(`BitinForm.jsx`/`BitinEdit.jsx` — achado da revisão: ~90% de código duplicado entre os dois,
e isso gerou um bug real de rota lá). Aqui, `/bitins/novo` e `/bitins/:id` reaproveitam o
mesmo componente.

## Estrutura

```text
frontend/
  src/
    lib/api.js              - cliente axios (token via localStorage, interceptor 401)
    context/AuthContext.jsx - login/logout/estado do usuário (Context API, sem lib externa)
    components/
      RequireAuth.jsx        - guarda de rota (redireciona pro /login sem token)
      Layout.jsx              - topo com e-mail do usuário + botão sair
      MaterialGrid.jsx        - grid de materiais (linhas/colunas), ver seção própria abaixo
      MaterialDetailModal.jsx - painel de edição de um material (todos os campos, mais espaço)
    pages/
      Login.jsx
      MeusBitins.jsx          - lista com abas Todos/Rascunhos/Enviados + busca
      BitinDetail.jsx         - criar/editar rascunho (form) OU visualizar enviado (resumo)
    App.jsx                   - rotas
```

## Grid de materiais (`MaterialGrid.jsx`, adicionado em 2026-07-13)

Decisão registrada: a visualização/criação de materiais continua no formato planilha (linha =
material, colunas = campos) — não um formulário empilhado. A estrutura real (`materiais[]` com
`dados_basicos` De/Para por campo, ver `docs/BITIN_MODEL.md`) é essencialmente tabular, e colar
do SAP (linha colada = 1 material) só faz sentido nesse formato. Isso segue a mesma ideia do
projeto irmão `GPT_Engineering_BITIN` (`CodeForm.jsx`), mas reconstruída com estas mudanças:

- **Colunas vêm do backend, não hardcoded**: `GET /bitins/schema/materiais` (ver
  `docs/BACKEND.md`) devolve identificação, snapshot, pares De/Para de `dados_basicos` e
  `impactos_operacionais` (com as opções válidas do POP, pra virar `<select>` em vez de texto
  livre). Evita a duplicação/divergência que o projeto irmão teve com ~80 colunas copiadas à
  mão no JS.
- **Erros de envio destacam a célula exata**: `POST /bitins/{id}/enviar` já devolve
  `{field, code, message}` com caminho tipo `materiais[0].alteracoes.dados_basicos.ncm.para` —
  o grid faz o parse desse caminho pra (linha, coluna) e marca a célula, em vez de só listar os
  erros em texto solto (o que o projeto irmão não fazia).
- **Importar relatório do SAP** via `POST /bitins/parse-sap-paste` (reaproveita
  `sap_paste_parser.py` testado, não reimplementa o parser em JS) — sempre cria linhas novas, é
  um import de formato fixo (ZBPP009), diferente do colar genérico abaixo.
- **Edição livre até o envio**: nenhuma validação roda nas teclas/células durante o rascunho —
  só no botão "Enviar" (mesma filosofia de `bitin_lifecycle`, ver `docs/BITIN_MODEL.md`).
- **Visual clean**: sem o tema escuro/glass do projeto irmão — Tailwind neutro, consistente com
  o resto do frontend.

### Navegação e colar estilo Excel (adicionado em 2026-07-13, mesmo dia — revisão de UX)

A primeira versão do grid usava blocos de `<input>` desconexos (cada campo era uma "ilha", sem
navegação entre células) — feedback direto do responsável do projeto: "muito ruim", não parecia
planilha de verdade. Reconstruído com uma lista única e achatada de colunas
(`buildColumns` em `MaterialGrid.jsx`, em vez de identificação/`dados_basicos`/
`impactos_operacionais` renderizados em blocos JSX separados como antes) — é o que permite
tratar o grid inteiro como uma única planilha contígua, com `(linha, coluna)` simples:

- **Navegação por teclado nas 4 setas** (revisado no mesmo dia, 2ª rodada de feedback: "não
  usar Tab pra navegar, colocar também nas setas pro lado"): `↑`/`↓`/`←`/`→` sempre pulam pra
  célula vizinha (mesma linha ou coluna), sem depender de Tab — a ordem do DOM inclui os
  botões "Detalhes"/"Remover" no fim de cada linha, o que quebraria o fluxo horizontal se Tab
  fosse o mecanismo principal. `Enter` confirma e desce (`Shift+Enter` sobe). Tentamos antes uma
  variante onde `←`/`→` só pulavam célula quando o cursor de texto já estava na borda do valor
  (pra não atrapalhar editar o meio de um texto) — na prática ficou confuso (digitar um valor e
  apertar seta não pulava célula na hora, porque o cursor ficava no fim do texto digitado, não
  na borda "zero"), então foi simplificado: as 4 setas sempre pulam, e cada célula já seleciona
  o conteúdo inteiro ao chegar (foco programático), então digitar direto substitui o valor —
  pra editar o meio de um texto longo, clique com o mouse ou use Home/End.
- **Colunas maiores** (2ª rodada de feedback: "muitos campos pra pouco espaço", "deixar maior e
  mais fácil de interagir"): larguras de coluna aumentadas (`CELL_WIDTHS`/`CELL_WIDTH_PX` em
  `MaterialGrid.jsx`), padding maior, checkboxes maiores.
- **Colunas "#" e "Código" congeladas** (`position: sticky`, como "congelar painéis" do Excel)
  — ao rolar a grade pra direita (inevitável com muitas colunas), o material em edição continua
  identificável sem precisar rolar de volta.
- **Painel de "Detalhes" por material** (`MaterialDetailModal.jsx`) — resposta direta ao "muitos
  campos pra pouco espaço": a grade é ótima pra visão geral e colar em bloco, mas uma célula de
  planilha é ruim pra ~30 campos com rótulo+valor. O botão "Detalhes" de cada linha abre um
  painel grande com todos os campos de `dados_basicos` (um por linha, com busca) e
  `impactos_operacionais` (grid maior de `<select>`), incluindo o mesmo destaque de erro de
  envio da grade. A grade continua útil pra fixar como coluna só os campos que o usuário quer
  editar em massa/colar (botão "Fixar campos na grade", renomeado do antigo "Campos de dados
  básicos" pra deixar clara a diferença do painel de Detalhes).
- **Colar em qualquer célula** (`handleCellPaste`): clicar numa célula e colar (`Ctrl+V`) um
  bloco de texto com tab/quebra de linha (copiado do Excel, ou de outra parte do grid) preenche
  a partir dali — cria materiais novos automaticamente se o bloco colado for maior que o grid
  atual. Colar um valor único (sem tab/quebra de linha) não aciona esse comportamento — usa o
  paste nativo do input, sem interferência. Diferente do "Importar relatório do SAP" (formato
  fixo, sempre cria linhas), este é genérico: funciona em qualquer coluna, e pode sobrescrever
  células já preenchidas.
- **Visual de grade contínua**: borda em toda célula (não só nas divisórias entre grupos),
  cabeçalho fixo (`sticky top-0`) junto com a primeira coluna (`sticky left-0`), sem cantos
  arredondados por célula — mais parecido com uma planilha real, menos com um formulário.
- **Erro de envio destaca a célula com contorno vermelho sempre visível** (não só um fundo
  sutil) — a versão anterior usava só `bg-red-50`, que ficou fraco demais nesse visual mais
  denso; o contorno (`ring`) precisa continuar óbvio mesmo quando a célula está selecionada
  (anel vermelho em vez de azul nesse caso).
- **Decisão explícita: sem seleção de intervalo (múltiplas células) nesta rodada** — copiar um
  intervalo de dentro do grid (Ctrl+C de várias células pra colar em outro lugar) e
  clique-arraste pra selecionar um retângulo de células não foram implementados. O pedido
  original era "copiar as ferramentas do Excel"; colar em qualquer célula (a partir do
  clipboard do sistema, incluindo do Excel de verdade) cobre o caso de uso real relatado —
  copiar um intervalo de dentro do próprio grid é um incremento futuro, não bloqueado por
  nada, só não construído ainda.

### Fidelidade com a planilha real do BITin (adicionado em 2026-07-13, 3ª rodada)

Pedido direto: "quero que a tela de cadastro de código seja uma cópia só que mais bonita do
excel de bitin que temos". Fomos direto na fonte — `examples/bitin teste 2.xlsm`, aba
`ZBPP009 + ALTERACAO` (a mesma que `Plan2`/`plan2_column_headers` em `config/vba_mapping.json`
já modelava) — e inspecionamos a formatação real via `openpyxl` (não só os dados):

- **Cabeçalho "Novo" em vermelho**: no Excel real, todo cabeçalho de coluna editável/"valor
  novo" tem o texto em vermelho negrito, diferente das colunas de valor atual (pretas). Essa é
  a única cor semântica usada no cabeçalho real (sem preenchimento por célula — dado em si não
  tem highlight, só o rótulo da coluna). Replicado: `MaterialGrid.jsx` (colunas De/Para viram
  duas colunas "Atual"/"Novo", com "Novo" em vermelho) e `MaterialDetailModal.jsx` (mesma
  convenção no cabeçalho da tabela "Dados básicos").
- **O que não foi copiado de propósito**: `freeze_panes` do arquivo real está em `BV1` (colunas
  A–BU congeladas, ~73 colunas) — claramente um acidente de uso manual (alguém rolou até ali e
  ativou "Congelar painéis" sem querer), não uma escolha de design. Mantido o congelamento
  sensato de "#"+"Código" (ver acima). Gridlines do Excel real estão desligadas
  (`showGridLines=False`) e o visual depende só da borda inferior do cabeçalho — no grid web
  optamos por manter borda fina em toda célula (diferente da planilha original), porque aqui é
  uma grade interativa onde o usuário precisa enxergar o alvo de clique, não um documento pra
  imprimir/ler.
- **Busca insensível a acento** (`lib/textSearch.js`, achado testando o painel de Detalhes):
  buscar "liquido" não encontrava "Peso Líquido" porque a comparação era string literal —
  corrigido normalizando os dois lados (remove diacríticos via `Unicode NFD`) antes de
  comparar, usado tanto no seletor de campos da grade quanto no painel de Detalhes.

**Achado técnico registrado** (pra não repetir): `position: sticky` em `<td>`/`<th>` não
funciona de forma confiável com `border-collapse` (a coluna congelada "Código" sobrepunha
"Descrição") — trocado por `border-separate` + `border-spacing-0`. Além disso, `table-layout:
fixed` sozinho não bastou: sem uma largura total explícita na `<table>`, o navegador encolhe
todas as colunas proporcionalmente pra caber no container, ignorando a largura declarada de
cada célula (a coluna "#" de 48px renderizava a ~25px) — o que quebra a matemática do offset
das colunas congeladas. A largura total agora é somada em JS (`tableWidth` em
`MaterialGrid.jsx`) a partir da largura de cada coluna e aplicada como `width` da `<table>`.

## O que já funciona

Validado com Playwright ad-hoc contra o backend real nesta máquina (sem MongoDB real, ver
"Rodando localmente" abaixo).

- Login (`POST /auth/login`) → redireciona pra "Meus Bitins".
- Rota protegida: sem token, qualquer rota de `/bitins/*` redireciona pro login.
- "Meus Bitins": lista com abas (status) + busca por termo, criar/excluir rascunho; botão
  "Excluir" some quando o usuário não é dono nem admin (o backend já recusava com `403`, a UI
  agora não oferece a ação — RBAC visível, adicionado em 2026-07-13).
- Criar rascunho: cabeçalho (setor/produto/motivo/solicitante/data) + **grid de materiais**
  (`MaterialGrid.jsx`, ver seção acima) — identificação, snapshot atual, `dados_basicos`
  De/Para (colunas fixadas pelo usuário ou editadas via painel de Detalhes) e
  `impactos_operacionais` (Alt/Est/Esp/LP/Pré/OC/OF com as opções válidas do POP) — salva com
  `POST /bitins/draft`.
- Reabrir rascunho: confirma que o conteúdo persistiu.
- Navegação por teclado nas 4 setas + `Enter`, colar em qualquer célula (`Ctrl+V`, bloco
  copiado do Excel ou de outra parte do grid), colunas "#"/"Código" congeladas ao rolar, e
  painel de "Detalhes" por material com todos os campos — ver "Navegação e colar estilo Excel"
  acima.
- Importar relatório do SAP: linhas coladas viram materiais novos no grid via
  `POST /bitins/parse-sap-paste`.
- Enviar (`POST /bitins/{id}/enviar`): se falhar, destaca a célula exata do grid pra cada erro
  associado a um material (via `field`) e mostra a lista completa de erros estruturados
  (`{field, code, message}`) sem travar nada; se passar, mostra o número gerado e a tela de
  resumo travada (materiais + checklist de 22 itens).

## O que NÃO está nesta fatia ainda (próximos incrementos)

- **`ordem_cliente[]` e `lista_tecnica[]`** — sem UI ainda; só o backend valida/aceita.
- **Checklist manual** (itens não cobertos por regra automática) — hoje só visualização, sem
  edição.
- **RBAC visível na tela de edição** — a lista já esconde "Excluir" por permissão (ver acima),
  mas quem abre o rascunho de outro usuário (sem ser dono/admin) ainda vê o formulário editável
  normalmente; só descobre que não pode salvar ao tentar (o backend recusa com `403` e a
  mensagem aparece, mas não é preventivo). Um modo de leitura explícito pra esse caso fica pro
  próximo incremento.
- **Importar relatório do SAP sempre cria linhas novas** — não tenta casar/mesclar com um
  material já existente no grid (mesmo código+centro importado duas vezes vira duas linhas) —
  o engenheiro precisa remover a duplicata manualmente se importar a mesma linha de novo.
- **Sem seleção de intervalo (múltiplas células)** — copiar um bloco de dentro do próprio grid
  (Ctrl+C de várias células) e clique-arraste pra selecionar um retângulo não existem ainda;
  colar (a partir do clipboard do sistema, incluindo do Excel) já funciona em qualquer célula.
- **Checklist manual** (itens não cobertos por regra automática) — hoje só visualização, sem
  edição.
- **RBAC visível na UI** (esconder ações que o backend recusaria por permissão) — o backend já
  recusa (`403`) quem tenta editar/excluir rascunho de outra pessoa sem ser admin, mas a UI
  não esconde os botões antes disso.

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
