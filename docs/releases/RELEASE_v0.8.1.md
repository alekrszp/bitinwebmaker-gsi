# Release v0.8.1 — Setores múltiplos + escopo por setor/nível

Release criado a partir da tag `v0.8.1`.

## Resumo

- Objetivo: pedido direto do usuário — "se um usuário for gestor, ele consegue só ver
  listagem de usuários do setor que ele é gestor, e coloca a opção de um usuário poder ser
  tanto armazenagem tanto quanto proteina" + "lista de usuários e bitins de todo mundo, com
  filtragem de solicitante".
- Status: fecha funcionalmente. Bump de patch (0.8.0 → 0.8.1) — extensão direta do modelo de
  autenticação/permissão fechado na v0.8.0, não um escopo novo do tamanho daquela rodada.

## O que fecha nesta versão

- **Setor deixa de ser único por usuário**: `Usuario.sector_id` (FK única) virou
  many-to-many (`Usuario.setores`, tabela `usuario_setores`) — um usuário pode pertencer a
  Proteína Animal e Armazenagem de Grãos ao mesmo tempo. Migração `dd1208ae65a6` (backfill +
  drop de coluna via `batch_alter_table`, primeira migração deste repositório a remover uma
  coluna).
- **Gestor ganha escopo de verdade**: `GET /users`/`GET /users/{id}` agora só mostram usuários
  que compartilham setor com o gestor (antes viam o sistema inteiro, igual admin). Gestor sem
  setor nenhum vê lista vazia. Lookup de usuário fora do escopo devolve `404`, não `403` — não
  entrega se o id existe.
- **`GET /bitins` (listagem "Meus Bitins") também ganha escopo por nível**:
  - Usuário comum: inalterado, só os próprios.
  - Gestor: BITins de qualquer um que compartilhe setor com ele (cai pros próprios se não
    tiver setor nenhum).
  - Admin: **sistema inteiro, sem filtro** — reverte a restrição de "só os meus" que valia
    até pra admin desde a v0.7.2, por pedido explícito ("Admin vê tudo").
- **Frontend**: cadastro de usuário (Configurações → admin) troca o setor único por um grupo
  de checkboxes; tabela de usuários e "Minha conta" juntam múltiplos nomes de setor com
  vírgula; título/rótulo de busca em "Meus Bitins" se ajustam pra quem tem visão mais ampla
  (gestor/admin).

## Validação

- Backend: 196 → **205** testes, todos verdes (9 novos: múltiplos setores por usuário, escopo
  de gestor/admin em `GET /users` e `GET /bitins`, 404 pra lookup fora de escopo).
- Frontend: `npm run typecheck`, `npx oxlint src`, `npm run test` (4/4), `npm run build` —
  todos limpos.
- Migração testada contra uma **cópia** do `bitin_backend.db` real (upgrade e downgrade) —
  banco real não tocado.

## Como reproduzir

```powershell
# backend
.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
.venv/Scripts/python.exe -m alembic upgrade head
.venv/Scripts/python.exe -m uvicorn backend.main:app --reload

# frontend (outro terminal)
cd frontend
npm install
npm run dev
```

## Notas

- A migração desta versão **não foi aplicada ao `bitin_backend.db` real** — rodar
  `alembic upgrade head` quando decidido (mesma cautela de sempre: banco já stampado em
  `6c6372519927`, então é um upgrade normal de um passo só).
- Continuam pendentes, já discutidos com o usuário: MongoDB real (Atlas), fluxo de "esqueci
  minha senha".
- Ver `docs/CHANGELOG.md` para a lista completa e `docs/BACKEND.md`/`docs/FRONTEND.md` para
  arquitetura e decisões registradas.
