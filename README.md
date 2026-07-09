**README FINAL PARA NOVO REPOSITÓRIO — Handoff Técnico Completo**

Uso: copie este arquivo para `docs/README_HANDOFF.md` no novo repositório `saas-bitin`. Contém inventário, análise técnica, especificações, planos de migração de macros, modelo de dados, API, testes, checklist e tarefas prioritárias para o próximo agente.
**README FINAL PARA NOVO REPOSITÓRIO — Handoff Técnico Completo**

Uso: copie este arquivo para `docs/README_HANDOFF.md` no novo repositório `saas-bitin`. Contém inventário, análise técnica, especificações, planos de migração de macros, modelo de dados, API, testes, checklist e tarefas prioritárias para o próximo agente.

SUMÁRIO
- Objetivo do projeto
- Inventário dos artefatos
- Análise detalhada do template XLSM
- Plano de extração e reimplementação de macros (VBA)
- Modelo de dados (exemplos JSON)
- Especificação de exportação (Winshuttle/SAP/Windchill)
- API sugerida (contratos e exemplos)
- Frontend: recomendações de editor e UX
- Testes, validação e critérios de aceitação
- Infra, deploy e segurança
- Checklist e tarefas prioritárias para o próximo agente

1) Objetivo do projeto (resumo executivo)

Criar um SaaS que substitua o uso do Excel para criação/gestão de BITins, mantendo compatibilidade com os scripts de cadastro (Winshuttle/SAP) e os processos de documentação/aprovação (Windchill). O produto deve:
- Oferecer editor de planilha com suporte a fórmulas, validações e named ranges;
- Persistir BITins com histórico e comentários;
- Gerar exports idênticos aos arquivos usados atualmente pelo time de cadastro para execução dos scripts Winshuttle;
- Orquestrar o fluxo interno até a entrega ao cadastro (rastreabilidade, notificações e aprovação).

2) Inventário dos artefatos (o que mover para o repositório de código)

- `Processos/BITIN/PROCESSO BITIN.md` — regras e fluxo operacional (leitura obrigatória);
- `Referência/APROVADORES WINDCHILL.md` — mapeamento de aprovadores;
- `Processos/SAP/PROCESSOS SAP.md` — exemplos e notas técnicas sobre Winshuttle;
- `Novo_template_BITin_V2 TESTE.xlsm` — template mestre (14 abas) — manter versão imutável;
- `Documentação/POP_ENG_7 3 7_001.pdf` e `_002.pdf` — POP com layout de criação (33 colunas) e regras de preenchimento;
- `scripts/inspect_xlsm_local.py` — utilitário para inventário de worksheets, named ranges e amostras de fórmulas;
- `scripts/extract_pdf_text.py` — utilitário para extrair texto dos POPs.

3) Análise técnica do template XLSM — pontos-chave

- VBA presente: `xl/vbaProject.bin` (tamanho ~210 KB). Macros fazem validações, preenchimento e geração das folhas finais para export.
- Abas principais (14): ZBPP009, ZBPP009 + ALTERACAO, Template apresentação, Listas Técnicas, Lista técnica, Dados, Formulário Winshuttle, Planilha1, SETORES CHECKLIST, Fluxograma, auxiliar, Planilha2, dados teste winshuttle, ideia pre. lt.
- A aba `Dados` contém grande parte da lógica via fórmulas (~995 funções detectadas) — IFs encadeados que realizam mapeamento condicional baseado em um controle externo (`[1]BITin!$G$2`).
- As abas de export (`Formulário Winshuttle`, `dados teste winshuttle`) possuem pouco ou nenhum cálculo — são escritas pelos macros.

Implicações:
- As macros implementam transformação final e precisam ser entendidas/portadas.
- Algumas fórmulas referenciam workbooks externos; é necessário normalizar essas dependências antes da migração.

4) Plano de extração e reimplementação de macros (passo-a-passo)

Objetivo: remover dependência do VBA reimplementando rotinas críticas.

Passos técnicos:
1. Exportar `xl/vbaProject.bin` e salvar em `artifacts/vba/` no repositório de implementação.
2. Rodar `olevba`/`oletools` para extrair módulos e strings:

```powershell
pip install --user oletools
olevba "Novo_template_BITin_V2 TESTE.xlsm" > artifacts/vba/olevba_report.txt
```

3. Exportar módulos (.bas/.cls) com ferramentas adequadas e revisar manualmente.
4. Catalogar rotinas em `docs/vba_catalog.md` com campos: `module`, `procedure`, `description`, `inputs`, `outputs`, `priority`.
5. Priorizar reimplementações:
- P0: macros que geram `Formulário Winshuttle` / `dados teste winshuttle` e validações SAP.
- P1: macros que criam códigos automáticos e alimentam listas técnicas.
- P2: macros de relatório/apresentação.

Reimplementação: preferir implementação server-side (Node/Python) para garantir reprodutibilidade e testes automatizados; algumas validações podem permanecer client-side para UX imediato.

5) Modelo de dados (detalhado)

Schema exemplo (JSON Schema simplificado):

Bitin:
- id: string (uuid)
- number: string | null
- type: enum
- status: enum
- requester: { id, name, email }
- product, line, alt, bitex, ncm, description
- items: array of BitinItem
- approvals: array { approver_id, role, status, commented_at }

BitinItem:
- sequence, material_code, description, action, quantity, unit, price, metadata

Exemplo JSON (resumido):

```json
{
  "id":"uuid",
  "type":"LIBERACAO",
  "requester":{"id":"u1","name":"Eng X"},
  "product":"Produto A",
  "items":[{"sequence":1,"material_code":"ABC-001","action":"ADD","quantity":10}]
}
```

6) Especificação de exportação — regras e mapeamento

Regras:
- O exportador deve produzir headers idênticos aos do template de referência.
- Deve validar tipos (string/number/date) e comprimentos (sap limits).
- Deve indicar diferenças de header de forma legível.

Formato de mapping (exemplo JSON):

```json
{
  "sheets":{
    "Formulário Winshuttle":["N°","Código","Verificação","Tipo de Material","Descrição PT",...],
    "dados teste winshuttle":["col1","col2","col3"]
  }
}
```

Validação:
- Implementar função `validate_headers(generated, reference) -> {ok:bool, diff:[]}`.

7) Contrato de API (exemplos completos)

Autenticação: JWT Bearer.

Endpoints principais:

- POST /api/bitin
  - Cria Bitin. Body: JSON do bitin. Retorna 201 + objeto criado.

- GET /api/bitin/{id}

- PUT /api/bitin/{id}

- POST /api/bitin/{id}/submit
  - Valida, muda status, notifica aprovadores.

- POST /api/bitin/{id}/export?format=xlsm|xlsx|csv&target=winshuttle|windchill
  - Gera arquivo e retorna stream; content-type apropriado.

Exemplo curl para export:

```bash
curl -H "Authorization: Bearer $TOKEN" -X POST "http://localhost:8000/api/bitin/UUID/export?format=xlsm&target=winshuttle" --output exported_bitin.xlsm
```

8) Frontend — stack, componentes e integração com HyperFormula

Recomendações:
- React + TypeScript + Vite
- Editor: AG-Grid + HyperFormula (ou Handsontable se a licença estiver disponível)
- Persistir edição como JSON do `Bitin`; salvar rascunho via API.

9) Testes e QA

Testes mínimos a implementar:
- Unit: transformações por item, validações de campos, validação de headers.
- Integration: geração de XLSX/XLSM e comparação binária ou via CSV com arquivos de referência.
- Acceptance: time de cadastro roda scripts Winshuttle em homolog e confirma comportamento.

10) Infra, deploy e segurança

Recomendação inicial:
- Backend: FastAPI (Python) ou Express (Node) — containerizado.
- DB: Postgres
- Storage: S3 / Azure Blob
- CI/CD: GitHub Actions — pipeline: lint → unit tests → build → integration tests → deploy.

Segurança:
- RBAC, logs de auditoria, secrets em vault.

11) Checklist de handoff e tarefas prioritárias (próximo agente)

P0 (imediato):
1. Rodar `scripts/inspect_xlsm_local.py "Novo_template_BITin_V2 TESTE.xlsm"` e salvar saída em `docs/inventory.md`.
2. Executar `olevba` e gerar `docs/vba_catalog.md` com listagem de módulos/rotinas.
3. Gerar `mapping/winshuttle_mapping.json` com headers exatos das sheets `Formulário Winshuttle`, `dados teste winshuttle` e `Dados`.

P1 (curto prazo):
4. Implementar PoC do endpoint `/api/bitin/{id}/export` que gera CSV para `dados teste winshuttle`.
5. Rodar testes de integração com exemplo real do time de cadastro.

P2 (médio prazo):
6. Implementar editor web com HyperFormula e salvar JSON.
7. Reimplementar macros críticos server-side e validar saída.

12) Comandos úteis (rápidos)

Inspecionar XLSM (exemplo de uso relativo ao repositório):

```powershell
python scripts/inspect_xlsm_local.py Novo_template_BITin_V2_TESTE.xlsm
```

Extrair texto do POP (primeiras páginas):

```powershell
python scripts/extract_pdf_text.py POP_ENG_7_3_7_001.pdf 5
```

Analisar macros com `olevba`:

```powershell
pip install --user oletools
olevba "Novo_template_BITin_V2_TESTE.xlsm" > artifacts/vba/olevba_report.txt
```

Criar ZIP dos protótipos (exemplo relativo):

```powershell
Compress-Archive -Path .\saas_prototype\* -DestinationPath .\saas_prototype_code.zip
```

13) Como requisitar os protótipos removidos

- Opções: gerar um ZIP com os protótipos e deixá-lo na raiz (`saas_prototype_code.zip`), criar um repositório local `saas-bitin/` com estrutura inicial e copiar o template para `assets/templates/`, ou executar a extração de macros e entregar o catálogo `docs/vba_catalog.md`.

