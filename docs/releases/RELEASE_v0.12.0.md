# Release v0.12.0 — Revisão item a item: BITex, hints, PDF/CSV, Subgrupo, buscas, validação

Release criado a partir da tag `v0.12.0`.

## Resumo

Rodada de revisão item a item de uma lista de pedidos levantada pelo usuário, cobrindo desde
UX de campos e telas até validação de dados e geração de documento. Cada item foi discutido e
fechado antes de passar pro próximo, ao invés de implementar tudo de uma vez.

## O que fecha nesta versão

### Campo BITex de volta ao cabeçalho + automação

`bitex` (`"SIM"`/`"NÃO"`, opcional) tinha sumido do formulário atual num refactor anterior,
mas continuava vivo no modelo de dados/checklist (`scripts/bitin_document.py`). Voltou ao
cabeçalho (`DadosGeraisCard.tsx`) e ganhou uma regra nova de automação — a única confirmada
fora das 8 regras originais da macro VBA: `bitex == "SIM"` aciona automaticamente o item 11 do
checklist ("Atualizar BITex"). O valor de `bitex` em si continua 100% manual.

### Hints ("?") revisadas uma a uma

As 9 páginas com popover de ajuda foram revisadas individualmente: título padronizado pra
"Hint" em todas, conteúdo segmentado por papel onde fazia sentido (Home e Painel geral — cada
setor só vê a explicação da própria fila, admin vê tudo), textos simplificados (removidas
menções a detalhes internos como "só admin reverte, em Configurações"). Corrigido de quebra:
`AjudaPopover.tsx` herdava `uppercase` do título do `Card` quando usado dentro dele (só
acontecia em `Settings.tsx`) — resolvido com `normal-case` no próprio componente.

### Pop-ups de confirmação revisados

Os 11 `window.confirm` do sistema revisados um a um — textos simplificados, sem menção a
detalhes internos que o usuário comum não precisa saber (ex.: "só um admin pode reverter, em
Configurações" removido do pop-up de baixar PDF).

### CSV e PDF polidos

- **CSV** (Painel geral): a montagem manual de string virou um helper reutilizável
  (`lib/csv.ts`) com proteção contra formula/CSV injection e CRLF (RFC 4180) — colunas e
  formato visível não mudaram.
- **PDF** (`scripts/bitin_pdf.py`): ganhou a logo real da marca no cabeçalho (antes não tinha
  nenhuma, ou usava um asset placeholder em branco), paleta trocada pros tokens oficiais do
  frontend (antes eram cores calculadas à mão, sem relação com o resto do sistema), e o layout
  foi reordenado pra bater com a tela de edição: cabeçalho → setores acionados (seção nova,
  espelha `SetoresBanner.tsx`) → checklist → materiais/alterações (antes pulava direto de
  cabeçalho pra materiais, sem mostrar setores).

### Subgrupo restrito à Engenharia

Subgrupo já só era **obrigatório** pra Engenharia no backend — mas o campo continuava
aparecendo no formulário pra todos os 3 setores. Agora só Engenharia mostra o campo
(`CriarUsuarioForm.tsx`/`GestaoUsuarios.tsx`); e trocar o setor de um usuário existente pra
fora de Engenharia (`PATCH /users/{id}/setor`) limpa os subgrupos atribuídos automaticamente,
evitando dado órfão no banco.

### Barra de busca única no Painel geral

Os campos separados "Buscar por motivo/solicitante/número" e "Usuário (e-mail)" viraram uma
barra só, buscando os 4 ao mesmo tempo (`GET /bitins` ganhou `incluir_criado_por_no_termo`,
opt-in — não muda o comportamento de `termo` nas outras telas). Resultados aparecem num
dropdown ao vivo; clicar em qualquer um (dropdown ou tabela) abre o BITin direto.

### Busca de campo na ZBPP009

A grade da ZBPP009 (~65 colunas sempre visíveis, sem paginação) ganhou uma barra de busca que
filtra em tempo real as colunas De/Novo pelo nome do campo — mesma função de busca tolerante a
acento/maiúscula (`normalizar()`) já usada pelo combobox "+ Campo alterado" da aba BITin,
extraída pra um util compartilhado (`lib/texto.ts`).

### Validação de domínio nos campos de alteração

Os ~30 campos de `dados_basicos` (De/Para) não tinham nenhuma validação de tipo/formato antes.
Cobertos nesta rodada: `nivel_revisao` precisa ser 1 letra maiúscula (A-Z — achado real ao
planejar a regra: pelo nome parece número, mas o BITin real usa letra de revisão SAP, ex. "C"→
"D"); `producao_interna`/`marcacao_eliminar_nivel_mandante`/`marcacao_eliminar_nivel_centro`
só aceitam `X`/`-` (mesmo domínio de `esp`). Aviso em tempo real no frontend (borda vermelha +
mensagem, nunca bloqueia a digitação); o backend (`bitin_business_rules.py`) é quem barra de
verdade no envio. Centro na ZBPP009 (texto livre, decisão anterior) ganhou aviso visual sem
bloquear se o valor final não for `2001`/`2005`.

## Validação

- `python -m unittest discover -s tests` — **370 testes**, verde.
- `npx tsc --noEmit`, `npx oxlint`, `npx vitest run` — sem erros/avisos.
- PDF de exemplo gerado e inspecionado visualmente antes de fechar o item.
