# Release v0.8.3 — Checklist automática, exclusão admin, Lista Técnica inline, permissões novas

Release criado a partir da tag `v0.8.3`.

## Resumo

- Cinco frentes fechadas nesta rodada, todas pedidas diretamente pelo usuário: checklist com
  automação verificada contra as macros VBA reais, admin poder excluir BITin já enviado,
  confirmação/navegação depois do envio, Lista Técnica editável direto na aba BITin, busca
  tolerante de campo alterado, e uma reformulação completa do modelo de permissões (4 níveis
  numerados: Usuário/Gestor/Cadastro/Admin).

## O que fecha nesta versão

### Checklist automática (verificada, não mais um chute)

- Auditoria completa dos 20 módulos VBA do Excel original (`artifacts/vba/*.bas`) — só um
  módulo (`Módulo4.bas`, `Sub Preencher_Bitin`) automatiza a checklist de verdade. Mapeadas
  as 8 regras reais: Alt (D/-, D/P, D/F, -/P, -/F) → Desenho/Processo/Fornecedor; nota do
  campo alterado igual a "SALVAR DWG" ou "SALVAR SAT" (texto exato) → Atualizar DWG/SAT; Est
  preenchido → Retrabalhar ou descartar estoque; Est="S" → Centro de custo; LP/PRE/OC/OF
  preenchidos → Lista de preço/Precificação/Ordem de cliente/Atualizar ordem de fabricação.
- Restaura a sugestão automática (removida numa rodada anterior por falta de verificação) —
  override manual continua valendo por cima, nas duas direções.
- Confirmado que "Especificações técnicas" e "Alteração lista técnica" NUNCA são automáticas,
  nem no Excel original — continuam só manuais.

### Admin exclui BITin enviado

- `DELETE /bitins/{id}` aceita excluir um BITin já enviado quando quem pede é admin — limpa a
  linha do SQLite (código sequencial) junto com o documento do Mongo.
- Botão "Excluir BITin enviado" na aba BITin e em "Meus Bitins", visível só pra admin.

### Confirmação + navegação pós-envio

- Banner verde com o código gerado ("BITin enviado com sucesso! Código: X").
- A tela atualiza sozinha pro estado "enviado" (trava os campos, mostra a checklist final)
  sem precisar recarregar a página manualmente.

### Lista Técnica direto na aba BITin

- Botão "+ Lista técnica" ao lado de "+ Campo alterado / nota" em cada material — abre uma
  grade inline editável, mesma estrutura da página dedicada (`ListaTecnicaInline.tsx`),
  escrevendo no mesmo `materiais[].alteracoes.lista_tecnica` compartilhado.

### Busca tolerante no "+ Campo alterado / nota"

- Digitar "niv" agora acha "Nível de Revisão" — a busca ignora acento e maiúscula/minúscula e
  casa por trecho, não exige mais o nome exato do campo.

### Modelo de permissões reformulado

| Nível | Papel | Setor obrigatório | Vê rascunho | Vê enviado |
|---|---|---|---|---|
| 99 | Admin | Não | Todos | Todos |
| 77 | Gestor | Sim | Só do(s) setor(es) dele | Só do(s) setor(es) dele |
| 88 | Cadastro (novo) | Sim | Só os próprios | Só do(s) setor(es) dele |
| 66 | Usuário | Sim | Só os próprios | Só os próprios |

- Ninguém consegue rebaixar um admin (nem outro admin) — bloqueado no backend, não só na UI.
- `check_permission` deixou de comparar por limiar numérico (`>=`) e passou a checar
  pertencimento a um conjunto explícito de níveis, já que os novos números não formam uma
  hierarquia linear limpa.
- Migração de dados dos usuários existentes já aplicada ao banco real (0→66, 1→77, 99
  inalterado) via `scripts/migrar_niveis_permissao.py` (dry-run por padrão, backup feito
  antes de aplicar).

## Validação

- Backend: 226 → **235** testes, todos verdes.
- Frontend: `npm run typecheck`, `npx oxlint src`, `npm run test` (4/4), `npm run build` —
  todos limpos.
- Validação visual ao vivo: checklist automática (Alt/DWG real), exclusão de BITin enviado
  como admin confirmada nos dois bancos, confirmação pós-envio sem reload, busca tolerante,
  e as 4 permissões novas (opções de cadastro, setor obrigatório, admin protegido contra
  rebaixamento).

## Como reproduzir

```powershell
# backend
.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
.venv/Scripts/python.exe -m uvicorn backend.main:app --reload

# frontend (outro terminal)
cd frontend
npm install
npm run dev
```

## Notas

- Continuam pendentes: fluxo de "esqueci minha senha", decisão final de hospedagem
  (Atlas vs. infra própria da empresa).
- Ver `docs/CHANGELOG.md` para a lista completa e `docs/BACKEND.md`/`docs/BITIN_MODEL.md`
  para arquitetura e decisões registradas.
