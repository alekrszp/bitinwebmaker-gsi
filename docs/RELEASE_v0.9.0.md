# Release v0.9.0 — Fila Cadastro/Processos, automações VBA auditadas, testes de ponta a ponta

Release criado a partir da tag `v0.9.0`.

## Resumo

Duas frentes principais nesta versão: uma auditoria completa das automações que existiam no
VBA original (checklist, Alt/Esp/DWG-SAT, "REVISAR ROTEIRO") pra garantir que os engenheiros
não sentissem falta de nada da ferramenta antiga, e um fluxo novo de roteamento pós-envio com
dois setores novos — Cadastro e Processos — substituindo o e-mail automático que a macro
disparava via Outlook. Fechado com uma suíte de testes de ponta a ponta dedicada
(`tests/test_bitin_workflow_e2e.py`) que já encontrou e corrigiu 2 bugs reais no processo.

## O que fecha nesta versão

### Automações do VBA auditadas e portadas

- **Sugestão automática de Alt/Esp/nota DWG-SAT** a partir do código de Grupo de Mercadorias
  (`scripts/bitin_document.py::suggest_impactos`) — só preenche campo em branco, nunca
  sobrescreve o que o engenheiro já declarou; código SAP desconhecido não sugere nada, não
  trava.
- **Checklist e setores acionados recalculam ao vivo** (`POST /bitins/preview-resumo`) durante
  a edição — antes só atualizava depois de "Salvar".
- **Aviso "Revisar roteiro de fabricação"** por material quando o Alt declarado é `"D/P"` ou
  `"-/P"` — mesmo lembrete que a macro original (Módulo4.bas) escrevia.
- Auditoria dos 20 módulos VBA confirmou que todo o resto já estava portado (checklist
  automático, diffs de dados básicos, exports Winshuttle, lista técnica) — o único gap real
  achado foi o e-mail automático (Módulo12.bas), tratado pela fila do Cadastro abaixo.

### Fila do setor Cadastro (`CadastroPage.tsx`)

- Substitui de vez o e-mail/PDF manual — três abas: **Recebidos** (recém-enviado, ação
  condicional dependendo da regra automática abaixo), **Enviados para roteiros** (aguardando
  o Processos) e **Retornados de roteiro** (estado final, com "Baixar PDF" pra registro
  externo).
- Visibilidade **global** (qualquer BITin `"enviado"`, de qualquer autor/Subgrupo) — corrigido
  nesta versão, era escopada por Subgrupo até então (ver "Correções" abaixo).

### Setor Processos (novo nível `permission_level=89`)

- Recebe BITins encaminhados pelo Cadastro (`encaminhado_roteiro=true`) — não vê nem cria
  nada além disso.
- **Única exceção do sistema a "BITin enviado é travado pra sempre"**: reedita o conteúdo
  (`POST /bitins/{id}/atualizar-processos`) enquanto ainda não concluiu, depois fecha a
  janela (`POST /bitins/{id}/concluir-processos`).
- "+ Novo BITin" some da UI pra esse nível — backend também recusa com 403.

### Decisão automática "precisa de roteiro"

- `bitin_document.precisa_roteiro(bitin)`: `True` se QUALQUER material do BITin tem Alt em
  `{"D/P", "D/-", "-/P"}` (pedido explícito do usuário). Quando `False`, o Cadastro conclui
  direto sem passar pelo Processos (`POST /bitins/{id}/concluir-sem-roteiro`) — PDF liberado
  na hora, reforçado no servidor (400 se a regra na verdade exigir roteiro).

### Correções achadas pela suíte de ponta a ponta

- **Visibilidade do Cadastro estava presa a Subgrupo** — herdada de 2026-07-16, de antes
  desse nível virar hub de roteamento. Um BITin de um engenheiro sem Subgrupo em comum com o
  Cadastro sumia da fila "Recebidos". Corrigido: agora é global.
- **`/atualizar-processos` apagava `encaminhado_roteiro` de dentro de `content`** quando o
  payload não vinha com esse campo espelhado — quebrava `/concluir-processos` logo depois com
  "ainda não foi encaminhado", mesmo o BITin estando de fato encaminhado. Corrigido: o
  servidor agora reforça todo campo administrado pelo sistema por cima do payload do cliente.

### Removido

- Botão "Enviar e-mail" (`MeusBitins.tsx`) e o endpoint `GET /users/cadastro-emails`.

## Validação

- `python -m unittest discover -s tests` — 322 testes, todos passando (inclui a suíte nova de
  ponta a ponta).
- `python -m ruff check backend scripts` limpo.
- `npx tsc -b --noEmit`, `npm run lint` (oxlint), `npm run build` limpos.

## Notas

- Documentação atualizada em `docs/BITIN_MODEL.md` (seção "Roteamento pós-envio (Cadastro →
  Processos)") e `docs/BACKEND.md` (tabela de permissões + endpoints novos).
- Nem Cadastro nem Processos exigem Subgrupo — os dois são times centrais, escopo mudou de
  propósito nesta versão.
