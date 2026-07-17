# Release v0.8.4 — Excluir usuário, correção de cores no modo escuro (telas de login)

Release criado a partir da tag `v0.8.4`.

## Resumo

Duas frentes, ambas pedidas diretamente pelo usuário: admin ganha um jeito de excluir
usuário na tela de Gestão de usuários, e correção das cores "estranhas" no modo escuro nas
telas fora da área logada (Entrar, Definir senha).

## O que fecha nesta versão

### Excluir usuário

- Botão de lixeira em cada linha de Gestão de usuários (admin-only), com confirmação
  (`window.confirm`).
- `DELETE /users/{id}` no backend. Decisão registrada explicitamente com o usuário: é
  **soft-delete** (`Usuario.ativo = False`), não apaga a linha do banco.
  - Motivo: `ativo` já é checado em todo request autenticado e no login — a conta já para de
    funcionar na hora, sem precisar revogar sessão à parte. BITins não têm FK pro usuário
    (dono é só um campo solto no documento do Mongo), mas `SessaoUsuario` tem — soft-delete
    evita ter que lidar com essa cascata. E fica reversível (reativar hoje só via banco; não
    foi pedida reativação pela UI).
  - Mesmas proteções de `PATCH /users/{id}/permission`: ninguém se auto-exclui, admin (99)
    não pode ser excluído por ninguém.
  - `GET /users` passou a filtrar `ativo=True` — usuário excluído some da listagem.

### Correção de cores no modo escuro (telas pré-login)

- `Login.tsx`: painel de marca usava `bg-white` fixo, que nunca escurecia e brigava com o
  texto claro do tema escuro (baixo contraste). Trocado por `bg-surface` — mesmo branco no
  tema claro, acompanha o tema escuro.
- `Login.tsx` e `DefinirSenha.tsx`: caixas de erro (`role="alert"`) usavam só
  `red-50/red-200/red-700`, sem variante de modo escuro. Adicionado
  `dark:bg-red-950 dark:border-red-900 dark:text-red-300`.

## Validação

- `npx tsc --noEmit` limpo no frontend.
- `python -m unittest tests.test_backend_auth -v` — 56 testes, todos passando, incluindo os
  6 novos cobrindo `DELETE /users/{id}` (sucesso, soft-delete some da listagem, login
  bloqueado depois, proteção contra auto-exclusão, proteção contra excluir admin, 403 para
  não-admin). Ambiente sem `pytest` instalado no venv — rodado via `unittest` puro (o arquivo
  de teste já usa `unittest.TestCase`, não depende de `pytest`).

## Notas

- Reativar um usuário excluído hoje só é possível editando o banco direto
  (`Usuario.ativo = True`) — não foi pedida uma tela/rota de reativação nesta rodada.
