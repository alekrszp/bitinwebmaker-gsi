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

**Lint (2026-07-16)**: `ruff` — primeiro linter Python do projeto (`backend/requirements.txt`).
Config em `pyproject.toml` na raiz (`E`/`F`/`I`: pycodestyle erros + pyflakes + import sorting,
conjunto conservador de propósito). Roda em CI (`.github/workflows/ci.yml`) via
`ruff check backend scripts`.

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
usuarios:         id, email (único), nome, hashed_password, ativo, permission_level (66/77/88/99,
                  ver seção "Autenticação" -- era 0/1/99 antes de 2026-07-16),
                  network_id (nullable), created_at
setores:          id, nome (único), descricao
usuario_setores:  usuario_id (FK usuarios), setor_id (FK setores) -- PK composta
```

`setores` aqui é o **departamento do usuário** (Engenharia, RH, TI, ...) — conceito diferente
do `setor` do BITin em si (`"Proteína Animal"`/`"Armazenagem de Grãos"`, que define o prefixo
`P`/`A` do número, ver `backend/bitin_number.py`). Os dois não têm relação hoje.

**Many-to-many desde 2026-07-15** (era `sector_id`, FK única nullable em `usuarios`): pedido
explícito do usuário, "um usuário poder ser tanto armazenagem tanto quanto proteina" — um
usuário agora pode pertencer a mais de um `Setor` ao mesmo tempo. `Usuario.setores`
(`relationship` via a tabela de associação pura `usuario_setores`, sem colunas extras) substitui
a antiga coluna. `UserOut.sector_ids: list[int]` expõe os ids pro frontend; migração
`dd1208ae65a6` faz o backfill de `sector_id` -> `usuario_setores` e derruba a coluna antiga
(SQLite exige `batch_alter_table` pra isso).

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
| GET | `/bitins` | Lista rascunhos + enviados, escopado por **nível de permissão** (alimenta `MeusBitins.tsx`), com filtro adicional por status/termo. Escopo revisto em 2026-07-15 (pedido explícito: "lista de usuários e bitins de todo mundo, com filtragem de solicitante"): usuário comum (0) só os próprios (`criado_por`, como sempre); gestor (1) os de qualquer um que compartilhe ao menos um `Setor` com ele (mesma consulta de `_usuarios_do_mesmo_setor_query`, sem setor nenhum cai pra "só os meus", nunca "todo mundo"); admin (99) o **sistema inteiro, sem filtro nenhum** — antes de 2026-07-15 até admin ficava preso a "só os meus" aqui, decisão que o usuário reverteu explicitamente ("Admin vê tudo"). |
| DELETE | `/bitins/{mongo_id}` | Apaga um rascunho (dono/admin). Um BITin já enviado só pode ser apagado por admin (`permission_level >= 99`, 2026-07-16) — nesse caso também apaga a linha `BitinSQL` correspondente (mesma ressalva de "sem transação real cobrindo os 2 bancos" do fluxo de `/enviar`, ver seção abaixo). |
| POST | `/bitins/{mongo_id}/enviar` | **O ponto-chave**: chama `bitin_lifecycle.enviar_bitin` (todas as validações de uma vez). Se falhar, devolve **200 com `ok=false` e a lista de erros estruturados** (`{field, code, message}`) no corpo — não é um erro HTTP, é um resultado de validação de negócio (a chamada em si funcionou). Se passar, gera o número sequencial (com retry seguro), cria a linha no Postgres, atualiza o Mongo. |
| GET | `/bitins/{mongo_id}/resumo` | `bitin_view.render_bitin_summary` — pré-visualização/tela final. |
| GET | `/bitins/schema/materiais` | `bitin_model.build_materiais_schema` — colunas do grid de materiais (identificação, `dados_basicos` com os 30 campos reais da ZBPP009, `impactos_operacionais` com as opções válidas do POP, `impactos_condicionais`) derivadas do `bitin_schema_crosswalk` (`config/vba_mapping.json`) e do `valores_validos` (`config/bitin_document_mapping.json`). Adicionado em 2026-07-13, sem o bloco `snapshot` inventado (removido em 2026-07-15 — ver "Grid de materiais dirigido por schema" abaixo). |
| POST | `/bitins/parse-sap-paste` | `sap_paste_parser.parse_sap_paste_to_materiais` — recebe o texto colado do SAP (`{"raw_text": "..."}`) e devolve `materiais[]` prontos (identificação + `dados_basicos_atual`, o "de" dos 30 campos, via `plan1_dados_basicos_columns`) pro frontend inserir na tabela de Códigos SAP. Adicionado em 2026-07-13, expandido em 2026-07-15 pra cobrir todos os campos (antes só extraía um recorte de 6). |
| GET | `/bitins/schema/checklist` | `bitin_document.build_checklist_schema` — os 22 itens fixos do checklist (id + etapa, do Quadro 01 do POP), pra tela de cadastro montar a tabela de checklist editável (`ChecklistEditor.jsx`). Mesma fonte que `bitin_document.build_checklist` usa pra calcular `afeta` na tela de resumo pós-envio, só sem o cálculo em si. Adicionado em 2026-07-13. |
| GET | `/bitins/resumo-usuario` | `{rascunhos, enviados}` — contagem de BITins do **próprio usuário logado** (`count_documents` filtrado por `criado_por`), alimenta os cartões de resumo da Home (`docs/FRONTEND.md`). Escopado por usuário de propósito ("só os meus", não o sistema inteiro) — decisão registrada com o usuário. Adicionado em 2026-07-14. |

**Ainda não incluído nesta rodada** (próximo passo natural, não construído agora pra manter
escopo gerenciável): endpoints que geram de fato os arquivos de export (Plan2 `.xlsx`, CSV do
Winshuttle, lista técnica) a partir de um BITin já enviado.

**Ordem de declaração das rotas importa**: `/bitins/resumo-usuario` (e as demais rotas
estáticas — `/schema/materiais`, `/schema/checklist`, `/parse-sap-paste`) precisam estar
declaradas **antes** de `/bitins/{mongo_id}` no código — o FastAPI casa rotas na ordem em que
são registradas, então se `/{mongo_id}` viesse primeiro, ele "engoliria" `resumo-usuario` como
se fosse um `mongo_id` literal. `count_documents` funciona igual no `mongomock-motor` usado
nos testes e no `motor` real — confirmado ao implementar, não assumido.

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

**Tela Códigos SAP idêntica à ZBPP009 (2026-07-15)**: `schema.dados_basicos` cobre os 30 campos
reais do crosswalk (não um recorte) — a tela `CodigosSapPage.tsx` monta uma coluna por campo
(igual à aba ZBPP009 do documento original) pra colar/digitar o snapshot "atual" de cada
material. O bloco `snapshot` que existia antes (`grupo_mercadorias_atual`/`tem_desenho`/
`desenho_aprovado`/`ncm_aprovado_fiscal`) foi removido do schema exposto — eram campos
inventados fora do JSON canônico do BITin, não usados por nenhuma regra de negócio real.
`config/vba_mapping.json::plan1_dados_basicos_columns` mapeia cada campo de `dados_basicos`
pra sua coluna na grade Plan1 (ZBPP009, 36 colunas) — derivado casando `plan1_to_plan2.rules`
pelo `plan2_col` (a coluna "atual" de cada par atual/novo é sempre `plan2_col - 1`, já que os
pares ficam sempre em colunas adjacentes).

**Auth/users/sectors** (ver seção "Autenticação" abaixo para o design completo):

| Método | Rota | O que faz |
|---|---|---|
| POST | `/auth/register` | Público. Cria usuário, sempre `permission_level=NIVEL_USUARIO` (66, exceto bootstrap do primeiro usuário). |
| POST | `/auth/login` | Público (`OAuth2PasswordRequestForm`: `username`=e-mail, `password`). Devolve `Token`. Grava `TentativaLogin`, atualiza `ultimo_acesso`, cria `SessaoUsuario` no sucesso. |
| POST | `/auth/logout` | Autenticado. Revoga a `SessaoUsuario` do token atual (ver "Tabelas de sessão e auditoria de login" abaixo) — chamadas seguintes com o mesmo token viram `401`. |
| POST | `/auth/change-password` | Autenticado. Exige `senha_atual` correta; `senha_nova` passa pela mesma validação de força de `UserCreate.password`. Revoga as OUTRAS sessões ativas do usuário (mantém a atual válida) — ver "Troca de senha self-service" abaixo. Também zera `Usuario.senha_temporaria` no sucesso (ver "Cadastro de usuário só por admin" abaixo) — mesma rota atende tanto troca voluntária quanto o primeiro login forçado. |
| GET | `/users/me` | Perfil do usuário autenticado. Inclui `senha_temporaria`. |
| POST | `/users` | Cadastro de usuário — exige `NIVEL_ADMIN` (99). Ver "Cadastro de usuário só por admin" abaixo. Usuário/Gestor/Cadastro (66/77/88) exigem ao menos 1 setor no corpo, 400 se faltar. Se o e-mail já pertence a um usuário **excluído** (`ativo=False`), REATIVA a mesma linha (novos dados, nova senha temporária) em vez de rejeitar com "e-mail já cadastrado" (2026-07-17, pedido explícito) — email é UNIQUE no banco, então recadastro tem que reaproveitar a linha, não inserir outra. Só bloqueia de verdade se o e-mail já é de alguém ATIVO. |
| GET | `/users` | Lista usuários — exige `NIVEL_ADMIN` (99) **só** (2026-07-16, revogado de Gestor: "em hipótese alguma 88, 77, 66 podem ver permissões e usuários que existem. gestão de usuários é só admin"; linha corrigida em 2026-07-17, achado de auditoria — dizia "Gestor ou Admin" com escopo por setor, desatualizado desde a revogação). Devolve ativos E excluídos juntos (2026-07-17, era só `ativo=True` — revertido pro filtro Ativados/Desativados de `GestaoUsuarios.tsx`); `UserOut.ativo` é quem distingue. |
| GET | `/users/{id}` | Busca usuário por id — mesmo gate de `GET /users` (Gestor/Admin). Mesmo escopo por setor: gestor pedindo um id fora do(s) setor(es) dele recebe **404** (não 403 — não vaza que o id existe). |
| PATCH | `/users/{id}/permission` | Promove/rebaixa — exige `NIVEL_ADMIN` (99). Ninguém mexe na própria permissão por esta rota (400). Rejeita com 400 se o ALVO já é admin (99) — ninguém pode rebaixar um admin, nem outro admin, **exceto o super-admin oculto** (ver "Super-admin oculto" abaixo). |
| DELETE | `/users/{id}` | "Excluir" usuário (2026-07-17) — exige `NIVEL_ADMIN` (99). **Soft-delete**: marca `Usuario.ativo=False`, não apaga a linha; login e todo request autenticado já checam `ativo`, então a conta para de funcionar na hora. Rejeita com 400 se o alvo é o próprio chamador (sempre, sem exceção) ou já é admin (99) — **exceto o super-admin oculto** pra excluir outro admin (ver abaixo). |
| POST | `/users/{id}/reativar` | Reverte o soft-delete — exige `NIVEL_ADMIN` (99). Corpo: `{email}` (pode repetir o e-mail antigo ou trocar — 400 se já em uso por OUTRO usuário). Sempre gera senha temporária nova (`senha_temporaria=True`, devolvida uma única vez em `senha_temporaria_gerada`, mesmo padrão de `POST /users`) — 2026-07-17, pedido explícito: "quando eu reativo aparece de novo com uma nova senha do 0 e novo email". Sem confirmação de senha do admin (não é criação de conta nem escalonamento de privilégio). |
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
- RBAC (`Usuario.permission_level`) -- ver "Revisão do modelo de permissões" abaixo pro esquema
  atual de 4 níveis (era 3 níveis 0/1/99 até 2026-07-15).
- Tabela `Setor` (departamento do usuário — Engenharia, RH, TI, ... — **não confundir** com o
  `setor` do BITin em si, que define o prefixo `P`/`A`).

**Corrigido em relação ao `GPT_Engineering_authAPI`** (achados da revisão, ver histórico do
chat/commit para a lista completa):

- **Vulnerabilidade de escalonamento de privilégio**: lá, `POST /auth/register` aceitava
  `permission_level` direto do corpo da requisição — qualquer um podia se registrar como admin.
  Aqui, `UserCreate` (`backend/auth/schemas.py`) nem tem esse campo — o nível é sempre decidido
  no servidor (`backend/auth/routes.py`): **`NIVEL_USUARIO` (66) por padrão**, exceto o
  **primeiro usuário já registrado no sistema**, que vira admin automaticamente (bootstrap —
  sem isso, o sistema nasceria sem nenhum admin capaz de promover ninguém). Promoções depois
  disso só via `PATCH /users/{id}/permission`, protegido por `check_permission(NIVEL_ADMIN)`.
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

**`pode_editar` no `BitinResponse`** (adicionado em 2026-07-14, achado de auditoria "RBAC
incompleto"): campo calculado por requisição (não vem do Mongo) — `false` quando quem está
vendo não é dono nem admin, ou quando o BITin já foi enviado (nem o dono pode mais editar
depois disso). Objetivo: quando a tela de Bitins for reconstruída, o frontend pode abrir a
tela travada (modo leitura) de cara pra quem não pode editar, em vez de deixar editar
livremente e só descobrir o erro (`403`) ao tentar salvar. Ainda **não consumido por nenhuma
UI** (a tela de Bitins foi apagada no reset da v0.5.0, ver `docs/FRONTEND.md`) — é só o
backend já ficando pronto pra quando ela voltar. `_pode_editar()` reaproveita o mesmo critério
de `_require_owner_or_admin()`, só devolvendo bool em vez de levantar `403`.

**Ainda não implementado** (não é mais bloqueado por decisão de arquitetura, só não construído
ainda): restringir QUEM pode criar/ver/listar (hoje qualquer usuário autenticado pode; só
editar/excluir rascunho de outra pessoa é restrito, e agora também sinalizado via
`pode_editar` acima); vínculo entre `Usuario.sector_id` e o `setor` do BITin (ex.: engenheiro
só vê BITins do próprio setor) — não pedido ainda, registrado como possibilidade futura.

**Limite de tentativas de login** (`backend/auth/rate_limit.py`, adicionado em 2026-07-13,
achado de auditoria): antes, `/auth/login` não tinha limite nenhum — força bruta contra uma
senha fraca só era limitada pelo custo do hash `pbkdf2`. Agora, 5 tentativas erradas pro mesmo
e-mail em 5 minutos bloqueiam novas tentativas com `429` (mesmo com a senha certa) até a janela
passar ou até um login bem-sucedido "limpar" o contador. **Lastreado no banco desde
2026-07-15** (antes era em memória, ver abaixo) — cada tentativa de login (sucesso ou falha)
vira uma linha em `tentativas_login`, e o limite conta as falhas depois do último sucesso pro
mesmo e-mail (em vez de apagar linhas, o que perderia o histórico/auditoria). Isso substituiu
o dict em memória do processo, que tinha uma limitação conhecida: não sobrevivia a um restart
nem funcionava com múltiplos workers/réplicas sem um store compartilhado (Redis etc.) — agora
sobrevive a restart de graça, e o "múltiplos workers" já funciona também, já que todos batem
no mesmo Postgres/SQLite. `backend/auth/rate_limit.py` manteve os mesmos nomes de função
(`excedeu_limite`, agora com um `db: Session` a mais) pra minimizar o blast radius em quem já
chamava esse módulo.

### Tabelas de sessão e auditoria de login (adicionado em 2026-07-15)

Duas tabelas novas em `backend/auth/models.py`, além dos campos novos em `Usuario`
(`numero_eng` — só relevante pra contas de engenheiro —, `email_verificado` — sempre `False`
no registro, sem fluxo de verificação construído ainda —, `updated_at`, `ultimo_acesso`):

```text
sessoes_usuario: id, usuario_id (FK usuarios), token (hash sha256 do JWT, único),
                 ip_address, user_agent, expires_at, created_at, revogada
tentativas_login: id, email, ip_address, user_agent, sucesso, data_tentativa
```

**Por que hash do token, não o token cru**: mesmo raciocínio de nunca guardar senha em texto
puro — um vazamento da tabela `sessoes_usuario` não pode virar bearer tokens válidos direto
(`backend/auth/security.py::hash_token`, sha256 simples; o "segredo" aqui já é um JWT de alta
entropia assinado com `SECRET_KEY`, não uma senha de usuário sujeita a força bruta).

**Logout de verdade (`POST /auth/logout`, autenticado)**: antes não existia — JWT sozinho é
stateless e válido até expirar naturalmente, então não tinha como invalidar um token antes da
hora. Agora marca a `SessaoUsuario` correspondente (achada pelo hash do token atual) como
`revogada=True`. `backend/auth/deps.py::get_current_user` passou a checar, depois de validar
a assinatura/expiração do JWT, se existe uma `SessaoUsuario` pra aquele hash e, se existir, se
ela não está revogada nem expirada — só então o usuário é considerado autenticado.

**Compatibilidade com tokens mintados direto em teste**: `create_access_token()` sozinho (sem
passar por `/auth/login`) não cria nenhuma `SessaoUsuario`. A checagem em `get_current_user`
só bloqueia quando EXISTE uma sessão pro hash do token E ela está revogada/expirada — token
sem sessão nenhuma (caso de testes que chamam `create_access_token` direto, ver
`tests/test_backend_auth.py::_create_user` e `tests/test_backend_bitins.py`) continua
funcionando normalmente. Só quem passa pelo fluxo real de login ganha uma sessão revogável —
é a garantia que importa (logout funciona pra usuário real), sem forçar todo teste a simular
login completo.

**`login` (`backend/auth/routes.py`)** agora recebe `request: Request` pra capturar
`ip_address`/`user_agent`, grava uma `TentativaLogin` em toda tentativa (sucesso ou falha),
atualiza `Usuario.ultimo_acesso` e cria a `SessaoUsuario` no sucesso, com `expires_at` igual
ao do próprio JWT (`ACCESS_TOKEN_EXPIRE_MINUTES`).

### Política de senha forte + troca de senha self-service (adicionado em 2026-07-15)

Antes, `POST /auth/register` aceitava qualquer senha (mesmo "123"), e não existia jeito
nenhum de um usuário trocar a própria senha sem edição direta no banco. Pedido explícito do
usuário: "vamos fazer uma autenticação melhor, segurança nas senhas etc.".

- **`backend/auth/security.py::validate_password_strength`**: mínimo de 8 caracteres e pelo
  menos 3 dos 4 tipos de caractere (maiúscula, minúscula, número, especial). Reaproveitado
  (não duplicado) tanto por `UserCreate.password` (registro) quanto por
  `ChangePasswordRequest.senha_nova` (troca de senha) — um validator Pydantic só, chamado dos
  dois lugares.
- **Não é retroativa**: a validação só roda contra senha em texto puro submetida a
  registro/troca — nunca contra hashes já salvos. Contas criadas direto no banco antes dessa
  regra existir (ex.: usuários de exemplo com senha `123`, propositalmente fracos pra teste)
  continuam autenticando normalmente; só cadastros/trocas novos são obrigados a senha forte.
- **`POST /auth/change-password`** (`ChangePasswordRequest`: `senha_atual`, `senha_nova`):
  400 se `senha_atual` não bate (`verify_password`); se bate, troca o hash e revoga todas as
  OUTRAS sessões ativas do usuário (mesmo padrão de revogação do logout) — troca de senha em
  outro dispositivo/navegador desloga esses, mas não a sessão que acabou de fazer a própria
  troca.

### Revisão do modelo de permissões (2026-07-16)

Substituído o esquema antigo de 3 níveis (`0`/`1`/`99`) por 4 níveis explícitos, nomeados em
`backend/auth/deps.py` (`NIVEL_USUARIO`, `NIVEL_GESTOR`, `NIVEL_CADASTRO`, `NIVEL_ADMIN`) e
usados em todo o backend em vez de números mágicos. Os valores em si (66/77/88/99) foram
escolhidos pelo usuário e **não formam uma hierarquia numérica limpa** — em particular, `88`
(Cadastro) fica numericamente "entre" Gestor (77) e Admin (99), mas não herda os privilégios de
nenhum dos dois. Por isso `check_permission` mudou de assinatura: em vez de um único threshold
(`level: int`, checava `user.permission_level < level`), agora recebe um conjunto explícito de
níveis permitidos — `check_permission(*allowed_levels: int)`, checando
`user.permission_level in allowed_levels`. Cada rota passa o conjunto exato de quem pode
chamá-la (ex.: `check_permission(NIVEL_GESTOR, NIVEL_ADMIN)` em `GET /users`).

**Tabela de permissões completa** — os 4 valores de `Usuario.permission_level` que existem hoje,
o que cada um pode ver/fazer, e as restrições especiais de cada um. O número em si **não é uma
escala contínua** (ver acima: 88 fica numericamente "entre" 77 e 99 mas não herda privilégio de
nenhum dos dois) — esta tabela é a fonte de verdade de o que cada valor faz, não a ordem
numérica:

| Nível | Nome interno | BITins que vê | Gestão de usuários | Subgrupo obrigatório? | Restrições especiais |
|---|---|---|---|---|---|
| **66** | `NIVEL_USUARIO` (era `0`) | Só os próprios (qualquer status). | Não acessa `GET /users`. | Sim — 400 se `subgrupo_ids` vier vazio. | Nenhuma. |
| **77** | `NIVEL_GESTOR` (era `1`) | Rascunho + enviado de quem compartilha ao menos 1 Subgrupo com ele, além dos próprios. | Não acessa `GET /users` (revogado em 2026-07-16 — só Admin gerencia usuários hoje). | Sim — 400 se vazio. | Nenhuma. |
| **88** | `NIVEL_CADASTRO` (novo, 2026-07-16) | Só os **enviados** (não rascunho) de colegas de mesmo Subgrupo, além dos próprios em qualquer status. Cria/edita/envia os próprios normalmente. | Não acessa `GET /users`. | Sim — 400 se vazio. | Nenhuma. |
| **99** | `NIVEL_ADMIN` | Todos, sem escopo de Subgrupo. | Único nível com acesso — cria, lista, promove/rebaixa, exclui (soft-delete) e reativa usuário. | Não — único nível que pode ficar sem Subgrupo. | Nunca pode ser rebaixado (`PATCH .../permission` rejeita com 400 se o ALVO já é 99) nem excluído (`DELETE /users/{id}` idem) — nem por outro admin, **exceto o super-admin oculto** (ver seção abaixo). Sem rota de despromoção pública pra quem não é o super-admin (só edição direta no banco). |

### Super-admin oculto (2026-07-17)

Pedido explícito do usuário: "me coloca como admin TOTAL, eu posso fazer o que eu quiser,
remover admins, tirar permissão etc, mas isso vai ser uma permissão escondida no front que só
existe no back". `backend/auth/deps.py::CONTAS_SUPER_ADMIN` (hoje só
`alessandro.pereiradarosafilho@grainproteintech.com`) + `eh_super_admin(user)` — checagem de
e-mail contra esse set, usada em `update_user_permission` e `delete_user`
(`backend/api/users.py`) pra pular a proteção "admin não mexe em admin".

- **De propósito não existe NENHUM sinal disso no frontend** — nem campo em `UserOut`, nem
  lógica condicional no bundle JS. Um check client-side seria visível no DevTools/bundle,
  o que destruiria o "escondido"; a única forma de exercer esse privilégio é chamando a API
  direto (não tem botão na UI pra rebaixar/excluir outro admin, pra ninguém).
- **Não é bypass de autoproteção**: mesmo essa conta continua sem poder alterar a própria
  permissão (`update_user_permission` agora rejeita com 400 se `user.id == current_user.id`,
  independente de quem é) nem se auto-excluir (`delete_user`, checagem já existia). Só a
  proteção contra mexer em **outro** admin tem bypass.
- Cobertura de teste: `tests/test_backend_auth.py`, testes
  `test_super_admin_pode_rebaixar_outro_admin` /
  `test_super_admin_nao_pode_alterar_o_proprio_nivel` /
  `test_super_admin_pode_excluir_outro_admin` /
  `test_super_admin_nao_pode_se_auto_excluir`.

**Setor obrigatório para 66/77/88**: `AdminUserCreate` (`POST /users`) agora valida que
`sector_ids` tem ao menos 1 item quando `permission_level` é 66, 77 ou 88 — 400 se faltar
(`backend/api/users.py::create_user_by_admin`, mesma "voz" de erro de `_resolve_setores`).
Admin (99) é o único nível que pode ficar sem setor nenhum.

**Migração de dados dos usuários existentes**: `permission_level` é uma coluna `Integer` simples
— não precisou de migração de *schema*, só de *dados* pros usuários já cadastrados no esquema
antigo. `scripts/migrar_niveis_permissao.py` remapeia `0→66` e `1→77` (`99` fica como está) via
`UPDATE`, dry-run por padrão (mesmo padrão de segurança de `backend/purge_db.py`):

```bash
.venv/Scripts/python.exe scripts/migrar_niveis_permissao.py            # dry-run
.venv/Scripts/python.exe scripts/migrar_niveis_permissao.py --confirm  # aplica de verdade
```

### Cadastro de usuário só por admin (adicionado em 2026-07-15)

Pedido explícito do usuário: "tela de cadastro de usuário SÓ PARA ADMIN para não ter que
cadastrar no banco". Antes, a única forma de criar uma conta era `POST /auth/register` (auto-
atendimento, sempre `permission_level=0`) ou edição direta no banco.

- **`POST /users`** (`AdminUserCreate`: `email`, `nome`, `numero_eng?`, `sector_ids?` (lista,
  2026-07-15 — era `sector_id` único), `permission_level`) — exige `check_permission(99)`. Ao
  contrário de `UserCreate`, aqui
  `permission_level` VEM do corpo de propósito: não é a mesma vulnerabilidade de
  escalonamento de privilégio documentada no registro aberto, porque só quem já é admin passa
  por `check_permission(99)`.
- Não recebe senha nenhuma no corpo — gerada no servidor por
  `backend/auth/security.py::generate_temp_password` (12 caracteres, garante 1 de cada classe
  — maiúscula/minúscula/número/especial — via `secrets.SystemRandom`, não por sorte tipo
  `secrets.token_urlsafe`). Devolvida em texto puro UMA ÚNICA VEZ no corpo de resposta
  (`AdminUserCreateOut.senha_temporaria_gerada`) pro admin repassar fora do sistema.
- `Usuario.senha_temporaria` fica `True` na criação. Login funciona normalmente com essa senha
  (`POST /auth/login` não sabe nem se importa se é temporária). `GET /users/me` expõe a flag —
  é o FRONTEND (`RequireAuth.tsx`) quem força a rota `/definir-senha` antes de liberar o resto
  do app; não há bloqueio de outros endpoints no servidor por essa flag (decisão deliberada,
  pra não precisar tocar em toda rota autenticada por um gate que é essencialmente de UI).
- `POST /auth/change-password` (mesma rota de sempre) zera `senha_temporaria=False` no
  sucesso — não existe endpoint separado pra "definir senha pela primeira vez", a senha
  temporária já é a `senha_atual` dessa primeira chamada.

**Checagem de segurança na subida** (`backend/main.py::lifespan`, adicionado em 2026-07-13,
achado de auditoria): antes, um deploy sem `.env` configurado subia silenciosamente com a
`SECRET_KEY` padrão — qualquer um forjaria um token de admin válido, sem nenhum aviso. Agora, se
`ENVIRONMENT=production` (`.env`) e `SECRET_KEY` continua no valor padrão, o app **recusa
subir** (`RuntimeError` na inicialização) em vez de subir inseguro. Dev local/testes nunca
setam `ENVIRONMENT`, então continuam funcionando sem `.env` como sempre.

**Rodando localmente**:

```powershell
.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
.venv/Scripts/python.exe -m uvicorn backend.main:app --reload
```

`SECRET_KEY` (`backend/.env`) precisa ser uma chave real em qualquer ambiente que não seja dev
local — o default em `backend/config.py` existe só pra não quebrar testes/SQLite sem `.env`, e
setar `ENVIRONMENT=production` sem trocar a `SECRET_KEY` agora impede o app de subir (ver
acima).

## Corrida no número sequencial (correção do achado no backend de referência)

`bitin_number.py` tenta gerar+inserir o próximo número numa transação; se a constraint
`unique` do `codigo` disparar (dois envios simultâneos calculando o mesmo próximo número), o
`IntegrityError` é capturado e a geração é **retentada** (até N vezes) em vez de estourar um
erro 500 pro usuário.

**O que acontecia quando as tentativas se esgotavam** (achado de auditoria, corrigido em
2026-07-13): se `gerar_e_salvar_bitin_sql` esgotasse as `MAX_RETRIES` tentativas (na prática,
quase sempre porque o mesmo `mongo_document_id` — `unique` em `BitinSQL` — já tinha sido
enviado por uma requisição concorrente enquanto esta rodava: 2 cliques em "Enviar", ou 2 abas
abertas), o `RuntimeError` subia sem tratamento e virava um `500` puro pro usuário, sem
explicação. `backend/api/bitins.py::enviar_bitin_endpoint` agora captura esse erro, distingue
os dois casos (já foi enviado por outra requisição → erro estruturado explicando isso; erro
genuíno e raro → `503` com log) e nunca mais deixa a corrida virar um 500 sem contexto.

**Sem transação real cobrindo Postgres + MongoDB** (achado de auditoria, mitigado em
2026-07-13, não eliminado): `gerar_e_salvar_bitin_sql` faz `commit()` no Postgres *antes* do
`collection.update_one` no Mongo marcar o BITin como enviado — os dois bancos não compartilham
uma transação. Se o processo morrer ou o Mongo falhar nesse meio-tempo, sobraria um `BitinSQL`
"fantasma" (número reservado) apontando pra um rascunho que nunca foi marcado como enviado.
Mitigação: se o `update_one` falhar, o `BitinSQL` recém-criado é desfeito (`db.delete` +
`db.commit`, best-effort) e o erro vira `500` explícito pro usuário tentar de novo — se até o
desfazimento falhar, fica logado como `CRITICAL` (precisa de reconciliação manual). Isso reduz
bastante a janela de inconsistência, mas não é uma solução de transação distribuída de verdade
(um saga pattern ou outbox seria o próximo passo, se a taxa de falha do Mongo justificar o
investimento).

## Migrações (Alembic, adicionado em 2026-07-15)

Antes disso, o schema SQL só existia como efeito colateral de `Base.metadata.create_all`
(`backend/main.py::lifespan`) — sem histórico de mudanças, sem jeito de aplicar uma mudança
de schema num banco com dados sem recriar tudo do zero. Agora `alembic/` (raiz do repo,
`alembic.ini` + `migrations/`) é a fonte de verdade daqui pra frente: qualquer mudança de
schema (coluna/tabela nova) vira uma migração, não só uma edição em
`backend/auth/models.py`/`backend/models_sql.py`. `migrations/env.py` lê `DATABASE_URL` de
`backend.config.settings` (mesma fonte usada pelo app em runtime) e aponta pro
`Base.metadata` real (importa `backend.auth.models` e `backend.models_sql` explicitamente,
senão autogenerate não veria as tabelas).

`Base.metadata.create_all` continua no `lifespan` como conveniência de dev (idempotente, não
conflita com um banco já migrado) — ver comentário em `backend/main.py`. Os testes
(`tests/test_backend_*.py`) não usam Alembic nem o lifespan: criam um SQLite em memória e
chamam `Base.metadata.create_all` direto por teste, então não são afetados por nada disto.

**Quatro migrações**:
- `f19fae8abd7f_baseline_usuarios_setores_bitins.py` — schema como ele já existia antes desta
  rodada (`usuarios`, `setores`, `bitins`). Existe só pra dar um ponto de partida consistente
  ao histórico Alembic; não deve ser "upgraded" contra um banco que já tem essas tabelas (ver
  abaixo).
- `6c6372519927_..._novos_.py` — `sessoes_usuario`, `tentativas_login`, e os campos novos em
  `usuarios` (`numero_eng`, `email_verificado` com `server_default='0'` — necessário porque a
  coluna é `NOT NULL` e o banco de dev já tem usuários cadastrados —, `updated_at`,
  `ultimo_acesso`).
- `11420a31c617_senha_temporaria_em_usuarios.py` — `usuarios.senha_temporaria` (`server_default
  ='0'`, mesmo motivo acima).
- `dd1208ae65a6_usuario_setores_many_to_many.py` (2026-07-15) — cria `usuario_setores`
  (PK composta `usuario_id`+`setor_id`), faz o backfill de `usuarios.sector_id` pra lá (`INSERT
  ... SELECT ... WHERE sector_id IS NOT NULL`), depois derruba `usuarios.sector_id` via
  `batch_alter_table` (primeira migração desta base a dropar coluna — SQLite não suporta `DROP
  COLUMN` direto, precisa do modo batch, que recria a tabela por trás dos panos). `downgrade()`
  é com perda de propósito se algum usuário tiver 2+ setores (só o de menor id volta pra
  `sector_id`) — documentado no próprio arquivo da migração. **Testado contra uma cópia de
  `bitin_backend.db`** antes de entrar no repo (upgrade preservou os 3 usuários reais e o
  backfill dos 2 que já tinham `sector_id`; downgrade reverteu limpo) — não aplicada ao banco
  real, precisa dos comandos abaixo rodados manualmente.

**Clone novo / banco vazio** — roda as duas migrações do zero:

```powershell
.venv/Scripts/python.exe -m alembic upgrade head
```

**Banco de dev já existente (`bitin_backend.db` na raiz do repo, já tem `usuarios`/`setores`/
`bitins` com dados)** — a migração baseline faria `CREATE TABLE usuarios` e estouraria "table
already exists" se você rodasse `upgrade head` direto nele. Em vez disso, primeiro "carimba"
o banco como já estando na revisão baseline (sem executar SQL nenhum, só grava a revisão
numa tabela de controle `alembic_version`), e só depois aplica a migração nova de verdade:

```powershell
.venv/Scripts/python.exe -m alembic stamp f19fae8abd7f
.venv/Scripts/python.exe -m alembic upgrade head
```

Testado de verdade (não só em teoria) em 2026-07-15: copiei `bitin_backend.db` (5 usuários, 2
setores, 1 bitin na época) pra um arquivo separado, rodei exatamente os dois comandos acima
nessa cópia, e confirmei que (a) as 3 tabelas antigas continuaram com as mesmas linhas
(`select count(*)` batendo antes/depois, dados legíveis), (b) as tabelas/colunas novas
apareceram, e (c) o schema final é byte-a-byte igual ao de um banco vazio rodando só
`upgrade head` (mesmo `pragma table_info`) — os dois caminhos convergem. **Nunca rode
migração nenhuma direto no `bitin_backend.db` original sem copiar primeiro.**

## Rodando localmente (sem Postgres/MongoDB reais)

Não há Postgres nem MongoDB rodando neste ambiente (nem Docker disponível). Os testes
automatizados (`tests/test_backend_*.py`) usam:
- **SQLite** (arquivo temporário) no lugar do Postgres — mesmo código SQLAlchemy funciona.
- **`mongomock-motor`** no lugar do MongoDB real — mock em memória, compatível com a API do
  Motor.

Pra rodar de verdade (Postgres/MongoDB reais), configurar `.env` com `DATABASE_URL` e
`MONGO_URL` apontando pra instâncias reais (ou `docker-compose`, a fazer depois).

**Dependências com versão fixada** (`backend/requirements.txt`, desde 2026-07-13): antes não
fixava nenhuma versão — `pip install` hoje e daqui uns meses podiam resolver pacotes
completamente diferentes. Agora fixado nas versões que rodam os 164 testes automatizados nesta
máquina (`pip freeze`), com uma exceção deliberada: `psycopg2-binary` fica sem versão fixa
porque não está instalado neste ambiente de dev (só SQLite é usado aqui) — não há uma versão
"provada" nesta máquina pra fixar com confiança; fixar assim que for instalado contra um
Postgres real.

**Logging básico** (`backend/main.py`, desde 2026-07-13): antes não existia nenhuma chamada de
`logging` no backend inteiro — uma falha em produção (Mongo fora do ar, corrida no envio, erro
de JWT) não deixava rastro nenhum além da resposta HTTP pro cliente. Configuração simples
(`logging.basicConfig`, nível `INFO`) o suficiente pra diagnosticar sem precisar de infra de
log estruturado ainda; usado nos pontos de falha tratados nesta rodada (corrida no envio,
inconsistência Postgres/Mongo).
