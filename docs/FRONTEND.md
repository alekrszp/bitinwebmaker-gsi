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
| `brand-orange` | Acento no wordmark "BITin" (sobre fundo claro, onde dourado não teria contraste) e indicador "Novo"/coluna editável no grid de materiais e no painel de Detalhes — deliberadamente **não** vermelho (que já é usado pra erro de validação na mesma tela; usar as duas cores evita confundir "isto você edita" com "isto está errado"). |

**Semânticos** (mudam entre os temas — todo componente usa estes nomes, nunca `gray-*`
direto, pra que os dois temas fiquem consistentes num só lugar):

| Token | Uso |
|---|---|
| `app-bg` | Fundo da página (fora dos cards). |
| `surface` / `surface-alt` | Fundo de card/tabela/modal / fundo de zebra e painéis sutis. |
| `surface-header` | Tom sólido (não translúcido) — cabeçalho de tabela e hover de linha. Precisa ser sólido, não com opacidade, porque cabeçalhos com coluna congelada (`position: sticky`) já tiveram bug de conteúdo vazando por trás de fundo translúcido (ver "Achado técnico registrado" abaixo). |
| `line` | Toda borda/divisória. |
| `ink` / `ink-muted` / `ink-faint` | Texto primário / secundário / terciário-desabilitado. |

Erros de validação continuam em vermelho puro (Tailwind `red-*`) — cor semântica de erro não
muda com a marca nem com o tema, em nenhuma tela.

**Tema claro/escuro** (`ThemeContext.jsx`, adicionado em 2026-07-13): toggle no cabeçalho
(ícone sol/lua), classe `.dark` na raiz (`@custom-variant dark` em `index.css`, não
`prefers-color-scheme` — decisão explícita: **padrão é sempre claro**, não detecta o tema do
sistema operacional). Escolha do usuário persiste em `localStorage`. Os tokens semânticos
acima são redefinidos sob `.dark` — como o Tailwind gera variáveis CSS de verdade a partir de
`@theme`, a troca de tema não precisa de `dark:` em cada classe usada nos componentes.

**Logo**: ainda usando um wordmark em texto ("BIT**in**", com acento dourado/laranja) como
placeholder — o arquivo de verdade da logo (Grain & Protein Technologies) ainda não está no
repositório. Local reservado pra trocar: `Layout.jsx` (cabeçalho) e `Login.jsx` (tela de
login), ambos com comentário `TODO` no código apontando onde entra o `<img>`.

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
      ChecklistEditor.jsx     - checklist de 22 itens (Documento/Afeta/Observação)
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

- **Cabeçalho "Novo" destacado**: no Excel real, todo cabeçalho de coluna editável/"valor
  novo" tem o texto em vermelho negrito, diferente das colunas de valor atual (pretas). Essa é
  a única cor semântica usada no cabeçalho real (sem preenchimento por célula — dado em si não
  tem highlight, só o rótulo da coluna). Replicado em `MaterialGrid.jsx`/`MaterialDetailModal.jsx`
  (colunas De/Para viram duas colunas "Atual"/"Novo") — mas em **laranja da marca**, não
  vermelho, porque vermelho já é usado pra erro de validação nas mesmas telas (ver "Identidade
  visual" acima).
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

### Grade completa por padrão, não escondida (4ª rodada, mesmo dia)

Feedback direto: "a tela deve ser um excel enorme, com a mesma estrutura" — a 3ª rodada já
tinha a estrutura certa (colunas De/Novo, rótulos fiéis ao Plan2), mas ainda escondia os ~30
campos de `dados_basicos` até o usuário escolher quais fixar como coluna (ver "Navegação e
colar estilo Excel" acima). Isso contrariava o pedido: não é resumo, é cópia.

- **Todos os 30 campos aparecem como coluna desde o carregamento** (`visibleFields` inicia com
  `schema.dados_basicos.map(c => c.key)` assim que o schema chega, não `[]`) — a grade é
  literalmente enorme (~70 colunas contando identificação/snapshot/impactos), com rolagem
  horizontal, exatamente como abrir a planilha real.
- **"Colunas visíveis" continua existindo, mas inverteu de papel**: antes era a única forma de
  *mostrar* um campo (porta de entrada obrigatória); agora é só uma forma opcional de
  *esconder* o que não interessa no momento — texto do botão e do painel atualizados pra
  deixar isso claro.
- **Rótulos das colunas De/Novo ajustados pra bater literalmente com o texto do Plan2 real**
  (`DADOS_BASICOS_LABELS` em `scripts/bitin_model.py`) — ex.: "Unidade Peso" (não "Unidade de
  Peso"), "Resp. Crtrl. Produção" (não "Responsável Controle de Produção"), "Depósito Sup.
  Externo" (não "Depósito de Suprimento Externo"). O `uppercase` do CSS já deixa maiúsculo de
  qualquer forma — a fidelidade que importa aqui é a *palavra*, não a caixa.
- O painel de "Detalhes" continua existindo como atalho opcional (revisar/editar um material
  sem rolar a grade inteira), não como o lugar "certo" de editar dados básicos — a grade em si
  já é suficiente, igual à planilha original.

### Tela de cadastro = aba "Template apresentação" real, não a "ZBPP009 + ALTERACAO" (5ª rodada)

Correção de rota: as rodadas 1-4 usaram a aba `ZBPP009 + ALTERACAO` (grade De/Novo crua) como
referência pra "tela de cadastro". O usuário mandou print de uma aba diferente — `Template
apresentação` (o documento formatado: logo, título, BITex, Setor, Produto/Solicitante,
Motivo/Data Solicitação, faixa "CHECK LIST" com os 22 itens, e uma tabela de alterações com
cabeçalho amarelo) — e pediu a cópia literal dessa, "só que com nossas regras nos campos".

- **Cabeçalho em faixas, igual ao print** (`BitinDetail.jsx`): logo (placeholder por
  enquanto) + título "Boletim de Informações Técnicas Interno (BITIn)" em navy/branco, BITex
  (select SIM/NÃO, valor sempre em vermelho negrito — mesma convenção de "isso chama atenção"
  usada em outras células da planilha real) e Setor como um `<select>` com fundo dourado
  sólido (a cor de destaque do print pro setor escolhido). Abaixo, Produto/Solicitante e
  Motivo/Data Solicitação em pares label-azul + campo, réplica das linhas 2-3 do documento.
- **Campo `bitex` adicionado ao formulário** (já existia no modelo — `docs/BITIN_MODEL.md`
  registra que foi encontrado no `Template apresentação` real — mas não tinha campo de edição
  no frontend ainda).
- **Checklist editável de verdade** (`ChecklistEditor.jsx`, novo componente): faixa
  "CHECK LIST" vermelho-escura + tabela Documento/Afeta/Observação com os 22 itens fixos do
  POP, vindos de `GET /bitins/schema/checklist` (novo endpoint, `bitin_document.
  build_checklist_schema` — mesma lista usada por `build_checklist`, só id+etapa, sem o
  cálculo de `afeta`). Antes desta rodada, `checklist[]` só existia read-only na tela de
  resumo pós-envio — não dava pra editar no rascunho.
  - **Decisão registrada: `afeta` fica livre pro engenheiro marcar (SIM/NÃO), não
    auto-calculado a partir dos materiais nesta rodada.** `scripts/bitin_document.
    build_checklist` já teria a lógica pra derivar boa parte dos 22 itens automaticamente a
    partir de `impactos_operacionais`/`bitex` (usada na tela de resumo/envio) — replicar esse
    cálculo *ao vivo* no formulário exigiria ou reimplementar a lógica em JS (duplicação que o
    projeto evita de propósito) ou um endpoint de prévia chamado a cada edição (custo/
    complexidade não pedidos ainda). Fica registrado como incremento futuro possível, não
    bloqueado por nada.
- **Cabeçalho da tabela de materiais virou amarelo/dourado** (`MaterialGrid.jsx`), igual à
  tabela de alterações do print — e o indicador "Novo" voltou a ser vermelho (não laranja da
  3ª/4ª rodada): sobre fundo dourado, vermelho tem contraste bom e bate com a cor literal do
  Excel real; a preocupação original (confundir com erro de validação) é menor aqui porque o
  cabeçalho amarelo já é uma região visualmente separada das células de dado (brancas) onde o
  destaque de erro aparece.

### Logo real, tela inteira pra grade de materiais, sem moldura de card (6ª rodada)

O usuário mandou o arquivo real do logo (`Imagem1.svg`) e apontou dois problemas na 5ª
rodada: a grade de materiais ainda estava pequena (contida no mesmo `max-w-6xl` do resto da
página) e o cadastro ainda parecia "um formulário com uma tabela dentro", não uma planilha.

- **Logo de verdade** (`frontend/public/logo.svg`, cópia do arquivo enviado): substitui o
  placeholder de texto em `Layout.jsx` (cabeçalho, dentro de um `bg-white` — o arquivo é um
  JPEG embutido em SVG com fundo branco sólido, não transparente, então precisa de um fundo
  branco próprio sobre o navy), `Login.jsx` e a célula de logo em `BitinDetail.jsx`.
- **`<main>` deixou de ter `max-w-6xl` global** (`Layout.jsx`): antes, todo o conteúdo do app
  ficava preso a uma largura de ~1152px, inclusive a grade de materiais. Agora `<main>` só tem
  padding, e cada página decide sua própria largura. "Meus Bitins" e o cabeçalho/checklist do
  cadastro ganharam seu próprio `mx-auto max-w-6xl` pra não mudarem de aparência.
- **Grade de materiais quebra pra fora do container centralizado** (`BitinDetail.jsx`): fica
  dentro de `<div className="-mx-4">`, que cancela o padding horizontal do `<main>` e faz a
  grade encostar nas bordas reais da tela — literalmente uma planilha ocupando a tela inteira,
  não uma caixa de conteúdo.
- **Moldura de card removida da grade** (`MaterialGrid.jsx`): o wrapper externo perdeu borda,
  cantos arredondados e padding (`rounded border border-line bg-surface p-4` → só `bg-surface`);
  a área de rolagem trocou `rounded border` por `border-y` (só linhas horizontais, sem laterais
  nem cantos) e o teto de altura subiu de `75vh` pra `calc(100vh-260px)` — usa o espaço vertical
  que sobra abaixo do cabeçalho/checklist em vez de parar cedo.
- **Células e cabeçalhos maiores**: unificado o cálculo de largura de coluna num único helper
  `widthClass()` (antes havia dois mapas duplicados `CELL_WIDTHS`/`CELL_WIDTH_PX`
  desincronizados); aumentado padding e tamanho de fonte de cabeçalho, células, checkbox e
  botões de ação em todo o grid, e as colunas fixas "#" e "Ações" ficaram mais largas (48→56px
  e 168→220px) pra caber o texto maior sem cortar.

### Checklist em grade de colunas + 3 faixas em largura total (7ª rodada)

O usuário mandou um wireframe simples (retângulos coloridos, sem detalhe visual) confirmando
a estrutura de página antes de enviar o Figma de verdade: cabeçalho, checklist e tabela de
códigos devem ocupar a largura inteira da tela, e o checklist precisa ficar compacto pra não
"descer" a tela e empurrar a tabela de materiais pra fora da dobra.

- **Checklist virou grade em colunas, não lista de 22 linhas empilhadas**
  (`ChecklistEditor.jsx`): trocado `<table>` por um grid CSS (2 colunas em telas médias, 3 em
  telas largas, 4 em ultrawide). Cada item é um bloco compacto — etapa + seletor Afeta na
  mesma linha — e o campo Observação só aparece quando o item está marcado "SIM" (a maioria
  fica "NÃO", então esconder o campo economiza ainda mais altura, e escrever observação sem
  afetar não fazia sentido mesmo). Resultado: a faixa caiu de ~750px pra ~280px de altura numa
  tela cheia com 22 itens.
- **Cabeçalho e checklist passaram a compartilhar a mesma largura total da grade de
  materiais** (`BitinDetail.jsx`): antes só a grade de materiais tinha `-mx-4` (quebrava pra
  fora do container centralizado); agora cabeçalho, checklist e grade dividem um único wrapper
  `-mx-4`, então as 3 faixas encostam nas bordas reais da tela, igual ao wireframe. Cantos
  arredondados e borda lateral removidos de cabeçalho/checklist pelo mesmo motivo (mesmo
  tratamento "sem moldura" já aplicado à grade na 6ª rodada).
- **Achado de teste**: como o checklist deixou de ser uma `<table>`, a grade de materiais
  passou a ser a única tabela HTML da página — os scripts de regressão ad-hoc (Playwright, só
  no scratchpad, não fazem parte do repo) que localizavam a grade por `table.nth(1)` e o
  checklist por `table.nth(0)` precisaram ser reescritos (checklist agora localizado por texto
  do banner "Check list" + `following-sibling`). Sem impacto em código de produção.

## O que já funciona

Validado com Playwright ad-hoc contra o backend real nesta máquina (sem MongoDB real, ver
"Rodando localmente" abaixo).

- Login (`POST /auth/login`) → redireciona pra "Meus Bitins".
- Rota protegida: sem token, qualquer rota de `/bitins/*` redireciona pro login.
- "Meus Bitins": lista com abas (status) + busca por termo, criar/excluir rascunho; botão
  "Excluir" some quando o usuário não é dono nem admin (o backend já recusava com `403`, a UI
  agora não oferece a ação — RBAC visível, adicionado em 2026-07-13).
- Criar rascunho: cabeçalho em faixas (logo/título/BITex/Setor + Produto/Solicitante +
  Motivo/Data, ver "Tela de cadastro = aba Template apresentação" acima) + **checklist
  editável** (`ChecklistEditor.jsx`, 22 itens) + **grid de materiais** (`MaterialGrid.jsx`) —
  identificação, snapshot atual, os 30 pares De/Novo de `dados_basicos` (todos visíveis por
  padrão) e `impactos_operacionais` (Alt/Est/Esp/LP/Pré/OC/OF com as opções válidas do POP) —
  salva com `POST /bitins/draft`.
- Reabrir rascunho: confirma que o conteúdo persistiu (cabeçalho, checklist e materiais).
- Navegação por teclado nas 4 setas + `Enter`, colar em qualquer célula (`Ctrl+V`, bloco
  copiado do Excel ou de outra parte do grid), colunas "#"/"Código" congeladas ao rolar, e
  painel de "Detalhes" por material (atalho opcional) — ver "Navegação e colar estilo Excel" e
  "Grade completa por padrão" acima.
- Importar relatório do SAP: linhas coladas viram materiais novos no grid via
  `POST /bitins/parse-sap-paste`.
- Enviar (`POST /bitins/{id}/enviar`): se falhar, destaca a célula exata do grid pra cada erro
  associado a um material (via `field`) e mostra a lista completa de erros estruturados
  (`{field, code, message}`) sem travar nada; se passar, mostra o número gerado e a tela de
  resumo travada (materiais + checklist de 22 itens).
- Tema claro/escuro (toggle no cabeçalho, padrão claro, escolha persiste no navegador).

## O que NÃO está nesta fatia ainda (próximos incrementos)

- **`ordem_cliente[]` e `lista_tecnica[]`** — sem UI ainda; só o backend valida/aceita.
- **Checklist sem auto-cálculo a partir dos materiais** — os 22 itens já são editáveis
  (`ChecklistEditor.jsx`), mas `afeta` fica 100% manual; a lógica que já existe em
  `bitin_document.build_checklist` (deriva boa parte automaticamente de
  `impactos_operacionais`/`bitex`, usada hoje só na tela de resumo pós-envio) ainda não roda
  ao vivo no formulário — ver "Tela de cadastro = aba Template apresentação" acima.
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
- **Logo real ainda não está no repositório** — cabeçalho e tela de login usam um wordmark em
  texto como placeholder (ver "Identidade visual" acima). Trocar assim que o arquivo (PNG/SVG)
  estiver disponível.
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
