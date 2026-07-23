# Release v0.3.0 — Autenticação, reforço de dono e validação de ordem de cliente

Release criado a partir da tag `v0.3.0`.

## Resumo

- Objetivo: fechar a lacuna de autenticação que ficou deliberadamente adiada na v0.2.0, e
  corrigir pendências pequenas encontradas ao revisar dois projetos de referência
  (`GPT_Engineering_BITIN`, back+front antigo; `GPT_Engineering_authAPI`, serviço de auth).
- Status: backend com autenticação de verdade, RBAC simples e reforço de dono nos rascunhos;
  motor Python ganhou validação estrutural de `ordem_cliente[]`. Frontend ainda não construído
  — é o próximo passo real.

## Principais adições

- **Autenticação unificada no backend** (`backend/auth/`): `Usuario`/`Setor` no mesmo
  Postgres do resto do sistema (não um serviço separado), hash `pbkdf2_sha256`, JWT emitido e
  validado localmente. RBAC de 3 níveis (`0` usuário, `1` gestor, `99` admin). Primeiro
  usuário registrado vira admin automaticamente (bootstrap).
- **`/users` e `/sectors`**: perfil, listagem/busca de usuários (gestor+), promoção de
  permissão (admin), setores (departamento do usuário — RH/TI/Engenharia, não confundir com o
  `setor` do BITin que define o prefixo P/A).
- **Reforço de dono nos rascunhos**: só quem criou (ou um admin) edita/exclui; admin editando
  não rouba a autoria (`criado_por` preservado).
- **Todos os endpoints de `/bitins` agora exigem token** — sem `Authorization: Bearer`, `401`.
- **Validação estrutural de `ordem_cliente[]`**: `codigo` obrigatório, itens de
  `acrescentar_no_pedido[]`/`retira_do_pedido[]` exigem `codigo_material`+`quantidade`,
  entrada sem nenhum item é sinalizada.

## Decisão de arquitetura revisada no mesmo dia

Cogitamos rodar a autenticação como serviço separado (`GPT_Engineering_authAPI` como processo
independente, JWT validado por segredo compartilhado entre dois `.env`). Optamos por unificar
no mesmo backend/processo/banco: evita sincronizar segredo manualmente entre dois arquivos
`.env`, e resolve de graça RBAC e reforço de dono, que exigiriam uma chamada de rede síncrona
por requisição no modelo desacoplado. Ver `docs/BACKEND.md`, seção "Autenticação".

## Correções (achados revisando o `GPT_Engineering_authAPI` como referência)

- **Escalonamento de privilégio**: lá, `POST /auth/register` aceitava `permission_level` do
  corpo da requisição — qualquer um podia virar admin. Aqui, o cliente nunca controla esse
  campo.
- **CORS inválido**: `allow_origins=["*"]` + `allow_credentials=True` — trocado por origens
  explícitas.
- Rotas `/bitins` próprias do serviço de referência (numeração incompatível, persistência
  redundante) não foram trazidas.

## Mudanças de comportamento

- Endpoints de `/bitins` deixam de ser abertos — exigem login.
- `criado_por` (Postgres e Mongo) passa a ser preenchido de verdade (antes só existia a
  coluna, sem nada preenchendo).

## Validação

- 147 testes automatizados (era 114 na v0.2.0): 13 novos de robustez de API
  (`tests/test_backend_bitins.py`) + arquivo novo `tests/test_backend_auth.py`
  (registro/bootstrap-admin/login/RBAC/promoção/setores) + testes de `ordem_cliente[]`.
- Smoke test manual do servidor `uvicorn` real: registro → bootstrap admin → login →
  `/users/me` → `/bitins` bloqueando sem token, ponta a ponta.

## Como reproduzir

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests

# backend (agora exige login)
.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
.venv/Scripts/python.exe -m uvicorn backend.main:app --reload
# POST /api/v1/auth/register (primeiro usuário vira admin)
# POST /api/v1/auth/login -> access_token
# demais chamadas: Authorization: Bearer <access_token>
```

## Notas

- Próximo passo recomendado: frontend (React + Vite + Tailwind, sem lib de estado global —
  ver decisões em `docs/BACKEND.md`/histórico de commits), começando por uma fatia fina
  (login → "Meus Bitins" → criar rascunho → visualizar) antes do formulário completo de
  criação/edição.
- Pendências conhecidas, não bloqueantes: RBAC ainda não aplicado às ações de `/bitins` em si
  (hoje qualquer usuário autenticado cria/vê/lista); vínculo entre `Usuario.sector_id` e o
  `setor` do BITin (ex.: engenheiro só vê BITins do próprio setor) não implementado.
- Ver `CHANGELOG.md` para a lista completa e `docs/BACKEND.md`/`docs/BITIN_MODEL.md` para
  arquitetura e decisões registradas.
