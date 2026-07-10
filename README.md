# bitinwebmaker-gsi

Sistema de criação e gestão de BITin (Boletim de Informações Técnicas Internas), migrando o
fluxo hoje feito em Excel/VBA (`Novo_template_BITin_V2 TESTE.xlsm`) para Python + API web.

## Documentação principal

- `requirements.md` — como a colaboração neste projeto funciona (leia antes de mexer em código).
- `docs/BITIN_MODEL.md` — modelo de dados do BITin, regras de negócio, ciclo de vida.
- `docs/VBA_EXPORT_MAPPING.md` — mapeamento de colunas do fluxo real `Módulo1`/`Módulo2`.
- `docs/VBA_MIGRATION_GUIDE.md` — estado da migração VBA → Python.
- `docs/BACKEND.md` — arquitetura da API (`backend/`).
- `docs/README_HANDOFF.md` — histórico do PoC original (inventário, macros, comparação com export real).

## Uso rápido (motor Python — `scripts/`)

1. Gerar o export fiel do fluxo real `Plan1` (`ZBPP009`) -> `Plan2` -> `Plan3` (`Formulário
   Winshuttle`). `Módulo1` (sync) e `Módulo2` (export) são subcomandos separados, porque na
   vida real o engenheiro preenche as colunas "... Novo" de `Plan2` entre um passo e outro:

   ```powershell
   # sync: atualiza os valores atuais de Plan2 a partir de Plan1/ZBPP009
   .venv/Scripts/python.exe scripts/vba_port_export.py sync "examples/Novo_template_BITin_V2 TESTE.xlsm" --out-xlsx plan2_sync.xlsx

   # export: lê Plan2 (com as colunas "Novo" já preenchidas pelo engenheiro) e gera o export Winshuttle
   .venv/Scripts/python.exe scripts/vba_port_export.py export "examples/Novo_template_BITin_V2 TESTE.xlsm" --out plan3_export.csv --audit-report reports/vba_port_audit.txt
   ```

   Veja `docs/VBA_EXPORT_MAPPING.md` para o mapeamento completo de colunas e o padrão "atual
   vs. Novo".

2. Validar um BITin (JSON, ver `docs/BITIN_MODEL.md`) e gerar a aba `Plan2` real:

   ```powershell
   .venv/Scripts/python.exe scripts/bitin_model.py meu_bitin.json --out-xlsx plan2_gerado.xlsx
   ```

3. Gerar o export de lista técnica (CS02/BOM):

   ```powershell
   .venv/Scripts/python.exe scripts/lista_tecnica_export.py meu_bitin.json --out-csv lista_tecnica.csv
   ```

4. Rodar a suíte de testes (129 testes cobrindo tudo acima):

   ```powershell
   .venv/Scripts/python.exe -m unittest discover -s tests
   ```

## Backend (API)

`backend/` expõe uma API FastAPI em cima da lógica de `scripts/` — validação real, ciclo de
vida rascunho/enviado, persistência (Postgres + MongoDB). Ver `docs/BACKEND.md` para
arquitetura completa e decisões.

```powershell
.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
.venv/Scripts/python.exe -m uvicorn backend.main:app --reload
```

Sem autenticação por enquanto (foco na lógica do BITin primeiro). Sem Postgres/MongoDB
configurados em `.env`, a API sobe mas as operações de banco falham ao serem chamadas — ver
`docs/BACKEND.md` para como os testes automatizados rodam sem bancos reais (SQLite +
mongomock-motor).

## Release manual

A release `v0.1.0` foi criada manualmente no GitHub usando `docs/RELEASE_v0.1.0.md` como corpo da release.

O processo de release não é automatizado no repositório, portanto a publicação deve ser feita pelo GitHub web interface.

Release URL: <https://github.com/alekrszp/bitinwebmaker-gsi/releases/tag/v0.1.0>

Veja também `docs/CHANGELOG.md` para as notas de release.

## Arquivos principais

**Motor Python (`scripts/`)**

- `vba_port_export.py` — port fiel do fluxo real `Módulo1`+`Módulo2`+`Módulo11` (sync/export)
- `bitin_model.py` — valida o JSON do BITin e gera a aba `Plan2` real
- `bitin_business_rules.py` — regras do POP + regras gerais de consistência (portão de envio)
- `bitin_document.py` — Alt/Esp/checklist/diffs (`Módulo4`+`Módulo10`+`Módulo13`)
- `bitin_lifecycle.py` — ciclo de vida rascunho ↔ enviado
- `bitin_view.py` — modelo de visualização/resumo do BITin
- `lista_tecnica_export.py` — export de lista técnica (CS02/BOM), automação nova (nunca existiu em VBA)
- `sap_paste_parser.py` — parser do texto colado do SAP (TAB-delimited)
- `csv_safety.py` — sanitização contra CSV/formula injection
- `bitin_errors.py` — formato de erro estruturado (`{field, code, message}`)

**Config (`config/`)**: `vba_mapping.json`, `bitin_document_mapping.json`, `lista_tecnica_mapping.json`

**Backend (`backend/`)**: API FastAPI (ver seção acima e `docs/BACKEND.md`)

**Documentação (`docs/`)**: `BITIN_MODEL.md`, `VBA_EXPORT_MAPPING.md`, `VBA_MIGRATION_GUIDE.md`, `BACKEND.md`

**Arquivos de exemplo/dados reais (`examples/`)**: `Novo_template_BITin_V2 TESTE.xlsm` (template original), `exported_winshuttle.csv` (referência), `bitin teste.xlsm`, `bitin teste 2.xlsm` (BITins reais usados para validar o motor), `POP_ENG_7 3 7_002.pdf`

**PoC legado (`scripts/legacy_poc/`)**: scripts e saídas do PoC leve original (v0.1.0), superados pelo motor atual — mantidos como histórico documentado, não usar para trabalho novo.

## Dependências

```powershell
.venv/Scripts/python.exe -m pip install pandas openpyxl oletools numpy msoffcrypto-tool
.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
```

## Próximo passo

Ler `docs/BITIN_MODEL.md` (modelo de dados e regras) e `docs/BACKEND.md` (API) para a visão
completa do sistema atual. `docs/README_HANDOFF.md` guarda o histórico do PoC original
(v0.1.0).
