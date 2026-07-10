# Changelog

All notable changes to this project will be documented in this file.

## [v0.2.0] - 2026-07-10

### Added
- **Port fiel `Módulo1`/`Módulo2`/`Módulo11`** (`scripts/vba_port_export.py`): fluxo real
  `Plan1` (`ZBPP009`) → `Plan2` (`ZBPP009 + ALTERACAO`) → `Plan3` (`Formulário Winshuttle`),
  orientado por mapeamento declarativo (`config/vba_mapping.json`), com dois subcomandos
  (`sync`/`export`) que refletem o passo humano real entre eles. Validado contra dois BITins
  reais fornecidos como exemplo.
- **Modelo de dados do BITin** (`scripts/bitin_model.py`, `docs/BITIN_MODEL.md`): valida
  cabeçalho/materiais e converte `materiais[]` em linhas de `Plan2`, com geração do `.xlsx`
  real da aba.
- **Export de lista técnica / CS02-BOM** (`scripts/lista_tecnica_export.py`): automação nova
  (nunca existiu em VBA), cobrindo alteração de quantidade e troca de componente
  (`operacao: inserir/alterar/excluir`). Validado contra caso real de troca de componente.
- **Documento do BITin** (`scripts/bitin_document.py`, port de `Módulo4`+`Módulo10`+`Módulo13`):
  determina Alt/Esp/ação de desenho como sugestão, monta checklist de 22 itens e diffs
  "campo alterado / de / para". Validado contra BITin real (8 materiais com revisão de
  desenho alterada).
- **Regras de negócio** (`scripts/bitin_business_rules.py`): 4 regras do `POP_ENG_7.3.7_002`
  (desenho aprovado, NCM/fiscal, sucateamento/centro de custo, ordem de cliente) + regras
  gerais de consistência (duplicidade código+centro, campo sem efeito, Alt inconsistente).
  `Alt`/`Esp`/`Est`/`LP`/`Pre`/`OC`/`OF` são **declarados pelo engenheiro**, não derivados de
  código SAP (decisão registrada: código de Grupo Mercadorias é vasto demais pra confiar).
- **Ciclo de vida rascunho → enviado** (`scripts/bitin_lifecycle.py`): edição livre em
  rascunho, toda a validação roda de uma vez só no envio; BITin enviado fica travado.
- **Visualização** (`scripts/bitin_view.py`): resumo estruturado do BITin (prévia e tela final).
- **Erros estruturados** (`scripts/bitin_errors.py`): todas as validações devolvem
  `{field, code, message}` em vez de string solta.
- **Parser de colar do SAP** (`scripts/sap_paste_parser.py`): separa por TAB (não espaço),
  preservando a liberdade do engenheiro de copiar do SAP e colar direto.
- **Sanitização de exports** (`scripts/csv_safety.py`): proteção contra CSV/formula injection.
- **Backend/API** (`backend/`, `docs/BACKEND.md`): FastAPI + Postgres (metadado) + MongoDB
  (conteúdo), sem autenticação por enquanto. Endpoint de envio roda toda a validação antes de
  travar o BITin e gerar o número sequencial (com proteção contra corrida).

### Fixed
- `pd.read_excel` tratava a string `"N/A"` (valor de negócio real neste domínio) como célula
  vazia — corrigido com `keep_default_na=False`.
- `scripts/winshuttle_export.py`: `build_plan3_rows` não normalizava `"N/A"` → `""` como o
  teste já esperava.
- Regra de duplicidade validava só `codigo_material`, travando por engano quando o mesmo
  material precisa de alteração em centros diferentes (caso real).

### Changed
- `bitin_model.validate_bitin`: número do BITin (`bitin`) deixou de ser obrigatório no
  cabeçalho — agora é **gerado pelo sistema no momento do envio**, não digitado pelo
  engenheiro. `setor` passou a ser obrigatório (define o prefixo P/A do número gerado).

### Removed
- `.pyc` compilado rastreado por engano em `scripts/__pycache__/`.
- 3 arquivos `.xlsx` de PoC antigo sem nenhuma referência no repositório
  (`poc_winshuttle_export.xlsx`, `_aligned.xlsx`, `_robust.xlsx`).

### Notes
- 114 testes automatizados cobrindo motor Python + backend, vários validados contra BITins
  reais fornecidos como exemplo durante o desenvolvimento.
- Documentação completa das decisões e achados em `docs/BITIN_MODEL.md`,
  `docs/VBA_EXPORT_MAPPING.md`, `docs/VBA_MIGRATION_GUIDE.md`, `docs/BACKEND.md`.

## [v0.1.0] - 2026-07-09
### Added
- Public release `v0.1.0` published on GitHub.
- Release notes sourced from `docs/RELEASE_v0.1.0.md`.
- Documentation updated in `README.md` and `docs/README_HANDOFF.md` with release URL.

### Notes
- Release was created manually via GitHub UI.
- Release automation script removed from repository.
