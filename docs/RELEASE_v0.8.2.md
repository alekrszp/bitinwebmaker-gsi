# Release v0.8.2 — MongoDB Atlas real + limpeza de código

Release criado a partir da tag `v0.8.2`.

## Resumo

- Objetivo: duas frentes — (1) configurar o MongoDB Atlas de verdade, destravando a
  persistência real do conteúdo de BITin pela primeira vez (até aqui, tudo rodava em
  `mongomock`, apagado a cada restart); (2) limpeza geral de código pedida explicitamente:
  "remova coisas inúteis, limpa ele, deixa ele 100% otimizado... deixa clean code, componetiza
  bem direitinho tudo".
- Status: as duas fecham funcionalmente, comportamento do app preservado 100% na parte de
  limpeza (é refactor puro, não muda nenhuma tela nem endpoint).

## O que fecha nesta versão

### MongoDB Atlas

- Cluster M0 (free tier) configurado, `MONGO_URL` real apontando pro Atlas via `.env`
  (gitignorado, nunca commitado).
- **Bug de conexão real corrigido**: o handshake TLS com o Atlas falhava de forma
  intermitente nesta máquina (Windows + Python 3.14 + OpenSSL 3.0.18,
  `SSL: TLSV1_ALERT_INTERNAL_ERROR`). Corrigido em `backend/db/mongodb.py` passando
  `tlsCAFile=certifi.where()` explicitamente em vez de depender do trust store do sistema
  operacional.
- Validado ao vivo, ponta a ponta: criei um BITin de teste, reiniciei o backend do zero, e o
  BITin continuou lá — persistência real confirmada (antes, com mongomock, tudo sumia a cada
  restart). BITin de teste removido depois da validação.
- **Migrations pendentes finalmente aplicadas ao banco real**: `senha_temporaria` e
  `usuario_setores` (das versões v0.8.0/v0.8.1) nunca tinham sido rodadas contra o
  `bitin_backend.db` de verdade — o código já esperava essas colunas, então **qualquer login
  estava devolvendo 500**. Corrigido nesta rodada (backup feito antes de aplicar).

### Limpeza de código (zero mudança de comportamento)

- `Settings.tsx`: 401 → 46 linhas — `TrocarSenhaForm`, `GestaoUsuarios`, `CriarUsuarioForm`
  viraram componentes próprios em `components/settings/`.
- `extrairErro` (duplicado) → `lib/errors.ts` compartilhado.
- Lógica de troca de senha (duplicada entre Settings e a tela de primeiro login) →
  `hooks/usePasswordChangeForm.ts`.
- `FormLabel`/`TextInput` novos — label e input repetidos ao pé da letra 10+ vezes em telas
  diferentes viram componentes compartilhados.
- `AuthContext`/`ThemeContext` separados em Provider + hook — zera os 2 avisos de lint que
  existiam desde sempre.
- `ruff` adicionado ao backend (primeiro linter Python do projeto), rodando em CI.

## Validação

- Backend: 205 testes, todos verdes (sem teste novo — rodada de refactor/infra).
- Frontend: `npm run typecheck`, `npx oxlint src` (**0 avisos**), `npm run test` (4/4),
  `npm run build` — todos limpos.
- Validação visual ao vivo (Playwright): login, tema, Settings inteira, restrição de admin —
  tudo funcionando depois do refactor, zero erro de console.
- MongoDB Atlas testado com criação + leitura + persistência através de restart do servidor.

## Como reproduzir

```powershell
# backend
.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
.venv/Scripts/python.exe -m alembic upgrade head
# criar backend/.env (ou .env na raiz) com MONGO_URL apontando pro seu cluster Atlas
.venv/Scripts/python.exe -m uvicorn backend.main:app --reload

# frontend (outro terminal)
cd frontend
npm install
npm run dev
```

## Notas

- O cluster Atlas é o free tier (M0) — combinado explicitamente como solução "por enquanto",
  até a decisão final de infraestrutura da empresa. Migrar depois é só trocar a `MONGO_URL`,
  nenhum código muda.
- Continuam pendentes: tela de "esqueci minha senha", decisão final de hospedagem (Atlas vs.
  infra própria da empresa).
- Ver `docs/CHANGELOG.md` para a lista completa e `docs/BACKEND.md`/`docs/FRONTEND.md` para
  arquitetura e decisões registradas.
