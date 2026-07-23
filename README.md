# bitinwebmaker-gsi

[![CI](https://github.com/alekrszp/bitinwebmaker-gsi/actions/workflows/ci.yml/badge.svg)](https://github.com/alekrszp/bitinwebmaker-gsi/actions/workflows/ci.yml)

Sistema de criação e gestão de BITin (Boletim de Informações Técnicas Internas) — substitui
de vez o fluxo que era feito em Excel/VBA (`Novo_template_BITin_V2 TESTE.xlsm`). Cobre o
ciclo completo: o engenheiro cria e envia o BITin pela web, o setor Cadastro recebe e decide
se precisa de revisão de roteiro, o setor Processos revisa quando precisa, e o PDF final fica
disponível pra registro externo — nenhuma etapa depende mais de e-mail/Excel manual.

## Documentação principal

- `requirements.md` — como a colaboração neste projeto funciona (leia antes de mexer em código).
- `docs/BITIN_MODEL.md` — modelo de dados do BITin, regras de negócio, ciclo de vida completo
  (rascunho → enviado → roteamento Cadastro/Processos → PDF final).
- `docs/BACKEND.md` — arquitetura da API (`backend/`), RBAC, endpoints.
- `docs/DEPLOY.md` — deploy do sistema interno via Docker Compose (Postgres + MongoDB +
  backend + frontend auto-hospedados, substituindo o MongoDB Atlas usado até a v0.12.0),
  stacks separadas de teste e produção.
- `docs/FRONTEND.md` — arquitetura do frontend web (`frontend/`), telas e decisões de UI.
- `sap-agent/README.md` — agente SAP local opcional (Windows), arquitetura, empacotamento e
  mapeamento de campos.
- `docs/VBA_EXPORT_MAPPING.md` — mapeamento de colunas do fluxo real `Módulo1`/`Módulo2`
  (referência histórica do motor de export, ainda válida).
- `docs/VBA_MIGRATION_GUIDE.md` — o que foi portado do VBA original módulo a módulo.
- `docs/README_HANDOFF.md` — histórico do PoC original (`v0.1.0`), documento congelado.
- `docs/CHANGELOG.md` — notas de todas as versões.
- `docs/releases/RELEASE_vX.Y.Z.md` — corpo de cada release publicada no GitHub (documentos
  congelados, um por versão).

## O sistema hoje

**Backend** (`backend/`, FastAPI): autenticação própria (JWT, RBAC por `permission_level`),
CRUD de BITin com ciclo de vida completo (rascunho/enviado/roteamento), gestão de usuários e
Subgrupos, geração de PDF, persistência em Postgres (usuários/sequência de números) + MongoDB
(conteúdo do BITin).

**Frontend** (`frontend/`, React + TypeScript + Vite): login, shell autenticado (sidebar +
topbar + Home), "Meus Bitins" (listagem escopada por permissão), edição completa de um BITin
numa única tela (aba BITin — cadastro de material, ZBPP009 e Lista Técnica deixaram de ser
páginas separadas em 2026-07-23), Gestão de usuários (admin), e a fila do setor Cadastro
(`/cadastro`) que substitui o e-mail manual que existia no processo original.

**Agente SAP local** (`sap-agent/`, opcional): aplicativo Windows que roda no PC do engenheiro
e fala com o SAP GUI via SAP GUI Scripting (COM). Com o agente instalado e ativo, uma aba
"Automação" aparece na edição do BITin para buscar/validar dados direto no SAP; sem o agente,
o engenheiro preenche tudo manualmente na mesma tela — nunca é uma tela paralela. Ver
`sap-agent/README.md`.

**Modelo de permissões** (2ª revisão, 2026-07-20): `Usuario.permission_level` é só o RANK — 77
Individual, 88 Gestor, 99 Admin — cruzado com `Usuario.setor` (`"cadastro"`/`"processos"`/
`"engenharia"`), que controla acesso de verdade. Cadastro recebe todo BITin enviado e decide se
precisa de roteiro; Processos revisa quando precisa (única exceção a "enviado é travado pra
sempre"); Admin vê tudo. Subgrupo (Proteína Animal/Armazenagem de Grãos) só existe pra
Engenharia. Detalhes completos em `docs/BACKEND.md`.

## Uso rápido (motor Python — `scripts/`)

1. Gerar o export fiel do fluxo real `Plan1` (`ZBPP009`) -> `Plan2` -> `Plan3` (`Formulário
   Winshuttle`). `Módulo1` (sync) e `Módulo2` (export) são subcomandos separados, porque na
   vida real o engenheiro preenche as colunas "... Novo" de `Plan2` entre um passo e outro:

   ```powershell
   # sync: atualiza os valores atuais de Plan2 a partir de Plan1/ZBPP009
   .venv/Scripts/python.exe scripts/vba_port_export.py sync "examples/vba_original/Novo_template_BITin_V2 TESTE.xlsm" --out-xlsx plan2_sync.xlsx

   # export: lê Plan2 (com as colunas "Novo" já preenchidas pelo engenheiro) e gera o export Winshuttle
   .venv/Scripts/python.exe scripts/vba_port_export.py export "examples/vba_original/Novo_template_BITin_V2 TESTE.xlsm" --out plan3_export.csv --audit-report reports/vba_port_audit.txt
   ```

   Veja `docs/VBA_EXPORT_MAPPING.md` para o mapeamento completo de colunas e o padrão "atual
   vs. Novo".

2. Validar um BITin (JSON, ver `docs/BITIN_MODEL.md`) e gerar a aba `Plan2` real:

   ```powershell
   .venv/Scripts/python.exe scripts/bitin_model.py meu_bitin.json --out-xlsx plan2_gerado.xlsx
   ```

3. Gerar o export de lista técnica (CS02/BOM):

   ```powershell
   .venv/Scripts/python.exe scripts/lista_tecnica_export.py meu_bitin.json --out-csv lista_tecnica.csv
   ```

4. Rodar a suíte de testes (322 testes cobrindo motor Python + backend + fluxo de ponta a
   ponta):

   ```powershell
   .venv/Scripts/python.exe -m unittest discover -s tests
   ```

## Backend (API)

`backend/` expõe uma API FastAPI em cima da lógica de `scripts/` — validação real, ciclo de
vida completo do BITin (rascunho → enviado → roteamento Cadastro/Processos), persistência
(Postgres + MongoDB). Ver `docs/BACKEND.md` para arquitetura completa e decisões.

```powershell
.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
.venv/Scripts/python.exe -m uvicorn backend.main:app --reload
```

Schema do Postgres é versionado por **Alembic** (`alembic.ini`, `migrations/`) — não é mais
uma pendência bloqueada, já em uso desde as migrações de RBAC/Subgrupo.

**Autenticação é parte deste mesmo backend** (`backend/auth/`, mesmo processo/Postgres) —
todo endpoint de `/bitins`, `/users` (exceto `/users/me` de quem já tem token) e `/subgrupos`
(exceto `GET`, público) exige `Authorization: Bearer <token>` obtido via `POST /auth/login`. O
primeiro usuário registrado (`POST /auth/register`) vira admin automaticamente (bootstrap); os
demais nascem como usuário comum. `SECRET_KEY` (`.env` deste backend) precisa ser trocada por
um valor real fora de dev local. Ver `docs/BACKEND.md`, seção "Autenticação", pro design
completo (RBAC, reforço de dono do rascunho). Sem Postgres/MongoDB configurados em `.env`, a
API sobe mas as operações de banco falham ao serem chamadas — ver `docs/BACKEND.md` pra como
os testes automatizados rodam sem bancos reais (SQLite + mongomock-motor).

## Frontend (web)

`frontend/` é a interface web que substitui o Excel/VBA pro engenheiro — React 19 +
TypeScript + Vite + Tailwind + react-router-dom, sem lib de estado global. Ver
`docs/FRONTEND.md` para arquitetura completa e o histórico de decisões de cada tela.

Telas hoje: Login, Home (resumo pessoal ou da fila do setor + recentes), Meus Bitins
(listagem escopada por permissão), edição completa de BITin numa única tela (aba BITin —
cadastro de material do zero, colar do SAP, checklist com sugestão automática, validação de
regras de negócio no envio; aba "Automação" some/aparece conforme o Agente SAP local está
conectado ou não), Configurações (conta própria + aba "Bitins Concluídos" pra admin), Gestão
de usuários (super-admin), Painel geral (Gestor/Admin — todo BITin visível, Status x Etapa,
sem ações), fila do setor Cadastro (`/cadastro` — decide se precisa de revisão de roteiro,
conclui e manda pro Windchill) e fila do setor Processos (`/processos` — revisa roteiro).

### Agente SAP local (`sap-agent/`)

Aplicativo Windows opcional, instalado pelo próprio engenheiro (botão de download dentro da
tela de edição de BITin quando o agente não está detectado). Roda em segundo plano (bandeja
do Windows), com uma janela própria de 3 abas — Leia-me, BITin (ativar/desativar, usuário
identificado) e Configurações (abrir com o Windows, local de instalação) — que serve **só**
para status/configuração, nunca para comandos. Os comandos (buscar material, validar código
no SAP) ficam no sistema web, na aba "Automação", que só aparece com o agente conectado — o
sistema web já tem toda a validação/auth que a janela do agente não tem. O agente expõe uma
API HTTP local (`127.0.0.1`) que fala com o SAP GUI via SAP GUI Scripting (COM); o frontend
detecta a conexão por polling (`useAgenteSapConectado`, ~4s + recheck ao focar a aba) e mostra
um badge verde/vermelho na barra inferior da edição de BITin. Ver `sap-agent/README.md` para
arquitetura completa, empacotamento (PyInstaller) e mapeamento de campos.

```powershell
cd frontend
npm install
npm run typecheck   # tsc -b --noEmit
npm run test        # vitest run
npm run dev
```

## Release manual

Releases são criadas manualmente no GitHub, usando `docs/releases/RELEASE_vX.Y.Z.md` como corpo de
cada release. O processo não é automatizado — a publicação é feita pelo GitHub web interface.

- v0.13.0 — agente SAP local opcional (`sap-agent/`, integração com SAP GUI Scripting),
  ZBPP009 e Lista Técnica deixam de ser páginas separadas (tudo na aba BITin + aba Automação
  quando o agente está conectado):
  `docs/releases/RELEASE_v0.13.0.md` — <https://github.com/alekrszp/bitinwebmaker-gsi/releases/tag/v0.13.0>
- v0.12.0 — BITex de volta ao cabeçalho (com automação de checklist), hints e pop-ups
  revisados um a um, PDF com logo/paleta oficial e layout reordenado, CSV protegido contra
  injection, Subgrupo restrito à Engenharia, busca única no Painel geral, busca de campo na
  ZBPP009, validação de domínio nos campos de alteração:
  `docs/releases/RELEASE_v0.12.0.md` — <https://github.com/alekrszp/bitinwebmaker-gsi/releases/tag/v0.12.0>
- v0.11.0 — admin reseta senha de qualquer usuário ("esqueci minha senha" sem SMTP), Painel
  geral com paginação real no servidor:
  `docs/releases/RELEASE_v0.11.0.md` — <https://github.com/alekrszp/bitinwebmaker-gsi/releases/tag/v0.11.0>
- v0.10.1 — bloqueio de envio sem alteração real, confirmação antes de enviar, correção de
  bug real de perda de dados no Salvar/Importar da Lista Técnica/Códigos SAP:
  `docs/releases/RELEASE_v0.10.1.md` — <https://github.com/alekrszp/bitinwebmaker-gsi/releases/tag/v0.10.1>
- v0.10.0 — etapa final "Concluído" (Windchill, reversível só por admin), 2ª revisão do
  modelo de permissões (Cadastro/Processos viram `setor`, não mais níveis fixos), Painel
  geral, Cadastro/Processos reformulados, componentização/performance do frontend:
  `docs/releases/RELEASE_v0.10.0.md` — <https://github.com/alekrszp/bitinwebmaker-gsi/releases/tag/v0.10.0>
- v0.9.0 — fila do setor Cadastro + setor Processos (substitui o e-mail automático do VBA
  original), decisão automática de "precisa de roteiro", auditoria completa das automações do
  VBA, suíte de testes de ponta a ponta:
  `docs/releases/RELEASE_v0.9.0.md` — <https://github.com/alekrszp/bitinwebmaker-gsi/releases/tag/v0.9.0>
- v0.8.5 — reativação de usuário vira recadastro, admin "super" oculto, auditoria de
  permissões: `docs/releases/RELEASE_v0.8.5.md` — <https://github.com/alekrszp/bitinwebmaker-gsi/releases/tag/v0.8.5>
- v0.8.4 — rename Setor→Subgrupo, tela de Gestão de usuários própria, export PDF:
  `docs/releases/RELEASE_v0.8.4.md` — <https://github.com/alekrszp/bitinwebmaker-gsi/releases/tag/v0.8.4>
- v0.8.3 — checklist automática mapeada das macros VBA reais, admin exclui BITin enviado,
  Lista Técnica direto na aba BITin, modelo de permissões reformulado (Usuário/Gestor/
  Cadastro/Admin):
  `docs/releases/RELEASE_v0.8.3.md` — <https://github.com/alekrszp/bitinwebmaker-gsi/releases/tag/v0.8.3>
- v0.8.2 — MongoDB Atlas real (conteúdo de BITin passa a persistir de verdade), limpeza de
  código (componentização de `Settings.tsx`, `ruff` no backend, avisos de lint zerados):
  `docs/releases/RELEASE_v0.8.2.md` — <https://github.com/alekrszp/bitinwebmaker-gsi/releases/tag/v0.8.2>
- v0.8.1 — setores múltiplos por usuário + escopo por setor/nível em usuários e BITins
  (gestor vê só o próprio setor, admin vê o sistema inteiro):
  `docs/releases/RELEASE_v0.8.1.md` — <https://github.com/alekrszp/bitinwebmaker-gsi/releases/tag/v0.8.1>
- v0.8.0 — autenticação real (Alembic, sessões revogáveis, rate limit persistente, senha
  forte, troca de senha self-service) + reformulação das telas de BITin/ZBPP009/Lista Técnica
  (cadastro/edição completo, checklist manual) + paleta de cores oficial da marca:
  `docs/releases/RELEASE_v0.8.0.md` — <https://github.com/alekrszp/bitinwebmaker-gsi/releases/tag/v0.8.0>
- v0.7.2 — tela "Meus Bitins": listagem escopada por usuário + visualização só-leitura:
  `docs/releases/RELEASE_v0.7.2.md` — <https://github.com/alekrszp/bitinwebmaker-gsi/releases/tag/v0.7.2>
- v0.7.1 — shell autenticado: sidebar de navegação + topbar + Home de boas-vindas, seguindo o
  padrão visual do login; primeira mudança de UI desde a v0.5.0:
  `docs/releases/RELEASE_v0.7.1.md` — <https://github.com/alekrszp/bitinwebmaker-gsi/releases/tag/v0.7.1>
- v0.7.0 — CI (GitHub Actions), TypeScript no frontend inteiro, `pode_editar` no `BitinResponse`
  (RBAC/modo leitura, pronto pro backend, ainda sem UI); sem mudança de UI visível:
  `docs/releases/RELEASE_v0.7.0.md` — <https://github.com/alekrszp/bitinwebmaker-gsi/releases/tag/v0.7.0>
- v0.6.0 — auditoria de segurança/robustez do backend (SECRET_KEY, rate limiting, corrida de
  double-submit, inconsistência Postgres/Mongo) + primeira suíte de testes de frontend
  (Vitest); sem mudança de UI: `docs/releases/RELEASE_v0.6.0.md` — <https://github.com/alekrszp/bitinwebmaker-gsi/releases/tag/v0.6.0>
- v0.5.0 — autenticação consolidada + tela de login redesenhada + identidade visual/tema
  claro-escuro; a tela de cadastro/listagem de Bitins foi apagada após 8 rodadas sem chegar
  num resultado bom e foi reconstruída do zero, incrementalmente (concluído nas versões
  seguintes):
  `docs/releases/RELEASE_v0.5.0.md` — <https://github.com/alekrszp/bitinwebmaker-gsi/releases/tag/v0.5.0>
- v0.4.0 — primeira fatia do frontend web: `docs/releases/RELEASE_v0.4.0.md` — <https://github.com/alekrszp/bitinwebmaker-gsi/releases/tag/v0.4.0>
- v0.3.0 — autenticação, reforço de dono, validação de `ordem_cliente[]`: `docs/releases/RELEASE_v0.3.0.md` — <https://github.com/alekrszp/bitinwebmaker-gsi/releases/tag/v0.3.0>
- v0.2.0 — modelo de BITin, regras de negócio, ciclo de vida, backend: `docs/releases/RELEASE_v0.2.0.md` — <https://github.com/alekrszp/bitinwebmaker-gsi/releases/tag/v0.2.0>
- v0.1.0 — PoC inicial: `docs/releases/RELEASE_v0.1.0.md` — <https://github.com/alekrszp/bitinwebmaker-gsi/releases/tag/v0.1.0>

Veja também `docs/CHANGELOG.md` para as notas de release completas (inclui v0.7.2 → v0.8.0 →
v0.9.0 → v0.10.0 → v0.10.1 → v0.11.0 → v0.12.0 sem pular nenhuma).

## Arquivos principais

**Motor Python (`scripts/`)**

- `vba_port_export.py` — port fiel do fluxo real `Módulo1`+`Módulo2`+`Módulo11` (sync/export)
- `bitin_model.py` — valida o JSON do BITin e gera a aba `Plan2` real
- `bitin_business_rules.py` — regras do POP + regras gerais de consistência (portão de envio)
- `bitin_document.py` — Alt/Esp/checklist/diffs/decisão de roteiro (`Módulo4`+`Módulo10`+`Módulo13`)
- `bitin_lifecycle.py` — ciclo de vida completo: rascunho ↔ enviado ↔ roteamento Cadastro/Processos
- `bitin_view.py` — modelo de visualização/resumo do BITin
- `bitin_pdf.py` — geração do PDF final (registro externo)
- `lista_tecnica_export.py` — export de lista técnica (CS02/BOM), automação nova (nunca existiu em VBA)
- `sap_paste_parser.py` — parser do texto colado do SAP (TAB-delimited)
- `csv_safety.py` — sanitização contra CSV/formula injection
- `bitin_errors.py` — formato de erro estruturado (`{field, code, message}`)

**Config (`config/`)**: `vba_mapping.json`, `bitin_document_mapping.json`, `lista_tecnica_mapping.json`

**Backend (`backend/`)**: API FastAPI (ver seção acima e `docs/BACKEND.md`)
- `api/bitins.py`, `api/users.py`, `api/subgrupos.py` — endpoints
- `auth/` — autenticação unificada (models, hash/JWT, dependências de permissão, rotas de
  registro/login)

**Frontend (`frontend/`)**: interface web (ver seção acima e `docs/FRONTEND.md`)

**Agente SAP local (`sap-agent/`)**: aplicativo Windows opcional (ver seção acima e
`sap-agent/README.md`)

**Documentação (`docs/`)**: `BITIN_MODEL.md`, `VBA_EXPORT_MAPPING.md`, `VBA_MIGRATION_GUIDE.md`, `BACKEND.md`, `FRONTEND.md`, `CHANGELOG.md`

**Arquivos de exemplo/dados reais (`examples/`)**: `examples/vba_original/` guarda o material
do fluxo VBA original — `Novo_template_BITin_V2 TESTE.xlsm` (template), `exported_winshuttle.csv`
(referência), `bitin teste.xlsm`, `bitin teste 2.xlsm`, `POP_ENG_7 3 7_002.pdf`; usados de
verdade por `tests/test_vba_port_export.py`/`test_winshuttle_export.py` — não remover.
`examples/bitins_reais_auditoria/` guarda 4 BITins reais (`*.xlsm`) usados só como referência
pra auditar as automações do VBA (não usados por nenhum teste automatizado).

**PoC legado (`scripts/legacy_poc/`)**: scripts e saídas do PoC leve original (v0.1.0), superados pelo motor atual — mantidos como histórico documentado, não usar para trabalho novo.

## Dependências

O motor principal (`scripts/`, exceto `legacy_poc/`) só precisa de `pandas`/`openpyxl`:

```powershell
.venv/Scripts/python.exe -m pip install pandas openpyxl
.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
```

`oletools`/`msoffcrypto-tool`/`numpy` só são usados por `scripts/legacy_poc/extract_vba.py`
(arqueologia do `.xlsm` original, um passo único já feito) — não são necessários pra rodar o
sistema hoje.

## CI (adicionado em 2026-07-14)

`.github/workflows/ci.yml` roda em todo push/PR pra `main`: suíte Python (`unittest discover`)
e suíte de frontend (`typecheck` + `lint` + `test` + `build`). Sem serviço de Postgres/MongoDB
no workflow: os testes automatizados já usam SQLite + mongomock-motor (ver "Rodando
localmente" em `docs/BACKEND.md`), não precisam de banco real pra rodar.

## Próximo passo

Ler `docs/BITIN_MODEL.md` (modelo de dados, regras e ciclo de vida completo), `docs/BACKEND.md`
(API) e `docs/FRONTEND.md` (interface web) para a visão completa do sistema atual.
`requirements.md`, seção 5, mantém o backlog vivo do que ainda falta/está bloqueado.
`docs/README_HANDOFF.md` guarda o histórico do PoC original (v0.1.0), documento congelado.
