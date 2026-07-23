# Release v0.6.0 — Auditoria de segurança/robustez do backend + primeira suíte de testes de frontend

Release criado a partir da tag `v0.6.0`.

## Resumo

- Objetivo: depois de fechar a v0.5.0 (autenticação consolidada + tela de login redesenhada),
  o usuário pediu uma avaliação geral do projeto — coisas críticas e interessantes de
  melhorar. Uma auditoria dedicada revisou o backend (segurança, arquitetura, cobertura de
  testes) e o restante do repositório foi revisado diretamente.
- Pedido direto de fechamento: "ajuste tudo que você acha interessante de ajustar e após isso
  push, e se achar necessário um release". Esta versão aplica as correções encontradas.
- Status: **sem mudança de UI visível pro engenheiro** — tudo aqui é segurança, robustez e
  testes. A reconstrução da tela de Bitins (ver v0.5.0) continua no mesmo ponto.

## O que fecha nesta versão

**Segurança:**
- `SECRET_KEY` padrão não deixa mais o app subir com `ENVIRONMENT=production`
  (`backend/main.py::lifespan`) — antes, um deploy sem `.env` configurado subia
  silenciosamente inseguro, permitindo forjar um token de admin válido.
- Rate limiting simples no login (`backend/auth/rate_limit.py`, novo): 5 tentativas erradas
  por e-mail em 5 minutos bloqueiam com `429`. Em memória (processo único) de propósito,
  registrado como limitação conhecida.
- Busca (`termo`) escapada (`re.escape`) antes de virar `$regex` do MongoDB.

**Robustez:**
- Corrida de double-submit no envio do BITin não vaza mais como `500` puro —
  `enviar_bitin_endpoint` distingue "já enviado por uma requisição concorrente" (erro
  estruturado) de um erro genuíno e raro (`503` com log).
- Falha do MongoDB depois do commit no Postgres desfaz o número sequencial reservado
  (best-effort) em vez de deixar um registro órfão — mitiga (não elimina) a falta de uma
  transação real cobrindo os 2 bancos.
- Logging básico adicionado ao backend (não existia nenhum antes).
- Dependências do backend com versão fixada (`requirements.txt`); `psycopg2-binary`
  descomentado (deliberadamente sem versão fixa — não instalado neste ambiente de dev).

**Testes:**
- 158 → **164 testes automatizados Python**, cobrindo cada correção acima.
- **Primeira suíte de testes de frontend commitada** (Vitest + Testing Library,
  `frontend/src/pages/Login.test.jsx`, 4 testes) — até aqui toda validação de frontend vivia
  só em scripts Playwright ad-hoc fora do repo.

## Validação

- **164/164 testes Python** (`python -m unittest discover -s tests`).
- **4/4 testes de frontend** (`npm run test`).
- `npx oxlint src` sem warning novo (só os 2 pré-existentes de fast-refresh).
- `npm run build` conclui sem erro.

## Achados durante a implementação

- **`mongomock-motor` não respeita `unittest.mock.patch` na classe real do `motor`**: os
  métodos (`update_one` etc.) são gerados por um proxy dinâmico que não passa pela resolução
  normal de atributos de classe — confirmado empiricamente (o patch simplesmente não
  interceptava a chamada). O teste que simula falha do Mongo usa um wrapper de coleção
  próprio em vez de mockar a classe do motor.
- **Vitest precisou de `esbuild.jsxInject`**: sob Vitest (não sob `vite build`/`vite dev`),
  todo componente com JSX falhava com `ReferenceError: React is not defined`, mesmo com
  `@vitejs/plugin-react` registrado e o runtime automático funcionando normalmente fora de
  teste. Corrigido em `vite.config.js` sem afetar o build/dev real. Ver `docs/FRONTEND.md`.

## Como reproduzir

```powershell
# backend
.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
.venv/Scripts/python.exe -m unittest discover -s tests -q
.venv/Scripts/python.exe -m uvicorn backend.main:app --reload

# frontend (outro terminal)
cd frontend
npm install
npm run test
npm run dev
```

## Notas

- Próximo incremento: reconstrução incremental da tela de Bitins, continuando de onde a v0.5.0
  parou (ver `docs/FRONTEND.md`, seção "O que NÃO está nesta fatia ainda").
- Limitações conhecidas e registradas, não escondidas: rate limiting em memória (não
  compartilhado entre múltiplos workers/réplicas); mitigação de inconsistência Postgres/Mongo
  não é uma transação distribuída completa (saga/outbox seria o próximo passo, se justificado
  pela taxa de falha real do Mongo); sem migrations de schema (só `create_all`); sem
  Docker/CI ainda.
- Ver `CHANGELOG.md` para a lista completa e `docs/BACKEND.md`/`docs/FRONTEND.md` para
  arquitetura e decisões registradas.
