# Release v0.2.0 — Modelo de BITin, regras de negócio, ciclo de vida e backend API

Release criado a partir da tag `v0.2.0`.

## Resumo

- Objetivo: sair do PoC leve (v0.1.0, só validava contra uma aba sintética) e construir o
  sistema real de criação/validação de BITin, fiel ao processo de negócio (POP_ENG_7.3.7_002)
  e ao fluxo VBA real (`Módulo1`/`Módulo2`/`Módulo4`/`Módulo10`/`Módulo11`/`Módulo13`),
  culminando numa API backend pronta pra receber uma interface web.
- Status: motor Python completo e testado (114 testes); backend FastAPI funcional
  (validado via testes de API real, sem Postgres/MongoDB disponíveis neste ambiente de
  desenvolvimento — ver `docs/BACKEND.md`).

## Principais adições

- **Port fiel `Módulo1`/`Módulo2`/`Módulo11`** (`scripts/vba_port_export.py`): fluxo real
  `Plan1` (`ZBPP009`) → `Plan2` (`ZBPP009 + ALTERACAO`) → `Plan3` (`Formulário Winshuttle`),
  com subcomandos `sync`/`export` refletindo o passo humano real entre eles (o engenheiro
  preenche as colunas "... Novo" entre os dois). Validado contra dois BITins reais.
- **Modelo de dados do BITin** (`scripts/bitin_model.py`, `docs/BITIN_MODEL.md`).
- **Export de lista técnica / CS02-BOM** (`scripts/lista_tecnica_export.py`) — automação nova,
  cobrindo alteração de quantidade e troca de componente. Validado contra caso real.
- **Documento do BITin** (`scripts/bitin_document.py`, port de `Módulo4`+`Módulo10`+`Módulo13`):
  Alt/Esp/ação de desenho (sugestão), checklist de 22 itens, diffs de campo. Validado contra
  BITin real.
- **Regras de negócio** (`scripts/bitin_business_rules.py`): 4 regras do
  `POP_ENG_7.3.7_002` + regras gerais de consistência.
- **Ciclo de vida rascunho → enviado** (`scripts/bitin_lifecycle.py`).
- **Erros estruturados** (`scripts/bitin_errors.py`): `{field, code, message}`.
- **Parser de colar do SAP** (`scripts/sap_paste_parser.py`) e **sanitização de exports**
  (`scripts/csv_safety.py`, proteção contra CSV/formula injection).
- **Backend/API** (`backend/`): FastAPI + Postgres (metadado) + MongoDB (conteúdo), sem
  autenticação por enquanto. Endpoint de envio roda toda a validação antes de travar o BITin.

## Correções

- `pd.read_excel` tratava `"N/A"` (valor de negócio real) como célula vazia.
- `winshuttle_export.py` não normalizava `"N/A"` → `""` como o teste esperava.
- Regra de duplicidade validava só `codigo_material`, travando por engano quando o mesmo
  material precisa de alteração em centros diferentes (caso real).

## Mudanças de comportamento

- Número do BITin (`bitin`) deixou de ser digitado pelo engenheiro — agora é **gerado pelo
  sistema no momento do envio**. `setor` passou a ser obrigatório (define o prefixo P/A).

## Validação

- 114 testes automatizados (`tests/`), incluindo:
  - Fidelidade contra dois BITins reais fornecidos como exemplo durante o desenvolvimento.
  - Testes de API real (`tests/test_backend_bitins.py`) via FastAPI `TestClient` + SQLite +
    `mongomock-motor` (sem Postgres/MongoDB reais disponíveis neste ambiente).
  - Smoke test do servidor `uvicorn` real, confirmando que o app sobe e responde.

## Como reproduzir

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests

# motor Python
.venv/Scripts/python.exe scripts/vba_port_export.py export "Novo_template_BITin_V2 TESTE.xlsm" --out plan3_export.csv

# backend
.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
.venv/Scripts/python.exe -m uvicorn backend.main:app --reload
```

## Notas

- Próximos passos recomendados: frontend (formulário web pro engenheiro), endpoints de
  geração de arquivo de export a partir de um BITin enviado, autenticação/isolamento por
  usuário quando houver mais de um usuário testando.
- Ver `CHANGELOG.md` para a lista completa e `docs/BITIN_MODEL.md`/`docs/BACKEND.md` para
  arquitetura e decisões registradas.
