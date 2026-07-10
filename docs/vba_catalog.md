# VBA Catalog — Novo_template_BITin_V2 TESTE.xlsm

> **Atualizado em 2026-07-10**: P0 (`Módulo1`, `Módulo2`, `Módulo11`) e boa parte de P1
> (`Módulo4`, `Módulo10`, `Módulo13`) já foram portados para Python — ver
> `docs/VBA_EXPORT_MAPPING.md` (mapeamento detalhado + quirks), `docs/BITIN_MODEL.md`
> (modelo de dados/regras) e `scripts/vba_port_export.py`, `scripts/bitin_document.py`.
> Este catálogo continua válido como inventário original das rotinas VBA; a versão
> machine-readable está em `docs/vba_catalog.json`.

Resumo dos módulos VBA extraídos (prioridade P0 = export/Winshuttle crítico, P1 = integrações/notifications/DWG, P2 = helpers/formatos):

- `Módulo1.bas` — Procedures: `PREENCHER` — Priority: P0
  - Preenche `Plan2` a partir de `Plan1` (mapeamento de campos para export). Essencial para gerar dados de exportação.

- `Módulo2.bas` — Procedures: `DateTime`, `Winshuttle` — Priority: P0
  - `Winshuttle` monta e preenche `Plan3` (Formulário Winshuttle) a partir de `Plan2`. Núcleo do fluxo de export.

- `Módulo3.bas` — Procedures: `CLEAR_ZBPP009` — Priority: P2
  - Limpeza da aba ZBPP009.

- `Módulo4.bas` — Procedures: `Preencher_Bitin` (e funções `DateTime`, `UserName`, `UsuarioRede` presentes em `Plan4`) — Priority: P1
  - Preenche apresentação/bitin visual; chama rotinas DWG/SAT (Módulo10/13).

- `Módulo5.bas` — Procedures: `INSERIR_LINHA` — Priority: P2

- `Módulo6.bas` — Procedures: `limpar3` — Priority: P2

- `Módulo7.bas` — Procedures: `MP` — Priority: P2

- `Módulo8.bas` — Procedures: `pintatudo` — Priority: P2

- `Módulo9.bas` — Procedures: `linhadivid` — Priority: P2

- `Módulo10.bas` — Procedures: `DWG_SAT` — Priority: P1
  - Rotina para tratar marcação de desenho/SAT (mapeamento para salvar DWG/SAT).

- `Módulo11.bas` — Procedures: `clear_winshuttle` — Priority: P0
  - Limpa template do Winshuttle (pré-step antes de popular `Formulário Winshuttle`).

- `Módulo12.bas` — Procedures: `EMAIL`, `Worksheet_Change` — Priority: P1
  - Geração de e-mail com anexo do workbook e rotina de evento para preencher data; integração de notificações.

- `Módulo13.bas` — Procedures: `DWG_SAT_N_DESENHO` — Priority: P1
  - Variante do DWG/SAT quando não há desenho.

- `Módulo14.bas` — Procedures: `NEGRITO` — Priority: P2

- `Módulo15.bas` — Procedures: `dados_lista_técnia` — Priority: P2

- `Módulo16.bas` — Procedures: `Lib_bot` — Priority: P2

- `Módulo17.bas` — Procedures: `Limpeza` — Priority: P2

- `Módulo18.bas` — Procedures: `Lib_Manual` — Priority: P2

- `Módulo19.bas` — Procedures: `UsuarioRede` — Priority: P2
  - Retorna o usuário de rede (usado no Workbook_Open e em preenchimentos automáticos).

- `Módulo20.bas` — Procedures: `cor` — Priority: P2

- `EstaPasta_de_trabalho.cls` — Procedures: `Workbook_Open` — Priority: P2
  - Chama `UsuarioRede` ao abrir o workbook.

- `Plan2.cls` — Worksheet event handlers: `Worksheet_Change` — Priority: P1
  - Lida com marcação visual e estados dos itens em `Plan2` (afeta fluxo de export).

- Outros módulos de `Plan*.cls` e `Planilha*.cls` contêm atributos de planilhas e algumas funções utilitárias; prioridade geralmente P2.

Observações e status (atualizado 2026-07-10):
- **P0 — concluído**: `Módulo1.PREENCHER`, `Módulo2.Winshuttle` e `Módulo11.clear_winshuttle`
  portados em `scripts/vba_port_export.py` (subcomandos `sync`/`export`), orientado por
  `config/vba_mapping.json`. Validado contra BITins reais — ver `docs/VBA_EXPORT_MAPPING.md`.
- **P1 — parcialmente concluído**: `Módulo4.Preencher_Bitin` + `Módulo10.DWG_SAT` +
  `Módulo13.DWG_SAT_N_DESENHO` portados em `scripts/bitin_document.py` (Alt/Esp/checklist).
  `Módulo12` (e-mail/notificações) e `Plan2.cls.Worksheet_Change` (coloração visual) ainda não
  portados — não são necessários pro fluxo de dados, só cosméticos/notificação no Excel.
- **P2**: macros de UI/formato e utilitários (`Módulo3,5-9,14-20`) seguem não portados — não
  fazem parte do fluxo de dados do BITin, ficam substituídos naturalmente pela interface web
  quando ela existir.
