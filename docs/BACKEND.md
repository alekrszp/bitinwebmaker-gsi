# Backend do BITin (API)

Este documento descreve a API (`backend/`) que envolve a lógica já construída em `scripts/`
(`bitin_model`, `bitin_business_rules`, `bitin_document`, `lista_tecnica_export`,
`bitin_lifecycle`, `bitin_view`, `vba_port_export`, `sap_paste_parser`, `csv_safety`) com
persistência real e uma API HTTP, pronta pra futura interface web.

## Origem e decisões

Baseado numa análise de um backend de teste já tinha feito (FastAPI +
Postgres + MongoDB + auth desacoplada via JWT, ver `backend para teste/` na raiz — cópia
de referência do projeto `GPT_Engineering_BITIN`). Decisões registradas depois da análise:

- **Persistência**: mantemos a combinação **Postgres (metadado) + MongoDB (conteúdo)** —
  ideia boa do backend de referência. Postgres guarda só o que precisa ser único/pesquisável
  (código do BITin, status); MongoDB guarda o documento inteiro (estrutura profundamente
  aninhada e variável, forçar isso em colunas SQL rígidas seria dor de cabeça).
- **Autenticação unificada neste backend** — decisão inicial foi adiar auth pra focar na
  lógica do BITin primeiro; virou pendência real em 2026-07-10. Cogitamos rodar o
  `GPT_Engineering_authAPI` como serviço separado (processo/porta/banco próprios), mas optamos
  por trazer o auth pra dentro deste mesmo backend/processo/banco — um só `uvicorn`, um só
  Postgres, sem precisar sincronizar `SECRET_KEY` entre dois `.env` nem aceitar as pendências
  de RBAC/dono que o modelo desacoplado teria deixado em aberto (ver seção "Autenticação").
- **Número do BITin gerado pelo sistema no envio**, não digitado pelo engenheiro — mudança
  registrada em `bitin_model.py` (`REQUIRED_HEADER_FIELDS` não exige mais `bitin`, exige
  `setor` — que define o prefixo `P`/`A`).
- **O que NÃO foi copiado do backend de referência** (motivos em `docs/BITIN_MODEL.md` —
  achados da revisão): endpoint de envio sem nenhuma validação de negócio; modelo de dados
  duplicado (`atributos_alterados` legado + `alteracoes` aninhado); geração de número
  sequencial sem proteção contra corrida; script de purga sem nenhuma trava de segurança;
  isolamento de dono nos rascunhos — já implementado (ver seção "Autenticação").
- **Rotas `/bitins` do backend de referência** (`app/api/bitin_routes.py` do
  `GPT_Engineering_authAPI`): não trazidas — implementam numeração e persistência de BITin
  próprias, completamente redundantes com (e num formato de código diferente de) o sistema
  real deste repositório.

## Estrutura

```
backend/
  config.py       - Settings (pydantic-settings): DATABASE_URL, MONGO_URL, SECRET_KEY, etc.
  db/
    session.py     - engine/sessão SQLAlchemy (Postgres em produção, SQLite em teste)
    mongodb.py      - cliente Motor (MongoDB em produção, mongomock-motor em teste)
  models_sql.py    - BitinSQL (tabela `bitins`: id, codigo, prefixo, ano, sequencial,
                      mongo_document_id, criado_por, created_at, updated_at)
  bitin_number.py  - geração do número sequencial, com retry seguro contra corrida
  auth/
    models.py       - Usuario, Setor (mesmo Postgres/Base das tabelas acima)
    security.py     - hash de senha (pbkdf2_sha256), criação de JWT
    schemas.py       - pydantic: UserCreate, UserOut, Token, SectorCreate, ...
    deps.py         - get_current_user/get_current_active_user/check_permission(nível)
    routes.py       - /auth/register, /auth/login
  main.py          - app FastAPI
  api/
    bitins.py       - endpoints de BITin
    users.py        - /users/me, /users (RBAC), /users/{id}/permission (promoção)
    sectors.py      - /sectors
```

`backend/` importa direto de `scripts/` (mesmo padrão de `sys.path.insert` usado em
`tests/`) — não duplica nenhuma lógica de validação/export, só orquestra.

## Modelo de dados

**Postgres — tabela `bitins`** (só existe uma linha por BITin **enviado**, nunca por
rascunho — o status em si vive no documento Mongo, não aqui):
```
id, codigo (único, ex: "P6601/26"), prefixo (P/A), ano, sequencial,
mongo_document_id, criado_por (nullable, ver nota abaixo), created_at, updated_at
```

**`criado_por` (adicionado em 2026-07-10)**: campo nullable (a coluna aceita `None` pra manter
retrocompatibilidade com o formato antigo) com o **e-mail** do usuário autenticado que enviou
o BITin (achado da revisão do `GPT_Engineering_authAPI`: a tabela `Bitin` de referência tem
`usuario_id`/autoria e a nossa não tinha nenhum campo equivalente). Guardamos e-mail em vez de
id numérico porque agora a tabela `usuarios` mora no mesmo Postgres — não custa nada exibir um
valor legível direto, sem o frontend precisar resolver id→nome.

**Postgres — tabelas `usuarios`/`setores`** (`backend/auth/models.py`):

```text
usuarios: id, email (único), nome, hashed_password, ativo, permission_level (0/1/99),
          network_id (nullable), sector_id (nullable, FK setores), created_at
setores:  id, nome (único), descricao
```

`setores` aqui é o **departamento do usuário** (Engenharia, RH, TI, ...) — conceito diferente
do `setor` do BITin em si (`"Proteína Animal"`/`"Armazenagem de Grãos"`, que define o prefixo
`P`/`A` do número, ver `backend/bitin_number.py`). Os dois não têm relação hoje.

**MongoDB — coleção `bitin_contents`** (rascunho e enviado, documento inteiro):
o conteúdo é exatamente a estrutura de `docs/BITIN_MODEL.md` (não o modelo antigo
`atributos_alterados`/`alteracoes` duplicado do backend de referência) + campos de
armazenamento: `_id`, `sql_ref_id` (preenchido só após o envio), `titulo` (nome livre pro
rascunho antes de ter número, ideia boa do backend de referência), `criado_por` (e-mail de
quem criou o rascunho, gravado só na criação — não muda em atualizações, mesmo quando um admin
edita o rascunho de outra pessoa), `created_at`, `updated_at`.

## Endpoints

| Método | Rota | O que faz |
|---|---|---|
| POST | `/bitins/draft` | Cria ou atualiza um rascunho — **sem validação de negócio** (liberdade de edição). Se `mongo_id` vier no corpo, atualiza; senão, cria novo. |
| GET | `/bitins/{mongo_id}` | Busca um BITin (rascunho ou enviado) pelo id do Mongo. |
| GET | `/bitins` | Lista rascunhos + enviados (filtro simples por status/termo). |
| DELETE | `/bitins/{mongo_id}` | Apaga um rascunho. Recusa se já enviado. |
| POST | `/bitins/{mongo_id}/enviar` | **O ponto-chave**: chama `bitin_lifecycle.enviar_bitin` (todas as validações de uma vez). Se falhar, devolve **200 com `ok=false` e a lista de erros estruturados** (`{field, code, message}`) no corpo — não é um erro HTTP, é um resultado de validação de negócio (a chamada em si funcionou). Se passar, gera o número sequencial (com retry seguro), cria a linha no Postgres, atualiza o Mongo. |
| GET | `/bitins/{mongo_id}/resumo` | `bitin_view.render_bitin_summary` — pré-visualização/tela final. |
| GET | `/bitins/schema/materiais` | `bitin_model.build_materiais_schema` — colunas do grid de materiais (identificação, snapshot, `dados_basicos` De/Para, `impactos_operacionais` com as opções válidas do POP) derivadas do `bitin_schema_crosswalk` (`config/vba_mapping.json`) e do `valores_validos` (`config/bitin_document_mapping.json`). Adicionado em 2026-07-13 (ver "Grid de materiais dirigido por schema" abaixo). |
| POST | `/bitins/parse-sap-paste` | `sap_paste_parser.parse_sap_paste_to_materiais` — recebe o texto colado do SAP (`{"raw_text": "..."}`) e devolve `materiais[]` prontos (identificação + snapshot atual) pro frontend inserir no grid. Adicionado em 2026-07-13. |
| GET | `/bitins/schema/checklist` | `bitin_document.build_checklist_schema` — os 22 itens fixos do checklist (id + etapa, do Quadro 01 do POP), pra tela de cadastro montar a tabela de checklist editável (`ChecklistEditor.jsx`). Mesma fonte que `bitin_document.build_checklist` usa pra calcular `afeta` na tela de resumo pós-envio, só sem o cálculo em si. Adicionado em 2026-07-13. |

**Ainda não incluído nesta rodada** (próximo passo natural, não construído agora pra manter
escopo gerenciável): endpoints que geram de fato os arquivos de export (Plan2 `.xlsx`, CSV do
Winshuttle, lista técnica) a partir de um BITin já enviado.

### Grid de materiais dirigido por schema (adicionado em 2026-07-13)

Decisão registrada: o frontend do grid de materiais (ver `docs/FRONTEND.md`) **não hardcoda**
a lista de colunas (nomes de campo, rótulos, opções de enum). Isso já causou duplicação
arriscada no projeto irmão `GPT_Engineering_BITIN` (array de ~80 colunas copiado à mão no JS, a
partir do mesmo crosswalk que o backend já tinha) — qualquer mudança no crosswalk exigiria
lembrar de atualizar os dois lados, e nada acusa a divergência automaticamente. Em vez disso,
`GET /bitins/schema/materiais` devolve a lista de colunas pronta (`bitin_model.build_materiais_schema`),
e o frontend renderiza o grid a partir dela — uma fonte única de verdade.

Pelo mesmo motivo, `POST /bitins/parse-sap-paste` reaproveita `sap_paste_parser.py` (já testado)
em vez de reimplementar o parser de colagem em JavaScript.

**Auth/users/sectors** (ver seção "Autenticação" abaixo para o design completo):

| Método | Rota | O que faz |
|---|---|---|
| POST | `/auth/register` | Público. Cria usuário, sempre `permission_level=0` (exceto bootstrap do primeiro usuário). |
| POST | `/auth/login` | Público (`OAuth2PasswordRequestForm`: `username`=e-mail, `password`). Devolve `Token`. |
| GET | `/users/me` | Perfil do usuário autenticado. |
| GET | `/users` | Lista usuários — exige `permission_level >= 1` (gestor/admin). |
| GET | `/users/{id}` | Busca usuário por id — exige `permission_level >= 1`. |
| PATCH | `/users/{id}/permission` | Promove/rebaixa — exige `permission_level >= 99` (admin). |
| GET | `/sectors` | Público (form de registro precisa listar antes do login existir). |
| POST | `/sectors` | Cria setor — exige admin. |

## Autenticação (adicionado em 2026-07-10, unificado no mesmo dia)

Decisão registrada com o responsável do projeto: autenticação é parte deste mesmo backend —
mesmo processo FastAPI, mesmo Postgres (tabelas `usuarios`/`setores` ao lado de `bitins`), uma
porta só. Chegamos a desenhar uma versão com o `GPT_Engineering_authAPI` rodando como serviço
separado (JWT validado por segredo compartilhado entre dois `.env`), mas isso deixava RBAC e
"reforço de dono" pendentes (exigiriam uma chamada de rede síncrona a cada requisição pra
buscar o perfil completo do usuário) — unificar resolve isso de graça, com uma consulta local.

**Boas ideias trazidas da revisão do `GPT_Engineering_authAPI`** (código adaptado, não copiado
1:1 — ver `backend/auth/`):

- Hash de senha com `pbkdf2_sha256` (não `bcrypt` — bug conhecido do bcrypt no Windows, e este
  backend também roda em Windows).
- Cadeia de dependências `get_current_user` → `get_current_active_user` → `check_permission(nível)`
  (`backend/auth/deps.py`).
- RBAC simples de 3 níveis: `0` usuário comum, `1` gestor, `99` admin (`Usuario.permission_level`).
- Tabela `Setor` (departamento do usuário — Engenharia, RH, TI, ... — **não confundir** com o
  `setor` do BITin em si, que define o prefixo `P`/`A`).

**Corrigido em relação ao `GPT_Engineering_authAPI`** (achados da revisão, ver histórico do
chat/commit para a lista completa):

- **Vulnerabilidade de escalonamento de privilégio**: lá, `POST /auth/register` aceitava
  `permission_level` direto do corpo da requisição — qualquer um podia se registrar como admin.
  Aqui, `UserCreate` (`backend/auth/schemas.py`) nem tem esse campo — o nível é sempre decidido
  no servidor (`backend/auth/routes.py`): **`0` por padrão**, exceto o **primeiro usuário já
  registrado no sistema**, que vira admin automaticamente (bootstrap — sem isso, o sistema
  nasceria sem nenhum admin capaz de promover ninguém). Promoções depois disso só via
  `PATCH /users/{id}/permission`, protegido por `check_permission(99)`.
- **CORS inválido**: `allow_origins=["*"]` + `allow_credentials=True` (combinação insegura,
  rejeitada por navegadores em vários cenários) — trocado por uma lista explícita de origens
  em `backend/main.py` (hoje só as portas padrão do Vite em dev; adicionar o domínio real
  quando houver).
- **Rotas `/bitins` próprias do serviço de referência** (numeração e persistência
  redundantes/incompatíveis com este sistema) — não trazidas, ver seção "Origem e decisões".

**O que passou a funcionar, agora que auth é local** (não dava pra fazer no modelo desacoplado
sem uma chamada de rede por requisição):

- Todos os endpoints de `/bitins`, `/users`, `/sectors` (exceto `POST /auth/*` e
  `GET /sectors`, públicos) exigem `Authorization: Bearer <token>` — sem token válido, `401`.
- `criado_por` (Postgres e Mongo) é preenchido com o **e-mail** do usuário autenticado.
- **Reforço de dono**: só quem criou o rascunho (ou um admin, `permission_level >= 99`) pode
  editar (`POST /bitins/draft` com `mongo_id`) ou excluir (`DELETE /bitins/{mongo_id}`) —
  qualquer outro usuário autenticado recebe `403`. Um admin editando o rascunho de outra
  pessoa **não muda** o `criado_por` original.

**Ainda não implementado** (não é mais bloqueado por decisão de arquitetura, só não construído
ainda): RBAC nos próprios endpoints de `/bitins` (hoje qualquer usuário autenticado pode
criar/ver/listar — só editar/excluir rascunho de outra pessoa é restrito); vínculo entre
`Usuario.sector_id` e o `setor` do BITin (ex.: engenheiro só vê BITins do próprio setor) — não
pedido ainda, registrado como possibilidade futura.

**Rodando localmente**:

```powershell
.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
.venv/Scripts/python.exe -m uvicorn backend.main:app --reload
```

`SECRET_KEY` (`backend/.env`) precisa ser uma chave real em qualquer ambiente que não seja dev
local — o default em `backend/config.py` existe só pra não quebrar testes/SQLite sem `.env`.

## Corrida no número sequencial (correção do achado no backend de referência)

`bitin_number.py` tenta gerar+inserir o próximo número numa transação; se a constraint
`unique` do `codigo` disparar (dois envios simultâneos calculando o mesmo próximo número), o
`IntegrityError` é capturado e a geração é **retentada** (até N vezes) em vez de estourar um
erro 500 pro usuário.

## Rodando localmente (sem Postgres/MongoDB reais)

Não há Postgres nem MongoDB rodando neste ambiente (nem Docker disponível). Os testes
automatizados (`tests/test_backend_*.py`) usam:
- **SQLite** (arquivo temporário) no lugar do Postgres — mesmo código SQLAlchemy funciona.
- **`mongomock-motor`** no lugar do MongoDB real — mock em memória, compatível com a API do
  Motor.

Pra rodar de verdade (Postgres/MongoDB reais), configurar `.env` com `DATABASE_URL` e
`MONGO_URL` apontando pra instâncias reais (ou `docker-compose`, a fazer depois).
