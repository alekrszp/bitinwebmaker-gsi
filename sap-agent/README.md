# Agente SAP local (BITin)

Mini-projeto Python separado do resto do repositório (`backend/`/`scripts/`) -- roda **na
máquina do engenheiro**, não no servidor do BITin. Faz a ponte entre a tela do BITin (navegador)
e o SAP GUI já aberto/logado nesta máquina, via **SAP GUI Scripting** (automação COM da
interface, não uma API REST/RFC/BAPI/OData do SAP).

## Por que existe

Sem o agente, o BITin é 100% manual (aba BITin só, ver `docs/FRONTEND.md`). Com o agente
conectado, uma aba extra ("Automação") passa a existir, e o engenheiro consegue consultar de
verdade se um código de material existe no SAP, trazer a descrição real e preencher campos de
`dados_basicos` (via `MM03`/`MM60`/`MM06`) sem sair do navegador.

## Como funciona

```text
Navegador (BITin)  <-- HTTP localhost:39217 -->  Agente (este diretório)  <-- COM/SAP GUI Scripting -->  SAP GUI aberto
```

- `sap_gui.py` -- port em Python das macros VBA fornecidas pelo usuário
  (`PESQUISA_CODIGO 11.xlsm`): abre `MM60`/`MM03`/`MM06`, digita o código do material, executa,
  lê os valores de volta.
- `servidor.py` -- servidor HTTP local (Flask) que expõe `GET /status`,
  `POST /consultar-materiais`, `GET /campos-disponiveis`, `POST /preencher-dados-basicos` e
  `POST /identificar-usuario`. `ServidorAgente` (classe no mesmo arquivo) controla o ciclo de
  vida de verdade -- `.iniciar()`/`.parar()` (via `werkzeug.serving.make_server`, não o
  `app.run()` bloqueante) -- pra dar suporte ao botão "Agente ativo" da janela (abaixo).
- `estado_agente.py` -- estado em memória compartilhado entre o servidor e a janela (só quem
  está logado no BITin agora, ver "Identificação do usuário" abaixo).
- `config_agente.py` -- configuração persistida (`%LOCALAPPDATA%\AgenteSAP\config.json`):
  `ativo` (default `False`) e `abrir_com_windows` (default `True`).
- `startup_windows.py` -- registra/remove o agente da inicialização do Windows (chave `Run`,
  HKCU, sem admin).
- `atalho_windows.py` (2026-07-23) -- atalho no **Menu Iniciar** (o que faz o agente aparecer
  na busca do Windows/barra de tarefas, pedido explícito: "consegue pesquisar na barra de
  tarefas") + entrada em **Programas e Recursos** (Painel de Controle), pra desinstalar como
  qualquer aplicativo de verdade -- `UninstallString` chama o próprio `.exe` com
  `--desinstalar` (ver `agente_app.py::_desinstalar`), sem precisar de um 2º executável só pra
  isso. Tudo em HKCU/pasta do usuário, sem admin, mesmo espírito do resto do instalador.
- `instancia_unica.py` (2026-07-23) -- garante só 1 agente rodando por vez nesta máquina
  (pedido explícito: "coloca validação de poder abrir somente 1 agente no pc"). Mutex nomeado
  do Windows (`CreateMutex`); se já existe uma instância, a nova tentativa só traz a janela da
  instância existente pra frente (`mostrar_instancia_existente`, via API de janela do Windows,
  funciona mesmo com o servidor HTTP desligado) e encerra, sem criar janela/bandeja/servidor
  duplicados -- corrige o comportamento de antes, onde cada clique em `bitinsap://abrir` (ou
  reabrir pelo atalho) lançava um processo novo.
- `agente_app.py` -- **o agente de verdade**: roda `servidor.py` numa thread, mostra uma
  **janela de verdade** (Tkinter, **tamanho fixo, não redimensiona**) com 3 abas e um ícone na
  bandeja do Windows. Minimizar ou fechar (botão X) só esconde a janela (nunca encerra o
  processo); só **"Sair"** no menu da bandeja encerra de verdade.
  - **Leia-me** -- explicação do que o agente é/faz/não faz.
  - **BITin** -- checkbox **"Agente ativo"** (liga/desliga o servidor HTTP de verdade -- a tela
    do BITin detecta a queda no próprio poll de status, testado de verdade: parar o servidor
    derruba `/status` na hora) e "Conectado como: ..." (ver "Identificação do usuário" abaixo).
  - **Configurações** -- checkbox **"Abrir automaticamente com o Windows"** (já vem marcado por
    padrão, registra/remove via `startup_windows.py`) e o caminho de onde o `.exe` está
    instalado nesta máquina.

  É este arquivo que vira o executável `AgenteSAP.exe`, não `servidor.py` diretamente -- rodar
  `servidor.py` sozinho continua funcionando (útil pra depurar no terminal, sem janela/ícone).
- `instalador.py` / `instalador_logica.py` -- **tela de instalação**: pede a pasta de destino
  (pré-preenchida com `%LOCALAPPDATA%\AgenteSAP\`, mas o engenheiro pode trocar, "como se
  fosse qualquer outro executável"), copia `AgenteSAP.exe` pra lá, registra `bitinsap://` e
  registra o agente como aplicativo de verdade (atalho no Menu Iniciar + Programas e Recursos,
  ver `atalho_windows.py` acima) -- **nunca inicia o agente sozinho** (garantido por teste,
  `test_instalar_nunca_inicia_o_processo`). O agente só passa a rodar quando alguém pede de
  verdade: botão "Ativar agora" na tela final do instalador, procurando "Agente SAP" no menu
  Iniciar, ou clicando em "Abrir agente" na tela do BITin (dispara `bitinsap://abrir`).
- `AgenteSAP.exe` vem **embutido dentro do `Instalador.exe`** (via `--add-data`) -- o engenheiro
  baixa e distribui **1 arquivo só**.

## Identificação do usuário (2026-07-23)

Quando o sistema web detecta o agente conectado, manda quem está logado
(`POST /identificar-usuario`, `frontend/src/lib/sapAgent.ts::identificarUsuarioNoAgente`,
chamado de `BitinDetail.tsx`) -- a janela do agente (aba Configurações) mostra "Conectado como:
Fulano (`fulano@empresa.com`)". **Isso não é autenticação nenhuma** -- é só exibição, pro
engenheiro confirmar visualmente que é a conta certa; qualquer processo rodando em
`localhost:39217` já é implicitamente confiável nesta máquina (mesmo modelo de confiança do
resto do agente). Desativar o agente (checkbox "Agente ativo") limpa esse estado.

## Empacotamento (quem gera o `.exe` -- 1 vez por versão nova do agente)

1. Instalar as dependências (numa máquina Windows, com Python 3.11+):

   ```bash
   pip install -r requirements.txt
   ```

2. Gerar o ícone `.ico` a partir da logo (mesma imagem da bandeja/janela/frontend, ver
   `logo_agente.py::gerar_ico` -- sem isso os `.exe` usam o ícone padrão do Python):

   ```bash
   python logo_agente.py
   ```

   Gera `sap-agent/icone.ico` (não versionado, ver `.gitignore` -- é gerado, não um asset).
3. Gerar `AgenteSAP.exe` primeiro (o instalador embute ele):

   ```bash
   pyinstaller --onefile --windowed --name AgenteSAP --icon icone.ico agente_app.py
   ```

4. Gerar `Instalador.exe` embutindo o `AgenteSAP.exe` gerado no passo anterior (`--add-data`,
   separador `;` no Windows):

   ```bash
   pyinstaller --onefile --windowed --name Instalador --icon icone.ico --add-data "dist/AgenteSAP.exe;." instalador.py
   ```

   `dist/Instalador.exe` agora é **auto-contido** (~65-70MB, já inclui o agente dentro).
5. Colocar esse `Instalador.exe` no caminho apontado por
   `backend/config.py::AGENTE_SAP_INSTALADOR_PATH` (padrão: `sap-agent/dist/Instalador.exe`,
   relativo à raiz do repo -- produção pode apontar pra outro caminho via `.env`). O backend
   serve ele em `GET /api/v1/agente-sap/download` (endpoint público, sem login -- ver
   `backend/api/agente_sap.py`), e a tela "Instalar o agente SAP" do BITin
   (`InstalarAgenteCard.tsx`) já tem o botão "Baixar instalador (.exe)" apontando pra lá.

## Instalação (o engenheiro, na própria máquina dele)

1. Na tela do BITin, clica em "Ativar agente?"/"Instalar o agente SAP" → "Baixar instalador
   (.exe)" -- baixa o `Instalador.exe` direto do sistema, sem precisar pedir pra ninguém.
2. Roda o `.exe` baixado (não precisa de administrador). Tela inicial → escolhe a pasta de
   destino (vem pré-preenchida, mas pode trocar) → "Instalar" → tela final com "Ativar agora"
   (opcional) e "Fechar". Sem clicar em "Ativar agora", o `.exe` fica instalado mas **não é
   executado** até ser aberto manualmente ou pela tela do BITin depois -- e mesmo depois de
   aberto, o servidor HTTP em si começa **desativado** (checkbox "Agente ativo" desmarcado, ver
   seção do `agente_app.py` acima) até o engenheiro marcar.

Alternativa manual (sem o instalador gráfico, ex. pra depurar): `registrar_protocolo.ps1`
continua funcionando exatamente como antes, registrando o protocolo pra um `.exe` já copiado
manualmente.

## Uso

Com o SAP GUI aberto e logado: botão "Abrir agente"/"Instalar o agente SAP" na tela do BITin
(ou procurando "Agente SAP" no menu Iniciar do Windows, ver `atalho_windows.py`) →
`bitinsap://abrir` → Windows inicia o `AgenteSAP.exe` (se já tiver uma instância rodando, só
traz a janela dela pra frente -- nunca abre uma segunda, ver `instancia_unica.py`) → na janela
que abre, aba **BITin** → marca **"Agente ativo"** → a tela do BITin detecta sozinha (poll a
cada ~4s + checagem imediata ao focar a aba do navegador, ver
`hooks/useAgenteSapConectado.ts`). Pra desligar, desmarca o mesmo checkbox (a janela continua
aberta/minimizada, só o servidor HTTP para) -- a tela do BITin percebe na checagem seguinte e
volta pro modo manual (aba Automação some). Fechar a janela (botão X) ou minimizar só manda pra
bandeja, nunca desliga o agente nem encerra o processo; só **"Sair"** no menu da bandeja encerra
de verdade.

**Desinstalar**: painel de controle → "Programas e Recursos" → "Agente SAP - BITin" →
Desinstalar (chama `AgenteSAP.exe --desinstalar`, que remove o registro do Windows/atalho/
protocolo; a pasta de instalação em si precisa ser apagada manualmente -- um processo não
consegue apagar o próprio `.exe` em execução).

**Deploy fora de `localhost` (CORS)**: `servidor.py::ORIGENS_PERMITIDAS` só libera as portas de
dev do Vite por padrão -- **qualquer** deploy real do frontend (mesmo padrão de
`backend/config.py::CORS_ORIGINS`, ver `docs/DEPLOY.md`) precisa da variável de ambiente
`BITIN_AGENTE_CORS_ORIGENS` (string separada por vírgula) apontando pra URL de verdade do
sistema web, senão o navegador bloqueia toda chamada do BITin pro agente local.

## Rodando os testes

```bash
pip install -r requirements.txt
pytest tests
```

Os testes de `sap_gui.py` usam um mock do objeto COM da SAP GUI Scripting -- não dependem de
`pywin32` nem de SAP GUI real instalado, rodam em qualquer máquina/CI.

**Não testado nesta rodada** (só é possível numa máquina Windows com SAP GUI aberto e logado):
o fluxo completo `obter_sessao()` -> `MM60` -> leitura da grade contra um SAP real. Testar isso
de verdade fica a cargo do primeiro engenheiro a usar o agente em produção.

## Limitações conhecidas (por design, herdadas da macro original)

- Serial: um material por vez (SAP GUI Scripting não paraleliza).
- Nunca bloqueia o envio do BITin -- só avisa (mesma filosofia do resto do sistema).
- Resultado da validação fica só na sessão do navegador -- não é persistido no BITin. Reabrir a
  tela perde o indicador (✓/✗), mas não perde o dado já preenchido/salvo normalmente.

## Campos de `dados_basicos` mapeados (modo "Código + Campos")

Além de Descrição (via `MM60`), o modo "Código + Campos" (aba Automação, ver
`docs/FRONTEND.md`) já sabe buscar estes campos direto do `MM03`/`MM06` -- IDs de tela
confirmados por gravação real do SAP GUI Scripting (`Alt+F12` → Scripting → "Gravar script"),
NUNCA inferidos a partir do nome da tabela/campo ABAP (ver `sap_gui.py::CAMPOS_MM03`):

- `nivel_revisao` (Dados básicos 1)
- `grupo_mercadorias` (Dados básicos 1)
- `hierarquia` (Dados básicos 1)
- `peso_bruto` (Dados básicos 1)
- `peso_liquido` (Dados básicos 1)
- `unidade_peso` (Dados básicos 1)
- `unidade_volume` (Dados básicos 1)
- `volume` (Dados básicos 1)
- `material_substituto` (Dados básicos 2)
- `documento` (Dados básicos 2)
- `planejador` (MRP 1)
- `grupo_compradores` (MRP 1)
- `prazo_entrega` (MRP 2)
- `deposito_suprimento_externo` (MRP 2)
- `deposito_producao` (MRP 2)
- `tipo_suprimento` (MRP 2)
- `tipo_suprimento_especial` (MRP 2)
- `perfil_producao` (Esquematiz.trabalho)
- `responsavel_controle_producao` (Esquematiz.trabalho)
- `producao_interna` (Contabilidade 2, checkbox)
- `origem_material` (Contabilidade 2)
- `utilizacao_material` (Contabilidade 2)
- `data_bloqueio_vendas` (SD: Org.Vendas 1)
- `status_bloqueio_vendas` (SD: Org.Vendas 1)
- `ncm` (Com.ext: Importação/Exportação)
- `marcacao_eliminar_nivel_mandante` (MM06 sem preencher Centro, checkbox)
- `marcacao_eliminar_nivel_centro` (MM06 preenchendo o Centro antes, mesmo checkbox)

26 campos no total -- só falta `texto_pedidos_compras` (a única aba de bloco de texto; nas 4
gravações a aba foi selecionada mas o texto em si nunca foi clicado). Pra mapear os que faltam:
achado real das 4 gravações (`Script1.vbs`-`Script4.vbs`) -- o gravador do SAP GUI só mantém
com confiança **1 campo por abertura de transação**; pra capturar mais de 1 campo na MESMA aba,
é preciso **reabrir a MM03 do zero** (`/nMM03` + material + Enter de novo) entre cada campo, não
basta trocar de aba dentro da mesma sessão aberta.
