# Release v0.1.0 — PoC: Robust Winshuttle exporter

Release criado a partir da tag `v0.1.0`.

Resumo

- Objetivo: entregar um PoC que reproduz com precisão o CSV de exportação usado pelo time (Winshuttle).
- Status: PoC estável; export gerado é idêntico ao arquivo de referência `exported_winshuttle.csv`.

Principais arquivos adicionados

- `scripts/robust_export.py` — exportador robusto que gera CSV/XLSX idênticos ao export real a partir da sheet `dados teste winshuttle`.
- `scripts/verify_poc.py` — utilitário de verificação ponta-a-ponta (gera PoC + compara com referência + escreve `reports/diff_report.txt`).
- `scripts/compare_report.py` — relatório de diferenças entre dois CSVs.
- `docs/README_HANDOFF.md` — documentação técnica completa do PoC e plano de migração.

Validação

- Executado `scripts/robust_export.py` produzindo `poc_winshuttle_export_robust.csv`.
- Comparação com `exported_winshuttle.csv` retornou equivalência total (48 linhas, sem diferenças).
- `scripts/verify_poc.py` executado e escreveu `reports/diff_report.txt` confirmando paridade.

Como reproduzir

```powershell
C:/Python314/python.exe scripts/robust_export.py "Novo_template_BITin_V2 TESTE.xlsm" --out poc_winshuttle_export_robust.csv
C:/Python314/python.exe scripts/verify_poc.py
```

Notas

- Próximos passos recomendados: portar as rotinas VBA críticas (Módulo1.PREENCHER, Módulo2.Winshuttle, Módulo11.clear_winshuttle) para servidor Python, adicionar testes automatizados e integrar ao pipeline CI.

Contatos

- Autor do PoC: (veja `agent/README.md` e `docs/README_HANDOFF.md` para contexto técnico)
