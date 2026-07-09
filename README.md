# bitinwebmaker-gsi

Este repositório contém o PoC e a documentação de migração do fluxo BITin / Winshuttle.

## Documentação principal

A documentação completa está em:

- `docs/README_HANDOFF.md`

Esse arquivo reúne:
- inventário do arquivo Excel
- análise das macros e do fluxo de exportação
- scripts criados para PoC e validação
- resultados da comparação com o export real
- próximos passos para migração e implementação

## Uso rápido

1. Inspecionar o arquivo `.xlsm`:

```powershell
C:/Python314/python.exe scripts/inspect_xlsm_local.py "Novo_template_BITin_V2 TESTE.xlsm" --out docs/inventory.md
```

2. Gerar PoC de exportação com metadata:

```powershell
C:/Python314/python.exe scripts/export_from_itemsheet.py "Novo_template_BITin_V2 TESTE.xlsm" --out poc_winshuttle_export_full.csv --metadata-from exported_winshuttle.csv --out-with-meta poc_winshuttle_export_full_with_meta.csv
```

3. Gerar exportação robusta diretamente da sheet:

```powershell
C:/Python314/python.exe scripts/robust_export.py "Novo_template_BITin_V2 TESTE.xlsm" --out poc_winshuttle_export_robust.csv
```

4. Comparar com o arquivo de referência:

```powershell
C:/Python314/python.exe scripts/compare_report.py poc_winshuttle_export_full_with_meta.csv exported_winshuttle.csv reports/diff_report.txt
```

5. Verificar o PoC completo em um só passo:

```powershell
C:/Python314/python.exe scripts/verify_poc.py
```

## Arquivos principais

- `Novo_template_BITin_V2 TESTE.xlsm`
- `exported_winshuttle.csv`
- `poc_winshuttle_export_full.csv`
- `poc_winshuttle_export_full_with_meta.csv`
- `poc_winshuttle_export_full_with_meta.xlsx`
- `reports/diff_report.txt`
- `docs/README_HANDOFF.md`
- `docs/inventory.md`
- `docs/vba_catalog.md`
- `scripts/export_from_itemsheet.py`
- `scripts/compare_report.py`
- `scripts/verify_poc.py`

## Dependências

```powershell
C:/Python314/python.exe -m pip install --user pandas openpyxl oletools numpy msoffcrypto-tool
```

## Próximo passo

Ler `docs/README_HANDOFF.md` para a visão completa e o plano de migração.
