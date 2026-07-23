# Release v0.8.0 — Autenticação real, telas de BITin completas, paleta oficial

Release criado a partir da tag `v0.8.0`.

## Resumo

- Objetivo: três frentes fechadas nesta rodada, todas pedidas diretamente pelo usuário —
  (1) autenticação de verdade (banco persistente com migrations, sessões revogáveis, senha
  forte, troca de senha), (2) cadastro/edição completo de BITin nas três telas
  (BITin/ZBPP009/Lista Técnica), (3) paleta de cores oficial da marca.
- Escopo maior que os incrementos anteriores — bump de **minor** (0.7.2 → 0.8.0) em vez de
  patch, decisão do usuário.
- Status: as três frentes fecham funcionalmente. Ficam para a próxima rodada: MongoDB real
  (hoje roda em mongomock pra dev/teste), tela de criar usuário (só via API direta hoje) e
  fluxo de "esqueci minha senha".

## O que fecha nesta versão

### Autenticação

- **Migrations Alembic** (`migrations/`, `alembic.ini`): schema deixa de ser criado só via
  `Base.metadata.create_all()` — baseline + migration versionadas, testadas contra uma cópia
  do `bitin_backend.db` real antes de aplicar no arquivo de verdade.
- **`sessoes_usuario`**: `POST /auth/logout` agora revoga o token de verdade — antes o JWT era
  stateless, sem jeito de invalidar antes de expirar.
- **`tentativas_login`**: rate limit de login persistido em banco (5 tentativas/5min),
  substitui o dict em memória que não sobrevivia a restart nem funcionava com múltiplos
  workers.
- **Política de senha forte** (`validate_password_strength`, `backend/auth/security.py`):
  mínimo 8 caracteres + 3 dos 4 tipos de caractere, aplicada em registro e troca — não
  retroativa (contas antigas continuam autenticando normalmente).
- **`POST /auth/change-password`** (novo) + formulário em Configurações → Minha conta: antes
  não existia jeito nenhum de trocar a própria senha sem edição direta no banco.
- **Normalização de e-mail** (minúsculo, registro e login): corrige um bug real que impedia
  login quando o e-mail era digitado com capitalização diferente do cadastro.

### Telas de BITin (BITin / ZBPP009 / Lista Técnica)

- Cadastro e edição completos — as três telas operam sobre o mesmo `materiais[]`, nenhuma
  depende da outra pra existir.
- **Checklist 100% manual**: tirada a sugestão automática a partir dos campos do material —
  todo item precisa de clique do engenheiro. Layout em grade responsiva (1–3 colunas).
- **ZBPP009** (renomeada de "Códigos SAP"): bug de colagem corrigido — cola em qualquer célula
  da linha, não só a primeira.
- **Lista Técnica** virou página independente estilo planilha, não depende mais de materiais
  já cadastrados.
- **Bloco de material simplificado**: "Atualizar DWG/SAT" e "Centro de custo"/"Conta razão"
  saíram, viraram itens/anotação da checklist (Nota 8 do POP). Campo "Tipo" escondido no
  bloco, mas continua visível na ZBPP009 (réplica fiel da grade real do SAP).
- **`AjudaPopover.tsx`**: ícone "?" com tutorial resumido nas três telas.
- **Excluir rascunho** direto na listagem "Meus Bitins".
- **Regras de negócio**: só bloqueiam envio as que o sistema consegue verificar sozinho (Nota
  8, Nota 10) — as que dependem de confirmação externa (Nota 2, Nota 17) viraram lembrete no
  `AjudaPopover`, já que não há campo de UI pra satisfazê-las.

### Interface

- **Configurações**: layout mais largo, e-mail longo não estoura mais o card, tabela de
  usuários rola em vez de cortar colunas.
- **Paleta de cores oficial**: tokens de marca atualizados pros valores do guia oficial
  (hex/CMYK/Pantone) — `brand-navy` `#32464d`, `brand-navy-light` `#6c8899` (novo, reaproveita
  "GPT Light Blue"), `brand-gold` `#f3d148`, `brand-green` `#79aa00`, `brand-orange` `#ea7603`.

## Validação

- Backend: suíte de testes 158 → **192**, todos verdes (`unittest discover -s tests`).
- Frontend: `npm run typecheck`, `npx oxlint src`, `npm run test` (4/4), `npm run build` —
  todos limpos.
- Migrations verificadas duas vezes: contra um SQLite vazio e contra uma **cópia** do
  `bitin_backend.db` real (nunca rodadas direto no original sem cópia primeiro) — schema final
  idêntico nos dois caminhos, dados existentes intactos.
- Validação visual ao vivo com Playwright cobrindo login, troca de senha, colagem na ZBPP009,
  checklist manual, Lista Técnica independente e paleta de cores nos dois temas.
- **Sem MongoDB real nesta máquina** (mesma limitação já documentada desde a v0.7.1) — telas
  que dependem de conteúdo de BITin foram validadas com `mongomock-motor` (testes automatizados
  + servidor de dev local), não contra um Mongo de produção.

## Como reproduzir

```powershell
# backend
.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
.venv/Scripts/python.exe -m alembic upgrade head   # banco novo
# ou, num bitin_backend.db já existente de antes desta versão:
.venv/Scripts/python.exe -m alembic stamp f19fae8abd7f
.venv/Scripts/python.exe -m alembic upgrade head
.venv/Scripts/python.exe -m uvicorn backend.main:app --reload

# frontend (outro terminal)
cd frontend
npm install
npm run dev
```

## Notas

- Próximos incrementos naturais, já discutidos com o usuário: MongoDB real (Atlas, pra
  destravar persistência de verdade do conteúdo de BITin), tela de "criar usuário" em
  Configurações (hoje só via `POST /auth/register` direto), fluxo de "esqueci minha senha".
- Ver `docs/CHANGELOG.md` para a lista completa e `docs/BACKEND.md`/`docs/FRONTEND.md` para
  arquitetura e decisões registradas.
