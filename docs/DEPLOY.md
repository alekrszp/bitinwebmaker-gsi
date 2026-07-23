# Deploy do sistema interno

> **Estado atual (2026-07-21)**: `docker-compose.yml` + `Dockerfile`s do backend/frontend
> prontos e validados só localmente (YAML/sintaxe, imports, testes automatizados) — **ninguém
> rodou `docker compose up` de verdade ainda**, porque o servidor interno onde isso vai morar
> não está acessível a partir daqui. Assim que tiver acesso, siga este documento passo a passo
> e ajuste o que não bater com a realidade do servidor (ele é o guia inicial, não a verdade
> definitiva — corrija aqui se algo divergir na hora H).

## Por quê

Até a v0.12.0, produção usava **MongoDB Atlas** (cloud, cluster M0 free tier, ver
`docs/releases/RELEASE_v0.8.2.md`) e o Postgres nunca chegou a rodar de verdade fora de dev (só SQLite).
Decisão do usuário (2026-07-21): sistema é **interno**, então banco de dados E aplicação
(backend/frontend) passam a rodar auto-hospedados, dentro da rede da empresa, sem depender de
nenhum serviço cloud externo. O usuário também pediu **duas versões separadas do sistema**:
uma de **teste** e uma de **produção**.

## Duas stacks independentes (teste e produção)

Mesmo `docker-compose.yml` sobe as duas — o que muda é o arquivo de env e o **nome de
projeto** (`-p`), que o Compose usa pra isolar volumes/rede automaticamente (prefixa tudo com
ele). As duas podem rodar ao mesmo tempo no mesmo host (portas diferentes, já configuradas nos
`.env.*.example`) ou em hosts separados (mesmos arquivos, só ajustar `CORS_ORIGINS`/porta pra
refletir o endereço de cada host).

| | Teste | Produção |
|---|---|---|
| Arquivo de env | `.env.test` (copiado de `.env.test.example`) | `.env.prod` (copiado de `.env.prod.example`) |
| Nome de projeto | `bitin-test` | `bitin-prod` |
| Porta do site (`WEB_PORT`) | `8081` | `80` |
| Banco Postgres | `bitin_test` | `bitin` |
| Banco Mongo | `bitin_test_db` | `bitin_db` |

**Não existe hoje uma diferenciação funcional teste/produção no código** (feature flag,
banner "você está no ambiente de teste", etc.) — a separação é só de infraestrutura (bancos e
processos completamente isolados). Se precisar de diferenciação visual/funcional depois, é um
item novo a discutir.

## Pré-requisitos no servidor

- Docker + Docker Compose (`docker compose version` — plugin, não o `docker-compose` antigo).
- Portas livres conforme a tabela acima (ou as que você escolher nos `.env.*`).
- Git, pra clonar o repositório.

## Primeira subida (repetir pra cada stack — teste primeiro, depois produção)

```powershell
git clone https://github.com/alekrszp/bitinwebmaker-gsi.git
cd bitinwebmaker-gsi

# TESTE
copy .env.test.example .env.test
# edite .env.test: troque TODAS as senhas/SECRET_KEY, confirme CORS_ORIGINS com o endereço
# real onde o navegador vai acessar
docker compose --env-file .env.test -p bitin-test up -d --build
docker compose -p bitin-test ps   # confirma os 4 serviços (postgres/mongo/backend/frontend)

# PRODUÇÃO (mesma coisa, arquivo/projeto diferentes)
copy .env.prod.example .env.prod
docker compose --env-file .env.prod -p bitin-prod up -d --build
docker compose -p bitin-prod ps
```

`--build` na primeira vez (constrói as imagens de backend/frontend a partir do Dockerfile);
`docker compose ... up -d` sozinho nas próximas, a menos que o código tenha mudado.

Os bancos usam volumes nomeados (prefixados pelo nome do projeto, ex. `bitin-test_pgdata`) que
persistem entre restarts/recriações de container — **não precisa recriar dado nenhum só por
reiniciar o servidor**. Só se apaga de verdade com `down -v` (nunca rode isso sem backup).

## Rodando as migrações contra o Postgres da stack

O container do backend NÃO roda `alembic upgrade head` sozinho na subida (decisão consciente
— rodar migração automaticamente no boot de um container é arriscado se duas réplicas subirem
ao mesmo tempo; nesse tamanho de sistema, rodar manualmente uma vez por deploy é mais simples e
mais seguro). Depois do `up -d`:

```powershell
docker compose -p bitin-test exec backend python -m alembic upgrade head
# (troque -p bitin-test por -p bitin-prod pra produção)
```

## Primeiro acesso (bootstrap do admin)

O primeiro `POST /auth/register` contra um banco de usuários vazio vira admin automaticamente
(`backend/auth/routes.py`, comentário "usuário zero") — não precisa de seed manual nem script
especial. Acesse `http://<host>:<WEB_PORT>`, registre a primeira conta (vira admin), e a partir
daí todo cadastro novo é feito **só pelo admin** via Gestão de usuários.

## Deploy de uma versão nova (depois da primeira subida)

```powershell
git pull
docker compose --env-file .env.test -p bitin-test up -d --build
docker compose -p bitin-test exec backend python -m alembic upgrade head   # se houve migração nova
```

Recomendado: valide na stack de **teste** primeiro, só depois repita os mesmos 2 comandos
trocando `.env.test`/`bitin-test` por `.env.prod`/`bitin-prod`.

## CORS (achado real ao preparar este deploy)

Antes, `backend/main.py` tinha a lista de origens permitidas **fixa no código**, só com as
portas de dev do Vite (`5173`/`5174`) — qualquer deploy real ficaria bloqueado por CORS no
navegador assim que o frontend não estivesse numa dessas portas. Corrigido: virou
`CORS_ORIGINS` (`.env`, `backend/config.py`), lida pelo backend em runtime. **Sempre confirme
que `CORS_ORIGINS` no `.env.test`/`.env.prod` bate com a URL real de onde o navegador acessa o
frontend daquela stack** — senão a tela carrega mas toda chamada à API falha silenciosamente
(erro de CORS só aparece no console do navegador, não em log do backend).

## Sem TLS entre backend e MongoDB (diferente do Atlas)

`backend/db/mongodb.py` passa `tlsCAFile=certifi.where()` incondicionalmente, mas isso só tem
efeito se TLS estiver realmente ligado (via `tls=true` na URI) — a `MONGO_URL` montada pelo
`docker-compose.yml` (`mongodb://...` simples, sem esse parâmetro) conecta em texto claro
dentro da rede do Compose, sem exigir nenhum ajuste de código. Aceitável porque o tráfego não
sai da rede interna da empresa (diferente do Atlas, que atravessava a internet).

## Backup

```powershell
# Postgres (dump lógico, restaurável com pg_restore) -- troque bitin-test por bitin-prod
docker compose -p bitin-test exec postgres pg_dump -U bitin_test -d bitin_test -F c -f /tmp/bitin.dump
docker cp $(docker compose -p bitin-test ps -q postgres):/tmp/bitin.dump ./backup-postgres-$(Get-Date -Format yyyy-MM-dd).dump

# MongoDB (dump binário, restaurável com mongorestore)
docker compose -p bitin-test exec mongo mongodump --username bitin_test --authenticationDatabase admin --archive=/tmp/bitin.mongo
docker cp $(docker compose -p bitin-test ps -q mongo):/tmp/bitin.mongo ./backup-mongo-$(Get-Date -Format yyyy-MM-dd).archive
```

Sem rotina automática de backup configurada ainda (ex. Tarefa Agendada do Windows chamando os
comandos acima todo dia) — próximo passo depois que a stack estiver validada em uso real.

## Ainda não endereçado (próximos passos)

- Rodar isso de verdade pela primeira vez (ninguém validou `docker compose up` contra hardware
  real ainda — só sintaxe/lint local).
- Rotina de backup automatizada (agendada) + teste de restore de verdade (restaurar um backup
  e confirmar que o sistema volta a funcionar).
- Usuário de aplicação dedicado no MongoDB (hoje o backend usa o usuário root do cluster,
  criado via `MONGO_INITDB_ROOT_*` — suficiente pra este tamanho de sistema, endurecimento
  possível depois).
- HTTPS/TLS pro tráfego do navegador até o `frontend`/nginx, se o acesso for além da rede
  interna confiável.
- CI/CD automatizado (hoje o deploy é manual, `git pull` + `docker compose up --build` — dá
  pra automatizar depois que o fluxo manual estiver validado algumas vezes).
