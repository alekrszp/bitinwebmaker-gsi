# Release v0.10.0 — Windchill, revisão de permissões, Painel geral, componentização e navegação

Release criado a partir da tag `v0.10.0`.

## Resumo

Fecha o fluxo pós-envio até o fim: BITin agora tem uma etapa final de "Concluído" (enviado
pro Windchill), reversível só por admin. O modelo de permissões passou por uma 2ª revisão —
Cadastro/Processos deixaram de ser níveis numéricos fixos e viraram um campo `setor` cruzado
com o rank (Individual/Gestor/Admin), o que abriu espaço pra Gestor de qualquer setor ganhar
um painel de acompanhamento (`Painel geral`, admin vê o sistema inteiro). Cadastro e Processos
ganharam telas próprias reformuladas (antes reaproveitavam telas genéricas), com a mesma
linguagem de Status x Etapa usada em todo o sistema. Fecha com uma revisão geral de
performance/arquitetura (componentização de tabelas/toolbars repetidas, hook de "voltar"
correto por tela) e textos de ajuda ("?") em cada tela principal.

## O que fecha nesta versão

### Etapa final "Concluído" (Windchill)

- **`enviar_windchill(bitin)`** (`scripts/bitin_lifecycle.py`) — Cadastro confirma que baixou
  o PDF final e mandou pro Windchill; `windchill_enviado=True`. Não muda o campo `status` bruto
  (continua `"enviado"` — todo filtro do sistema depende disso); "Concluído" é um Status
  DERIVADO, calculado por `lib/bitinEtapa.ts::statusDoBitin`.
- **Botão único "Baixar PDF"** em `CadastroPage.tsx`: baixa o PDF E marca como concluído na
  mesma ação, com confirmação antes (ação sai da fila normal do Cadastro).
- **`reverter_windchill(bitin)`** + `POST /bitins/{id}/reverter-windchill` — admin-only
  (`check_permission(NIVEL_ADMIN)`, não `check_setor`) — desfaz o passo acima, volta o BITin
  pra "Pendência de envio".
- **Aba "Bitins Concluídos" em Configurações** (`Settings.tsx`, admin-only): lista travada de
  todo BITin com Status="Concluído", com botão "Voltar bitin" por linha. Saiu de
  `CadastroPage.tsx`/`Sidebar.tsx`, onde vivia antes.

### Revisão do modelo de permissões (2ª revisão)

- `Usuario.permission_level` virou só o RANK (`77` Individual, `88` Gestor, `99` Admin);
  Cadastro/Processos deixaram de ser níveis numéricos (`88`/`89`) e viraram
  `Usuario.setor: "cadastro" | "processos" | "engenharia"`.
- `eh_do_setor`/`check_setor` (backend) e `ehDoSetor`/`isCadastro`/`isProcessos` (frontend)
  substituem a checagem antiga por nível fixo — Gestor tem a mesma fila de trabalho do
  Individual do mesmo setor, só ganha o Painel geral a mais.
- **Gestão de usuários** restrita à conta super-admin fixa (`CONTAS_SUPER_ADMIN`); qualquer
  outra conta `99` continua vendo o sistema inteiro, mas não gerencia usuário.
- Ver tabela completa em `docs/BACKEND.md`, seção "Revisão do modelo de permissões".

### Painel geral

- **`PainelGeral.tsx`** (rota `/painel-geral`, Gestor ou Admin): visão de leitura de todos os
  BITins visíveis pro usuário — quem está com cada um e em que etapa, sem ações. Filtros de
  Setor/Usuário/**Status**/**Etapa** (independentes) + busca + export CSV.
- **`lib/bitinEtapa.ts`** (novo, fonte única): `statusDoBitin`/`etapaDoBitin` — Status
  (Rascunho/Enviado/Concluído) é o estado geral; Etapa (Recebido/Com Processos/Aguardando
  cadastro/Pendência de envio) só existe pra Status=Enviado. Painel geral, Cadastro e
  Processos usam o mesmo vocabulário, pra nunca divergir entre telas.
- **`GET /bitins/resumo-painel`** (`$facet`, um round-trip só) — substitui até 7 chamadas
  paralelas que `Home.tsx` fazia antes só pra contar `.length` no cliente.

### Cadastro e Processos reformulados

- **`CadastroPage.tsx`**: etapas "Aguardando cadastro"/"Pendência de envio" (Etapa-only,
  Status="Enviado" sempre — Concluído saiu daqui, ver acima).
- **`ProcessosPage.tsx`** (novo, substitui o reaproveitamento de `MeusBitins.tsx`): etapas
  "Pendente"/"Revisado". BITins que nunca precisaram de roteiro
  (`sem_necessidade_roteiro=True`, ex.: só troca de fornecedor `-/F`) são excluídos das duas
  etapas — Processos nunca teve contato real com eles, não deviam aparecer como se tivessem
  "passado" por lá. Esse filtro (`sem_necessidade_roteiro`) também ganhou suporte em
  `GET /bitins` e no `$facet` de `resumo-painel`.
- Botão "Concluir processamento" em `BitinDetail.tsx` renomeado pra só "Concluir".

### Revisão de arquitetura/performance (frontend)

- **`components/bitin/BitinTableSection.tsx`** + `bitinColunas.tsx` — tabela de listagem de
  BITins compartilhada, substitui 4 blocos de `<table>` quase idênticos em `CadastroPage.tsx`,
  `ProcessosPage.tsx`, `MeusBitins.tsx` e a aba "Bitins Concluídos" de `Settings.tsx`.
- **`components/bitin/FiltroEtapaToolbar.tsx`** — toolbar de filtro (select de etapa + busca)
  compartilhada entre `CadastroPage.tsx`/`ProcessosPage.tsx`.
- **`hooks/useDebouncedValue.ts`** — substitui 3 cópias idênticas do debounce de busca.
- **`hooks/useVoltar.ts`** — "Voltar" em `BitinDetail.tsx` agora volta pra tela de onde o
  usuário realmente veio (`navigate(-1)`, com fallback pra `/bitins` só quando não há
  histórico em app) — antes era sempre um alvo fixo (`/bitins`), perdendo o filtro de quem
  vinha de Cadastro/Processos/Painel geral/Configurações.
- `Card.tsx` passa a aceitar título em JSX (não só texto), pra caber um ícone de ajuda no
  título de um card.

### Ajuda ("?") em cada tela principal

- `AjudaPopover` (já existia em BITin/ZBPP009/Lista Técnica) ganhou uma instância nova em
  Cadastro, Processos, Meus Bitins, Painel geral, Início, Gestão de usuários e na aba "Bitins
  Concluídos" — cada uma explica só o fluxo e os filtros/botões daquela tela específica.

## Validação

- `python -m ruff check backend scripts` — sem apontamentos.
- `python -m unittest discover -s tests` — 350 testes, verde (cobre `reverter_windchill`,
  filtro `sem_necessidade_roteiro`, permissões da 2ª revisão).
- `npx tsc -b --noEmit`, `npm run lint` (oxlint), `npm run build` — sem erros/avisos.

## Notas

Sem mudança de schema Mongo que exija migração retroativa — os campos novos
(`bitin_cadastrado`, `windchill_enviado`, `sem_necessidade_roteiro`) usam o mesmo padrão
"ausente = ainda não" (`$ne: True`) dos campos de roteamento anteriores.
`scripts/migrar_setores_2026_07_20.py`/`scripts/resetar_usuarios_setores_2026_07_20.py` são
scripts one-off usados pra migrar as contas de exemplo pro modelo `setor` novo — não fazem
parte do fluxo normal da aplicação.
