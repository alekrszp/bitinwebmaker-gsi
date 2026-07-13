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
- **Colar do SAP** via `POST /bitins/parse-sap-paste` (reaproveita `sap_paste_parser.py`
  testado, não reimplementa o parser em JS).
- **Edição livre até o envio**: nenhuma validação roda nas teclas/células durante o rascunho —
  só no botão "Enviar" (mesma filosofia de `bitin_lifecycle`, ver `docs/BITIN_MODEL.md`).
- **Visual clean**: sem o tema escuro/glass do projeto irmão — Tailwind neutro, consistente com
  o resto do frontend.

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
  De/Para (colunas escolhidas pelo usuário) e `impactos_operacionais` (Alt/Est/Esp/LP/Pré/OC/OF
  com as opções válidas do POP) — salva com `POST /bitins/draft`.
- Reabrir rascunho: confirma que o conteúdo persistiu.
- Colar do SAP: linhas coladas viram materiais novos no grid via `POST /bitins/parse-sap-paste`.
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
- **Colar do SAP sempre cria linhas novas** — não tenta casar/mesclar com um material já
  existente no grid (mesmo código+centro colado duas vezes vira duas linhas) — o engenheiro
  precisa remover a duplicata manualmente se colar a mesma linha de novo.
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
