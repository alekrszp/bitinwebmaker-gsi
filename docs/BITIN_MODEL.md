# Modelo de dados do BITin

Este documento descreve o modelo de dados que o engenheiro manipula na interface web
(`frontend/`, ver `docs/FRONTEND.md`) e como ele se conecta ao mapeamento `Módulo1`/`Módulo2`
já portado (`config/vba_mapping.json`, `scripts/vba_port_export.py`).


## Estrutura

```
bitin              - número no formato YXXXX/AA (Y = P/Proteína ou A/Armazenagem) --
                      GERADO PELO SISTEMA no momento do envio (não preenchido pelo
                      engenheiro), vazio/ausente durante o rascunho (ver "Backend")
status              - "rascunho" (editável) ou "enviado" (travado) -- ver seção "Ciclo de vida"
setor              - "Proteína Animal" ou "Armazenagem de Grãos" -- obrigatório no envio
                      (define o prefixo P/A do número gerado, ver "Backend")
produto             - hierarquia de produto (SAP)
motivo              - motivo da alteração (SPN, SPE, melhoria, correção, ...)
solicitante         - engenheiro responsável
data_solicitacao    - data de emissão do BITin
ordem_cliente[]     - itens que afetam ordens de cliente (acrescentar/retirar do pedido)
checklist[]         - 22 itens fixos de responsabilidade pós-aprovação (Quadro 01 do POP)
materiais[]:
  codigo_material
  descricao_material
  centro              - 2001 (Marau) ou 2005 (Passo Fundo) -- POR MATERIAL, não por BITin
                        (um mesmo BITin pode alterar materiais em centros diferentes)
  tipo_material       - POR MATERIAL, pelo mesmo motivo
  desenho_aprovado    - bool, exigido quando há alteração de desenho (POP Nota 2)
  ncm_aprovado_fiscal - bool, exigido quando NCM muda (POP Nota 17)
  grupo_mercadorias_atual - snapshot do Grupo Mercadorias ATUAL (SAP/ZBPP009), sempre
                        necessário pro cálculo de Alt/Esp/DWG-SAT, muda ou não
  tem_desenho         - bool, snapshot de "este material tem desenho associado" (SAP/ZBPP009)
  alteracoes:
    lista_tecnica[]     - componentes filhos alterados na lista técnica
    dados_basicos:      - um {de, para} por campo SAP alterável (ver crosswalk abaixo)
    impactos_operacionais: alt / est / esp / lp / pre / oc / of (campos do ANEXO A do POP)
                          + centro_custo / conta_razao (exigidos quando est="S", POP Nota 8)
```

**Decisão registrada**: Centro e Tipo Material ficam por material (`materiais[].centro`,
`materiais[].tipo_material`), não no cabeçalho do BITin — confirmado com o responsável do
projeto, já que um BITin pode abranger materiais de mais de um centro.

## Regras de campo (view + cadastro — consolidado em 2026-07-14)

Regras confirmadas com o responsável do projeto ao revisar a visualização contra um BITin real
(`A263326.xlsm`). **Vale tanto pra visualização (já implementada) quanto pro cadastro/edição
(ainda não construído) — as duas telas têm que aplicar exatamente as mesmas regras**, não
lógicas divergentes.

| Campo | Quem preenche | Quando é editável | Observação |
|---|---|---|---|
| `bitin` (número) | Sistema, automático | Nunca (nem no rascunho) | Gerado só no envio, por `backend/bitin_number.py`. Vazio durante o rascunho. |
| `produto` | Engenheiro, texto livre | Enquanto rascunho | Sem enum/validação de formato. |
| `motivo` | Engenheiro, texto livre | Enquanto rascunho | Sem enum/validação de formato. |
| `setor` | Engenheiro, escolhe entre as opções fixas | Enquanto rascunho | "Proteína Animal" ou "Armazenagem de Grãos" — define o prefixo P/A do número gerado no envio (`backend/bitin_number.py::SETOR_PREFIXO`). |
| `solicitante` | Engenheiro, texto livre | Enquanto rascunho | |
| `data_solicitacao` | Sistema, automático (carimbada quando o rascunho é salvo) | Enquanto rascunho | Não é escolhida livremente pelo engenheiro — é a data em que o BITin foi salvo como rascunho pela primeira vez. |
| `data_envio` | Sistema, automático (carimbada no envio) | Nunca | Ausente/`null` até o BITin ser enviado. |
| `checklist[]` | Sistema, calculado, **com override manual** | Enquanto rascunho (só o override) | Sugestão automática a partir dos impactos operacionais de cada material (`scripts/bitin_document.py::build_checklist`). O engenheiro pode clicar num item da checklist (aba "BITin", tela editável) e sobrescrever manualmente — o valor fica em `bitin['checklist_overrides']` (dict `id -> bool`) e tem prioridade sobre o cálculo automático quando presente. Cada item devolvido carrega `manual: bool` pra UI marcar o que foi sobrescrito. Decisão registrada com o usuário (2026-07-15): "não tem como clickar na checklist e ir mudando os setores". |
| Setores acionados | Sistema, calculado | Nunca editado diretamente | Derivado do checklist (já com overrides aplicados) via crosswalk fixo `config/bitin_document_mapping.json::checklist_setores` (extraído de um BITin real, aba "SETORES CHECKLIST"). Clicar num item da checklist muda os setores acionados pelo mesmo motivo que a sugestão automática mudaria — não existe lógica separada pros dois casos. |
| `materiais[].alteracoes.dados_basicos` | Engenheiro | Enquanto rascunho | Cada entrada é `{de, para}`. Se a chave bate com um campo do crosswalk (`vba_mapping.json::bitin_schema_crosswalk.dados_basicos`, 30 campos), é um **campo SAP reconhecido** — mostrado normal, com rótulo traduzido, numa tabela De/Para. Se não bate, é **texto livre** (o engenheiro digitou uma nota solta, tipo "Salvar DWG") — mostrado destacado (vermelho/`--color-livre-text`), num bloco à parte (nunca dentro da mesma tabela De/Para), com a chave exibida do jeito que foi escrita. Essa distinção é a mesma nos dois lados — visualização (`AlteracaoTable`) e edição (`MaterialEditorCard`) — reaproveitando o mesmo crosswalk (`scripts/bitin_document.py::build_campo_alterado_diffs` na visualização; `MateriaisSchema.dados_basicos` na edição), nunca reimplementada em paralelo. |
| `materiais[].alteracoes.lista_tecnica[]` | Engenheiro | Enquanto rascunho | Cada item é `{codigo_filho, quantidade_de, quantidade_para, operacao}`. O código pai é o próprio `codigo_material` do material (não repetido no item). `operacao` (inserir/alterar/excluir) é só pro cadastro decidir a intenção — **não aparece na visualização**, o engenheiro nem precisa pensar nisso ao ler o documento. |
| `ordem_cliente[]` | Engenheiro | Enquanto rascunho | Só relevante quando `impactos_operacionais.oc == "X"` em algum material (Nota 10 do POP). |
| `materiais[].alteracoes.impactos_operacionais` (Alt/Est/Esp/LP/Pre/OC/OF + `atualizar_dwg_sat`/`centro_custo`/`conta_razao`) | Engenheiro declara | Enquanto rascunho | Não é derivado de código SAP (só existem sugestões opcionais não-autoritativas, ver `suggest_alt`/`suggest_dwg_sat_action`). |

## Tela Códigos SAP (idêntica à ZBPP009, adicionado em 2026-07-15)

A tela "Códigos SAP" (`frontend/src/pages/CodigosSapPage.tsx`, rota
`/bitins/:mongoId/codigos-sap`) é deliberadamente **igual à aba ZBPP009** do documento
original: uma tabela com a identificação do material (código/centro/tipo/descrição) + os 30
campos de `dados_basicos`, pra colar do SAP (`POST /bitins/parse-sap-paste`,
`scripts/sap_paste_parser.py::plan1_row_to_material_atual`, que agora extrai o "de" de todos
os campos via `config/vba_mapping.json::plan1_dados_basicos_columns`) ou digitar na mão. Não
tem indicadores nem coluna "Para" aqui — isso é declarado só na aba "BITin"
(`MaterialEditorCard` em modo `somenteAlteracao`), material por material, reaproveitando o
"de" já preenchido nesta tela. As colunas vêm do schema do backend
(`GET /bitins/schema/materiais`), nunca hardcodadas no frontend.

Decisão registrada com o usuário: "tudo que o engenheiro altera no bitin, ele manipula aquele
JSON que eu te mandei" — os campos de `materiais[]` usados nas telas de edição são sempre os
mesmos do JSON canônico (`GPT_Engineering_BITIN/schema.json`, refeito com o crosswalk real),
nunca um campo novo inventado só pra UI.

Status geral: **todas essas regras já valem pras 3 telas de edição** (`BitinDetail.tsx`,
`CodigosSapPage.tsx`, `ListaTecnicaPage.tsx`) e pra visualização (mesma tela, travada quando
não é mais rascunho).

## Crosswalk `dados_basicos` -> coluna "Novo" de `Plan2`

O campo `para` de cada entrada em `dados_basicos` é exatamente o valor que vai para a coluna
`"... Novo"` da aba real `ZBPP009 + ALTERACAO`, que o `Módulo2.Winshuttle` lê (ver
`docs/VBA_EXPORT_MAPPING.md`, seção "Padrão atual vs. Novo"). O crosswalk completo está em
`config/vba_mapping.json` → `bitin_schema_crosswalk`, e é usado por `scripts/bitin_model.py`.

Duas convenções de "campo não alterado" coexistem (herdadas do VBA original):

- **Convenção `N/A`**: campos que o `Módulo1` inicializa com a constante `"N/A"` — usado por
  `material_substituto`, `status_bloqueio_vendas`, `data_bloqueio_vendas`, `grupo_compradores`,
  `tipo_suprimento_especial`, `deposito_producao`, `deposito_suprimento_externo`,
  `prazo_entrega`, `responsavel_controle_producao`, `perfil_producao`, `producao_interna`,
  `texto_pedidos_compras`. Se o engenheiro não informar `para` para esses campos, o valor
  correto para Plan2 é a string `"N/A"`, não vazio.
- **Convenção vazio**: todos os outros campos de `dados_basicos` — se `para` não for
  informado, o valor correto para Plan2 é `""`.

`scripts/bitin_model.py` aplica a convenção certa automaticamente por campo, sem precisar que
quem monta o BITin saiba dessa distinção.

## Lacunas conhecidas entre o `schema.json` de referência e o `Módulo2`

- O `schema.json` não tinha `centro`/`tipo_material` — adicionados por material (ver acima).
- A coluna `Plan2` 71 ("Marcação eliminar nível centro Novo") não tem campo correspondente no
  `schema.json` — só existe `marcacao_eliminar_nivel_mandante` (coluna 69). Por enquanto o
  port só preenche a coluna 69; a 71 fica sempre vazia até o schema ganhar esse campo.
- `checklist[]` e `ordem_cliente[]` ainda não têm uso no export (servem para o processo humano
  — roteamento, Windchill — descrito no POP, não para um upload SAP em si).

## Export de `lista_tecnica[]` (CS02 — estrutura de material / BOM)

Diferente de `dados_basicos` (que alimenta o `Módulo2`/MM02), alteração de lista técnica é
outra transação SAP inteira (**CS02**) e usa outro template Winshuttle, com campos de
`RC29N`/`RC29P` (cabeçalho e item da lista técnica), não `MARA`/`MARC`/`MVKE`. **Não existe
nenhuma macro VBA que gera esse export** — no workbook original, `Módulo15.dados_lista_técnia`
só insere rótulos em branco no documento de apresentação (`Plan4`) para alguém preencher à
mão; a aba real `Lista técnica` (Winshuttle) é preenchida manualmente, direto no formato final.
Por isso `scripts/lista_tecnica_export.py` não é um port — é automação nova, construída a
partir da estrutura real observada em exemplos de BITin verdadeiros (`bitin teste 2.xlsm`,
aba `Lista técnica`, ~60 linhas de um BITin de 2023).

Colunas reais da aba `Lista técnica` (confirmadas no exemplo real, ver
`config/lista_tecnica_mapping.json`):

| Coluna | Campo SAP | Origem no BITin |
|---|---|---|
| 1 | Nº do material (`RC29N-MATNR`) | `materiais[].codigo_material` (material pai) |
| 2 | Centro (`RC29N-WERKS`) | `materiais[].centro` |
| 3 | Utilização de listas técnicas (`RC29N-STLAN`) | constante (`"5"` — todo exemplo real observado usa esse valor; **assumido, não confirmado com o time**) |
| 4 | Nº modificação (`RC29N-AENNR`) | `bitin` (número do BITin — confirmado: exemplo real tinha `A0618/23`, mesmo formato `YXXXX/AA`) |
| 5 | Componente de lista técnica (`RC29P-IDNRK`) | `materiais[].alteracoes.lista_tecnica[].codigo_filho` |
| 6 | Quantidade do componente (`RC29P-MENGE`) | `quantidade_para` (inserir/alterar) ou `quantidade_de` (excluir) |
| 7 | INSERIR | `"X"` quando `operacao = "inserir"` |
| 8 | ALTERAR | `"X"` quando `operacao = "alterar"` (ou quando `operacao` não é informado — default) |
| 9 | EXCLUIR | `"X"` quando `operacao = "excluir"` |

### Campo `operacao` (adicionado em 2026-07-10)

Cada item de `lista_tecnica[]` agora tem um campo `operacao: "inserir" | "alterar" | "excluir"`
(opcional — default `"alterar"`, para não quebrar BITins já criados sem esse campo). Isso
cobre o caso real observado (troca de componente = um item `"excluir"` pro código antigo +
um item `"inserir"` pro código novo), além do caso simples de só mudar a quantidade
(`"alterar"`, um único item, mesmo `codigo_filho`).

Exemplo de troca de componente (2 itens numa `lista_tecnica[]`):

```json
"lista_tecnica": [
  {"operacao": "excluir", "codigo_filho": "S2048-122264", "quantidade_de": "1"},
  {"operacao": "inserir", "codigo_filho": "S2048-122232", "quantidade_para": "2"}
]
```

Validação: `codigo_filho` é sempre obrigatório; `quantidade_para` é obrigatório para
`inserir`/`alterar`; `quantidade_de` é obrigatório para `excluir` (é o valor que vai na
coluna "Quantidade do componente" ao remover a associação).

## Documento do BITin (Alt/Esp/checklist — `Módulo4`+`Módulo10`+`Módulo13`)

`scripts/bitin_document.py` porta `Módulo4.Preencher_Bitin` (+ `Módulo10.DWG_SAT` e
`Módulo13.DWG_SAT_N_DESENHO`, que ele chama).

### Alt/Esp declarados pelo engenheiro, não derivados de código SAP (decisão de 2026-07-10)

O `Módulo4` original deriva `Alt`/`Esp`/ação de desenho a partir de códigos de Grupo de
Mercadorias (`SA003`, `SA013`, `SA014`, `SA016`, `SA017`, prefixo `"MP"`). Na prática esse
catálogo de códigos é vasto e muda com o tempo — codificar regras de negócio em cima de
códigos específicos é frágil (qualquer código novo/desconhecido quebra a classificação
silenciosamente). Decisão registrada: **o engenheiro declara `alt`/`esp`/`atualizar_dwg_sat`
diretamente em `impactos_operacionais`** (é exatamente o que `schema.json` já modelava) — o
sistema não tenta adivinhar a partir de código SAP.

`suggest_alt`, `suggest_esp` e `suggest_dwg_sat_action` continuam existindo em
`bitin_document.py`, mas como **sugestão opcional, não autoritativa** (útil como dica de UI
no futuro formulário web, nunca para validação). Foram validados contra dados reais
(`bitin teste 2.xlsm`, BITin `P0812/26`): os 8 materiais com revisão de desenho alterada e
Grupo Mercadorias `SA016` sugeririam `Alt = "D/P"` e `DWG_SAT = "SALVAR DWG"`, batendo com o
que está na aba `Template apresentação` desse arquivo real; os materiais sem alteração de
desenho (`NAP-0734`, `NAP-2339`) sugeririam `Alt = "-"`, também batendo.

`build_campo_alterado_diffs` monta a lista "Campo alterado / De / Para" por material direto
do JSON, sem precisar reconsultar `Plan2` — a diff real "Nível Revisão: C → D" bateu
exatamente com o exemplo real.

**Divergência deliberada do `.bas` extraído (checklist)**: `Módulo4.bas` escreve o checklist
em linhas fixas da planilha (`Plan4.Cells(9,3)`, `Cells(8,3)`, etc.) que **não batem** com os
rótulos reais observados no exemplo — o código escreve `Alt="D/P"` na linha 9, mas a linha 9
real é "Desenho", não "Desenho/Processo"; o dado real mostra "Desenho/Processo" marcado
quando `Alt="D/P"`, batendo com a linha 10, não a 9. Isso indica que o `.bas` extraído está
desatualizado em relação ao que realmente gera esses arquivos. Diferente do `Módulo2` (onde a
posição da coluna tem risco real de quebrar o upload SAP), aqui não há esse risco — é uma
estrutura de dados nova, não uma célula de planilha legada. Por isso o checklist usa o
**mapeamento semântico por rótulo** (`alt_to_checklist_id` em
`config/bitin_document_mapping.json`), que bateu com os dados reais, em vez da posição de
linha literal do `.bas`.

**Checklist automático, restaurado em 2026-07-16 após auditoria real da macro**: até
2026-07-15 a automação tinha sido removida inteira ("checklist é marcada manualmente"), por
desconfiar das regras antigas (nunca verificadas contra o `.bas`). O usuário então relatou, na
prática, que a planilha original marca sozinha a checklist ao digitar uma nota específica
("quando colocado no campo nota salvar dwg ele marca sozinho a checklist") — o que motivou
reabrir o `Módulo4.bas` e conferir grep por grep (`, 3) = "SIM"`) em todos os 20 módulos de
`artifacts/vba/`. Resultado: `Módulo4.Preencher_Bitin` (linhas ~144-202) é a ÚNICA origem de
automação em toda a macro, com exatamente 8 regras, agora portadas em
`bitin_document._checklist_ids_auto_sugeridos`:

1. Alt declarado → id via `alt_to_checklist_id` (D/- =1, D/P=2, D/F=3, -/P=4, -/F=5).
2. Nota livre em `dados_basicos` igual, exatamente (case-sensitive), a `"SALVAR DWG"` ou
   `"SALVAR SAT"` → id 18 ("Atualizar DWG / SAT"). Não é mais um checkbox — o antigo campo
   `impactos_operacionais.atualizar_dwg_sat` foi removido do frontend; o único jeito de
   acionar isso é a nota de texto batendo exatamente com uma dessas duas strings.
3. `Est` fora de `{"", "-"}` → id 8 ("Retrabalhar ou descartar estoque").
4. `Est == "S"` → id 22 ("Centro de custo (se tem sucata)", sucateamento, POP Nota 8).
5. `LP` fora de `{"", "-"}` → id 19 ("Lista de preço").
6. `PRE` fora de `{"", "-"}` → id 20 ("Precificação").
7. `OC` fora de `{"", "-"}` → id 10 ("Ordem de cliente").
8. `OF` fora de `{"", "-"}` → id 17 ("Atualizar ordem de fabricação").

Em todos os casos, `checklist_overrides` (clique manual do engenheiro) continua vencendo a
sugestão automática, nos dois sentidos.

**Itens de checklist ainda sem regra automática** (`manual_only_checklist_ids`): "Especificações
técnicas" (id 6) e "Alteração lista técnica" (id 7) — confirmado na auditoria: nenhuma regra os
ativa automaticamente, nem na macro real, apesar de serem código de item de checklist "normal"
como os outros. Além deles: DPO-PAN, Atualizar manual, Atualizar instrução de montagem,
Elétrica/Embalagem/Montagem/Helicoides, Estamparia, Madeira ou Plástico, Atualizar custos —
nenhuma regra no `Módulo4` lido determina esses automaticamente a partir dos campos que temos
hoje; continuam dependendo de marcação manual. "Atualizar BITex" (id 11) é coberto parcialmente,
só via o campo `bitex` do cabeçalho — mas nem esse campo aciona nada sozinho (bitex não faz
parte das 8 regras confirmadas), fica 100% manual também.

**Campo `bitex` adicionado ao cabeçalho do BITin** (visto no `Template apresentação` real,
linha 2: `"BITex" / "NÃO"`) — não estava em `schema.json`; usado só para o checklist id 11.

## Validação estrutural de `ordem_cliente[]` (adicionado em 2026-07-10)

Cada entrada de `ordem_cliente[]` tem o formato herdado do `schema.json` original:

```json
{
  "codigo": "CT30-7103",
  "descricao": "Pedido especial exportação",
  "acrescentar_no_pedido": [{"codigo_material": "COD999", "quantidade": "2 pçs"}],
  "retira_do_pedido": [{"codigo_material": "COD111", "quantidade": "1 pç"}]
}
```

Até aqui só o campo `codigo` era efetivamente lido (pela regra da Nota 10, ver abaixo) — `acrescentar_no_pedido[]`/`retira_do_pedido[]` existiam no schema mas nada validava seu conteúdo.
`bitin_model.validate_ordem_cliente` (chamada por `validate_bitin`) agora garante:

- `codigo` é obrigatório em toda entrada de `ordem_cliente[]`.
- cada item de `acrescentar_no_pedido[]`/`retira_do_pedido[]` precisa de `codigo_material` e
  `quantidade`.
- uma entrada sem nenhum item nas duas listas é sinalizada (`ordem_cliente_sem_itens`) — declarar
  um pedido afetado sem dizer o que muda nele não tem efeito real.

Isso é validação **estrutural** (roda em `validate_bitin`, junto com os campos obrigatórios do
cabeçalho/material) — diferente da regra de negócio da Nota 10 (`bitin_business_rules.py`), que
continua checando só se existe uma entrada com `codigo` igual ao material quando `oc == "X"`.

## Erros estruturados (decisão de 2026-07-10)

Todas as funções `validate_*` (`bitin_model.validate_bitin`, `lista_tecnica_export.validate_lista_tecnica`,
`bitin_business_rules.validate_business_rules`) devolvem `list[dict]`, não `list[str]`. Cada
erro é `{"field": "...", "code": "...", "message": "..."}`:

- `field` — caminho no estilo `materiais[0].alteracoes.impactos_operacionais.alt` (o frontend
  usa isso pra destacar o campo exato, sem precisar fazer parsing de texto).
- `code` — identificador estável em snake_case (ex.: `invalid_alt_value`,
  `desenho_aprovado_required`) — o frontend pode decidir tratamento por código sem depender do
  texto da mensagem (que pode mudar).
- `message` — texto em português pronto pra mostrar ao usuário.

Decisão registrada: essa troca foi feita **antes** de existir qualquer frontend consumindo o
formato antigo (string solta) — é a hora mais barata de fazer essa mudança.

### Validação de enum dos campos do POP (adicionado junto)

`alt`/`est`/`esp`/`lp`/`pre`/`oc`/`of` em `impactos_operacionais` agora são validados contra os
valores do `ANEXO A` do POP (`config/bitin_document_mapping.json` → `valores_validos`); antes
qualquer string passava despercebida. `"-"` é aceito em todos como "sem impacto" (convenção já
usada no resto do sistema), mesmo quando o POP não lista `"-"` explicitamente pra `Est`
(ambiguidade registrada: o POP diz "indicar sempre" o destino do estoque, mas não fica claro
se isso é obrigatório em BITins que não mexem em estoque — mantivemos `"-"` como aceitável até
confirmação).

## Regras de negócio do POP (portão de envio, não bloqueia edição)

Filosofia registrada com o responsável do projeto: o engenheiro tem liberdade total pra editar
o BITin (adicionar/remover material, mudar de ideia, sem validação no meio do caminho) — as
regras abaixo só rodam no **envio** (mesmo espírito de `validate_bitin`/`validate_lista_tecnica`),
implementadas em `scripts/bitin_business_rules.py` (`validate_business_rules`).

Regras derivadas das Notas do `POP_ENG_7.3.7_002`, com automação clara a partir dos dados que
já temos (`alt` aqui é o valor **declarado** pelo engenheiro, não derivado de código SAP):

| Regra | Nota do POP | Condição | Exigência |
|---|---|---|---|
| Desenho aprovado | Nota 2 | `impactos_operacionais.alt` começa com `"D"` (D/P, D/-, D/F) | `materiais[].desenho_aprovado == true` |
| NCM exige fiscal | Nota 17 | `alteracoes.dados_basicos.ncm.para` preenchido | `materiais[].ncm_aprovado_fiscal == true` |
| Sucateamento exige centro de custo | Nota 8 | `impactos_operacionais.est == "S"` | `impactos_operacionais.centro_custo` e `.conta_razao` preenchidos |
| Ordem de cliente precisa do quadro 2 | Nota 10 | `impactos_operacionais.oc == "X"` | existe uma entrada em `ordem_cliente[]` com `codigo` igual ao `codigo_material` |

**Não automatizadas ainda** (precisam de mais contexto ou integração externa antes de virar
regra): Nota 6 (conferir versão do desenho aprovada no Windchill — precisa integração com o
Windchill, fora do escopo Python atual), Nota 9 (texto "Retirado bloqueio de vendas" ao
liberar/precificar — formato exato do texto não confirmado), Nota 19 (formato do campo
`Documento` para materiais novos — formato exato não confirmado), Nota 20 (múltiplos centros
na mesma lista técnica — é julgamento de negócio, não uma regra determinística clara).

### Regras gerais de consistência (não dependem de código específico)

Complementam as regras do POP acima — pegam erro de digitação/inconsistência entre o que foi
**declarado** (`alt`) e o que foi **de fato registrado como mudança**, sem precisar conhecer
nenhum código SAP específico (por isso "gerais" — funcionam pra qualquer material, presente
ou futuro):

| Regra | Condição | Por quê |
| --- | --- | --- |
| Código+centro duplicado | mesmo par `(codigo_material, centro)` aparece 2x em `materiais[]` | ambíguo qual entrada vale — mas o **mesmo código em centros diferentes é permitido** (ex.: material `8661` em 2001/2003/2005/2006, caso real) |
| Campo sem efeito real | `dados_basicos.<campo>.de == .para` (e `para` não vazio) | listar um campo que não muda é sinal de erro de preenchimento |
| Alt inconsistente com mudanças | `alt == "-"` mas há `dados_basicos` com `para` preenchido | se declarou "sem alteração" mas hay mudança registrada, o Alt provavelmente está errado |
| Alt de desenho sem revisão | `alt` começa com `"D"` mas não há mudança em `nivel_revisao` | alteração de desenho sem bater com nenhum campo de desenho mudando é sinal de Alt errado |

## Ciclo de vida do BITin (rascunho → enviado)

Decisão registrada com o responsável do projeto: o BITin tem duas telas/estados —
**criação/edição** (rascunho, liberdade total, sem validação no meio do caminho — "salvar
rascunho") e **visualização** (depois de enviado, travado, ninguém edita mais). Implementado
em `scripts/bitin_lifecycle.py`:

- `status: "rascunho" | "enviado"` no cabeçalho do BITin (default `"rascunho"`).
- `is_editable(bitin) -> bool` — `False` quando `status == "enviado"`.
- `enviar_bitin(bitin, vba_mapping_config, document_config) -> (bool, list[str])` — o único
  ponto em que TODA a validação roda de uma vez (estrutural + lista técnica + regras de
  negócio do POP + regras gerais, todas já construídas). Se passar, marca `status="enviado"`
  e carimba `data_envio`; se falhar, `status` continua `"rascunho"` e a lista de erros volta
  pra tela de edição. Tentar enviar um BITin já `"enviado"` retorna erro (não reenvia).
- `require_editable(bitin)` — guarda a ser chamada por qualquer função que for *mutar* um
  BITin (adicionar/remover material, editar campo); levanta `ValueError` se `status ==
  "enviado"`. É o mecanismo de trava — nenhuma edição deve contornar essa checagem.

Essa separação é também a "otimização do sistema" da conversa: a validação cara (5 funções,
todo o cruzamento de regras) só roda **uma vez**, no envio — não em cada tecla digitada
durante o rascunho.

`scripts/bitin_view.py` gera o modelo de visualização (`render_bitin_summary`): cabeçalho +
status + por material (Alt/Esp/diffs de dados básicos/itens de lista técnica) + checklist —
serve tanto de prévia durante o rascunho quanto de tela final depois de enviado. É um dict
estruturado (não HTML/markdown) — a formatação visual fica a cargo do frontend.

## Roteamento pós-envio (Cadastro → Processos, 2026-07-17)

Depois de `"enviado"`, o BITin ainda passa por um segundo ciclo — não é mais só o estado
binário rascunho/enviado. Substitui o e-mail automático que o VBA original (Módulo12.bas)
disparava via Outlook ao enviar; em vez de e-mail, o setor Cadastro tem uma fila própria
(`CadastroPage.tsx`) e o BITin carrega o próprio estado de roteamento em 3 campos novos,
espelhados TANTO no documento Mongo top-level QUANTO dentro de `content` (achado real desta
sessão: `encaminhar_para_roteiro`/`concluir_processamento`/`concluir_sem_roteiro`, abaixo,
mutam o dict `content` que recebem — se um endpoint substituir `content` inteiro sem
preservar esses campos, o espelho se perde mesmo o doc top-level continuando correto; ver
`backend/api/bitins.py::atualizar_processos_endpoint`, bloco `campos_do_sistema`, pra como
isso é reforçado no servidor):

- `encaminhado_roteiro: bool` + `data_encaminhado_roteiro` — BITin foi encaminhado pro setor
  Processos.
- `processos_concluido: bool` + `data_processos_concluido` — Processos terminou a revisão (ou
  o Cadastro decidiu que nem precisava, ver `sem_necessidade_roteiro` abaixo). Estado final —
  o PDF de registro externo (`GET /bitins/{mongo_id}/pdf`) só faz sentido pra exibir/baixar
  depois daqui (aba "Retornados de roteiro" em `CadastroPage.tsx`).
- `sem_necessidade_roteiro: bool` — só pra exibição/auditoria, diferencia os dois jeitos de
  chegar em `processos_concluido=True` (passou pelo Processos de verdade, ou o Cadastro
  concluiu direto). Nenhum filtro depende dele — todos leem `processos_concluido`.

**Decisão automática "precisa de roteiro"** — `bitin_document.precisa_roteiro(bitin)`: `True`
se QUALQUER material do BITin tem `Alt` em `{"D/P", "D/-", "-/P"}` (pedido explícito do
usuário, 2026-07-17: "quando não houver: D/P, D/- ou -/P... se tiver isso na alteração do
código é roteiro, quando não tiver não é"). **Não confundir** com
`bitin_document.revisar_roteiro(material)` — o lembrete "REVISAR ROTEIRO" por material,
herdado do VBA original (Módulo4.bas), que usa um conjunto DIFERENTE (`{"D/P", "-/P"}`, sem
o `"D/-"`) e não afeta roteamento nenhum, é só um aviso visual na tela de edição.

`CadastroPage.tsx` usa essa decisão pra escolher qual ação mostrar na aba "Recebidos":

```text
enviado ──┬── precisa_roteiro=True  ──> Cadastro clica "Encaminhar para roteiro"
          │                              (encaminhar_para_roteiro) ──> encaminhado_roteiro=True
          │                              ──> Processos edita (única exceção a "enviado é
          │                              travado pra sempre", ver abaixo) ──> Processos clica
          │                              "Concluir processamento" (concluir_processamento)
          │                              ──> processos_concluido=True
          │
          └── precisa_roteiro=False ──> Cadastro clica "Não precisa de roteiro"
                                         (concluir_sem_roteiro) ──> os dois campos viram True
                                         de uma vez, sem passar pelo Processos
```

As 3 funções de roteamento vivem em `scripts/bitin_lifecycle.py`, mesmo estilo de
`enviar_bitin` (mutam o `bitin`/`content` recebido, levantam `ValueError` se a pré-condição
não bate):

- `encaminhar_para_roteiro(bitin)` — exige `status == "enviado"` e ainda não encaminhado.
- `concluir_processamento(bitin)` — exige já encaminhado e ainda não concluído.
- `concluir_sem_roteiro(bitin)` — exige `status == "enviado"` e ainda não encaminhado; seta
  `encaminhado_roteiro`/`processos_concluido`/`sem_necessidade_roteiro` todos `True` de uma
  vez. O endpoint (`backend/api/bitins.py::concluir_sem_roteiro_endpoint`) reforça
  `precisa_roteiro` de novo no servidor antes de chamar — 400 se o BITin na verdade precisa
  de roteiro (não confia só no frontend esconder o botão errado).

**Única exceção a "enviado é travado pra sempre"**: enquanto `encaminhado_roteiro=True` e
`processos_concluido=False`, o setor Processos (nível `NIVEL_PROCESSOS=89`, ou admin) PODE
reeditar o BITin — `backend/api/bitins.py::_bitin_liberado_para_processos`/`_pode_editar`.
Isso NÃO reaproveita `POST /bitins/draft` (esse caminho reverte `status` pra `"rascunho"` via
`replace_one`, o que corromperia um BITin já enviado) — usa uma rota dedicada,
`POST /bitins/{mongo_id}/atualizar-processos`, que só troca o campo `content` via `$set`,
preservando status/número/histórico do envio.

Processos não cria BITin (`POST /bitins/draft` sem `mongo_id` recusa com 403 pra esse
nível) — só recebe da fila do Cadastro e revisa.

## Uso

- `scripts/bitin_model.py`:
  - `validate_bitin(bitin)` — valida cabeçalho obrigatório, formato do número do BITin, e campos
    obrigatórios por material (`codigo_material`, `centro`, `tipo_material`).
  - `bitin_to_plan2_rows(bitin, config)` — converte `materiais[]` em linhas de `Plan2` (mesmo
    formato usado por `scripts/vba_port_export.py`), prontas para alimentar `build_plan3_row()`
    direto, sem precisar de um arquivo `.xlsm` intermediário.
- `scripts/lista_tecnica_export.py` — export CS02/BOM (ver seção acima).
- `scripts/bitin_document.py` — Alt/Esp/checklist/diffs (ver seção acima).
- `scripts/bitin_lifecycle.py`, `scripts/bitin_view.py` — ciclo de vida e visualização (ver seção acima).
- `scripts/sap_paste_parser.py`, `scripts/csv_safety.py` — colar do SAP e sanitização (ver seção abaixo).

## Colar dados do SAP direto na interface (`sap_paste_parser.py`)

Decisão registrada: hoje o engenheiro copia a grade do SAP (ZBPP009 ou relatório
equivalente) e cola direto no Excel — o Excel separa em colunas sozinho porque o SAP usa
**TAB real** entre células (confirmado com o responsável do projeto). A futura interface web
deve suportar esse mesmo fluxo de "colar" — sem isso, o engenheiro perderia uma liberdade que
já tem hoje.

`parse_sap_paste(raw_text)` separa por `\t` (não por espaço/largura fixa) — decisão
deliberada, porque campos de texto livre como a descrição podem ter espaços internos (ex.:
`TUBO MENOR 1/2"`) que quebrariam qualquer parser baseado em espaço. Cada linha colada vira
um dict de 36 colunas (mesma estrutura de `Plan1`/`ZBPP009`, ver `plan1_column_headers` em
`config/vba_mapping.json`). `parse_sap_paste_to_materiais` já extrai os campos de
identificação + snapshot "atual" (`tipo_material`, `codigo_material`, `centro`,
`descricao_material`, `grupo_mercadorias_atual`, `tem_desenho`) prontos para virar
`materiais[]` no BITin.

**Importante**: um mesmo código de material pode aparecer em várias linhas coladas, cada uma
com um `centro` diferente (ex.: material `8661` em 2001/2003/2005/2006) — são materiais
distintos no BITin, não duplicata (ver correção na regra geral de duplicidade abaixo).

## Sanitização de exports (`csv_safety.py`)

Toda célula escrita nos exports (`vba_port_export.py`, `lista_tecnica_export.py`,
`bitin_model.py`) passa por `csv_safety.sanitize_row` antes de gravar — protege contra CSV/
formula injection (OWASP): células começando com `=`, `+` ou `@` são prefixadas com `'` pra
não serem interpretadas como fórmula quando o arquivo é aberto no Excel. **`-` (hífen) foi
deliberadamente excluído** dessa lista (diferente da recomendação OWASP completa) porque é um
valor de domínio legítimo e onipresente neste sistema — os códigos de `Alt` são literalmente
`"-"`, `"-/P"`, `"-/F"`; sanitizar isso quebraria o export real.
