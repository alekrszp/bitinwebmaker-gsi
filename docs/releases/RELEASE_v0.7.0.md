# Release v0.7.0 — CI, TypeScript no frontend, e início de RBAC mais completo

Release criado a partir da tag `v0.7.0`.

## Resumo

- Objetivo: continuação direta da avaliação geral do projeto que fechou a v0.6.0. Desse
  pacote de itens, 4 foram escolhidos pra atacar agora: CI, rate limiting compartilhado entre
  processos, TypeScript no frontend, e RBAC mais completo (modo leitura). Os outros 4 itens
  (tela de Bitins, setup de Postgres/MongoDB reais, migrations, transação distribuída) ficam
  pra depois — os 2 últimos, inclusive, **bloqueados** até existir acesso a um Postgres real.
- **Rate limiting compartilhado não entrou nesta versão**: depende do mesmo Postgres real que
  ainda não está disponível — documentado como pendência em `requirements.md`, não
  implementado. Continua em memória (ver v0.6.0), com a limitação já registrada.
- Status: **sem mudança de UI visível pro engenheiro** de novo — CI e TypeScript são
  infraestrutura interna; `pode_editar` é um campo novo na API que nenhuma UI consome ainda
  (a tela de Bitins continua não reconstruída).

## O que fecha nesta versão

**CI** (`.github/workflows/ci.yml`, novo):
- Roda em todo push/PR pra `main`: suíte Python (`unittest discover -s tests`) e suíte de
  frontend (`typecheck` + `lint` + `test` + `build`) em jobs separados.
- Sem serviço de banco no workflow — os testes automatizados já rodam contra SQLite +
  mongomock-motor, não precisam de Postgres/MongoDB reais.
- Badge no `README.md` mostrando o status do último run.

**TypeScript no frontend** (migração completa, não incremental):
- Só 11 arquivos existiam no frontend (a tela de Bitins foi apagada no reset da v0.5.0) —
  pequeno o suficiente pra converter tudo de uma vez em vez de arrastar a dívida.
- `tsconfig.app.json`/`tsconfig.node.json` com `strict: true`, `noUnusedLocals`/
  `noUnusedParameters`. `npm run typecheck` novo (`tsc -b --noEmit`); `npm run build` agora
  typecheca antes de gerar o bundle.
- Achado técnico: `vitest/config` empacota sua própria cópia interna de `vite`, com um tipo
  `PluginOption` estruturalmente diferente do `vite` de nível superior — conflito de tipos
  entre as duas cópias aninhadas, sem afetar nada em runtime (build/dev/test já funcionavam
  antes de qualquer mudança). Contornado com um cast pontual, comentado no próprio
  `vite.config.ts`.

**RBAC — `pode_editar` no `BitinResponse`** (`backend/api/bitins.py`):
- Campo calculado por requisição — `false` quando quem está vendo não é dono nem admin, ou
  quando o BITin já foi enviado (nem o dono pode editar depois disso).
- Prepara o backend pra, quando a tela de Bitins for reconstruída, abrir em modo leitura de
  cara pra quem não pode editar — em vez de deixar editar livremente e só descobrir o erro
  (`403`) ao tentar salvar.
- Ainda não consumido por nenhuma UI (não existe tela de Bitins hoje) — é só o backend ficando
  pronto.

**`requirements.md` atualizado**:
- Nova seção "Pendências conhecidas" documentando o que está bloqueado por depender de acesso
  a um Postgres real, pra não repetir a pergunta a cada rodada.
- Nova regra explícita: ler `requirements.md` antes de começar qualquer trabalho novo.

## Validação

- 164 → **168 testes automatizados Python** (4 novos cobrindo `pode_editar`: dono, outro
  usuário, admin, BITin já enviado).
- Frontend: `npm run typecheck` limpo, `npx oxlint src` sem warning novo (só os 2
  pré-existentes de fast-refresh), 4/4 testes (Vitest), `npm run build` sem erro — tudo
  reverificado com `npm ci` (instalação limpa, mesma que o CI usa) depois da migração
  TypeScript completa.

## Como reproduzir

```powershell
# backend
.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
.venv/Scripts/python.exe -m unittest discover -s tests -q

# frontend (outro terminal)
cd frontend
npm install
npm run typecheck
npm run test
npm run build
npm run dev
```

## Notas

- Pendências conhecidas e bloqueadas por dependência externa (ver `requirements.md`, seção 5):
  rate limiting de login compartilhado entre processos, migrations de schema (Alembic),
  transação distribuída Postgres↔MongoDB — todas esperando o Alessandro passar acesso a um
  Postgres real.
- Próximo incremento: reconstrução incremental da tela de Bitins (ver `docs/FRONTEND.md`,
  "O que NÃO está nesta fatia ainda") — é quando `pode_editar` finalmente vira UI de verdade.
- Ver `CHANGELOG.md` para a lista completa e `docs/BACKEND.md`/`docs/FRONTEND.md` para
  arquitetura e decisões registradas.
