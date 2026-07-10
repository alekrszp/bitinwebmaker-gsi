# Backend do BITin (API)

Este documento descreve a API (`backend/`) que envolve a lógica já construída em `scripts/`
(`bitin_model`, `bitin_business_rules`, `bitin_document`, `lista_tecnica_export`,
`bitin_lifecycle`, `bitin_view`, `vba_port_export`, `sap_paste_parser`, `csv_safety`) com
persistência real e uma API HTTP, pronta pra futura interface web.

## Origem e decisões

Baseado numa análise de um backend de teste que o Alessandro já tinha feito (FastAPI +
Postgres + MongoDB + auth desacoplada via JWT, ver `backend para teste/` na raiz — cópia
de referência do projeto `GPT_Engineering_BITIN`). Decisões registradas depois da análise:

- **Persistência**: mantemos a combinação **Postgres (metadado) + MongoDB (conteúdo)** —
  ideia boa do backend de referência. Postgres guarda só o que precisa ser único/pesquisável
  (código do BITin, status); MongoDB guarda o documento inteiro (estrutura profundamente
  aninhada e variável, forçar isso em colunas SQL rígidas seria dor de cabeça).
- **Autenticação como serviço separado** (`GPT_Engineering_authAPI`) — decisão inicial foi
  adiar auth pra focar na lógica do BITin primeiro; virou pendência real em 2026-07-10 e foi
  resolvida optando por rodar o serviço de auth de referência como processo independente, não
  reimplementado dentro deste backend (ver seção "Autenticação" abaixo).
- **Número do BITin gerado pelo sistema no envio**, não digitado pelo engenheiro — mudança
  registrada em `bitin_model.py` (`REQUIRED_HEADER_FIELDS` não exige mais `bitin`, exige
  `setor` — que define o prefixo `P`/`A`).
- **O que NÃO foi copiado do backend de referência** (motivos em `docs/BITIN_MODEL.md` —
  achados da revisão): endpoint de envio sem nenhuma validação de negócio; modelo de dados
  duplicado (`atributos_alterados` legado + `alteracoes` aninhado); geração de número
  sequencial sem proteção contra corrida; script de purga sem nenhuma trava de segurança;
  isolamento de dono nos rascunhos (agora que há autenticação, `criado_por` já é rastreado,
  mas a checagem "só o dono edita/exclui" ainda não está implementada — ver seção
  "Autenticação").

## Estrutura

```
backend/
  config.py       - Settings (pydantic-settings): DATABASE_URL, MONGO_URL, etc.
  db/
    session.py     - engine/sessão SQLAlchemy (Postgres em produção, SQLite em teste)
    mongodb.py      - cliente Motor (MongoDB em produção, mongomock-motor em teste)
  models_sql.py    - BitinSQL (tabela `bitins`: id, codigo, prefixo, ano, sequencial,
                      mongo_document_id, criado_por, created_at, updated_at)
  bitin_number.py  - geração do número sequencial, com retry seguro contra corrida
  main.py          - app FastAPI
  api/
    bitins.py       - endpoints
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
retrocompatibilidade com o formato antigo, mas na prática sempre vem preenchido agora que a
autenticação está ligada — ver seção "Autenticação" abaixo) com o id do usuário autenticado
que enviou o BITin (achado da revisão do `GPT_Engineering_authAPI`: a tabela `Bitin` de
referência tem `usuario_id`/autoria e a nossa não tinha nenhum campo equivalente).

**MongoDB — coleção `bitin_contents`** (rascunho e enviado, documento inteiro):
o conteúdo é exatamente a estrutura de `docs/BITIN_MODEL.md` (não o modelo antigo
`atributos_alterados`/`alteracoes` duplicado do backend de referência) + campos de
armazenamento: `_id`, `sql_ref_id` (preenchido só após o envio), `titulo` (nome livre pro
rascunho antes de ter número, ideia boa do backend de referência), `criado_por` (id do usuário
que criou o rascunho, gravado só na criação — não muda em atualizações), `created_at`,
`updated_at`.

## Endpoints

| Método | Rota | O que faz |
|---|---|---|
| POST | `/bitins/draft` | Cria ou atualiza um rascunho — **sem validação de negócio** (liberdade de edição). Se `mongo_id` vier no corpo, atualiza; senão, cria novo. |
| GET | `/bitins/{mongo_id}` | Busca um BITin (rascunho ou enviado) pelo id do Mongo. |
| GET | `/bitins` | Lista rascunhos + enviados (filtro simples por status/termo). |
| DELETE | `/bitins/{mongo_id}` | Apaga um rascunho. Recusa se já enviado. |
| POST | `/bitins/{mongo_id}/enviar` | **O ponto-chave**: chama `bitin_lifecycle.enviar_bitin` (todas as validações de uma vez). Se falhar, devolve **200 com `ok=false` e a lista de erros estruturados** (`{field, code, message}`) no corpo — não é um erro HTTP, é um resultado de validação de negócio (a chamada em si funcionou). Se passar, gera o número sequencial (com retry seguro), cria a linha no Postgres, atualiza o Mongo. |
| GET | `/bitins/{mongo_id}/resumo` | `bitin_view.render_bitin_summary` — pré-visualização/tela final. |

**Ainda não incluído nesta rodada** (próximo passo natural, não construído agora pra manter
escopo gerenciável): endpoints que geram de fato os arquivos de export (Plan2 `.xlsx`, CSV do
Winshuttle, lista técnica) a partir de um BITin já enviado.

## Autenticação (adicionado em 2026-07-10)

Decisão registrada com o responsável do projeto: autenticação roda como **serviço separado**
(`GPT_Engineering_authAPI`, um repo/processo/porta independente — não uma cópia, o serviço em
si), não dentro deste backend. Este backend nunca teve tabela de usuários e continua sem uma —
ele só sabe validar a **assinatura e a expiração** do JWT emitido pelo serviço de auth.

**Como funciona** (`backend/auth.py`):

- `get_current_user_id(token)` decodifica o JWT localmente com `python-jose`, usando
  `AUTH_SECRET_KEY`/`AUTH_ALGORITHM` (`backend/config.py`) — **têm que ser idênticos** ao
  `SECRET_KEY`/`ALGORITHM` do `.env` do serviço de auth (dois arquivos `.env` distintos, dois
  processos distintos, mesma chave — sincronizada manualmente hoje, não há nenhum mecanismo
  automático de rotação/distribuição de chave).
- Extrai o `sub` do payload (id numérico do usuário, formato confirmado lendo
  `GPT_Engineering_authAPI/app/core/security.py`/`deps.py`) — não faz nenhuma chamada de rede
  pro serviço de auth. Suficiente pra saber "existe um usuário autenticado com esse id".
- Todos os endpoints de `/bitins` agora exigem `Authorization: Bearer <token>` — sem token
  válido, `401`.
- `criado_por` (Postgres, BITins enviados) e o campo `criado_por` do documento Mongo (todos os
  rascunhos, gravado só na criação, preservado em atualizações) passam a ser preenchidos com o
  id do usuário autenticado (`str(user_id)`), não mais `None`.

**Deliberadamente NÃO implementado ainda** (pendência registrada, não esquecida):

- **RBAC / nível de permissão**: este backend não busca o perfil completo do usuário (nome,
  `permission_level`), então não há nenhuma checagem de autorização por nível — só "está
  autenticado ou não". Buscar o perfil exigiria uma chamada HTTP a `GET {AUTH_API_URL}/users/me`
  no serviço de auth a cada requisição (ou algum cache) — evitado por ora pra não acoplar uma
  chamada de rede síncrona a toda operação.
- **Reforço de dono** ("só quem criou o rascunho pode editar/excluir"): `criado_por` já é
  rastreado (suficiente pra construir isso), mas a checagem em si não está implementada —
  qualquer usuário autenticado ainda pode editar/apagar o rascunho de qualquer outro. Fica
  pendente até decidirmos também a regra de exceção (admin?), que depende do RBAC acima.
- **Resolver id → nome legível** ("criado por Fulano" na tela): fica a cargo do frontend, que
  já precisa falar com o serviço de auth pra fazer login — não duplicado aqui.

**Rodando os dois serviços localmente**:

```powershell
# terminal 1 -- serviço de auth (porta 8001, ver seu próprio README)
cd caminho\para\GPT_Engineering_authAPI
uvicorn app.main:app --port 8001 --reload

# terminal 2 -- este backend (porta 8000)
cd bitinwebmaker-gsi
.venv/Scripts/python.exe -m uvicorn backend.main:app --reload
```

`AUTH_SECRET_KEY` (backend/.env) precisa ser igual a `SECRET_KEY` (GPT_Engineering_authAPI/.env).

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
