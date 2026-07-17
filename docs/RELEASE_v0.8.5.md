# Release v0.8.5 — Reativação vira recadastro, admin oculto, consistência e auditoria de permissões

Release criado a partir da tag `v0.8.5`.

## Resumo

Continuação direta do trabalho de v0.8.4 (excluir usuário): a reativação virou um mini
recadastro (e-mail + senha novos do zero), foi adicionado um admin "total" oculto (só no
backend), e uma rodada de auditoria completa do sistema de permissões — backend e UI — achou
e corrigiu uma lacuna de auditoria de login, três mensagens de erro genéricas, uma doc
desatualizada, uma duplicação de checagem de admin e um bug de nível de permissão obsoleto.

## O que fecha nesta versão

### Reativação de usuário

- `POST /users/{id}/reativar` agora pede um e-mail (repetir o antigo ou trocar é válido) e
  sempre gera senha temporária **nova do zero** — mesmo padrão de `POST /users`, incluindo o
  callout com "Copiar senha" e "Abrir e-mail".
- Recadastrar um e-mail já excluído (`POST /users`) reativa a mesma linha em vez de rejeitar
  com "e-mail já cadastrado" — só bloqueia de verdade se o e-mail é de alguém ativo.

### Admin "total" oculto

- Uma conta específica (`backend/auth/deps.py::CONTAS_SUPER_ADMIN`) pode rebaixar/excluir
  outros admins — bypass deliberado, sem nenhum sinal no frontend (nem campo de API, nem
  lógica condicional no bundle). Autoproteção continua valendo até pra ela.

### Botão "Copiar senha" + correção de autofill

- Clipboard API nos dois callouts de senha temporária, pra eliminar o risco de arrastar
  espaço/quebra de linha ao selecionar o texto na mão (causa raiz de um bug de login real
  nesta sessão).
- Autofill do Chrome no formulário de "Cadastrar usuário" parou de puxar a credencial errada
  do admin — sem o campo `username` oculto decoy que tinha sido tentado antes (esse causava o
  balão nativo "Salvar senha?" aparecer em qualquer ação da página).

### Auditoria do sistema de permissões (sem mudança de regra de negócio)

Duas auditorias read-only (backend RBAC + UI) não encontraram nenhuma falha de segurança
real. Corrigido:

- Login de usuário desativado com senha certa não era registrado em `TentativaLogin` (buraco
  de auditoria + escapava do rate limit).
- Três handlers de `GestaoUsuarios.tsx` escondiam o erro real do servidor atrás de mensagem
  genérica.
- Comentário/doc desatualizados afirmando que Gestor ainda acessa `GET /users` (revogado
  2026-07-16).
- `BitinDetail.tsx`/`MeusBitins.tsx` duplicavam a checagem de admin em vez de usar o helper
  centralizado `isAdmin()`.
- `MeusBitins.tsx` tinha um nível de permissão obsoleto (`GESTOR_LEVEL = 1`, do esquema antigo
  0/1/99) que na prática deixava a busca por "Solicitante" visível pra qualquer usuário.

## Validação

- `npx tsc -b --noEmit` limpo.
- `python -m ruff check backend scripts` limpo.
- `python -m unittest discover -s tests` — 269 testes, todos passando.

## Notas

- Nenhuma das correções de auditoria muda comportamento visível pro usuário final — são
  consistência de mensagem/doc, não regra de negócio nova.
