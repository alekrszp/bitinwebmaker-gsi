# Release v0.4.0 — Primeira fatia do frontend web

Release criado a partir da tag `v0.4.0`.

## Resumo

- Objetivo: sair do "só backend" e ter uma primeira interface web de verdade, validada ponta
  a ponta contra o backend real (v0.3.0), provando que a stack inteira funciona antes de
  investir no formulário completo de criação de BITin.
- Status: fatia fina funcional (login → listar → criar rascunho → enviar → visualizar) — o
  formulário ainda não cobre os campos que tornam um BITin realmente utilizável (dados
  básicos alterados, impactos operacionais, lista técnica, ordem de cliente). Backend
  inalterado nesta versão.

## Principais adições

- **`frontend/`**: React 19 + Vite + Tailwind 4 + react-router-dom + axios. Sem lib de estado
  global — Context API (`AuthContext`) é suficiente pro volume de estado de um formulário de
  BITin.
- **Componente único de criação/edição** (`BitinDetail.jsx`): evita a duplicação
  `BitinForm.jsx`/`BitinEdit.jsx` (~90% de código igual) encontrada no projeto de referência
  `GPT_Engineering_BITIN` durante a revisão que fizemos antes de começar o frontend.
- **Telas**: Login, "Meus Bitins" (abas Todos/Rascunhos/Enviados + busca por termo), criar/
  editar rascunho (cabeçalho + lista de materiais), visualização travada pós-envio (dados +
  materiais + checklist de 22 itens).
- **Rota protegida** (`RequireAuth`): sem token válido, redireciona pro login. Interceptor
  axios limpa o token guardado se a API responder `401`.

## Validação

- **Ponta a ponta com Playwright**, não só `npm run build`: login → "Meus Bitins" vazio →
  criar rascunho (cabeçalho + 1 material) → salvar → reabrir (confirma persistência) → enviar
  → número gerado (`P1/26` no teste) e tela travada com checklist. Screenshots de cada etapa
  conferidos, zero erro de console.
- 147 testes automatizados Python inalterados (nenhuma mudança no backend nesta versão).

## Achado durante o teste (não é bug, é limitação de ambiente já documentada)

Não há MongoDB real disponível neste ambiente de desenvolvimento — sem ele, qualquer ação de
`/bitins` falha com `500` (login/registro funcionam normalmente, só usam Postgres/SQLite). Pra
validar o frontend de ponta a ponta, o backend foi rodado com `mongomock-motor` no lugar do
cliente Mongo real — mesma estratégia que a suíte de testes automatizados já usa.

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

- Próximo incremento: colar do SAP, edição de `dados_basicos`/`impactos_operacionais` por
  material, `lista_tecnica[]`, `ordem_cliente[]`, RBAC visível na UI — ver `docs/FRONTEND.md`,
  seção "O que NÃO está nesta fatia ainda".
- Ver `CHANGELOG.md` para a lista completa e `docs/FRONTEND.md`/`docs/BACKEND.md` para
  arquitetura e decisões registradas.
