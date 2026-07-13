# Release v0.5.0 — Grid de materiais em formato planilha (estilo Excel real)

Release criado a partir da tag `v0.5.0`.

## Resumo

- Objetivo: a fatia anterior (v0.4.0) só cobria identificação de material — não dava pra
  montar um BITin realmente útil (sem `dados_basicos` De/Para, sem `impactos_operacionais`,
  sem colar do SAP). Esta versão fecha esse gap com um grid de materiais em formato planilha
  de verdade — navegação por teclado, colar de blocos, colunas congeladas — inspirado
  diretamente na planilha Excel real que o time já usa (`ZBPP009 + ALTERACAO`), não só numa
  ideia genérica de "grid".
- Passou por 4 rodadas de feedback direto até chegar nesse ponto: v1 (colunas dirigidas por
  schema, sem navegação alguma) → v2 (navegação/colar estilo Excel, mas "muito ruim" pra
  usar) → v3 (setas completas, painel de Detalhes, e fidelidade visual com o Excel real do
  BITin) → v4 (todos os ~30 campos visíveis por padrão — "a tela deve ser um excel enorme" —
  identidade visual da marca e tema claro/escuro).
- Status: grid de materiais completo (identificação + snapshot + `dados_basicos` +
  `impactos_operacionais`); `ordem_cliente[]`, `lista_tecnica[]` e checklist editável
  continuam sem UI (próximo incremento).

## Principais adições

- **`GET /bitins/schema/materiais`** e **`POST /bitins/parse-sap-paste`**
  (`backend/api/bitins.py`, `scripts/bitin_model.build_materiais_schema`): 2 endpoints novos,
  pequenos, que reaproveitam lógica Python já testada (crosswalk, parser de colagem) em vez de
  duplicá-la em JavaScript.
- **`MaterialGrid.jsx`**: navegação por teclado nas 4 setas (não Tab) + Enter, colar em
  qualquer célula (bloco copiado do Excel, cria linha nova se precisar), colunas "#"/"Código"
  congeladas, todos os ~30 pares De/Novo de `dados_basicos` visíveis por padrão (rótulos fiéis
  ao texto do Plan2 real) com cabeçalho "Novo" destacado em laranja da marca, `<select>` de
  `impactos_operacionais` com as opções válidas do POP, e destaque de célula exata quando o
  envio falha.
- **`MaterialDetailModal.jsx`**: painel de edição por material com todos os campos de
  `dados_basicos` num layout espaçoso (com busca) — atalho opcional pra revisar um material
  sem rolar a grade inteira.
- **Identidade visual + tema claro/escuro**: paleta da marca (Grain & Protein Technologies)
  como tokens Tailwind, cabeçalho navy com faixa de 3 cores, toggle claro/escuro (padrão
  claro, persiste no navegador). Logo real ainda pendente (wordmark em texto por enquanto).
- **RBAC visível em "Meus Bitins"**: botão "Excluir" some quando o usuário não é dono nem
  admin.
- **Busca insensível a acento** (`lib/textSearch.js`) no seletor de campos e no painel de
  Detalhes.

## Validação

- **154 testes automatizados Python** (era 147 na v0.4.0): 8 novos cobrindo
  `build_materiais_schema` e os 2 endpoints novos.
- **Roteiro de 25 checagens via Playwright ad-hoc** (não faz parte da suíte automatizada),
  cobrindo login, edição básica, navegação por teclado, colunas congeladas, colar em bloco,
  importar SAP, colunas visíveis, painel de Detalhes, validação de envio (célula destacada
  tanto na grade quanto no painel, dependendo de onde o campo com erro está) e tema
  claro/escuro (padrão, toggle, persistência). 25/25 passaram nesta rodada; zero erro de
  console.

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

- Próximo incremento: `ordem_cliente[]`, `lista_tecnica[]`, checklist editável, modo de
  leitura explícito para quem abre o rascunho de outra pessoa sem ser dono/admin, mesclar (em
  vez de sempre duplicar) ao colar do SAP em cima de um material já existente — ver
  `docs/FRONTEND.md`, seção "O que NÃO está nesta fatia ainda".
- Ver `CHANGELOG.md` para a lista completa e `docs/FRONTEND.md`/`docs/BACKEND.md` para
  arquitetura e decisões registradas.
