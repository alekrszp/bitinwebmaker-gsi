# Release v0.11.0 — Resetar senha (admin), Painel geral com paginação real

Release criado a partir da tag `v0.11.0`.

## Resumo

Segunda rodada dos itens levantados na revisão de "o que falta" do sistema: "esqueci minha
senha" e paginação de verdade no Painel geral. Um terceiro item (RBAC visível na UI) foi
revisado e não gerou mudança — os controles de edição já consultam o mesmo cálculo de
permissão do backend, não achamos um botão que apareça e sempre falhe.

## O que fecha nesta versão

### "Esqueci minha senha" → resetar senha pelo admin

O backend não tem SMTP configurado (nenhum e-mail é enviado de verdade hoje — a senha
temporária de conta nova usa `mailto:` aberto pelo próprio admin, que reenvia manualmente). Um
fluxo self-service de reset por link não teria como entregar nada de verdade sem esse SMTP.
Decisão: em vez disso, uma ação direta do admin.

- `POST /users/{id}/resetar-senha` (`backend/api/users.py`) — admin-only (na prática só o
  super-admin oculto), gera senha temporária nova pra qualquer conta ativa (mesmo padrão de
  `reativar`: devolvida em texto puro uma única vez, `senha_temporaria=True` força troca no
  próximo login). Não mexe em e-mail/`ativo`. 400 se o alvo está excluído.
- Botão "Resetar senha" em cada linha ativa de `GestaoUsuarios.tsx`, com confirmação antes,
  mesmo callout de senha gerada + `mailto:` já usado em reativação.

### Painel geral: paginação real

Antes, `PainelGeral.tsx` buscava até 5000 BITins em lotes de 500 e filtrava tudo (Setor/
Usuário/Status/Etapa/busca) no cliente, sobre a lista inteira já carregada — funcionava, mas
não escala indefinidamente e carrega dado que nunca aparece na tela.

- `GET /bitins` ganhou `criado_por` (substring/case-insensitive) como filtro novo.
- `PainelGeral.tsx` agora pagina de verdade: 50 BITins por página, `limit`/`skip` no servidor,
  botões "Anterior"/"Próxima". Setor/Status/Etapa viraram os mesmos parâmetros booleanos que
  `CadastroPage.tsx`/`ProcessosPage.tsx` já usam (`encaminhado_roteiro`/`processos_concluido`/
  `bitin_cadastrado`/`windchill_enviado`) — a tradução espelha `etapaDoBitin`
  (`lib/bitinEtapa.ts`) pra nunca divergir. "Usuário" virou busca por trecho do e-mail em vez
  de um dropdown com todo mundo já visto na tela (não dava mais pra montar esse dropdown sem
  carregar tudo de novo). "Exportar CSV" agora baixa só a página atual — rotulado como tal.

### RBAC visível na UI (revisado, sem mudança)

Auditoria dos controles de edição do sistema (`BitinDetail.tsx`, `CadastroPage.tsx`,
`MeusBitins.tsx`, `GestaoUsuarios.tsx`): todos já consultam `pode_editar` (calculado no
servidor, `backend/api/bitins.py::_pode_editar`) ou uma checagem de setor/permissão que
espelha exatamente a regra do backend, antes de mostrar um botão de ação. Não achamos um botão
real que apareça pra quem não tem permissão e sempre falhe com 403 ao clicar.

## Validação

- `python -m unittest discover -s tests` — **362 testes**, verde (cobre `resetar-senha`
  feliz/excluído/negado, e o filtro `criado_por`).
- `python -m ruff check backend scripts` — sem apontamentos.
- `npx tsc -b --noEmit`, `npm run lint` (oxlint), `npm run build` — sem erros/avisos.
