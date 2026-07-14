# Release v0.7.2 — "Meus Bitins": listagem escopada por usuário + visualização só-leitura

Release criado a partir da tag `v0.7.2`.

## Resumo

- Objetivo: primeiro pedaço de verdade da tela de Bitins desde o reset da v0.5.0 — listagem
  "Meus Bitins" (nome dado pelo próprio escopo: cada usuário só vê os próprios BITins) e uma
  visualização só-leitura ao clicar numa linha. Escopo fechado colaborativamente com o
  Alessandro via perguntas de múltipla escolha — a primeira formulação da pergunta de "escopo"
  não ficou clara o suficiente e precisou ser reexplicada em termos mais concretos antes de
  fechar.
- Status: listagem + visualização prontas. Cadastro/edição de rascunho, grid de materiais,
  checklist e botão "+ Novo BITin" continuam fora de escopo — próximos incrementos.

## O que fecha nesta versão

- **`pages/MeusBitins.tsx`** (novo, rota `/bitins`): tabela com abas Todos/Rascunhos/Enviados
  (`GET /bitins?status=`), colunas Código/Motivo/Solicitante/Status. Motivo e Solicitante
  aparecem sempre (não só Código) porque rascunhos ainda não têm código — só é gerado no envio
  — e sem eles a linha de um rascunho ficaria em branco.
- **`pages/BitinDetail.tsx`** (novo, rota `/bitins/:mongoId`, clique na linha): visualização
  só-leitura, sem edição ainda. Reaproveita `GET /bitins/{mongo_id}/resumo`
  (`bitin_view.render_bitin_summary`) em vez de montar a lógica de diffs de campo e impactos
  operacionais de novo no frontend.
- **`GET /bitins` (backend) passou a filtrar por `criado_por`**: mudança de comportamento do
  endpoint existente, não só um filtro novo no frontend — mesma decisão de escopo "só os meus"
  já usada em `resumo-usuario`/Home, pra não vazar motivo/solicitante de BITins de outros
  usuários. Nem admins veem a listagem do sistema inteiro aqui (diferente de "Gestão de
  usuários" em Configurações, que é uma função administrativa separada).
- **Sidebar**: novo item "Meus Bitins" (`Sidebar.tsx`, array `NAV_ITEMS`), com ícone novo
  (`ListIcon` em `components/icons.tsx`).
- **`lib/types.ts`**: novo tipo `Bitin`, espelhando `BitinResponse` do backend.

## Validação

- Backend: suíte de testes 172 (3 novos — dois cobrindo o isolamento por `criado_por` em
  `resumo-usuario` já existiam da v0.7.1, mais um novo confirmando que `GET /bitins` também
  isola entre usuários, inclusive contra um admin de outro usuário).
- Frontend: `npm run typecheck`, `npx oxlint src`, `npm run test` (4/4, suíte existente do
  login, sem regressão), `npm run build` — todos limpos.
- **Sem verificação visual ao vivo com Playwright nesta rodada**: não há MongoDB real nesta
  máquina (limitação já documentada desde a Home), e as credenciais dos usuários de teste
  locais não são conhecidas por mim — foram criadas pelo próprio Alessandro via
  `POST /auth/register`, não seedadas por script. Registrado como lacuna de verificação, não
  escondido — coberto pela suíte automatizada em vez disso.

## Nota de segurança pré-existente (não uma regressão desta rodada)

`GET /bitins/{mongo_id}` e `GET /bitins/{mongo_id}/resumo` não checam dono — só
`POST /draft`, `DELETE` e `/enviar` checam, via `_require_owner_or_admin`. Isso já existia
antes desta release: leitura de um BITin específico por id é aberta a qualquer usuário
autenticado, só a escrita é restrita. A listagem "Meus Bitins" não expõe ids de outras
pessoas, mas navegar direto pra uma URL `/bitins/{id}` de outro usuário ainda funciona.
Registrado em `docs/FRONTEND.md`, não implementado nesta rodada.

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

- Próximo incremento natural: cadastro/edição de rascunho — quando existir, o botão
  "+ Novo BITin" entra em `MeusBitins.tsx` e `BitinDetail.tsx` ganha um modo de edição
  (o campo `pode_editar`, já calculado pelo backend, existe justamente pra isso).
- Ver `docs/CHANGELOG.md` para a lista completa e `docs/FRONTEND.md`/`docs/BACKEND.md` para
  arquitetura e decisões registradas.
