# VBA Export Mapping

Este documento descreve o mapeamento exato de campos usados pelas rotinas VBA críticas do fluxo de exportação Winshuttle.

> **Atualizado em 2026-07-09** após leitura direta de `artifacts/vba/Módulo1.bas`, `Módulo2.bas` e `Módulo11.bas` e comparação com o workbook real. A versão anterior deste documento continha algumas imprecisões (ver seção "Correções feitas em 2026-07-09" no final).

## Nomes reais das abas (codename VBA -> nome exibido)

`Plan1`, `Plan2` e `Plan3` são **codenames VBA**, não os nomes exibidos nas abas do Excel. O mapeamento real, obtido via `sheet_properties.codeName` do openpyxl no workbook `Novo_template_BITin_V2 TESTE.xlsm`, é:

| Codename VBA | Aba exibida |
|---|---|
| `Plan1` | `ZBPP009` |
| `Plan2` | `ZBPP009 + ALTERACAO` |
| `Plan3` | `Formulário Winshuttle` |

Importante: a aba **`dados teste winshuttle`** (codename `Planilha3`), usada pelo PoC leve em `scripts/winshuttle_export.py`, **não é** `Plan1`. É uma amostra sintética independente, com apenas 24 colunas e já contendo pares valor/flag pré-preenchidos manualmente — não passa pela transformação real `Módulo1`→`Módulo2`. O PoC leve e o port fiel descrito abaixo são fluxos separados.

No momento da escrita, `ZBPP009` (Plan1 real) tem apenas 1 linha (cabeçalho, sem dados de material), então não há hoje um gabarito real de ponta a ponta — a validação do port fiel é feita com dados sintéticos construídos a partir da leitura literal do código VBA (ver `tests/test_vba_port_export.py`).

## Visão geral do fluxo

1. `Módulo1.PREENCHER` lê a partir da planilha `Plan1` (`ZBPP009`) e preenche `Plan2` (`ZBPP009 + ALTERACAO`).
2. `Módulo11.clear_winshuttle` limpa o template `Plan3` (`Formulário Winshuttle`) antes de gerar um novo export.
3. `Módulo2.Winshuttle` lê `Plan2` e popula `Plan3` linha a linha.

O objetivo final é reproduzir esse comportamento em Python para gerar CSV/XLSX compatíveis com o export do workbook. O port fiel vive em `scripts/vba_port_export.py`, orientado pelo mapeamento declarativo em `config/vba_mapping.json` (ver seção 8).

---

## 1. Mapeamento `Plan1 -> Plan2` (`Módulo1.PREENCHER`)

- Origem: `Plan1`, linha inicial `2`, coluna base 1.
- Destino: `Plan2`, linha inicial `5`.
- A rotina copia valores de `Plan1` para colunas específicas de `Plan2` conforme o mapeamento abaixo.
- A rotina repete até encontrar `Empty` em `Plan1.Cells(Linha1, 1)`.

| Plan2 coluna | Plan2 campo aproximado | Plan1 coluna | Comentário |
|--------------|------------------------|--------------|-----------|
| 3  | TIPO DO MATERIAL                        | 1  |   |
| 4  | CENTRO                                 | 4  |   |
| 5  | CÓDIGO                                 | 2  |   |
| 6  | DESCRIÇÃO                              | 5  |   |
| 8  | GRUPO DE MERCADORIAS                   | 6  |   |
| 10 | STATUS                                 | 7  |   |
| 12 | HIERARQUIA                             | 8  |   |
| 14 | PESO BRUTO                             | 9  |   |
| 16 | PESO LÍQUIDO                           | 10 |   |
| 18 | UNIDADE PESO                           | 11 |   |
| 20 | VOLUME                                 | 12 |   |
| 22 | UNIDADE VOLUME                         | 13 |   |
| 24 | DESENHO                                | 14 |   |
| 26 | NÍVEL REVISÃO                          | 15 |   |
| 28 | DOCUMENTO                              | 16 |   |
| 30 | MATERIAL SUBSTITUTO                    | 17 |   |
| 31 | MATERIAL SUBSTITUTO NOVO               | N/A | constante `N/A` |
| 32 | STATUS BLOQUEIO DE VENDAS              | 18 |   |
| 33 | STATUS BLOQUEIO DE VENDAS NOVO         | N/A | constante `N/A` |
| 34 | DATA BLOQUEIO DE VENDAS                | 19 |   |
| 35 | DATA BLOQUEIO DE VENDAS NOVO           | N/A | constante `N/A` |
| 36 | GRUPO ESTAT. MATERIAL                  | 20 |   |
| 38 | GRUPO DE COMPRADORES                   | 21 |   |
| 40 | NCM                                    | 22 |   |
| 42 | GRUPO DE COMPRADORES NOVO              | N/A | constante `N/A` |
| 44 | PLANEJADOR                             | 24 |   |
| 46 | TIPO DE SUPRIMENTO                     | 25 |   |
| 48 | TIPO SUPRIMENTO ESPECIAL               | 26 |   |
| 49 | TIPO SUPRIMENTO ESPECIAL NOVO          | N/A | constante `N/A` |
| 50 | DEPÓSITO PRODUÇÃO                      | 27 |   |
| 51 | DEPÓSITO PRODUÇÃO NOVO                 | N/A | constante `N/A` |
| 52 | DEPÓSITO SUPRIMENTO EXTERNO            | 28 |   |
| 53 | DEPÓSITO SUPRIMENTO EXTERNO NOVO       | N/A | constante `N/A` |
| 54 | PRAZO DE ENTREGA                       | 29 |   |
| 55 | PRAZO DE ENTREGA NOVO                  | N/A | constante `N/A` |
| 56 | RESP. CTR. PRODUÇÃO                    | 30 |   |
| 57 | RESP. CTR. PRODUÇÃO NOVO               | N/A | constante `N/A` |
| 58 | PERFIL DE PRODUÇÃO                     | 31 |   |
| 59 | PERFIL DE PRODUÇÃO NOVO                | N/A | constante `N/A` |
| 60 | UTILIZAÇÃO MATERIAL                    | 32 |   |
| 62 | ORIGEM MATERIAL                        | 33 |   |
| 64 | PRODUÇÃO INTERNA                       | 34 |   |
| 65 | PRODUÇÃO INTERNA NOVO                  | N/A | constante `N/A` |
| 66 | TEXTO PEDIDO DE COMPRAS                | 35 |   |
| 67 | TEXTO PEDIDO DE COMPRAS NOVO           | N/A | constante `N/A` |
| 68 | MARCAÇÃO PARA ELIMINAR NÍVEL MANDANTE  | 36 |   |

> Observação: a rotina copiou `Plan1.Cells(Linha1, 36)` para `Plan2.Cells(Linha2, 68)`.

---

## 2. Limpeza de formulário Winshuttle (`Módulo11.clear_winshuttle`)

- A rotina limpa `Plan3` a partir da linha 3 até o fim do conteúdo.
- Remove valores e também o preenchimento de interior da seleção.
- Em Python, isso equivale a resetar as linhas de saída antes de preencher o novo formulário.

---

## 3. Mapeamento `Plan2 -> Plan3` (`Módulo2.Winshuttle`)

- Origem: `Plan2`, linha inicial `5`.
- Destino: `Plan3`, linha inicial `3`.
- Loop encerra quando `Plan2.Cells(Linha2, 3).Value = Empty`.
- Cabeçalho de saída usa:
  - `BITIN`   = `Plan2.Cells(1, 2)`
  - `Produto` = `Plan2.Cells(2, 2)`
  - `Motivo`  = `Plan2.Cells(3, 2)`
  - `Data`    = `Now` formatado `dd.mm.yyyy`

### Padrão "atual vs. Novo" (não é bug — é o mecanismo central do BITin de Alteração)

A aba real `ZBPP009 + ALTERACAO` (Plan2) tem, para quase todo campo de negócio, **duas colunas**: o valor atual (auto-preenchido a partir de `ZBPP009`/Plan1 pelo `Módulo1`) e uma coluna `"... Novo"` adjacente. Confirmado lendo o cabeçalho real da aba (linha 4): `Descrição` / `Descrição Nova`, `Status` / `Status Novo`, `NCM` / `NCM Novo`, `Grupo Compradores` / `Grupo Compradores Novo`, etc. — o padrão se repete para praticamente todos os ~30 campos de negócio.

Conforme `context.md` (Fluxo B — Execução de BITin de Alteração): **o engenheiro solicitante** preenche o BITin, incluindo o que muda em cada código, e envia para a Central de Controle e Cadastro executar no SAP. Ou seja, é o **engenheiro** quem preenche as colunas `"... Novo"` (hoje, na planilha; no novo fluxo web, pelo formulário) — a Central não digita esses valores, ela só executa a alteração no SAP a partir do que recebe.

O `Módulo2.Winshuttle` lê exatamente essas colunas `"... Novo"` — nunca a coluna de "valor atual" — e só gera `SIM`/valor no export quando o campo `"... Novo"` foi de fato preenchido (ou é diferente de `"N/A"`, para os campos que usam esse padrão de placeholder). Isso implementa corretamente a semântica de "exportar só o que mudou", que é exatamente como uma alteração parcial de material funciona no Winshuttle/SAP (campos deixados em branco preservam o valor atual no SAP).

**Importante para o port Python**: como esse valor "Novo" depende de entrada humana (hoje na planilha, no futuro no formulário web do engenheiro), ele não pode ser derivado automaticamente de `Plan1`/`ZBPP009` — é dado de entrada do BITin em si, não um cálculo. Por isso o port lê a aba `Plan2` real diretamente (fiel ao Excel), em vez de tentar recalcular tudo a partir de `Plan1`.

### Mapeamento de campos diretos

Tabela **verificada linha a linha contra `artifacts/vba/Módulo2.bas`** (fonte de verdade). Onde a versão anterior deste documento divergia do código real, a coluna "campo" foi corrigida.

| Plan3 col | Plan3 campo | Plan2 col | Condição/algo extra |
|-----------|-------------|-----------|---------------------|
| 1  | BITIN        | (=header, `Plan2!B1`) | constante por linha |
| 2  | Produto      | (=header, `Plan2!B2`) | constante por linha |
| 3  | Motivo       | (=header, `Plan2!B3`) | constante por linha |
| 4  | Data         | `Now` formatado `dd.mm.yyyy` | constante por linha |
| 6  | ativo `SIM`  | texto fixo | sempre `SIM` |
| 106 | TIPO MATERIAL | 3  | ⚠️ ver quirk 1 abaixo |
| 10 | CENTRO       | 4  |   |
| 9  | CÓDIGO       | 5  |   |
| 12 | Descrição Nova | 7  |   |
| 11 | flag         | (= col 12) | `SIM` se col 12 não vazia, senão `""` |
| 14 | Grupo Mercadorias Novo | 9  |   |
| 13 | flag         | (= col 14) | `SIM` se col 14 não vazia, senão `""` |
| 16 | Status Novo  | 11 |   |
| 15 | flag         | (= col 16) | `SIM` se col 16 não vazia, senão `""` |
| 18 | Hierarquia Nova | 13 |   |
| 17 | flag         | (= col 18) | `SIM` se col 18 não vazia, senão `""` |
| 20 | Peso Bruto Novo | 15 |   |
| 19 | flag         | (= col 20) | `SIM` se col 20 não vazia, senão `""` |
| 22 | Peso Líquido Novo | 17 |   |
| 21 | flag         | (= col 22) | `SIM` se col 22 não vazia, senão `""` |
| 24 | Unidade Peso Novo | 19 |   |
| 23 | flag         | (= col 24) | `SIM` se col 24 não vazia, senão `""` |
| 26 | Volume Novo  | 21 |   |
| 25 | flag         | (= col 26) | `SIM` se col 26 não vazia, senão `""` |
| 28 | Unidade Vol. Novo | 23 |   |
| 27 | flag         | (= col 28) | `SIM` se col 28 não vazia, senão `""` |
| 30 | Desenho novo | 25 |   |
| 29 | flag         | (= col 30) | `SIM` se col 30 não vazia, senão `""` |
| 32 | Nível Revisão Novo | 27 |   |
| 31 | flag         | (= col 32) | `SIM` se col 32 não vazia, senão `""` |
| 38 | Documento Novo | 29 |   |
| 37 | flag         | (= col 38) | `SIM` se col 38 não vazia, senão `""` |
| 39 | flag         | `Material Substituto Novo` | apenas se Plan2 col 31 <> `"N/A"` então `SIM` |
| 40 | Material Substituto Novo | 31 | valor quando <> `"N/A"` (senão vazio) |
| 42 | Status Bloqueio vendas Novo | 33 | copiado sempre (mesmo `"N/A"`, quando o engenheiro não editou) |
| 41 | flag         | (= Plan2 col 33) | `""` se Plan2 col 33 = `"N/A"`, senão `SIM` |
| 43 | Data bloqueio vendas novo | 35 |   |
| 48 | NCM Novo     | 41 |   |
| 47 | flag         | (= col 48) | `SIM` se col 48 não vazia, senão `""` |
| 51 | flag         | `Grupo Compradores Novo` | apenas se Plan2 col 43 <> `"N/A"` então `SIM` |
| 52 | Grupo Compradores Novo | 43 | valor quando <> `"N/A"` |
| 54 | Planejador Novo | 45 |   |
| 53 | flag         | (= col 54) | `SIM` se col 54 não vazia, senão `""` |
| 56 | Tipo Suprimento Novo | 47 |   |
| 55 | flag         | (= col 56) | `SIM` se col 56 não vazia, senão `""` |
| 57 | flag         | `Tipo Sup. Especial Novo` | apenas se Plan2 col 49 <> `"N/A"` então `SIM` |
| 58 | Tipo Sup. Especial Novo | 49 | valor quando <> `"N/A"` |
| 59 | flag         | `Depósito Produção Novo` | apenas se Plan2 col 51 <> `"N/A"` então `SIM` |
| 60 | Depósito Produção Novo | 51 | valor quando <> `"N/A"` |
| 61 | flag         | `Depósito Sup. Externo Novo` | apenas se Plan2 col 53 <> `"N/A"` então `SIM` |
| 62 | Depósito Sup. Externo Novo | 53 | valor quando <> `"N/A"` |
| 63 | flag         | `Prazo de Entrega Novo` | apenas se Plan2 col 55 <> `"N/A"` então `SIM` |
| 64 | Prazo de Entrega Novo | 55 | valor quando <> `"N/A"` |
| 65 | flag (compartilhado) | `Resp. Crtrl. Produção Novo` **e** `Perfil de Produção Novo` | ⚠️ ver quirk 2 — as duas regras escrevem `SIM` na mesma coluna 65 |
| 66 | Resp. Crtrl. Produção Novo | 57 | valor quando <> `"N/A"` |
| 67 | Perfil de Produção Novo | 59 | valor quando <> `"N/A"` |
| 69 | Utilização Material Novo | 61 |   |
| 68 | flag         | (= col 69) | `SIM` se col 69 não vazia, senão `""` |
| 71 | Origem Material Novo | 63 |   |
| 70 | flag         | (= col 71) | `SIM` se col 71 não vazia, senão `""` |
| 72 | flag         | `Produção Interna Novo` | apenas se Plan2 col 65 <> `"N/A"` então `SIM` |
| 73 | Produção Interna Novo | 65 | valor quando <> `"N/A"` |
| 74 | flag         | `Texto Pedidos Compras Novo` | apenas se Plan2 col 67 <> `"N/A"` então `SIM` |
| 75 | Texto Pedidos Compras Novo | 67 | valor quando <> `"N/A"` |
| 82 | Marcação eliminar nível mandante/centro Novo | 69, depois 71 | valor bruto de Plan2 col 69 (marcação nível mandante); sobrescrito para `SIM` se Plan2 col 71 (marcação nível centro) = `"SIM"` |

> Observação: há um bloco inteiro comentado em `Módulo2.bas` (colunas 45/46, "GRUPO ESTAT. MATERIAL") que nunca é executado — não faz parte do mapeamento ativo. As colunas 72-79 de `Plan2` (Criar Visões de vendas, Bloqueio Cálculo Custos, ESTOQUE, LISTA DE PREÇO, PRECIFICAÇÃO, ORDEM DE CLIENTE, ORDEM DE FABRICAÇÃO — os mesmos campos do BITin descritos no POP_ENG_7.3.7_002) também não são lidas pelo `Módulo2`; hoje servem só para o checklist/roteamento manual do BITin, fora do escopo do export Winshuttle.

### Correções feitas em 2026-07-09

A versão anterior deste documento tinha duas classes de erro, corrigidas após ler `Módulo2.bas` linha a linha **e** o cabeçalho real da aba `ZBPP009 + ALTERACAO`:
- Erros de transcrição simples: PERFIL DE PRODUÇÃO usava coluna 67 como valor e citava a coluna 68 como flag (real: coluna 65, compartilhada — quirk 2); UTILIZAÇÃO MATERIAL e ORIGEM MATERIAL estavam com os pares valor/flag trocados.
- **Erro de interpretação mais sério**: a primeira revisão deste documento tratava as colunas que o `Módulo2` lê (7, 9, 11, 13... e todas as `"... Novo"`) como "colunas nunca preenchidas pelo Módulo1, logo sempre vazias/bug". Na verdade essas são as colunas que o **engenheiro** preenche manualmente com o valor novo, ao montar o BITin — não são calculadas pelo `Módulo1`, são entrada humana. Ver seção "Padrão atual vs. Novo" acima.

### Quirks reais (as únicas duas exceções que não seguem o padrão atual/Novo)

1. **Coluna 106 (TIPO MATERIAL)**: `Módulo2` grava o tipo de material também na coluna 106 do Plan3, bem fora do intervalo normal (1-82). Parece um resíduo de debug/consulta manual, não uma coluna real do formulário Winshuttle. Preservado fielmente no port.
2. **Coluna 65 (flag compartilhada)**: tanto a regra de `Resp. Crtrl. Produção Novo` (Plan2 col 57) quanto a de `Perfil de Produção Novo` (Plan2 col 59) escrevem `"SIM"` na mesma coluna 65 quando aplicável — provável copy-paste, já que as duas têm colunas de valor próprias (66 e 67) mas dividem a coluna de flag. Como as duas regras só escrevem `"SIM"` (nunca um valor diferente), isso não corrompe dados, mas impede saber qual das duas mudou quando as duas mudam na mesma linha. Preservado fielmente no port; sinalizado no relatório de auditoria (`--audit-report`) quando ambas disparam na mesma linha.

---

## 4. Regras especiais e condicionalidades

- Para vários campos há um par de colunas no `Plan3`:
  - uma coluna de valor real;
  - uma coluna de flag que recebe `SIM` se há valor, ou `""` se está vazio.
- Para alguns campos com valores `N/A` no `Plan2`, a rotina escreve a marcação `SIM` apenas se o valor for diferente de `N/A`.
- Isso significa que para a portabilidade em Python devemos tratar `N/A` como um sinal de valor omitido em vários campos.

---

## 5. Observação de cabeçalho

- A rotina `Módulo2.Winshuttle` recebe o valor de `BITIN`, `Produto` e `Motivo` diretamente de `Plan2`:
  - `Plan2.Cells(1, 2)`
  - `Plan2.Cells(2, 2)`
  - `Plan2.Cells(3, 2)`
- Em Python, esses valores devem ser lidos do `Plan2` ou do equivalente de input/header usado para gerar a exportação.

---

## 6. Uso em Python

O `Módulo1` e o `Módulo2` são executados em **momentos diferentes** no processo real, com um passo humano no meio (o engenheiro preenche as colunas `"... Novo"` ao montar o BITin). O port respeita essa separação em vez de encadear tudo em memória:

1. **Sync** (`Módulo1.PREENCHER`): lê `Plan1` (`ZBPP009`) e (re)popula as colunas de "valor atual" de `Plan2` (`ZBPP009 + ALTERACAO`) — não toca nas colunas `"... Novo"`, que são do engenheiro.
2. **Preenchimento humano** (fora do Python, hoje na planilha — no fluxo novo, no formulário web do engenheiro): alguém digita os valores `"... Novo"` para os campos que realmente mudam, mais o cabeçalho (`BITIN`, `Produto`, `Motivo`).
3. **Export** (`Módulo2.Winshuttle`): lê `Plan2` **como está no arquivo real** (fiel ao Excel — não recalculado a partir de `Plan1`) e aplica o mapeamento para gerar as linhas de `Plan3`/CSV.
4. **Limpeza** (`Módulo11.clear_winshuttle`): no port stateless, equivale a sempre gerar uma lista nova — não há estado residual a limpar.

Essa sequência está implementada em `scripts/vba_port_export.py` (ver seção 8): `sync_plan2_from_plan1()` para o passo 1, e a leitura direta de `Plan2` + `build_plan3_row()` para o passo 3.

---

## 7. Recomendações

- Use `N/A` como filtro especial nos campos que geram flags `SIM` a partir dos pares "atual/Novo".
- Garanta que linhas vazias em `Plan2.Col3` terminem o loop.
- Preserve o formato de data `dd.mm.yyyy` para a coluna `Data`.
- O quirk 2 (coluna 65 compartilhada, seção 3) vale a pena corrigir no VBA original em algum momento — baixo risco, mas o port Python não corrige por padrão (replica fielmente e sinaliza no relatório de auditoria).

---

## 8. Port fiel: `scripts/vba_port_export.py` + `config/vba_mapping.json`

Diferente do PoC leve (`scripts/winshuttle_export.py`, que opera sobre a aba sintética `dados teste winshuttle`), este port:

- Oferece **duas operações separadas**, refletindo que `Módulo1` e `Módulo2` rodam em momentos diferentes na vida real (ver seção 6): `sync` (recalcula as colunas de valor atual de `Plan2` a partir de `Plan1`/`ZBPP009`) e `export` (lê `Plan2` como está no arquivo — incluindo as colunas `"... Novo"` já preenchidas pelo engenheiro — e gera `Plan3`).
- Aplica o mapeamento `Plan1`→`Plan2` e `Plan2`→`Plan3` de forma **declarativa**, orientado por `config/vba_mapping.json` — a maioria das regras (cópia direta, par valor/flag, par valor/flag condicionado a `N/A`) é dado, não código. As duas exceções verdadeiramente especiais (coluna 106 e a coluna 65 compartilhada — os quirks da seção 3) ficam isoladas e comentadas na engine (`scripts/vba_port_export.py`).
- Lê o cabeçalho (`BITIN`, `Produto`, `Motivo`) diretamente das células `Plan2!B1`, `Plan2!B2`, `Plan2!B3` por padrão, com opção de sobrescrever via CLI.
- Valida cada linha de `Plan1` antes do `sync` (campos obrigatórios: TIPO DO MATERIAL e CÓDIGO não podem ser vazios) e produz um **relatório de auditoria** (`--audit-report`) no `export`: total de linhas lidas, linhas puladas por validação, e quantas vezes o quirk 2 (flag compartilhada) foi acionado.
- Testado em `tests/test_vba_port_export.py` com linhas sintéticas que exercitam cada tipo de regra (cópia direta, flag-se-não-vazio, flag-se-diferente-de-N/A) e o quirk documentado.

Uso:

```powershell
# sync: atualiza as colunas de valor atual de Plan2 a partir de Plan1/ZBPP009
.venv/Scripts/python.exe scripts/vba_port_export.py sync "Novo_template_BITin_V2 TESTE.xlsm" --out-xlsx plan2_sync.xlsx

# export: lê Plan2 (com as colunas "... Novo" já preenchidas) e gera o export Winshuttle
.venv/Scripts/python.exe scripts/vba_port_export.py export "Novo_template_BITin_V2 TESTE.xlsm" --out plan3_export.csv --audit-report reports/vba_port_audit.txt
```

---

## 9. Direção futura: criação de BITin pela web

O objetivo de médio prazo (fora do escopo imediato) é substituir a planilha Excel/VBA por um formulário web onde o engenheiro solicitante cria o BITin do zero — cobrindo tanto o cabeçalho/roteamento do template formal (`ANEXO A` do `POP_ENG_7.3.7_002`: Número, Solicitante, Data, Produto, Motivo, BITex, e por código: Alt/Est/Esp/LP/Pre/OC/OF) quanto os campos técnicos campo-a-campo (as colunas `"... Novo"` desta seção). O resultado é enviado para a Central de Controle e Cadastro (hoje por e-mail; no fluxo novo, pelo próprio sistema web) já pronto para gerar o export Winshuttle com `scripts/vba_port_export.py`. O foco imediato é o backend Python (modelo de dados do BITin + geração de `.xlsm` + export fiel); a interface web para o engenheiro vem depois.
