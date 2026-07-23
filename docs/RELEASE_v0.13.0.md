# Release v0.13.0 — Agente SAP local + edição de BITin numa única tela

Release criado a partir da tag `v0.13.0`.

## Resumo

Duas mudanças grandes, na verdade uma só: dar ao engenheiro a opção de conectar um agente SAP
local (Windows) que fala direto com o SAP GUI, e reorganizar a edição de BITin em volta dessa
opção — ZBPP009 e Lista Técnica deixaram de ser páginas próprias, viraram parte da mesma aba
BITin, com uma aba "Automação" adicional só quando o agente está conectado. Sem o agente, o
fluxo continua 100% manual, na mesma tela.

## O que fecha nesta versão

### Agente SAP local (`sap-agent/`, novo)

Aplicativo Windows opcional, instalado pelo próprio engenheiro direto do sistema (botão de
download na tela de edição de BITin). Roda em segundo plano na bandeja do Windows; janela
própria de 3 abas:

- **Leia-me** — o que o agente faz e por quê.
- **BITin** — ativar/desativar o agente, usuário identificado (puxado do sistema web).
- **Configurações** — abrir automaticamente com o Windows (pré-marcado), local de instalação.

Importante: essa janela é **só status/configuração**, nunca comando. Os comandos (buscar
material no SAP, validar código) ficam no sistema web, numa aba "Automação" que só aparece com
o agente conectado — decisão explícita para manter toda a validação/autenticação do sistema
web no caminho, em vez de expor comandos direto pela janela local.

Por baixo, o agente fala com o SAP GUI via **SAP GUI Scripting** (COM), mapeado a partir de
gravações reais (`Script1.vbs`–`Script4.vbs`). Expõe uma API HTTP local (`127.0.0.1`) que o
frontend consulta por polling (~4s, mais um recheck imediato ao focar a aba do navegador) para
mostrar um badge verde/vermelho de conexão.

Instalação: `Instalador.exe` (PyInstaller, com `AgenteSAP.exe` embutido) — pede pasta de
destino, extrai o agente, registra o protocolo customizado `bitinsap://abrir` (para reabrir a
janela depois, sem precisar reinstalar) e o registro de "abrir com o Windows". Nunca inicia o
processo sozinho — o engenheiro ativa explicitamente na primeira vez.

### ZBPP009 e Lista Técnica deixam de ser páginas separadas

As duas páginas (`CodigosSapPage.tsx`, `ListaTecnicaPage.tsx`) foram removidas. Cadastro de
material — de zero, colar do SAP, checklist, validação de regras de negócio — acontece todo
dentro da aba BITin, tanto no modo manual quanto com o agente conectado. O objetivo era acabar
com a divergência entre "tela com agente" e "tela sem agente": o agente é sempre uma camada
aditiva sobre a mesma tela, nunca um fluxo paralelo.

### Identidade visual do agente

Logo própria (SVG gerado em código, sem asset externo, sem emoji): navy + laranja da marca,
com uma versão animada (piscar de olho) para o badge web e uma versão estática para o ícone do
`.exe`/instalador — a mesma forma, gerada duas vezes (`AgenteLogoIcon.tsx` no frontend,
`logo_agente.py` no Python) para ficar idêntica nos dois mundos.

## Removido

- `frontend/src/pages/CodigosSapPage.tsx`, `frontend/src/pages/ListaTecnicaPage.tsx` e as
  rotas `/bitins/:mongoId/codigos-sap` e `/bitins/:mongoId/lista-tecnica`.
- `frontend/src/components/bitin/DadosBasicosTable.tsx` — componente sem nenhuma referência no
  código (achado em auditoria de arquivos mortos), superado por
  `AlteracaoTable.tsx`/`DadosGeraisCard.tsx`.

## Notas

- `*.xlsm`/`Script*.vbs` soltos na raiz (material de análise real fornecido pelo usuário —
  dados de material/preço, gravações do SAP GUI Scripting) protegidos no `.gitignore`. Nunca
  estiveram versionados, mas também não tinham entrada própria — corrigido nesta rodada.

## Validação

- Suíte Python completa (`tests/` + `sap-agent/tests/`) verde.
- `npx tsc --noEmit`, `npx oxlint`, `npx vitest run` — sem erros/avisos.
- Testado manualmente na máquina do usuário: instalação real do `.exe`, ativação/desativação
  do agente, `bitinsap://abrir`, badge de conexão no navegador sem precisar recarregar a
  página.
