# Changelog

All notable changes to this project will be documented in this file.

## [v0.13.0] - 2026-07-23

Agente SAP local (novo, opcional) + reorganização das telas de edição de BITin: ZBPP009 e
Lista Técnica deixaram de ser páginas separadas — tudo acontece numa única tela ("aba BITin"),
com uma aba "Automação" adicional quando o agente está conectado.

### Added

- `sap-agent/`: aplicativo Windows opcional (Tkinter + Flask + `pywin32`) que roda no PC do
  engenheiro e fala com o SAP GUI via SAP GUI Scripting (COM). Janela própria de 3 abas
  (Leia-me / BITin / Configurações) só para status/configuração — ativar/desativar, abrir com
  o Windows, local de instalação; nunca para comandos. Empacotado com PyInstaller
  (`Instalador.exe` gera `AgenteSAP.exe`), com protocolo customizado `bitinsap://abrir` para
  reabrir a janela depois de instalado.
- `GET /api/v1/agente-sap/download`: endpoint público que serve o instalador direto do
  sistema web (`backend/api/agente_sap.py`).
- Frontend: `AgenteGate`/`InstalarAgenteCard` (tela de instalação/gate quando o agente não é
  detectado num rascunho vazio), `AgenteSapStatus` (badge verde/vermelho na barra inferior da
  edição), `useAgenteSapConectado` (polling ~4s + recheck ao focar a aba), `AutomacaoPage`
  (stub, só acessível com o agente conectado), `AgenteLogoIcon` (logo SVG animada, própria da
  marca, sem emoji).
- `logo_agente.py`: mesma logo gerada em código (PIL) para o ícone estático do `.exe`/instalador.

### Changed

- ZBPP009 (`CodigosSapPage.tsx`) e Lista Técnica (`ListaTecnicaPage.tsx`) removidas como
  páginas próprias — cadastro de material acontece só na aba BITin, num único fluxo tanto no
  modo manual quanto com o agente conectado.

### Removed

- `frontend/src/components/bitin/DadosBasicosTable.tsx` — componente sem nenhuma referência
  no código, superado por `AlteracaoTable.tsx`/`DadosGeraisCard.tsx`.
- Rotas `/bitins/:mongoId/codigos-sap` e `/bitins/:mongoId/lista-tecnica`.

### Notes

- `*.xlsm`/`Script*.vbs` soltos na raiz (material de análise real da empresa) protegidos no
  `.gitignore` — nunca estiveram versionados, mas também nunca tinham entrada própria.

## [v0.12.0] - 2026-07-21

Revisão item a item de uma lista de pedidos: campo BITex de volta ao cabeçalho (com
automação de checklist), as 9 hints ("?") e os pop-ups de confirmação revisados um a um, CSV/PDF
polidos (PDF ganhou logo real da marca + paleta oficial + layout reordenado), Subgrupo restrito
à Engenharia (com limpeza automática ao trocar setor), barra de busca única no Painel geral,
busca de campo na ZBPP009, e validação de domínio (tempo real + envio) nos campos de alteração.

### Added

- Campo `bitex` (`"SIM"`/`"NÃO"`) de volta ao cabeçalho do BITin, com regra 9 de automação:
  `bitex == "SIM"` aciona o item 11 do checklist ("Atualizar BITex") automaticamente.
- Busca de campo na ZBPP009 (`CodigosSapPage.tsx`) — barra de busca filtra as ~30 colunas De/
  Novo em tempo real, mesma busca tolerante a acento/maiúscula do combobox "+ Campo alterado"
  da aba BITin (`lib/texto.ts`, extraída de `MaterialEditorCard.tsx`).
- Validação de domínio em `dados_basicos` (`nivel_revisao` = 1 letra A-Z; `producao_interna`/
  `marcacao_eliminar_nivel_mandante`/`marcacao_eliminar_nivel_centro` = `X`/`-`) — aviso em
  tempo real no frontend, bloqueio de verdade no envio (`bitin_business_rules.py`). Centro na
  ZBPP009 ganhou aviso visual (sem bloquear) se fora de `2001`/`2005`.
- Barra de busca única no Painel geral — motivo/solicitante/número/e-mail do criador num campo
  só, com dropdown de resultados ao vivo (clique abre o BITin direto).
- `GET /bitins` ganhou `incluir_criado_por_no_termo` (opt-in) pra unificar a busca acima.
- `POST /users/{id}/setor` limpa os subgrupos atribuídos ao trocar pra fora de Engenharia.

### Changed

- Subgrupo só aparece na UI (`CriarUsuarioForm.tsx`/`GestaoUsuarios.tsx`) pra usuários de
  Engenharia — Cadastro/Processos deixam de mostrar o campo.
- PDF do BITin (`scripts/bitin_pdf.py`) restilizado: logo real da marca no cabeçalho, paleta
  trocada pros tokens oficiais do frontend, layout reordenado (cabeçalho → setores acionados →
  checklist → materiais), nova seção "Setores acionados" (antes não existia no PDF).
- CSV do Painel geral (`lib/csv.ts`) — protegido contra formula/CSV injection, CRLF (RFC 4180).
- As 9 hints ("?") do sistema revisadas uma a uma: título padronizado pra "Hint", conteúdo
  segmentado por papel (Home/Painel geral), textos simplificados.
- Pop-ups de confirmação (`window.confirm`) revisados um a um: textos simplificados, sem
  menção a detalhes internos (admin/Configurações) que o usuário comum não precisa saber.

### Fixed

- `AjudaPopover.tsx` herdava `uppercase` do título do `Card` quando usado dentro dele (só
  acontecia em `Settings.tsx`) — corrigido com `normal-case` no próprio popover.

## [Unreleased] - Limpeza de repositório (2026-07-21)

Sem mudança de código de produto — só arrumação. Removidos do repositório: dumps de pesquisa
VBA superados (`docs/codes_found.md`, `context.md`, `inventory.md`, `vba_catalog.md`/`.json`,
`zbpp009_sample.md` — substituídos por
`VBA_EXPORT_MAPPING.md`/`VBA_MIGRATION_GUIDE.md`/`BITIN_MODEL.md`), 2 scripts de migração já
aplicados e obsoletos (`migrar_niveis_permissao.py`, `migrar_setores_2026_07_20.py` — o esquema
de permissão já mudou de novo desde então), backups de SQLite antigos e caches locais.
`examples/`/`bitinsparaexemplo/` (arquivos `.xlsm`/`.pdf` reais usados como referência durante
o desenvolvimento) foram mantidos — ainda são usados de verdade por
`tests/test_vba_port_export.py::RealWorkbookTest` e
`tests/test_winshuttle_export.py::test_matches_reference_export`.

Incorporado na v0.12.0 acima (era um commit já feito mas ainda não tinha entrado numa release
tagueada).

## [v0.11.0] - 2026-07-21

Admin reseta a senha de qualquer usuário direto em Gestão de usuários ("esqueci minha senha"
sem SMTP configurado), e Painel geral ganhou paginação real no servidor (antes buscava até
5000 BITins de uma vez e filtrava tudo no cliente). Ver `docs/releases/RELEASE_v0.11.0.md`.

### Added

- `POST /users/{id}/resetar-senha` (admin-only) + botão "Resetar senha" em
  `GestaoUsuarios.tsx` — gera senha temporária nova pra qualquer conta ativa.
- `criado_por` como filtro substring/case-insensitive em `GET /bitins` — alimenta o filtro
  "Usuário" do Painel geral.
- Paginação real (`limit`/`skip`, 50 por página, botões Anterior/Próxima) em `PainelGeral.tsx`
  — Setor/Status/Etapa/Usuário viram parâmetros de servidor em vez de filtro client-side sobre
  a lista inteira carregada.

## [Unreleased] - Limpeza de repositório (2026-07-21)

Sem mudança de código de produto — só arrumação. Removidos do repositório: dumps de pesquisa
VBA superados (`docs/codes_found.md`, `context.md`, `inventory.md`, `vba_catalog.md`/`.json`,
`zbpp009_sample.md` — substituídos por
`VBA_EXPORT_MAPPING.md`/`VBA_MIGRATION_GUIDE.md`/`BITIN_MODEL.md`), 2 scripts de migração já
aplicados e obsoletos (`migrar_niveis_permissao.py`, `migrar_setores_2026_07_20.py` — o esquema
de permissão já mudou de novo desde então), backups de SQLite antigos e caches locais.
`examples/`/`bitinsparaexemplo/` (arquivos `.xlsm`/`.pdf` reais usados como referência durante
o desenvolvimento) foram mantidos — ainda são usados de verdade por
`tests/test_vba_port_export.py::RealWorkbookTest` e
`tests/test_winshuttle_export.py::test_matches_reference_export`.

## [v0.10.1] - 2026-07-21

Bloqueio de envio de BITin sem nenhuma alteração real, confirmação antes de enviar, e
correção de um bug real de perda de dados no Salvar/Importar da Lista Técnica/Códigos SAP
(achado e reproduzido em teste manual + Playwright). Ver `docs/releases/RELEASE_v0.10.1.md`.

### Added

- Regra de negócio `nenhuma_alteracao_real` (`scripts/bitin_business_rules.py`) — bloqueia
  envio se nenhum material tem alteração de verdade.
- Confirmação antes de enviar (`EdicaoBottomBar.tsx`).
- Colunas Centro/Descrição na Lista Técnica — material novo já nasce completo.
- Autocompletar (`<datalist>`) de Código pai na Lista Técnica.
- Suite de ponta a ponta estendida (`tests/test_bitin_workflow_e2e.py`) até
  Concluir/Windchill/Reverter, gestor no Painel geral, e bloqueio de envio vazio.

### Fixed

- Salvar/Importar em Lista Técnica e Códigos SAP podiam não persistir a última linha editada
  (truque de captura de estado via `setState` funcional não era confiável) — trocado por uma
  `ref` síncrona.
- "+ Nova linha" da Lista Técnica não cria mais linha sozinha ao digitar.
- Etapa "Recebido (Cadastro)" (inatingível desde o roteamento automático) removida.

## [v0.10.0] - 2026-07-21

Etapa final "Concluído" (Windchill, reversível só por admin), 2ª revisão do modelo de
permissões (Cadastro/Processos viram `setor` cruzado com rank, não mais níveis fixos), Painel
geral novo, Cadastro/Processos reformulados na mesma linguagem Status x Etapa, revisão geral
de arquitetura/performance do frontend (componentização, navegação "voltar" correta) e ajuda
("?") em cada tela principal. Ver `docs/releases/RELEASE_v0.10.0.md` pra notas completas.

### Added

- `enviar_windchill`/`reverter_windchill` (`scripts/bitin_lifecycle.py`) — etapa final do
  BITin (Status derivado "Concluído"), reversível só por admin
  (`POST /bitins/{id}/reverter-windchill`, `check_permission(NIVEL_ADMIN)`).
- Aba "Bitins Concluídos" em `Settings.tsx` (admin-only) — lista travada com "Voltar bitin".
- `Usuario.setor` (`"cadastro"`/`"processos"`/`"engenharia"`), cruzado com
  `permission_level` (77/88/99) — substitui os níveis fixos `88`/`89` da 1ª revisão.
  `eh_do_setor`/`check_setor` no backend, `ehDoSetor`/`isCadastro`/`isProcessos` no frontend.
- `PainelGeral.tsx` (`/painel-geral`, Gestor/Admin) + `lib/bitinEtapa.ts` (Status x Etapa,
  fonte única usada também por Cadastro/Processos) + `GET /bitins/resumo-painel` (`$facet`).
- `ProcessosPage.tsx` (tela própria, substitui reaproveitamento de `MeusBitins.tsx`) —
  exclui BITins com `sem_necessidade_roteiro=True` das etapas Pendente/Revisado.
- `components/bitin/BitinTableSection.tsx`, `bitinColunas.tsx`, `FiltroEtapaToolbar.tsx`,
  `hooks/useDebouncedValue.ts`, `hooks/useVoltar.ts` — componentização/dedup do frontend.
- `AjudaPopover` novo em Cadastro, Processos, Meus Bitins, Painel geral, Início, Gestão de
  usuários e "Bitins Concluídos".

### Fixed

- "Voltar" em `BitinDetail.tsx` tinha alvo fixo (`/bitins`) — agora volta pra tela de origem
  real (`navigate(-1)`).
- BITins sem necessidade de roteiro apareciam como "Revisado" na fila do Processos mesmo
  nunca tendo passado por lá (mesmo bug refletido em `GET /bitins/resumo-painel`).
- Coluna "Número" perdeu cor/sublinhado ao virar componente compartilhado — corrigido.

## [v0.9.0] - 2026-07-20

Auditoria completa das automações do VBA original (checklist, Alt/Esp/DWG-SAT, "REVISAR
ROTEIRO"), fluxo novo de roteamento pós-envio com os setores Cadastro e Processos (substitui
o e-mail automático do VBA), e uma suíte de testes de ponta a ponta dedicada que já pegou 2
bugs reais no processo.

### Added

- **Sugestão automática de Alt/Esp/nota DWG-SAT** (`scripts/bitin_document.py::
  suggest_impactos`) a partir do código de Grupo de Mercadorias — só preenche campo em
  branco, nunca sobrescreve o que o engenheiro já declarou; código SAP desconhecido não
  sugere nada.
- **Checklist/setores recalculam ao vivo** (`POST /bitins/preview-resumo`) — antes só
  atualizava depois de "Salvar".
- **Aviso "Revisar roteiro de fabricação"** por material quando Alt é `"D/P"`/`"-/P"`
  (`bitin_document.revisar_roteiro`) — lembrete herdado da macro original (Módulo4.bas).
- **Setor Cadastro** (`CadastroPage.tsx`, `permission_level=88`): fila própria com 3 abas
  (Recebidos/Enviados para roteiros/Retornados de roteiro) — substitui o e-mail automático
  via Outlook que o VBA original disparava (Módulo12.bas).
- **Setor Processos** (novo nível `permission_level=89`, `NIVEL_PROCESSOS`): recebe BITins
  encaminhados pelo Cadastro, é a **única exceção do sistema** a "BITin enviado é travado pra
  sempre" — reedita enquanto `encaminhado_roteiro=True` e `processos_concluido=False`
  (`POST /bitins/{id}/atualizar-processos`), depois conclui
  (`POST /bitins/{id}/concluir-processos`). Não cria BITin.
- **Decisão automática "precisa de roteiro"** (`bitin_document.precisa_roteiro`): `True` se
  algum material tem Alt em `{"D/P", "D/-", "-/P"}` — quando `False`, o Cadastro conclui
  direto sem passar pelo Processos (`POST /bitins/{id}/concluir-sem-roteiro`), PDF liberado
  na hora.
- **`tests/test_bitin_workflow_e2e.py`**: suite de ponta a ponta dedicada — história completa
  do BITin pelos 4 papéis (Engenheiro/Cadastro/Processos/Admin), nos dois ramos (precisa ou
  não de roteiro), com matriz de visibilidade por papel.

### Fixed

- **Visibilidade do Cadastro estava escopada por Subgrupo** — herdada de quando esse nível só
  significava "colega com acesso extra" (2026-07-16), de antes de virar hub de roteamento;
  fazia BITins de fora do Subgrupo do Cadastro sumirem da fila "Recebidos". Achado pelo teste
  de ponta a ponta novo. Agora é global: qualquer BITin `"enviado"`, de qualquer autor.
- **`POST /atualizar-processos` apagava `encaminhado_roteiro` de dentro de `content`** quando
  o payload não vinha com esse campo espelhado — o `/concluir-processos` seguinte quebrava
  com "ainda não foi encaminhado", mesmo o BITin estando de fato encaminhado. O servidor
  agora reforça todo campo administrado pelo sistema (`bitin`, `status`,
  `encaminhado_roteiro`, `processos_concluido`, etc.) por cima do payload do cliente.

### Removed

- **Botão "Enviar e-mail"** (`MeusBitins.tsx`) e o endpoint `GET /users/cadastro-emails` —
  substituídos de vez pela fila do Cadastro.

### Changed

- Nem Cadastro (88) nem Processos (89) exigem Subgrupo mais (tirados de
  `NIVEIS_QUE_EXIGEM_SUBGRUPO`) — os dois são times centrais, não presos a um Subgrupo
  específico.
- "+ Novo BITin" some pra quem é só Processos (`MeusBitins.tsx`/`Home.tsx`) — backend também
  recusa com 403.

### Notes

- 322 testes automatizados (motor Python + backend + ponta a ponta), `ruff`/`tsc`/`oxlint`/
  `vite build` limpos.
- Documentação atualizada em `docs/BITIN_MODEL.md` (seção "Roteamento pós-envio") e
  `docs/BACKEND.md` (tabela de permissões + endpoints novos).

## [v0.8.5] - 2026-07-17

Reativação de usuário vira recadastro (e-mail + senha novos do zero), admin "super" oculto
(só no backend), consistência de mensagens de erro/UI em Gestão de usuários, correção de
autofill do navegador, e uma rodada de auditoria do sistema de permissões (bug de auditoria
de login, doc desatualizada, duplicação de checagem de admin).

### Added

- **Reativar usuário vira recadastro** (`POST /users/{id}/reativar`): agora pede um e-mail
  (pode repetir o antigo ou trocar) e sempre gera senha temporária **nova do zero**, mesmo
  padrão do cadastro — antes só virava `ativo=True` mantendo tudo igual. UI ganhou o mesmo
  callout de senha gerada (com botão "Copiar" e "Abrir e-mail") de `CriarUsuarioForm.tsx`.
- **Recadastro de e-mail excluído reativa a conta**: `POST /users` agora reativa a linha
  existente (dados/senha novos) em vez de rejeitar com "e-mail já cadastrado" quando o e-mail
  pertence a um usuário soft-deleted — só bloqueia de verdade se o e-mail já é de alguém
  ativo.
- **Admin "total" oculto** (`backend/auth/deps.py::CONTAS_SUPER_ADMIN`/`eh_super_admin`): uma
  conta específica pode rebaixar/excluir OUTROS admins (bypass da proteção normal
  "admin não mexe em admin"), sem nenhum sinal disso no frontend — autoproteção continua
  valendo até pra essa conta (não pode mexer na própria permissão nem se auto-excluir).
- **Botão "Copiar senha"** (Clipboard API) nos dois callouts de senha temporária (cadastro e
  reativação) — evita selecionar o texto na mão, fonte de bugs de login por espaço/quebra de
  linha arrastados na seleção.
- **`GET /users` volta a devolver ativos e excluídos juntos**, com filtro Ativados/Desativados
  na UI (`GestaoUsuarios.tsx`) — linha de usuário desativado fica só-leitura, com botão
  "Reativar".

### Fixed

- **Permissão/Nível na UI mostra só o número** (99/88/77/66, sem rótulo textual) nos dois
  lugares (Cadastrar usuário e a tabela) — pedido explícito.
- **Autocomplete do navegador**: campo de e-mail e senha da tela de Login continuam com
  autofill normal; os de "Cadastrar usuário" (Gestão de usuários) pararam de puxar
  credenciais erradas do admin — `autoComplete="new-password"` na senha de confirmação em vez
  de um campo `username` oculto decoy (que causava o balão nativo "Salvar senha?" aparecer em
  qualquer ação da página, efeito colateral pior que o problema original).
- **Trim() em campos de senha** (`Login.tsx`, `usePasswordChangeForm.ts`,
  `CriarUsuarioForm.tsx`) — espaço/quebra de linha arrastado ao copiar uma senha temporária
  derrubava o login mesmo com o texto "certo" visualmente.
- **Auditoria do sistema de permissões** (backend + UI, sem mudança de regra de negócio):
  - Login de usuário desativado com senha certa agora é registrado em `TentativaLogin` (antes
    tinha um buraco silencioso na auditoria e não contava pro rate limit).
  - `GestaoUsuarios.tsx`: `alterarSubgrupos`/`alterarSetor`/`reativarUsuario` agora mostram o
    erro real do servidor em vez de mensagem genérica (importante pro cenário "admin sem
    privilégio tentando mexer em outro admin").
  - Comentário em `backend/auth/deps.py` e linha do `GET /users` em `docs/BACKEND.md`
    corrigidos — diziam que Gestor ainda tinha acesso a `GET /users`, revogado desde
    2026-07-16.
  - `BitinDetail.tsx`/`MeusBitins.tsx` usam `isAdmin()` centralizado em vez de duplicar
    `ADMIN_LEVEL`/comparação numérica solta.
  - `MeusBitins.tsx`: `GESTOR_LEVEL` era `1` (sobra do esquema antigo 0/1/99) — com os níveis
    atuais (66/77/88/99) isso fazia a opção de busca "Solicitante" aparecer pra qualquer
    usuário logado, não só gestor/cadastro/admin. Corrigido pra `77`.

## [v0.8.4] - 2026-07-17

Admin pode excluir usuário (soft-delete) na tela de Gestão de usuários; correção de cores
"estranhas" no modo escuro nas telas de login (Login e Definir senha).

### Added

- **Excluir usuário** (`DELETE /users/{id}`, `backend/api/users.py::delete_user`): botão de
  lixeira em cada linha de Gestão de usuários, admin-only. É soft-delete (`Usuario.ativo =
  False`), não apaga a linha do banco — a conta some da listagem (`GET /users` já filtra
  `ativo=True`) e para de conseguir logar/usar a API imediatamente (`ativo` já era checado em
  todo request autenticado e no login). Mesmas proteções de `PATCH /users/{id}/permission`:
  ninguém se auto-exclui, admin (nível 99) não pode ser excluído por ninguém. Decisão de
  soft- em vez de hard-delete: BITins não têm FK pro usuário (dono é só um campo solto no
  documento do Mongo) mas `SessaoUsuario` tem, e soft-delete evita lidar com essa cascata,
  além de manter reversível e preservar o rastro de quem criou o quê.

### Fixed

- **Cores erradas no modo escuro nas telas pré-login** (`Login.tsx`, `DefinirSenha.tsx`):
  painel de marca da tela de Entrar usava `bg-white` fixo (nunca escurecia, brigando com o
  texto claro do tema escuro) — trocado por `bg-surface` (token que já se adapta ao tema,
  mesmo branco no claro). Caixas de erro (`role="alert"`) nas duas telas usavam só
  `red-50/red-200/red-700`, sem variante escura — adicionado `dark:bg-red-950
  dark:border-red-900 dark:text-red-300`.

Checklist automática mapeada das macros reais do Excel, admin exclui BITin enviado,
confirmação/navegação pós-envio, Lista Técnica direto na aba BITin, busca tolerante de campo
alterado, e reformulação completa do modelo de permissões (4 níveis: Usuário/Gestor/
Cadastro/Admin).

### Added

- **Checklist automática, verificada contra as macros VBA reais** (`scripts/bitin_document.py`):
  auditoria completa dos 20 módulos do Excel original (`artifacts/vba/*.bas`) encontrou 8
  regras reais de automação (Alt→Desenho/Processo/Fornecedor, nota "SALVAR DWG"/"SALVAR SAT"
  por texto exato→Atualizar DWG/SAT, Est/LP/PRE/OC/OF preenchidos→itens correspondentes) —
  restaurada a sugestão automática (removida numa rodada anterior por falta de verificação),
  agora com regras confirmadas uma a uma contra o código real. Override manual continua tendo
  prioridade em ambas as direções.
- **Admin exclui BITin enviado**: `DELETE /bitins/{id}` agora permite excluir um BITin já
  enviado quando quem pede é admin (nível 99) — limpa a linha correspondente no SQLite junto
  com o documento no Mongo. Botão na aba BITin e em "Meus Bitins".
- **Confirmação + navegação pós-envio**: banner de sucesso com o código gerado, a tela
  atualiza sozinha pro estado "enviado" sem precisar recarregar a página.
- **Lista Técnica direto na aba BITin**: botão "+ Lista técnica" ao lado de "+ Campo alterado
  / nota" em cada material — grade inline editável (`ListaTecnicaInline.tsx`), mesma
  `lista_tecnica[]` compartilhada com a página dedicada, sem precisar trocar de tela.
- **Busca tolerante no "+ Campo alterado / nota"**: digitar "niv" acha "Nível de Revisão" —
  ignora acento e maiúscula/minúscula, casa por trecho em vez de exigir o nome exato do campo.
- **Modelo de permissões reformulado** (4 níveis numerados, substituindo 0/1/99):
  - **99 Admin** — acesso total, ninguém consegue rebaixar (nem outro admin), sem setor
    obrigatório.
  - **77 Gestor** — vê rascunho+enviado só do(s) próprio(s) setor(es) (igual antes, só
    renumerado); setor agora obrigatório.
  - **88 Cadastro** (novo papel) — vê só os ENVIADOS do(s) próprio(s) setor(es) + os próprios
    rascunhos; pode criar/enviar BITin normalmente; setor obrigatório.
  - **66 Usuário** — só os próprios BITins (igual antes, renumerado de 0); setor obrigatório.
  - `check_permission` deixou de comparar por limiar numérico (`>=`) e passou a checar
    pertencimento a um conjunto explícito de níveis — os novos números não formam mais uma
    hierarquia linear limpa.
  - Migração de dados dos usuários existentes (`scripts/migrar_niveis_permissao.py`,
    dry-run por padrão) já aplicada ao banco real: 0→66, 1→77, 99 inalterado.

### Validação

- Backend: 226 → **235** testes, todos verdes.
- Frontend: `npm run typecheck`, `npx oxlint src`, `npm run test` (4/4), `npm run build` —
  todos limpos.
- Validação visual ao vivo cobrindo checklist automática (Alt/DWG/SAT reais), exclusão de
  BITin enviado como admin (confirmado nos dois bancos), confirmação pós-envio, busca
  tolerante, e as 4 permissões novas (opções no cadastro, setor obrigatório, admin
  protegido).

## [v0.8.2] - 2026-07-16

MongoDB Atlas real (destrava persistência de verdade do conteúdo de BITin, antes só rodava em
mongomock) + limpeza geral de código pedida explicitamente pelo usuário: "remova coisas
inúteis, limpa ele, deixa ele 100% otimizado... deixa clean code, componetiza bem direitinho
tudo".

### Added

- **MongoDB Atlas configurado** (`MONGO_URL` real via `.env`, gitignorado): primeira vez que o
  conteúdo de BITin persiste de verdade entre restarts do backend, fora do ambiente de teste.
  Validado ao vivo: BITin criado, servidor reiniciado do zero, BITin continuou lá.
- **`ruff`** — primeiro linter Python do projeto (`backend/requirements.txt`, `pyproject.toml`
  na raiz, `E`/`F`/`I`). Roda em CI. 54 → 32 achados corrigidos mecanicamente (imports
  mortos/desorganizados); os 32 restantes são estilo/tamanho de linha, deixados de propósito
  pra não gerar um diff gigante sem revisão.

### Fixed

- **Handshake TLS instável com MongoDB Atlas** (`backend/db/mongodb.py`): conexão falhava de
  forma intermitente nesta máquina (Windows + Python 3.14 + OpenSSL 3.0.18) com
  `SSL: TLSV1_ALERT_INTERNAL_ERROR`. Corrigido passando `tlsCAFile=certifi.where()`
  explicitamente ao invés de depender do trust store do SO — resolveu de forma consistente nos
  testes.

### Changed — Componentização/limpeza (comportamento preservado, zero mudança funcional)

- **`Settings.tsx`**: 401 → 46 linhas — `TrocarSenhaForm`, `GestaoUsuarios`,
  `CriarUsuarioForm` viraram arquivos próprios em `components/settings/`.
- **`extrairErro`** (duplicado em `Settings.tsx`/`DefinirSenha.tsx`) → `lib/errors.ts`,
  compartilhado.
- **Lógica de troca de senha** (duplicada entre `TrocarSenhaForm` e `DefinirSenha.tsx`) →
  `hooks/usePasswordChangeForm.ts` compartilhado; cada tela continua com a própria
  cópia/comportamento pós-sucesso.
- **`FormLabel.tsx`/`TextInput.tsx`** (novos): label repetida 12× e input repetido 11× ao pé
  da letra em `frontend/src` viram componentes compartilhados.
- **`AuthContext.tsx`/`ThemeContext.tsx`** separados em Provider + hook (`hooks/useAuth.ts`,
  `hooks/useTheme.ts`) + arquivo do context object cru — corrige os 2 avisos de Fast Refresh
  do oxlint (zero avisos agora).

### Validação

- Backend: 205 testes, inalterado (rodada de refactor/config, sem teste novo). `ruff check`
  limpo dos achados mecânicos.
- Frontend: `npm run typecheck`, `npx oxlint src` (**0 avisos**, antes 2), `npm run test`
  (4/4), `npm run build` — todos limpos.
- Validação visual ao vivo (Playwright): login, tema, Settings inteira (Minha conta, trocar
  senha, gestão de usuários, cadastrar usuário) e a restrição de admin — tudo funcionando após
  o refactor, zero erro de console.
- Migrations pendentes de rodadas anteriores (`senha_temporaria`, `usuario_setores`)
  finalmente aplicadas ao `bitin_backend.db` real nesta rodada (estavam causando 500 em
  qualquer login — banco preso 2 migrations atrás do código). Backup feito antes.

## [v0.8.1] - 2026-07-15

Setores múltiplos por usuário + escopo por setor/nível em usuários e BITins. Pedido explícito:
"se um usuário for gestor, ele consegue só ver listagem de usuários do setor que ele é gestor,
e coloca a opção de um usuário poder ser tanto armazenagem tanto quanto proteina" +
"lista de usuários e bitins de todo mundo, com filtragem de solicitante".

### Changed
- **`Usuario.sector_id` (FK única) → many-to-many** (`Usuario.setores`, tabela de associação
  `usuario_setores`): um usuário pode pertencer a mais de um `Setor` ao mesmo tempo. Migração
  `dd1208ae65a6` (backfill de `sector_id` + drop da coluna via `batch_alter_table`, testada
  contra cópia de `bitin_backend.db`, não aplicada ao banco real). `UserOut.sector_ids: list[int]`
  substitui `sector_id: int | None` em toda a API (`UserCreate`, `AdminUserCreate`, `UserOut`).
- **`GET /users`/`GET /users/{id}`**: gestor (nível 1) agora só vê usuários que compartilham
  ao menos um `Setor` com ele (antes via a lista do sistema inteiro, igual admin). Gestor sem
  setor nenhum vê lista vazia. `GET /users/{id}` fora do escopo do gestor → 404. Admin
  inalterado (vê todo mundo).
- **`GET /bitins`**: gestor passa a ver BITins de qualquer um que compartilhe setor com ele
  (antes só os próprios); admin passa a ver o **sistema inteiro sem filtro** (antes também
  ficava preso a "só os meus" — decisão de 2026-07-14 revertida explicitamente: "Admin vê
  tudo"). Usuário comum inalterado.
- Frontend: `Settings.tsx` — formulário "Cadastrar usuário" troca o `<select>` de setor único
  por um grupo de checkboxes; tabela "Gestão de usuários" e "Minha conta" juntam múltiplos
  nomes de setor com vírgula. `MeusBitins.tsx` — título e rótulo de busca "Solicitante" se
  ajustam pra gestor/admin (escopo mais amplo que "só os meus").

### Validação
- Backend: 205 testes (196 → 205, 9 novos cobrindo múltiplos setores por usuário, escopo de
  gestor/admin em `GET /users` e `GET /bitins`).
- `npm run typecheck`/`lint`/`test`/`build` limpos.
- Migração testada contra cópia de `bitin_backend.db` (upgrade e downgrade), banco real não
  tocado.

## [v0.8.0] - 2026-07-15

Rodada grande de três frentes: autenticação real (banco persistente + migrations, sessões
revogáveis, senha forte), reformulação completa das telas de cadastro/edição de BITin
(BITin/ZBPP009/Lista Técnica), e a paleta de cores oficial da marca. Escopo maior que os
incrementos anteriores — bump de minor (0.7.2 → 0.8.0) em vez de patch, decisão do usuário.

### Added — Autenticação

- **Migrations Alembic** (`migrations/`, `alembic.ini`, novos): antes o schema era criado via
  `Base.metadata.create_all()`, sem versionamento nenhum. Baseline + migration cobrindo os
  campos/tabelas novos abaixo.
- **`sessoes_usuario`**: sessão revogável por login — `POST /auth/logout` agora invalida o
  token de verdade (antes era JWT puro, stateless, sem jeito de derrubar antes de expirar).
- **`tentativas_login`**: rate limit de login persistido em banco (antes era um dict em
  memória do processo — não sobrevivia a restart nem funcionava com múltiplos workers).
- **`Usuario.numero_eng`, `email_verificado`, `updated_at`, `ultimo_acesso`** (colunas novas).
- **Política de senha forte** (`validate_password_strength`): mínimo 8 caracteres + 3 dos 4
  tipos de caractere, aplicada em registro e troca de senha (não retroativa).
- **`POST /auth/change-password`** (novo): antes não existia jeito de trocar a própria senha
  sem edição direta no banco. Revoga as outras sessões ativas ao trocar.
- **Normalização de e-mail** (sempre minúsculo, registro e login): corrige um bug real —
  e-mail cadastrado com maiúscula não conseguia logar se digitado diferente depois.

### Added — Telas de BITin (BITin / ZBPP009 / Lista Técnica)

- Cadastro e edição completos de um BITin: as três telas operam sobre o mesmo `materiais[]`,
  nenhuma dependendo da outra pra existir.
- **Checklist 100% manual** (`ChecklistTable.tsx`): tirada a sugestão automática a partir dos
  campos do material — todo item precisa ser clicado pelo engenheiro. Layout em grade
  responsiva (1–3 colunas) em vez de coluna única.
- **ZBPP009** (renomeada de "Códigos SAP"): bug de colagem corrigido (interceptador de colar
  agora funciona em qualquer célula da linha, não só a primeira).
- **Lista Técnica** virou página independente estilo planilha — não depende mais de materiais
  já cadastrados.
- **Bloco de material simplificado**: "Atualizar DWG/SAT" e "Centro de custo"/"Conta razão"
  saíram, viraram itens/anotação da checklist. Campo "Tipo" escondido no bloco (continua
  visível na ZBPP009, que é a réplica fiel da grade real do SAP).
- **`AjudaPopover.tsx`** (novo): ícone "?" com tutorial resumido nas três telas.
- **Excluir rascunho** direto na listagem "Meus Bitins", além de dentro do BITin.
- **Data de envio em `DD.MM.YYYY`**.

### Changed — Regras de negócio

- `scripts/bitin_business_rules.py` só bloqueia envio por regras verificáveis a partir do
  próprio BITin (Nota 8, Nota 10). Regras que dependem de confirmação externa (Nota 2 —
  desenho aprovado; Nota 17 — aprovação fiscal de NCM) não bloqueiam mais o envio — não havia
  (nem há) campo de UI pra satisfazê-las, travar nelas era travar pra sempre.

### Added — Interface

- **Configurações**: "Minha conta" ganhou troca de senha self-service; layout mais largo,
  campos longos (e-mail) não estouram mais o card, tabela de usuários rola em vez de cortar
  colunas.
- **Paleta de cores oficial da marca**: tokens de marca (`brand-navy`, `brand-gold`,
  `brand-green`, `brand-orange`, `brand-navy-light` novo) atualizados pros valores do guia
  oficial (hex/CMYK/Pantone), substituindo a aproximação anterior tirada dos arquivos de logo.

### Fixed

- `normalizarMaterial()`: material salvo antes de um campo existir no schema (ex.:
  `lista_tecnica`) quebrava a tela inteira (`Cannot read properties of undefined`), sem error
  boundary nenhum.

### Validação

- Backend: 192 testes (158 → 192), todos verdes.
- `npm run typecheck`/`lint`/`test`/`build` limpos.
- Migrations testadas contra uma cópia do `bitin_backend.db` real antes de aplicar no arquivo
  de verdade (nunca rodadas direto no original sem cópia primeiro).

## [v0.7.2] - 2026-07-14

Primeiro pedaço de verdade da tela de Bitins desde o reset da v0.5.0: listagem "Meus Bitins"
(escopada pro próprio usuário) + visualização só-leitura ao clicar numa linha. Escopo fechado
colaborativamente com o Alessandro.

### Added
- **`pages/MeusBitins.tsx`** (novo, rota `/bitins`): abas Todos/Rascunhos/Enviados, colunas
  Código/Motivo/Solicitante/Status.
- **`pages/BitinDetail.tsx`** (novo, rota `/bitins/:mongoId`): visualização só-leitura via
  `GET /bitins/{mongo_id}/resumo`, sem edição ainda.
- Novo item "Meus Bitins" na sidebar.

### Changed
- **`GET /bitins`** agora filtra por `criado_por` — cada usuário só vê os próprios BITins
  ("só os meus", mesma decisão já usada em `resumo-usuario`/Home). Antes listava o sistema
  inteiro.

### Validação
- Backend: 172 testes (3 novos, cobrindo isolamento entre usuários).
- `npm run typecheck`/`lint`/`test`/`build` limpos. Sem verificação visual ao vivo (sem
  MongoDB real nesta máquina, credenciais de teste locais desconhecidas).

## [v0.7.1] - 2026-07-14

Primeira mudança de UI visível pro engenheiro desde a v0.5.0 (a v0.6.0 e a v0.7.0 eram só
robustez/infra interna). Ainda pequena de propósito — o shell sozinho, sem a listagem de
Bitins atrás dele ainda.

### Added
- **Shell autenticado** (`Sidebar.tsx`, `Topbar.tsx`, novos): a área logada deixou de ser só
  um cabeçalho horizontal com logo/e-mail/sair — agora tem sidebar de navegação (off-canvas
  no celular) e topbar (menu mobile, tema, configurações, usuário, sair). Segue exatamente o
  padrão visual da tela de login (painel navy, logo em pílula branca, faixa de 3 cores) —
  pedido direto: "nunca fugir daquilo".
- **`pages/Home.tsx` reescrita**: de placeholder de texto ("Login funcionando.") pra uma
  página de boas-vindas de verdade, usando o primeiro nome do usuário.
- **`pages/Settings.tsx`** (novo, placeholder): o botão de configurações no topbar precisa
  levar a algum lugar real — ainda não há nada configurável de fato, mas não é mais um link
  morto.
- **`components/icons.tsx`** (novo): ícones SVG inline compartilhados entre Sidebar/Topbar.

### Validação
- Playwright ad-hoc: desktop/mobile, tema claro/escuro, navegação, configurações, logout —
  zero erro de console.
- `npm run typecheck`/`lint`/`test`/`build` limpos.

## [v0.7.0] - 2026-07-14

Continuação direta da avaliação geral do projeto (v0.6.0): CI, TypeScript no frontend, e
início de RBAC mais completo. Pendências que dependem de acesso a um Postgres real (rate
limiting compartilhado, migrations, transação distribuída) ficaram documentadas em
`requirements.md`, não implementadas ainda — aguardando o Alessandro passar a URL de acesso.

### Added
- **CI** (`.github/workflows/ci.yml`, novo): roda em todo push/PR pra `main` — suíte Python
  (`unittest discover`) e suíte de frontend (`typecheck` + `lint` + `test` + `build`). Antes
  disso nada rodava os testes automaticamente. Sem serviço de banco no workflow — os testes já
  usam SQLite + mongomock-motor.
- **TypeScript no frontend inteiro** (migração completa, não incremental — só 11 arquivos
  existiam, já que a tela de Bitins foi apagada no reset da v0.5.0): `tsconfig.app.json`/
  `tsconfig.node.json` com `strict: true`. `npm run typecheck` novo; `npm run build` agora
  typecheca antes de gerar o bundle.
- **`pode_editar` no `BitinResponse`** (`backend/api/bitins.py`, achado de auditoria "RBAC
  incompleto"): campo calculado por requisição — `false` quando quem vê não é dono/admin, ou
  quando o BITin já foi enviado. Prepara o backend pra tela de Bitins (quando reconstruída)
  abrir em modo leitura pra quem não pode editar, em vez de só descobrir com um `403` ao tentar
  salvar. 4 novos testes cobrindo dono/outro usuário/admin/já enviado.
- **`requirements.md` atualizado** com uma seção nova de "Pendências conhecidas" — itens já
  mapeados mas bloqueados por dependerem de acesso a infraestrutura externa (Postgres real),
  registrados pra não repetir a pergunta a cada rodada.

### Validação
- 164 → **168 testes automatizados Python** (4 novos cobrindo `pode_editar`).
- Frontend: `npm run typecheck` limpo, `npx oxlint src` sem warning novo, 4/4 testes (Vitest),
  `npm run build` sem erro — tudo reverificado depois da migração TypeScript completa.

## [v0.6.0] - 2026-07-13

Auditoria de segurança/arquitetura do backend (pedida diretamente) + primeira suíte de testes
automatizada do frontend. Sem mudança de UI visível pro engenheiro — tudo aqui é robustez.

### Security
- **`SECRET_KEY` padrão não deixa mais o app subir em produção**: antes, um deploy sem `.env`
  configurado subia silenciosamente com a chave JWT padrão (`backend/config.py`) — qualquer um
  forjaria um token de admin válido, sem aviso nenhum. Agora, `backend/main.py::lifespan`
  recusa subir (`RuntimeError`) se `ENVIRONMENT=production` e a `SECRET_KEY` continua no
  default. Dev local/testes nunca setam `ENVIRONMENT`, então nada muda pra eles.
- **Limite de tentativas de login** (`backend/auth/rate_limit.py`, novo): `/auth/login` não
  tinha limite nenhum — força bruta contra senha fraca só era limitada pelo custo do hash. 5
  tentativas erradas pro mesmo e-mail em 5 minutos bloqueiam com `429`. Em memória (processo
  único) de propósito — registrado como limitação conhecida se um dia rodar com múltiplos
  workers.
- **Busca (`termo`) escapada antes de virar `$regex` do Mongo**: metacaracteres de regex
  digitados pelo usuário podiam causar matches inesperados ou custo de busca patológico —
  `re.escape` aplicado em `backend/api/bitins.py::list_bitins`.

### Fixed
- **Corrida no envio (double-submit) não vaza mais como `500` puro**: se
  `gerar_e_salvar_bitin_sql` esgotasse as tentativas (quase sempre porque o mesmo BITin já
  tinha sido enviado por uma requisição concorrente — 2 cliques, 2 abas), o `RuntimeError`
  subia sem tratamento. `enviar_bitin_endpoint` agora distingue "já enviado por outra
  requisição" (erro estruturado, explicando) de um erro genuíno e raro (`503` com log).
- **Falha do Mongo depois do commit no Postgres não deixa mais número "fantasma"**: sem
  transação real cobrindo os 2 bancos, se `collection.update_one` falhasse depois do Postgres
  já ter reservado o número sequencial, sobrava um `BitinSQL` órfão. Agora desfaz o lado
  Postgres (best-effort) e loga `CRITICAL` se até isso falhar — reduz bastante a janela de
  inconsistência (não é uma solução de transação distribuída completa, ver `docs/BACKEND.md`).

### Added
- **Logging básico no backend** (`backend/main.py`): zero `logging` existia antes — uma falha
  em produção não deixava rastro nenhum além da resposta HTTP.
- **Dependências do backend com versão fixada** (`backend/requirements.txt`): antes sem
  nenhuma versão fixa (reprodutibilidade frágil); fixadas nas versões que rodam os 164 testes
  nesta máquina. `psycopg2-binary` descomentado, mas deliberadamente sem versão fixa (não
  instalado neste ambiente de dev).
- **Primeira suíte de testes de frontend commitada** (Vitest + Testing Library,
  `frontend/src/pages/Login.test.jsx`): até aqui toda validação de frontend vivia só em
  scripts Playwright ad-hoc fora do repo. `npm run test` roda smoke tests da tela de login
  (campos, mostrar/esconder senha, erro estruturado, tema).
- **3 novos testes Python** cobrindo a checagem de `SECRET_KEY` na subida
  (`tests/test_backend_main.py`), a corrida no envio e a falha do Mongo pós-commit
  (`tests/test_backend_bitins.py`), e o limite de tentativas de login
  (`tests/test_backend_auth.py`) — 164 testes automatizados no total (era 158).

## [v0.5.0] - 2026-07-13

### Removed
- **Reset da tela de Bitins**: depois de 8 rodadas de ajuste visual (ver "Added" abaixo — todo
  esse histórico fica registrado como referência do que já foi tentado), o resultado ainda
  estava "muito confuso" — decisão explícita: apagar `BitinDetail.jsx`, `MeusBitins.jsx`,
  `MaterialGrid.jsx`, `MaterialDetailModal.jsx`, `ChecklistEditor.jsx`,
  `lib/bitinFields.js`/`bitinErrors.js`/`textSearch.js` e reconstruir do zero, incrementalmente
  — login/autenticação primeiro, depois a parte de Bitins de novo, uma tela de cada vez. Lógica
  de negócio do backend (`scripts/`, `backend/api/`) não foi tocada — só a UI que consumia esses
  endpoints saiu. Ver `docs/FRONTEND.md`, seção "Reset da tela de Bitins".

### Added
- **Tela de login redesenhada** (pós-reset, foco 100% em UI/UX, backend real desde já — não
  mock): layout dividido (painel de marca navy + formulário), logo/título/subtítulo agrupados
  num bloco centralizado (1ª versão prendia a logo isolada no topo, "meio perdida"), campos com
  ícone, botão de mostrar/esconder senha, erro com `role="alert"`, spinner de carregamento,
  tema claro/escuro disponível já no login (`ThemeToggle.jsx` extraído de `Layout.jsx`),
  responsivo, versão da aplicação no rodapé lida de `frontend/package.json` (sincronizado de
  `0.0.0` pra `0.5.0`) em vez de texto fixo.
- **Tela de cadastro reconstruída como a aba "Template apresentação" real** (5ª rodada,
  correção de rota — as rodadas 1-4 tinham usado a aba `ZBPP009 + ALTERACAO`, mas o print
  enviado era do documento formatado): cabeçalho em faixas (logo/título/BITex/Setor dourado +
  Produto/Solicitante + Motivo/Data), campo `bitex` agora editável, **checklist de 22 itens
  editável de verdade** (`ChecklistEditor.jsx`, novo — antes só existia read-only no resumo
  pós-envio) via `GET /bitins/schema/checklist` (`bitin_document.build_checklist_schema`,
  novo), e cabeçalho da tabela de materiais em amarelo/dourado com "Novo" de volta pra
  vermelho (igual ao Excel real — cabeçalho dourado já separa visualmente do vermelho de erro
  de validação, que fica nas células de dado). `afeta` do checklist é 100% manual nesta
  rodada — a lógica de auto-cálculo que já existe em `build_checklist` (usada no resumo) ainda
  não roda ao vivo no formulário, ver `docs/FRONTEND.md`.
- **Grid de materiais dirigido por schema, com navegação e visual de planilha real**
  (`frontend/src/components/MaterialGrid.jsx`, `MaterialDetailModal.jsx`, `docs/FRONTEND.md`):
  substitui a lista simples de identificação por uma planilha completa (linha = material,
  colunas = campos), refeita em 3 rodadas de feedback direto até ficar de verdade "tipo
  Excel":
  - Navegação por teclado nas 4 setas (não depende de Tab) + `Enter`/`Shift+Enter`.
  - Colar em qualquer célula (`Ctrl+V`, bloco copiado do Excel), criando linhas novas
    automaticamente, além de "Importar relatório do SAP" (formato fixo, sempre linha nova).
  - Colunas "#"/"Código" congeladas ao rolar (como "congelar painéis" do Excel).
  - Painel de "Detalhes" por material (`MaterialDetailModal.jsx`) com todos os ~30 campos de
    `dados_basicos` (De/Para, com busca) e `impactos_operacionais` num layout espaçoso — a
    grade em si só fixa como coluna os campos que o usuário escolher (ideal pra colar em
    massa), evitando o problema de "muitos campos, pouco espaço".
  - **Cabeçalho "Novo" destacado**: convenção extraída da planilha real do BITin
    (`examples/bitin teste 2.xlsm`, aba `ZBPP009 + ALTERACAO`, inspecionada via `openpyxl`) —
    toda coluna de valor novo/editável tem o rótulo destacado (laranja da marca, não vermelho
    como no Excel original — vermelho já é erro de validação nesta tela).
  - **Todos os ~30 campos de `dados_basicos` visíveis por padrão** (não escondidos atrás de um
    seletor) — pedido direto: "a tela deve ser um excel enorme, com a mesma estrutura". A grade
    tem ~70 colunas contando identificação/impactos, com rolagem horizontal, igual a abrir a
    planilha real. Rótulos ajustados pra bater literalmente com o texto do Plan2 (ex.:
    "Unidade Peso", não "Unidade de Peso").
  - Modelado no `CodeForm.jsx` do projeto irmão `GPT_Engineering_BITIN`, mas reconstruído:
    colunas vêm do backend (não hardcoded), colar do SAP reaproveita o parser Python já
    testado, erros de envio destacam a célula exata (na grade ou no painel de Detalhes,
    dependendo de onde o campo está sendo editado) em vez de só listar texto solto.
- **Logo real e grade de materiais ocupando a tela inteira** (6ª rodada): logo enviado pelo
  usuário (`frontend/public/logo.svg`) substitui o placeholder de texto no cabeçalho, login e
  tela de cadastro; `<main>` (`Layout.jsx`) perdeu o `max-w-6xl` global, e a grade de materiais
  agora quebra pra fora do container centralizado (`-mx-4` em `BitinDetail.jsx`) e perdeu a
  moldura de card (`MaterialGrid.jsx`) — encosta nas bordas reais da tela, "literalmente um
  excel" em vez de uma tabela dentro de um formulário. Padding/fonte de células, cabeçalho e
  botões de ação aumentados; cálculo de largura de coluna unificado num único helper.
- **Checklist em grade de colunas, cabeçalho+checklist+grade em largura total** (7ª rodada,
  a partir de um wireframe de estrutura enviado pelo usuário): `ChecklistEditor.jsx` trocou a
  lista de 22 linhas empilhadas (`<table>`) por uma grade de 2-4 colunas (conforme a largura da
  tela), com o campo Observação só aparecendo quando o item está marcado "SIM" — a faixa caiu
  de ~750px pra ~280px de altura. Cabeçalho e checklist passaram a compartilhar o mesmo
  `-mx-4` de largura total que só a grade de materiais tinha, então as 3 faixas (cabeçalho,
  checklist, tabela) encostam nas bordas reais da tela.
- **Checklist volta a ser tabela even; grade de materiais vira "10 colunas + 300 linhas
  prontas"** (8ª rodada, correção de rota sobre a print real): a grade de cards da 7ª rodada
  deixava os 22 itens do checklist com altura desigual (Observação condicional) — voltou a ser
  uma `<table>` de verdade, que garante linhas parelhas de graça. A grade de materiais reduziu
  de ~70 colunas visíveis por padrão pra 10 (Código/Descrição/Centro + os 7 impactos
  operacionais, igual à print da aba "Template apresentação") — Tipo Material, Grupo
  Mercadorias e os 3 checkboxes de snapshot saíram da grade, mas continuam editáveis via novo
  painel "Identificação" em `MaterialDetailModal.jsx`. A grade nasce com 300 linhas em branco
  (`BitinDetail.jsx`), como uma planilha nova do Excel; linhas em branco são filtradas antes de
  salvar/enviar (`compactMateriais`/`hasContent`) já que o backend valida
  código/centro/tipo_material como obrigatórios em toda linha de `materiais[]`, sem exceção —
  os índices de erro do envio são traduzidos de volta pra célula certa da grade
  (`remapMaterialErrorIndices`). Texto explicativo acima da grade removido, só a barra de
  ferramentas.
  - Busca insensível a acento (`lib/textSearch.js`) no seletor de campos e no painel de
    Detalhes — achado testando: buscar "liquido" não encontrava "Peso Líquido".
- **Identidade visual da marca (Grain & Protein Technologies) + tema claro/escuro**
  (`frontend/src/index.css`, `ThemeContext.jsx`): paleta extraída do logo como tokens Tailwind
  v4, cabeçalho navy com faixa de 3 cores, tokens semânticos (`app-bg`/`surface`/`line`/`ink`)
  usados em todo componente pra que os dois temas fiquem consistentes num só lugar. Toggle
  claro/escuro no cabeçalho, padrão claro (não detecta o tema do sistema operacional de
  propósito), escolha persiste no navegador. Logo real ainda não está no repositório — usa
  wordmark em texto como placeholder.
- **`GET /bitins/schema/materiais`** (`bitin_model.build_materiais_schema`): fonte única de
  colunas do grid — identificação, snapshot, `dados_basicos` (na mesma ordem do crosswalk) e
  `impactos_operacionais` com os valores válidos do POP (`config/bitin_document_mapping.json`).
- **`POST /bitins/parse-sap-paste`**: expõe `sap_paste_parser.parse_sap_paste_to_materiais` pro
  frontend — colar linhas do SAP na planilha vira materiais novos direto no grid.
- **Erro de envio → célula do grid**: `frontend/src/lib/bitinErrors.js` faz o parse do `field`
  estruturado (`materiais[0].alteracoes.dados_basicos.ncm`, etc.) pra destacar a célula exata,
  além da lista completa de erros já existente.
- **RBAC visível em "Meus Bitins"**: o botão "Excluir" some quando o usuário não é dono nem
  admin (o backend já recusava com `403`; a UI agora não oferece a ação de antemão).

### Notes
- 8 testes novos (Python): `build_materiais_schema` (`tests/test_bitin_model.py`) + os dois
  endpoints novos (`tests/test_backend_bitins.py`) — 154 testes automatizados no total.
- Validado com um roteiro de 25 checagens via Playwright ad-hoc cobrindo as 10 áreas do grid
  (edição básica, navegação por teclado, colunas congeladas, colar em bloco, importar SAP,
  colunas visíveis, painel de Detalhes, validação de envio, tema claro/escuro) — mesma
  limitação de ambiente já documentada (sem MongoDB real, backend testado com
  `mongomock-motor`/rotas mockadas onde necessário). 2 bugs reais encontrados durante o teste e
  corrigidos antes de fechar: coluna congelada sobrepondo a seguinte (`position: sticky` não é
  confiável com `border-collapse`, nem `table-layout: fixed` sozinho sem largura total
  explícita — ver `docs/FRONTEND.md`) e busca de campo sem suporte a acento.
- Ainda não incluído (ver `docs/FRONTEND.md`, "O que NÃO está nesta fatia ainda"):
  `ordem_cliente[]`, `lista_tecnica[]`, checklist editável, modo de leitura explícito pra quem
  abre o rascunho de outra pessoa sem ser dono/admin, mesclar (em vez de sempre duplicar) ao
  colar do SAP em cima de um material já existente no grid.

## [v0.4.0] - 2026-07-10

### Added
- **Esqueleto do frontend** (`frontend/`, `docs/FRONTEND.md`): React 19 + Vite + Tailwind 4 +
  react-router-dom + axios, sem lib de estado global (Context API para autenticação). Primeira
  fatia funcional, validada ponta a ponta com Playwright contra o backend real: login → "Meus
  Bitins" (abas Todos/Rascunhos/Enviados + busca por termo) → criar rascunho → salvar → reabrir
  (confirma persistência) → enviar → tela travada com número gerado e checklist de 22 itens.
- `BitinDetail.jsx`: componente único cobrindo criação e edição (evita a duplicação
  `BitinForm`/`BitinEdit` vista no projeto de referência `GPT_Engineering_BITIN`).
- Rota protegida (`RequireAuth`) redireciona pro login sem token; interceptor axios limpa o
  token guardado ao receber `401`.

### Notes
- Ainda não incluído nesta fatia (documentado em `docs/FRONTEND.md`): colar do SAP, edição de
  `dados_basicos`/`impactos_operacionais` por material, `lista_tecnica[]`, `ordem_cliente[]`,
  RBAC visível na UI. Sem esses campos, o formulário ainda não cria um BITin realmente útil —
  esse é o próximo incremento.
- 147 testes automatizados (Python, sem mudança nesta versão) + verificação manual do
  frontend via Playwright (não faz parte da suíte automatizada ainda).
- Descoberta durante o teste: sem MongoDB real disponível no ambiente de desenvolvimento,
  qualquer ação de `/bitins` falha com `500` (limitação já documentada, não é bug) — o teste
  E2E rodou o backend com `mongomock-motor` no lugar do Mongo real, mesma estratégia da suíte
  de testes automatizados.

## [v0.3.0] - 2026-07-10

### Added
- **Autenticação unificada no backend** (`backend/auth/`: `models.py`, `security.py`,
  `schemas.py`, `deps.py`, `routes.py`): `Usuario`/`Setor` no mesmo Postgres do resto do
  backend, hash de senha `pbkdf2_sha256`, JWT emitido e validado localmente (sem serviço
  externo, sem segredo compartilhado entre processos). RBAC simples de 3 níveis
  (`0` usuário, `1` gestor, `99` admin). Primeiro usuário registrado (`POST /auth/register`)
  vira admin automaticamente (bootstrap); promoções depois só via
  `PATCH /users/{id}/permission`, restrito a admin.
- **Endpoints `/users` e `/sectors`** (`backend/api/users.py`, `backend/api/sectors.py`):
  perfil próprio, listagem/busca (gestor+), promoção de permissão (admin), setores (listagem
  pública, criação restrita a admin).
- **Reforço de dono nos rascunhos**: só quem criou o rascunho (ou um admin) pode editar
  (`POST /bitins/draft` com `mongo_id`) ou excluir (`DELETE /bitins/{mongo_id}`) — qualquer
  outro usuário autenticado recebe `403`. Edição por admin não reatribui `criado_por`.
- **`criado_por`** (Postgres `bitins` e Mongo `bitin_contents`): passa a ser preenchido de
  verdade com o e-mail do usuário autenticado (coluna já existia nullable desde antes).
- **Validação estrutural de `ordem_cliente[]`** (`bitin_model.validate_ordem_cliente`):
  `codigo` obrigatório por entrada, itens de `acrescentar_no_pedido[]`/`retira_do_pedido[]`
  exigem `codigo_material`+`quantidade`, entrada sem nenhum item é sinalizada
  (`ordem_cliente_sem_itens`). O schema já suportava essa forma aninhada; só o conteúdo não
  era validado ainda.
- **Todos os endpoints de `/bitins` agora exigem autenticação** (`Authorization: Bearer
  <token>`) — sem token válido, `401`.
- 13 testes novos de robustez em `tests/test_backend_bitins.py` (filtros de listagem,
  paginação, entrada degenerada em `/enviar`, lista técnica inválida via API) e um arquivo
  novo `tests/test_backend_auth.py` (registro/bootstrap-admin/login/RBAC/promoção/setores).

### Fixed (achados corrigindo o `GPT_Engineering_authAPI`, usado só como referência)
- **Escalonamento de privilégio**: no serviço de referência, `POST /auth/register` aceitava
  `permission_level` direto do corpo da requisição — qualquer um podia se registrar como
  admin. Aqui, `UserCreate` nem tem esse campo; o nível é sempre decidido no servidor.
- **CORS inválido**: `allow_origins=["*"]` + `allow_credentials=True` (combinação insegura) —
  trocado por lista explícita de origens.
- Rotas `/bitins` próprias do serviço de referência (numeração e persistência
  redundantes/incompatíveis com este sistema) não foram trazidas.

### Changed
- Reorganização de pastas: scripts/saídas do PoC leve original movidos para
  `scripts/legacy_poc/` e `scripts/legacy_poc/output/`; arquivos de exemplo/dados reais
  (`.xlsm`, `.pdf`, `exported_winshuttle.csv`) movidos para `examples/`.
- `backend/models_sql.py`: coluna `criado_por` (String, nullable) adicionada em `BitinSQL`.
- `backend/config.py`: `SECRET_KEY`/`ALGORITHM`/`ACCESS_TOKEN_EXPIRE_MINUTES` substituem as
  variáveis do design anterior de serviço de auth separado (abandonado antes de ser
  publicado); `VERSION` atualizado para `0.3.0`.

### Notes
- 147 testes automatizados no total (era 114 na v0.2.0).
- Decisão de arquitetura registrada e depois revisada no mesmo dia: cogitamos rodar a
  autenticação como serviço separado (JWT validado por segredo compartilhado entre dois
  `.env`), mas optamos por unificar no mesmo processo/banco — evita sincronizar segredo entre
  dois arquivos `.env` e resolve RBAC/reforço de dono sem exigir chamada de rede por
  requisição. Ver `docs/BACKEND.md`, seção "Autenticação", para o histórico completo da decisão.

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
- Release notes sourced from `docs/releases/RELEASE_v0.1.0.md`.
- Documentation updated in `README.md` and `docs/README_HANDOFF.md` with release URL.

### Notes
- Release was created manually via GitHub UI.
- Release automation script removed from repository.
