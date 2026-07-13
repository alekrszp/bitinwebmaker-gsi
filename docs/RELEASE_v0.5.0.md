# Release v0.5.0 — Tela de cadastro como réplica da planilha real do BITin

Release criado a partir da tag `v0.5.0`.

## Resumo

- Objetivo: a fatia anterior (v0.4.0) só cobria identificação de material — não dava pra
  montar um BITin realmente útil. Esta versão reconstrói a tela de cadastro inteira como
  réplica da planilha Excel real que o time já usa, em 5 rodadas de feedback direto:
  - v1: colunas de material dirigidas por schema, sem navegação.
  - v2: navegação/colar estilo Excel — mas "muito ruim" pra usar.
  - v3: setas completas, painel de Detalhes, fidelidade visual com a aba `ZBPP009 + ALTERACAO`.
  - v4: todos os ~30 campos visíveis por padrão ("a tela deve ser um excel enorme"),
    identidade visual da marca, tema claro/escuro.
  - **v5 (correção de rota)**: o print enviado mostrou que a referência certa era outra aba —
    `Template apresentação` (documento formatado: cabeçalho em faixas, BITex, Setor, checklist
    de 22 itens, tabela de alterações com cabeçalho amarelo), não a `ZBPP009 + ALTERACAO` usada
    nas rodadas anteriores. Tela de cadastro reconstruída pra bater com essa referência.
  - **v6**: logo real (`Imagem1.svg` enviado pelo usuário) substitui o wordmark de texto; a
    grade de materiais deixou de ficar presa ao `max-w-6xl` do resto da página e passou a
    ocupar a tela inteira, sem moldura de card — "literalmente um excel", célula/fonte/cabeçalho
    maiores.
  - **v7**: a partir de um wireframe de estrutura enviado pelo usuário, checklist virou grade
    de 2-4 colunas (não lista de 22 linhas empilhadas, com Observação só visível quando o item
    afeta), e cabeçalho+checklist passaram a compartilhar a mesma largura total que só a grade
    de materiais tinha — as 3 faixas da tela agora encostam nas bordas reais da tela.
  - **v8 (correção de rota)**: a print real mostrou que a grade de cards do checklist (v7)
    ficava desigual (altura variável) — voltou a ser uma `<table>`. A grade de materiais
    reduziu de ~70 pra 10 colunas por padrão (identificação + os 7 impactos, igual à print) e
    passou a nascer com 300 linhas em branco prontas pra digitar, como uma planilha nova do
    Excel — os campos que saíram da grade (Tipo Material, Grupo Mercadorias, snapshot) foram
    pro painel de Detalhes.
- Status: cadastro completo (cabeçalho + checklist em tabela even + grid de materiais de 10
  colunas com 300 linhas prontas, as 3 faixas em largura total, com logo real);
  `ordem_cliente[]`, `lista_tecnica[]` e auto-cálculo do checklist a partir dos materiais
  continuam sem UI/não implementados (próximo incremento). Aguardando telas do Figma do
  usuário pra próxima rodada de ajuste visual.

## Principais adições

- **Cabeçalho em faixas + checklist editável** (`BitinDetail.jsx`, `ChecklistEditor.jsx`
  novo): réplica da aba `Template apresentação` — logo/título/BITex/Setor (dourado), Produto/
  Solicitante, Motivo/Data, e a faixa "CHECK LIST" com os 22 itens (Documento/Afeta/
  Observação), antes só visível read-only no resumo pós-envio.
- **`GET /bitins/schema/materiais`**, **`GET /bitins/schema/checklist`** e
  **`POST /bitins/parse-sap-paste`** (`backend/api/bitins.py`): 3 endpoints pequenos que
  reaproveitam lógica Python já testada (crosswalk, checklist, parser de colagem) em vez de
  duplicá-la em JavaScript.
- **`MaterialGrid.jsx`**: navegação por teclado nas 4 setas (não Tab) + Enter, colar em
  qualquer célula (bloco copiado do Excel, cria linha nova se precisar), colunas "#"/"Código"
  congeladas, 300 linhas em branco desde o início, 10 colunas visíveis por padrão
  (identificação + os 7 impactos operacionais, igual à print real) — os ~30 pares De/Novo de
  `dados_basicos` continuam disponíveis via "Colunas visíveis" ou pelo painel de Detalhes,
  cabeçalho amarelo/dourado com "Novo" em vermelho (igual ao Excel real), `<select>` de
  `impactos_operacionais` com as opções válidas do POP, e destaque de célula exata quando o
  envio falha (mesmo em linhas em branco filtradas antes de enviar, ver `compactMateriais`/
  `remapMaterialErrorIndices` em `docs/FRONTEND.md`).
- **`MaterialDetailModal.jsx`**: painel de edição por material com seções "Identificação"
  (Tipo Material, Grupo Mercadorias, snapshot — campos que saíram da grade principal),
  "Impactos operacionais" e todos os campos de `dados_basicos` num layout espaçoso (com busca)
  — atalho opcional pra revisar um material sem rolar a grade inteira.
- **Identidade visual + tema claro/escuro**: paleta da marca (Grain & Protein Technologies)
  como tokens Tailwind, cabeçalho navy com faixa de 3 cores, toggle claro/escuro (padrão
  claro, persiste no navegador), logo real (`frontend/public/logo.svg`) no cabeçalho, login e
  tela de cadastro.
- **Grade de materiais em tela inteira, sem moldura de card**: `<main>` (`Layout.jsx`) deixou
  de ter `max-w-6xl` global; a grade quebra pra fora do container centralizado do cadastro
  (`-mx-4`) e perdeu borda/cantos arredondados/padding do wrapper — encosta nas bordas reais da
  tela. Células, cabeçalho e botões de ação maiores; largura de coluna calculada por um único
  helper (antes havia dois mapas duplicados).
- **3 faixas (cabeçalho, checklist, grade) em largura total**: cabeçalho e checklist passaram
  a compartilhar o mesmo `-mx-4` de largura total que só a grade de materiais tinha, encostando
  nas bordas reais da tela.
- **Checklist como tabela even + grade de materiais como "10 colunas + 300 linhas prontas"**
  (correção de rota, v8): o checklist voltou a ser `<table>` (22 linhas parelhas, não a grade
  de cards de altura desigual da v7); a grade de materiais reduziu pra 10 colunas por padrão e
  nasce com 300 linhas em branco (`BitinDetail.jsx`, `LINHAS_INICIAIS`) — linhas em branco
  nunca chegam no backend (`hasContent`/`compactMateriais`), já que `codigo_material`/`centro`/
  `tipo_material` são obrigatórios em toda linha de `materiais[]` sem exceção.
- **RBAC visível em "Meus Bitins"**: botão "Excluir" some quando o usuário não é dono nem
  admin.
- **Busca insensível a acento** (`lib/textSearch.js`) no seletor de campos e no painel de
  Detalhes.

## Validação

- **158 testes automatizados Python** (era 147 na v0.4.0): cobrindo `build_materiais_schema`,
  `build_checklist_schema` e os 3 endpoints novos (`/schema/materiais`, `/schema/checklist`,
  `/parse-sap-paste`). Sem mudança nesta última rodada (só frontend).
- **Roteiro de 27 checagens via Playwright ad-hoc** (não faz parte da suíte automatizada),
  cobrindo login, edição básica, navegação por teclado, colunas congeladas, colar em bloco,
  importar SAP, colunas visíveis (agora testando "marcar traz a coluna de volta", já que o
  padrão inverteu pra escondido), painel de Detalhes (incluindo a nova seção "Identificação"),
  validação de envio (célula destacada tanto na grade quanto no painel) e tema claro/escuro. +
  6 checagens dedicadas ao checklist (`drive_checklist.js`), incluindo confirmar que o payload
  salvo não inclui as 300 linhas em branco. Tudo passou; zero erro de console.

## Achados durante o teste (corrigidos antes de fechar)

- **Coluna congelada sobrepondo a seguinte**: `position: sticky` em `<td>`/`<th>` não funciona
  de forma confiável com `border-collapse`; `table-layout: fixed` sozinho também não bastou
  sem uma largura total explícita na `<table>` (o navegador encolhia as colunas
  proporcionalmente, ignorando a largura declarada de cada uma). Ver `docs/FRONTEND.md`.
- **Busca sem suporte a acento**: buscar "liquido" não encontrava "Peso Líquido" (comparação
  de string literal). Corrigido normalizando os dois lados antes de comparar.
- **Rótulos de campo sem acento** ("Descricao", "Peso Liquido") no backend — corrigido com
  rótulos explícitos em `scripts/bitin_model.py`.
- Sem MongoDB real disponível neste ambiente, `POST /bitins/draft` e
  `POST /bitins/{id}/enviar` foram interceptados (mockados) na camada do navegador pra validar
  o fluxo real de erro-estruturado→célula-destacada. Os 2 endpoints novos (`/schema/materiais`,
  `/parse-sap-paste`) não dependem do Mongo e foram exercitados de verdade, sem mock.

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

- Próximo incremento: `ordem_cliente[]`, `lista_tecnica[]`, auto-cálculo do checklist a partir
  dos materiais (lógica já existe em `bitin_document.build_checklist`, só não roda ao vivo no
  formulário ainda), modo de leitura explícito para quem abre o rascunho de outra pessoa sem
  ser dono/admin, mesclar (em vez de sempre duplicar) ao colar do SAP em cima de um material já
  existente — ver `docs/FRONTEND.md`, seção "O que NÃO está nesta fatia ainda".
- Ver `CHANGELOG.md` para a lista completa e `docs/FRONTEND.md`/`docs/BACKEND.md` para
  arquitetura e decisões registradas.
