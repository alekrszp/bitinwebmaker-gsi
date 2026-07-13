# Release v0.5.0 — Grid de materiais dirigido por schema

Release criado a partir da tag `v0.5.0`.

## Resumo

- Objetivo: a fatia anterior (v0.4.0) só cobria identificação de material — não dava pra
  montar um BITin realmente útil (sem `dados_basicos` De/Para, sem `impactos_operacionais`,
  sem colar do SAP). Esta versão fecha esse gap com um grid de materiais em formato planilha
  (linha/coluna), o mesmo padrão usado no projeto irmão `GPT_Engineering_BITIN`, mas
  reconstruído com colunas dirigidas por schema (não hardcoded), erros de envio destacando a
  célula exata, e colar do SAP reaproveitando o parser Python já testado.
- Status: grid de materiais completo (identificação + snapshot + `dados_basicos` +
  `impactos_operacionais`); `ordem_cliente[]`, `lista_tecnica[]` e checklist editável
  continuam sem UI (próximo incremento).

## Principais adições

- **`GET /bitins/schema/materiais`** e **`POST /bitins/parse-sap-paste`**
  (`backend/api/bitins.py`, `scripts/bitin_model.build_materiais_schema`): 2 endpoints novos,
  pequenos, que reaproveitam lógica Python já testada (crosswalk, parser de colagem) em vez de
  duplicá-la em JavaScript.
- **`MaterialGrid.jsx`**: planilha de materiais com colunas De/Para de `dados_basicos`
  (~30 campos, ocultos por padrão — o usuário escolhe quais editar), `<select>` de
  `impactos_operacionais` com as opções válidas do POP, colar do SAP, e destaque de célula
  exata quando o envio falha.
- **RBAC visível em "Meus Bitins"**: botão "Excluir" some quando o usuário não é dono nem
  admin.

## Validação

- **154 testes automatizados Python** (era 147 na v0.4.0): 8 novos cobrindo
  `build_materiais_schema` e os 2 endpoints novos.
- **Playwright ad-hoc** (não faz parte da suíte automatizada): login → criar rascunho →
  adicionar material manualmente → filtrar campo NCM no seletor de colunas → selecionar Alt →
  colar do SAP (linha nova aparece com snapshot correto) → enviar com erros mockados
  (sem MongoDB real disponível neste ambiente) → célula exata destacada em vermelho + lista
  completa de erros. Screenshots conferidos, zero erro de console em todas as etapas.

## Achado durante o teste (mesma limitação de ambiente já documentada)

Sem MongoDB real disponível, `POST /bitins/draft` e `POST /bitins/{id}/enviar` foram
interceptados (mockados) na camada do navegador pra validar o fluxo real de
erro-estruturado→célula-destacada do `MaterialGrid`/`BitinDetail`. Os 2 endpoints novos
(`/schema/materiais`, `/parse-sap-paste`) não dependem do Mongo e foram exercitados de
verdade, sem mock.

## Como reproduzir

```powershell
# backend
.venv/Scripts/python.exe -m uvicorn backend.main:app --reload

# frontend (outro terminal)
cd frontend
npm install
npm run dev
```

## Notas

- Próximo incremento: `ordem_cliente[]`, `lista_tecnica[]`, checklist editável, modo de
  leitura explícito para quem abre o rascunho de outra pessoa sem ser dono/admin, mesclar (em
  vez de sempre duplicar) ao colar do SAP em cima de um material já existente — ver
  `docs/FRONTEND.md`, seção "O que NÃO está nesta fatia ainda".
- Ver `CHANGELOG.md` para a lista completa e `docs/FRONTEND.md`/`docs/BACKEND.md` para
  arquitetura e decisões registradas.
