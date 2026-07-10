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
- **Sem autenticação por enquanto** — foco na lógica do BITin primeiro; login/permissão fica
  pra quando houver mais de um usuário testando de verdade. Todos os endpoints são abertos.
- **Número do BITin gerado pelo sistema no envio**, não digitado pelo engenheiro — mudança
  registrada em `bitin_model.py` (`REQUIRED_HEADER_FIELDS` não exige mais `bitin`, exige
  `setor` — que define o prefixo `P`/`A`).
- **O que NÃO foi copiado do backend de referência** (motivos em `docs/BITIN_MODEL.md` —
  achados da revisão): endpoint de envio sem nenhuma validação de negócio; modelo de dados
  duplicado (`atributos_alterados` legado + `alteracoes` aninhado); geração de número
  sequencial sem proteção contra corrida; script de purga sem nenhuma trava de segurança;
  nenhum isolamento de dono nos rascunhos (não avaliado aqui porque não há autenticação
  ainda — vira pendência para quando login existir).

## Estrutura

```
backend/
  config.py       - Settings (pydantic-settings): DATABASE_URL, MONGO_URL, etc.
  db/
    session.py     - engine/sessão SQLAlchemy (Postgres em produção, SQLite em teste)
    mongodb.py      - cliente Motor (MongoDB em produção, mongomock-motor em teste)
  models_sql.py    - BitinSQL (tabela `bitins`: id, codigo, prefixo, ano, sequencial,
                      status, mongo_document_id, created_at, updated_at)
  bitin_number.py  - geração do número sequencial, com retry seguro contra corrida
  main.py          - app FastAPI
  api/
    bitins.py       - endpoints
```

`backend/` importa direto de `scripts/` (mesmo padrão de `sys.path.insert` usado em
`tests/`) — não duplica nenhuma lógica de validação/export, só orquestra.

## Modelo de dados

**Postgres — tabela `bitins`** (só existe uma linha por BITin **enviado**, nunca por
rascunho):
```
id, codigo (único, ex: "P6601/26"), prefixo (P/A), ano, sequencial,
status ("enviado"), mongo_document_id, created_at, updated_at
```

**MongoDB — coleção `bitin_contents`** (rascunho e enviado, documento inteiro):
o conteúdo é exatamente a estrutura de `docs/BITIN_MODEL.md` (não o modelo antigo
`atributos_alterados`/`alteracoes` duplicado do backend de referência) + campos de
armazenamento: `_id`, `sql_ref_id` (preenchido só após o envio), `titulo` (nome livre pro
rascunho antes de ter número, ideia boa do backend de referência), `created_at`, `updated_at`.

## Endpoints

| Método | Rota | O que faz |
|---|---|---|
| POST | `/bitins/draft` | Cria ou atualiza um rascunho — **sem validação de negócio** (liberdade de edição). Se `mongo_id` vier no corpo, atualiza; senão, cria novo. |
| GET | `/bitins/{mongo_id}` | Busca um BITin (rascunho ou enviado) pelo id do Mongo. |
| GET | `/bitins` | Lista rascunhos + enviados (filtro simples por status/termo). |
| DELETE | `/bitins/{mongo_id}` | Apaga um rascunho. Recusa se já enviado. |
| POST | `/bitins/{mongo_id}/enviar` | **O ponto-chave**: chama `bitin_lifecycle.enviar_bitin` (todas as validações de uma vez). Se falhar, devolve **422 com a lista de erros estruturados** (`{field, code, message}`) direto — é exatamente pra isso que os erros estruturados foram feitos. Se passar, gera o número sequencial (com retry seguro), cria a linha no Postgres, atualiza o Mongo. |
| GET | `/bitins/{mongo_id}/resumo` | `bitin_view.render_bitin_summary` — pré-visualização/tela final. |

**Ainda não incluído nesta rodada** (próximo passo natural, não construído agora pra manter
escopo gerenciável): endpoints que geram de fato os arquivos de export (Plan2 `.xlsx`, CSV do
Winshuttle, lista técnica) a partir de um BITin já enviado.

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
