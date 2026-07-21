# Release v0.10.1 — bloqueio de envio sem alteração, confirmação, correções da Lista Técnica/ZBPP009

Release criado a partir da tag `v0.10.1`.

## Resumo

Fecha um buraco real encontrado em teste manual: o sistema deixava enviar um BITin sem
nenhuma alteração de verdade. Junto, uma confirmação antes de enviar (ação que trava o BITin
pra sempre) e a correção de um bug real nas telas Lista Técnica e Códigos SAP, onde "Salvar"/
"Importar" podia silenciosamente não persistir a linha que acabou de ser editada.

## O que fecha nesta versão

### Bloqueio de envio sem alteração real

- **Nova regra de negócio** (`scripts/bitin_business_rules.py`, código
  `nenhuma_alteracao_real`): mesmo que a estrutura do BITin passe (código/centro/tipo
  preenchidos em todo material), o envio agora é bloqueado se NENHUM material tem uma
  alteração de verdade — `dados_basicos` com mudança efetiva, `impactos_operacionais` fora do
  padrão `"-"`, `atualizar_dwg_sat` marcado, ou `lista_tecnica` não vazia.
- **Confirmação antes de enviar** (`EdicaoBottomBar.tsx`): um clique a mais avisando que o
  BITin fica travado pra sempre depois de enviado — cobre as 3 telas de edição (BITin/ZBPP009/
  Lista Técnica), que reaproveitam a mesma barra.

### Correção real: Salvar/Importar podia perder a última edição

- **Lista Técnica e Códigos SAP** (`ListaTecnicaPage.tsx`, `CodigosSapPage.tsx`): o truque
  usado pra ler o estado mais recente logo após forçar o blur do campo focado (`setLinhas`
  funcional só pra "espiar" o valor) não é confiável — reproduzido ao vivo com Playwright: o
  `POST /bitins/draft` saía sem o material que tinha acabado de ser editado, especialmente ao
  criar um material novo por um código pai/material ainda não existente. Substituído por uma
  `ref` atualizada de forma síncrona em cada mutador, sem depender de nenhum agendamento do
  React.
- **Autocompletar de Código pai** (Lista Técnica, `<datalist>`): sugere os códigos de material
  já existentes no BITin, reduzindo o risco de criar um material "fantasma" por typo (espaço,
  maiúscula) em vez de anexar no material certo.
- **Centro/Descrição na Lista Técnica**: colunas novas — quando o código pai é novo, o
  material criado já nasce com esses dois campos preenchidos (bloco completo, sem precisar
  voltar na aba BITin); quando já existe, só completam o que estiver em branco.
- **Linha nova só no botão**: "+ Nova linha" era automática ao terminar de preencher a última
  linha da Lista Técnica — agora só aparece quando o próprio "+ Nova linha" é clicado.

### "Recebido (Cadastro)" removido

- Etapa que representava o intervalo entre "enviado" e o roteamento manual pro Processos —
  inatingível na prática desde que o roteamento virou automático (v0.9.0). Removida de
  `lib/bitinEtapa.ts`/Painel geral.

## Validação

- `python -m unittest discover -s tests` — **358 testes**, verde. Suite de ponta a ponta
  (`tests/test_bitin_workflow_e2e.py`) estendida pra cobrir o fluxo INTEIRO: Concluir BITIN →
  Enviar Windchill → Reverter (admin), gestor escopado no Painel geral, e o bloqueio de envio
  sem alteração real.
- `python -m ruff check backend scripts` — sem apontamentos.
- `npx tsc -b --noEmit`, `npm run lint` (oxlint), `npm run build` — sem erros/avisos.
- Testado ao vivo (Playwright, contas reais): confirmação antes de enviar aparece; erro
  "nenhuma alteração de verdade" aparece na tela ao tentar enviar um BITin vazio; correção do
  bug de Salvar/Importar reproduzida e confirmada corrigida em Lista Técnica e Códigos SAP,
  lendo o BITin de volta pela API depois de cada ação.

## Notas

Banco de contas de teste/BITins de teste foi zerado depois da validação (só a conta
super-admin fixa permanece) — mesmo script `scripts/limpar_banco_2026_07_21.py` usado antes.
