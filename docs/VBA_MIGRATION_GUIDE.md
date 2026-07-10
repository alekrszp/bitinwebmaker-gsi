# VBA Migration Guide

## Objetivo

Este documento descreve o estado atual da migração das rotinas VBA do workbook `Novo_template_BITin_V2 TESTE.xlsm` para código server-side/Python e define o plano de trabalho para os próximos passos.

## Estado atual

- A release `v0.1.0` foi publicada manualmente no GitHub.
- O repositório contém um PoC leve (`scripts/legacy_poc/winshuttle_export.py`) que valida contra `exported_winshuttle.csv` — porém esse PoC opera sobre a aba sintética `dados teste winshuttle`, não sobre o fluxo real `Plan1`→`Plan2`→`Plan3`. Ver `docs/VBA_EXPORT_MAPPING.md` seção "Nomes reais das abas".
- **P0 concluído em 2026-07-09**: o port fiel do fluxo real (`Módulo1`+`Módulo2`+`Módulo11`) está implementado em `scripts/vba_port_export.py` (subcomandos `sync` e `export`), orientado por `config/vba_mapping.json`, com testes em `tests/test_vba_port_export.py`. Detalhes completos do mapeamento estão em `docs/VBA_EXPORT_MAPPING.md`.
- A lógica de exportação já foi parcialmente documentada em `docs/vba_catalog.md` e `docs/vba_catalog.json`.
- Os módulos VBA extraídos estão em `artifacts/vba/`.
- **Descoberta importante (2026-07-09)**: o que parecia um conjunto de bugs no `Módulo2` (colunas "sempre vazias") na verdade é o padrão de design "atual vs. Novo" da aba `ZBPP009 + ALTERACAO` — confirmado lendo o cabeçalho real da aba e `POP_ENG_7.3.7_002` + `context.md`. Quem preenche as colunas `"... Novo"` é o **engenheiro solicitante**, ao montar o BITin (não a Central de Controle e Cadastro, que só executa a alteração no SAP a partir do que recebe). Ver `docs/VBA_EXPORT_MAPPING.md` seção "Padrão atual vs. Novo". Restam só 2 quirks reais (não relacionados a esse padrão): coluna 106 (debug) e coluna 65 (flag compartilhada) — baixo impacto, replicados fielmente.
- **Direção confirmada com o responsável do projeto**: o próximo passo não é portar mais módulos VBA (P1/P2) — é usar o motor Python já portado (P0) como backend de uma **interface web onde o engenheiro cria o BITin do zero**, substituindo a planilha Excel/VBA. O fluxo alvo: engenheiro cria e envia o BITin pelo sistema web → Central baixa e executa no SAP (`Módulo2`/Winshuttle para BITins grandes, manual para pequenos) → se envolver roteiro, vai por e-mail pra Engenharia de Processos e depois pro Windchill (isso continua fora do sistema web por enquanto). Cobrir todos os setores da empresa é meta de longo prazo; o foco imediato é só a relação engenheiro ↔ Central de Controle e Cadastro.

## Prioridades de portabilidade

### P0 — Exportação crítica ✅ portado

Estas rotinas são o núcleo do fluxo Winshuttle e foram portadas primeiro, em `scripts/vba_port_export.py`.

- `Módulo1.bas` — `PREENCHER`
  - Mapeia linhas de `Plan1` (`ZBPP009`) para `Plan2` (`ZBPP009 + ALTERACAO`).
  - Executa transformação de colunas, incluindo campos como `TIPO DO MATERIAL`, `CÓDIGO`, `DESCRIÇÃO`, `NCM`, `PLANEJADOR`, `TIPO DE SUPRIMENTO`, `VOLUME`, etc.
  - Importante: mantém o mesmo mapeamento de colunas usado no export final.
  - Portado declarativamente via `config/vba_mapping.json` (seção `plan1_to_plan2`).

- `Módulo2.bas` — `Winshuttle`
  - Lê valores do cabeçalho `BITIN`, `Produto`, `Motivo` e data.
  - Percorre `Plan2` e popula `Plan3` (`Formulário Winshuttle`) usando as colunas `"... Novo"` de `Plan2` (preenchidas pelo engenheiro) — ver padrão "atual vs. Novo" em `VBA_EXPORT_MAPPING.md`.
  - Implementa muitas regras de preenchimento condicional de campos vazios e flags `SIM`/`""`.
  - Portado declarativamente via `config/vba_mapping.json` (seção `plan2_to_plan3`), com os 2 quirks reais (coluna 106, coluna 65) isolados como casos especiais na engine.

- `Módulo11.bas` — `clear_winshuttle`
  - Limpa o template Winshuttle antes de gerar novo conteúdo.
  - Remove conteúdos e formatação das linhas de `Plan3` a partir da linha 3.
  - No port Python (stateless), equivale a sempre gerar uma lista nova de linhas — não há necessidade de "limpar" nada porque não há planilha persistente sendo reaproveitada.

### Melhorias entregues junto com o port (além da tradução literal)

- **Validação de entrada**: linhas de `Plan1` sem `TIPO DO MATERIAL` ou `CÓDIGO` são puladas e reportadas no `sync`, em vez de gerar linhas incompletas silenciosamente (o VBA original não validava nada).
- **Relatório de auditoria** (`--audit-report` no `export`): total de linhas lidas e quantas vezes o quirk da coluna 65 foi acionado — dá visibilidade sem mudar o resultado.
- **Mapeamento configurável**: as regras de coluna vivem em `config/vba_mapping.json`, não hardcoded no script — ajustar uma coluna no futuro (ex.: se o SAP mudar um campo) é uma mudança de config, não de código.
- **`sync` e `export` separados**: reflete que `Módulo1` e `Módulo2` rodam em momentos diferentes na vida real, com o engenheiro preenchendo as colunas `"... Novo"` entre um e outro — evita a armadilha de tentar derivar tudo automaticamente de `Plan1` (o que geraria export vazio, já que o valor "Novo" é entrada humana).
- **Testes unitários por regra**: `tests/test_vba_port_export.py` cobre cada tipo de regra (cópia direta, flag-se-não-vazio, flag-se-diferente-de-N/A) e os 2 quirks reais isoladamente, com dados sintéticos (já que não há dados reais em `ZBPP009`/`ZBPP009 + ALTERACAO` hoje).

### P1 — Integrações e eventos

- `Módulo4.bas` — `Preencher_Bitin` ✅ **portado** em `scripts/bitin_document.py` (Alt/Esp/checklist/diffs), validado contra BITin real.
- `Módulo10.bas` — `DWG_SAT` ✅ **portado** (mesmo arquivo, como sugestão opcional — ver `docs/BITIN_MODEL.md` "Alt/Esp declarados pelo engenheiro").
- `Módulo13.bas` — `DWG_SAT_N_DESENHO` ✅ **portado** (idem).
- `Módulo12.bas` — `EMAIL`, `Worksheet_Change` — não portado (notificação por e-mail, fora do fluxo de dados).
- `Plan2.cls` — `Worksheet_Change` — não portado (coloração visual cosmética no Excel, sem efeito no dado).

### P2 — Helpers e formatação

Macros de UI, limpeza e utilitários que podem ficar para depois ou ser substituídas por funções de editor/post-processamento.

- `Módulo3.bas` — `CLEAR_ZBPP009`
- `Módulo5.bas` — `INSERIR_LINHA`
- `Módulo6.bas` — `limpar3`
- `Módulo7.bas` — `MP`
- `Módulo8.bas` — `pintatudo`
- `Módulo9.bas` — `linhadivid`
- `Módulo14.bas` — `NEGRITO`
- `Módulo15.bas` — `dados_lista_técnia`
- `Módulo16.bas` — `Lib_bot`
- `Módulo17.bas` — `Limpeza`
- `Módulo18.bas` — `Lib_Manual`
- `Módulo19.bas` — `UsuarioRede`
- `Módulo20.bas` — `cor`
- `EstaPasta_de_trabalho.cls` — `Workbook_Open`

## O que documentar agora

Para avançar com segurança, a documentação deve incluir:

1. Um resumo do fluxo de dados
   - origem: `dados teste winshuttle`
   - etapas: `Plan1` -> `Plan2` -> `Formulário Winshuttle` / `Plan3`
   - saída: CSV/XLSX compatível com Winshuttle

2. O mapeamento de colunas usado por `Módulo1.PREENCHER`.

3. As regras condicionais usadas por `Módulo2.Winshuttle`.

4. As dependências de cada rotina P0:
   - quais colunas de `Plan2` são necessárias
   - quais valores de cabeçalho são precisos
   - quais campos de saída são obrigatórios

5. Como validar a saída final:
   - `scripts/verify_poc.py`
   - `reports/diff_report.txt`

## Relação com `GPT_Engineering_BITIN`

Existe um projeto irmão, `GPT_Engineering_BITIN`, que foi uma primeira tentativa (menos rigorosa) de resolver o mesmo problema. Ele definiu um `schema.json` para a estrutura de dados de um BITin (cabeçalho + `ordem_cliente` + `checklist` de 22 itens + `materiais[].alteracoes` com `lista_tecnica` e `dados_basicos` no padrão `{de, para}`). Esse repositório (`bitinwebmaker-gsi`) é a refação feita com entendimento completo do processo real (POP_ENG_7.3.7_002, `context.md`, VBA extraído) — `GPT_Engineering_BITIN` não é reaproveitado como código, só como referência de formato para o modelo de dados do BITin (ver `docs/BITIN_MODEL.md`).

## Próximo passo recomendado

**Atualizado em 2026-07-10 — os 4 itens abaixo (registrados em 2026-07-09) estão concluídos:**

1. ✅ Modelo de dados do BITin — `scripts/bitin_model.py`, `docs/BITIN_MODEL.md`.
2. ✅ Validação (formato do número, campos obrigatórios, enum de Alt/Est/Esp/LP/Pre/OC/OF) —
   `scripts/bitin_business_rules.py`, erros estruturados em `scripts/bitin_errors.py`.
3. ✅ Geração do `.xlsm` real da aba `Plan2` — `bitin_model.write_plan2_xlsx`.
4. 🔶 Interface web — **backend pronto** (`backend/`, FastAPI + Postgres + MongoDB +
   autenticação unificada, ver `docs/BACKEND.md`); frontend (formulário pro engenheiro) ainda
   não construído — esse é o próximo passo real agora.

Também concluído desde então: lista técnica/CS02 (`scripts/lista_tecnica_export.py`),
documento do BITin/checklist (`scripts/bitin_document.py`, P1 do VBA), ciclo de vida
rascunho/enviado (`scripts/bitin_lifecycle.py`), parser de colar do SAP
(`scripts/sap_paste_parser.py`). Ver `CHANGELOG.md` (v0.2.0) para o resumo completo.

Módulos ainda não portados (`Módulo12.EMAIL`/`Worksheet_Change`, `Plan2.cls.Worksheet_Change`,
P2 inteiro) seguem registrados como trabalho futuro — só retomar se o frontend precisar
replicar algum desses comportamentos.

## Arquivos de referência

- `artifacts/vba/Módulo1.bas`
- `artifacts/vba/Módulo2.bas`
- `artifacts/vba/Módulo11.bas`
- `artifacts/vba/Plan1.cls`, `Plan2.cls` — codenames reais das abas `ZBPP009` / `ZBPP009 + ALTERACAO`
- `scripts/vba_port_export.py` — port fiel do P0
- `scripts/bitin_document.py` — port do P1 (`Módulo4`+`Módulo10`+`Módulo13`)
- `scripts/bitin_model.py`, `bitin_business_rules.py`, `bitin_lifecycle.py`, `bitin_view.py` — modelo/regras/ciclo de vida do BITin
- `backend/` — API (FastAPI + Postgres + MongoDB), ver `docs/BACKEND.md`
- `config/vba_mapping.json` — mapeamento declarativo usado pelo port
- `tests/` — suíte completa (147 testes)
- `scripts/poc_export.py`
- `scripts/robust_export.py`
- `scripts/verify_poc.py`
- `docs/vba_catalog.md`
- `docs/vba_catalog.json`
- `docs/VBA_EXPORT_MAPPING.md` — mapeamento detalhado e quirks

---

*Este arquivo serve como guia para a próxima fase da migração de VBA para Python.*
