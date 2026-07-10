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
    pages/
      Login.jsx
      MeusBitins.jsx          - lista com abas Todos/Rascunhos/Enviados + busca
      BitinDetail.jsx         - criar/editar rascunho (form) OU visualizar enviado (resumo)
    App.jsx                   - rotas
```

## O que já funciona (validado ponta a ponta com Playwright + backend real)

- Login (`POST /auth/login`) → redireciona pra "Meus Bitins".
- Rota protegida: sem token, qualquer rota de `/bitins/*` redireciona pro login.
- "Meus Bitins": lista com abas (status) + busca por termo, criar/excluir rascunho.
- Criar rascunho: cabeçalho (setor/produto/motivo/solicitante/data) + lista de materiais
  (código/descrição/centro/tipo) — salva com `POST /bitins/draft`.
- Reabrir rascunho: confirma que o conteúdo persistiu.
- Enviar (`POST /bitins/{id}/enviar`): se falhar, mostra a lista de erros estruturados
  (`{field, code, message}`) sem travar nada; se passar, mostra o número gerado e a tela de
  resumo travada (materiais + checklist de 22 itens).

## O que NÃO está nesta fatia ainda (próximos incrementos)

- **Colar do SAP** (`sap_paste_parser.py` já existe no backend, sem uso no frontend ainda) —
  hoje os materiais são digitados um a um, não colados em bloco.
- **Edição de `dados_basicos`/`impactos_operacionais`** por material (Alt/Esp/Est/etc.) — o
  form atual só cobre os campos de identificação do material, não as alterações em si.
  Enviar um BITin sem nenhum `dados_basicos` passa na validação estrutural (nenhum desses
  campos é obrigatório), mas não é um BITin útil de verdade ainda.
- **`ordem_cliente[]` e `lista_tecnica[]`** — sem UI ainda; só o backend valida/aceita.
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
