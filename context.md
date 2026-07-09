---
tags: [processo, bitin, sap, winshuttle, windchill, mm02, cc01]
status: ativo
atualizado: 2026-07-08
ref: POP_ENG_7.3.7_002 (Revisão J — 14/10/2025)
---

# Processos do BITIN

O BITin é o documento formal utilizado para solicitar alterações, liberações e correções de materiais, processos e desenhos. 

Existem duas naturezas de processo na Central: **gerar um BITin de Liberação** (para um código novo) e **executar um BITin de Alteração** (que vem preenchido da engenharia).

---

## 1. Regras Gerais e Numeração

O número de qualquer BITin segue o formato: **`YXXXX/AA`**

| Parte | Significado |
| ----- | ----------- |
| `Y` | `P` = Proteína Animal / `A` = Armazenagem de Grãos |
| `XXXX` | Número sequencial ligado ao cadastro do usuário na engenharia |
| `AA` | Dois últimos dígitos do ano corrente |

> Exemplo: **P3301/22** = usuário cadastrado com nº 33, primeiro BITin criado, ano 2022.
> **ATENÇÃO:** Na hora de salvar arquivos ou preencher campos no Windchill, o padrão exige que a barra seja removida: **`P330122`**.

### Quando emitir um BITin
Um BITin deve ser emitido quando ocorrer **ao menos uma** das situações abaixo:
- Liberação de material, desenho, produto ou processo
- Nacionalização de um material
- Alteração em lista técnica ou roteiro de fabricação
- Alteração de versão de desenho, instrução de montagem, manuais ou adesivos/serigrafias
- Criação ou alteração de dados básicos e especificações técnicas
- Alteração de NCM *(exige aprovação do departamento fiscal ANTES)*
- Eliminação de códigos inutilizados / Reativação de códigos eliminados
- Liberação de produto para venda (incluir item em lista de preço) / Precificação de materiais

---

## FLUXO A: Geração de BITIN de Liberação

Processo de geração e envio de um novo Bitin via automação Winshuttle.

### Passo a Passo (Geração)

1. Acessar a planilha:
   ```
   \\10.53.0.18\dados\CCM_MRU\CCM02 → STATUS CC02
   ```
2. Acessar a aba **Num_bitin**
3. No último código registrado, colocar a **data de hoje** no campo **"Data solicitação"**
   > Aplica-se tanto para Armazenagem quanto para Proteína
4. Acessar o Bitin gerado em:
   ```
   Y:\CONTROLES\BITin
   ```
5. Excluir linhas vazias e colocar a **data no Bitin**
6. Logar com o SAP, acessar a aba **Winshuttle** e rodar o script:
   ```
   bitin_automatico_base
   ```
7. Salvar o Bitin na pasta:
   ```
   Y:\CONTROLES\BITin
   ```

### Envio Windchill (Liberação Final)

No BITin de Liberação, o envio pelo Windchill destina-se à **Liberação Final** da linha.

1. Acessar a pasta de Bitins de **Armazenagem** ou **Proteína** no ano e mês correspondente
2. Criar novo documento:
   - **FILE TYPE:** Document
   - **FILE NAME:** acessar `Y:\CONTROLES\BITin` e colocar o Bitin desejado (nome sem barra)
   - **NUMBER/NAME:** número do Bitin (sem barra)
   - **DESCRIPTION:** produto/motivo do Bitin
3. Criar novo **PROMOTION REQUEST**:
   - Ir em: `NEW → NEW PROMOTION REQUEST`
   - Selecionar aprovadores correspondentes ao Bitin.

**Liberação Final:** A liberação das linhas é feita por **Jean Triches** (Armazenagem) ou **Wagner Bassani** (Proteína), em conjunto com a **Controladoria**.

### Envio Email (A e P)

1. Acessar a planilha `STATUS CC02` (`\\10.53.0.18\dados\CCM_MRU\CCM02 → STATUS CC02`)
2. Acessar a aba **Num_bitin**
3. Na coluna **email_ARM** ou **email_PAN**, digitar `x` na célula correspondente ao Bitin liberado

---

## FLUXO B: Execução de BITIN de Alteração

Este processo inicia quando um engenheiro manda o BITin preenchido por e-mail para execução.

### 1. Triagem Inicial
1. Abrir o BITin e identificar de imediato se é da linha de **Armazenagem** ou **Proteína**.
2. Ler o **Campo "Alt"** no documento para saber o tipo de alteração e definir a rota final do BITin:
   - `D/P`: Alteração de **desenho E processo** — (Ex: peso, lista técnica, dimensões). **ENVIA PRA PROCESSO**.
   - `D/-`: Apenas **desenho** — (Verificar se também altera processo). **ENVIA PRA PROCESSO**.
   - `-/P`: Apenas **processo** (sem desenho) — (Ex: alteração de lista técnica). **ENVIA PRA PROCESSO mas depende, sempre bom analisar**
   - `D/F`: Desenho para **fornecedor** — (Liberar ou alterar desenho). **NÃO ENVIA PRA PROCESSO**.
   - `-/F`: Modificação **com fornecedor** — (Alguma modificação comercial/fornecimento). **NÃO ENVIA PRA PROCESSO**.
   - `-/-`: **Sem alteração** de desenho, processo ou fornecedor. **NÃO ENVIA PRA PROCESSO**.
3. Analisar o volume do que é pedido:
   - **Bitin muito grande:** (Vários códigos, lista técnica grande) → Ir atrás dos templates de Winshuttle mapeados na rede: `Z:\Winshuttle Material\WINSHUTTLE LUCAS\TEMPLATES PRONTOS`.
   - **Bitin pequeno:** Proceder com o cadastro e alteração **manual** no SAP. (O passo a passo abaixo detalha a execução manual).

### 2. Criar CC01 no SAP (Pré-requisito Crítico)

> [!IMPORTANT] PRIMEIRA COISA ANTES DE ALTERAR CÓDIGOS
> Sempre criar o **CC01** antes de iniciar qualquer alteração nos materiais.

1. Acessar a transação **CC01**.
2. Informar o número do Bitin no campo do número.
3. **Template:** Nunca esquecer de colocar lá em baixo o modelo **`A0000/00`**. Com isso, o sistema puxa os campos corretos.
4. Preencher os campos subsequentes (todas essas informações são visualizadas no cabeçalho do BITin recebido):
   - **Produto:** Primeiro campo ao lado do número.
   - **Data:** Sempre constar a data que está no BITin. *Regra de exceção:* se for uma data muito antiga, colocar a data de hoje.
   - **Motivo:** Abaixo da data, descrever de forma bem simples o motivo da alteração.
5. Salvar. Só agora podemos fazer as alterações dos códigos.

### 3. Alteração Manual no SAP (MM02)

Procedimento geral para alterações de campos diretamente no sistema.

1. Acessar a transação **MM02** (módulo de modificação de material).
2. O SAP pedirá o **Material** que vai ser alterado e o **Número do BITin**.
3. Ao confirmar, abre-se uma janela de **Visões** (são bastantes abas, é nelas que ficam os campos).
   - Você marca as visões necessárias e entra. 
   - *Dica:* Você pode deixar visões pré-fixadas (marcadas como padrão) para sempre que entrar elas estarem selecionadas. As visões **Dados Básicos 1 e 2** concentram boa parte das alterações rotineiras.
4. Dependendo da visão escolhida, o SAP vai pedir o **Centro**:
   - `2001` = Marau
   - `2005` = Passo Fundo
   - O centro sempre deve constar no BITin. Se não tiver, pode ser que a alteração seja nos dois, mas **com dúvidas, sempre contatar o engenheiro**. Nunca tente adivinhar o centro, pois preenchimentos incorretos geram problemas graves lá na frente.
5. Centro escolhido, abrirá a tela dos campos. Navegue até o campo desejado, altere o valor.
6. *Nota sobre Salvamento:* Você não precisa salvar imediatamente e sair se houver mais de um campo para alterar no mesmo código. Continue editando e navegando pelas visões. Quando terminar tudo daquele código, aí sim salve e vá para o próximo.

#### MAPEAMENTO DE CAMPOS MANUAIS

> [!NOTE] Dicionário de Campos
> Duvidas de campos 
>: [[MAPEAMENTO CAMPOS SAP]]

### 4. Salvamento do Arquivo do BITIN (MUITO IMPORTANTE)

Após realizar todos os cadastros e alterações no SAP:
1. Voltar para o arquivo do BITin preenchido.
2. Salvar o arquivo na pasta oficial da rede:
   `\\10.53.0.18\dados\DENG_MRU\SISTEMA DE ENGENHARIA\CONTROLES\BITin`
3. **Padrão de Nome (Regra Crítica):** Salvar SEMPRE com apenas a letra que identifica o setor e o número, **SEM BARRA (`/`)** nem nada a mais. 
   - *Correto:* `P330122`
   - *Incorreto:* `P3301/22`
   - Esse é o padrão aceito e que facilita muito o cadastro no Windchill depois.
4. Deixe o arquivo aberto para facilitar o próximo passo.

### 5. Registro e Controle (Obrigatório)

Sempre que for executado um Bitin de alteração, atualizar a **planilha WEB de controle**:

| Coluna | Conteúdo |
| ------ | -------- |
| 1 | Número do Bitin |
| 2 | Nome do proprietário *(automático)* |
| 3 | Status |
| 4 | Observação |
| 5 | Quem executou |
| 6 | Data |

### 6. Envio

Agora vamos verificar se o BITin deve ir para Roteiro ou não.

#### Caminho 1: roteiro
Se houver alteração de roteiro, o BITin faz uma parada obrigatória no departamento de Processos antes do Windchill.
1. Encaminhar o e-mail para processos, colocando o solicitante em cópia.
2. Aguardar o retorno. Processos fará a parte dela e devolverá o e-mail para a Central (para você).
3. Ao receber de volta, **verificar se houve alteração de cadastro** solicitada por ela (é raro, mas pode acontecer). Se houver, execute as correções no SAP.
4. Estando tudo certo, o BITin **segue para o Envio Windchill (abaixo)**.

#### Caminho 2: Envio Windchill (Padrão para TODOS os BITins de Alteração)
Se não há alteração de roteiro (já tem a regra estabelecida para isso), ou se o BITin de roteiro já retornou, o documento segue para aprovação formal no sistema Windchill:

1. Acessar a pasta de Proteína ou Armazenagem no mês e ano correto.
2. Clicar para adicionar um novo documento:
   - **FILE TYPE:** Document
   - **FILE NAME:** Procurar o arquivo recém-salvo. O nome deve ser **O número do bitin sem barra**.
   - **NUMBER/NAME:** **O número do bitin sem barra** (ex: P330122).
   - **DESCRIPTION:** Produto + Motivo. *(Dica: É só copiar e colar do cabeçalho do arquivo).*
3. Clicar com o botão direito no documento inserido → `New` → `New Promotion Request`.
4. Pode avançar até a última etapa dos participantes (aprovadores e setores).
5. **Partes de setores:** Marcar corretamente as partes dos setores a serem atingidos dentro do Windchill.
6. **Aprovadores:** O aprovador segue a "check list de aprovação" do arquivo. 
   - *Lembrete:* Se o próprio solicitante constar nos aprovadores, coloque ele. (Consulte as regras gerais em: [[APROVADORES WINDCHILL]]).
7. Enviar. Tá feito!

> **Notificação Final:** O próprio fluxo encaminhará o BITin para o responsável pela solicitação, criando o e-mail para notificar. Lembre-se de atualizar na planilha que ele foi concluído.

---

## Rework (Retrabalho)

Rework ocorre quando um Bitin foi enviado para Promotion Request mas precisou ser **alterado em alguns pontos**.

1. No Windchill, em **HOME → My Tasks**: localizar o **Promotion Request** criado anteriormente
2. Acessar o Promotion Request → aba com o Bitin em questão → no dropdown **Actions → Check Out and Edit**
   - Abre a tela de edição do Bitin
   - Alterar o arquivo que foi feito o rework
   - Dar **check-in**
3. Voltar para a tela do Bitin inicial → clicar em **"Complete Task"**
   - O Promotion Request continua no fluxo de aprovação

   ---
tags: [referência, windchill, aprovadores, bitin]
status: ativo
atualizado: 2026-07-08
---

# Aprovadores Windchill

Lista de aprovadores para o **Promotion Request** no Windchill, por produto e linha.

> [!NOTE] Regra Geral
> Quando o **solicitante do Bitin** for um dos aprovadores dentro do Windchill, colocar **ele mesmo** como aprovador.

---

## Armazenagem

| Produto / Solicitante           | Aprovador                               |
| ------------------------------- | --------------------------------------- |
| Secadores / Adair Jung          | Jonas Tassi                             |
| Passarelas                      | Jean Triches                            |
| Jonathan Durante                | Edson Antonello                         |
| Elevador de canecas             | Nelson Brambatti                        |
| Silos de passo fundo            | Fabio Triches                           |
| Escadas                         | Edson Antonello                         |
| Transportador de Corrente – NPD | Leonardo                                |
| Transportador de Corrente – CP  | Kelly                                   |
| Controladores eletrônicos       | Marcos Dalmoro (A) / Sheila Rossoni (P) |
| Fornalha                        | Jonas Tassi                             |
| HI-FLIGHT                       | Leonardo Calioni                        |
| REDLER                          | Leonardo Calioni                        |
| Plataforma de interligação      | Edson Antonello                         |
| Jose Eduardo                    | Edson Antonello                         |
| Anel Colar Funil                | Edson                                   |
| Pisos                           | —                                       |
| PAS PAG/Bruna Esteres           | Fabio Triches                           |
| telhados silos/caroline colet   | Fabio Triches                           |

---

## Proteína

| Linha               | Segmento    | Produto                                 | Eng. Responsável  |
| ------------------- | ----------- | --------------------------------------- | ----------------- |
| Ambiência           | Aves/Suínos | Exaustores 36", 50", 54" e 58"          | Wagner            |
| Ambiência           | Aves/Suínos | Ventilador P3D                          | Wagner            |
| Ambiência           | Aves        | Circulador de Ar                        | Wagner            |
| Ambiência           | Aves/Suínos | Inlet Lateral                           | Edilson           |
| Ambiência           | Aves/Suínos | Inlet Teto                              | Wagner            |
| Ambiência           | Aves/Suínos | Tunnel Door                             | Jonathan / Wagner |
| Ambiência           | Aves/Suínos | Sistema Evap. Cooling                   | Tiago             |
| Ambiência           | Aves        | Light Trap                              | Edilson           |
| Ambiência           | Aves        | Nebulizadores                           | Tiago             |
| Ambiência           | Aves/Suínos | Máquinas Acionamento SS+                | Tiago             |
| Ambiência           | Aves        | Máquinas Powertrack                     | Tiago             |
| Silo e Linhas       | Aves/Suínos | Silos de Ração SAR3                     | Tiago             |
| Silo e Linhas       | Aves/Suínos | Linhas de Distribuição de Ração (LDR's) | Wagner            |
| Silo e Linhas       | Aves/Suínos | Chupins p/ Silos de Ração               | Wagner            |
| Comed. Aves         | Aves        | Comed. Manual                           | Wagner            |
| Comed. Aves         | Aves        | Comed. Infantil                         | Wagner            |
| Comed. Aves         | Aves        | Comed. Aut. p/ Frango (Hi-Lo e MiniPan) | Wagner            |
| Comed. Aves         | Aves        | Comed. Aut. p/ Perus                    | Wagner            |
| Comed. Aves         | Aves        | Comed. Aut. Corrente (CAC)              | Tiago             |
| Comed. Aves         | Aves        | Sist. Levante CAC                       | Jonathan / Tiago  |
| Beb. Aves           | Aves        | Beb. Nipple                             | Wagner            |
| Beb. Aves           | Aves        | Beb. Pendular                           | Wagner            |
| Beb. Aves           | Aves        | Filtro e Dosador                        | Wagner            |
| Ninho               | Aves        | Ninho Automático                        | Edilson           |
| Ninho               | Aves        | Esteira Transp. Ovos                    | Edilson           |
| Aquecedores         | Aves        | Aquecedor Global                        | Robson            |
| Aquecedores         | Aves        | Aquecedor ACS                           | Robson            |
| Aquecedores         | Aves/Suínos | Aquecedor Super Saver                   | Robson            |
| Comed. Suínos       | Suínos      | Comed. Max Pig                          | Edilson           |
| Comed. Suínos       | Suínos      | Comed. Multitratos                      | Edilson           |
| Comed. Suínos       | Suínos      | Dosificadores                           | Edilson           |
| Comed. Suínos       | Suínos      | Comed. Dosaflex                         | Edilson           |
| Comed. Suínos       | Suínos      | Comed. HD Plus                          | Edilson           |
| Comed. Suínos       | Suínos      | Comed. Hydromat                         | Edilson           |
| Comed. Suínos       | Suínos      | Comed. TF                               | Edilson           |
| Comed. Suínos       | Suínos      | Comed. CSC                              | Edilson           |
| Comed. Suínos       | Suínos      | Chain Disk                              | Edilson           |
| Beb. Suínos         | Suínos      | Bebedouros                              | Edilson           |
| Pisos e Divisórias  | Suínos      | Pisos Plásticos                         | Edilson           |
| Pisos e Divisórias  | Suínos      | Divisória PVC                           | Edilson           |
| Pisos e Divisórias  | Suínos      | Suportes p/ Pisos                       | Edilson           |
| Ferragens p/ Suínos | Suínos      | Celas/Baias                             | Edilson           |
| Ferragens p/ Suínos | Suínos      | Periféricos                             | Edilson           |
| Outros              | Aves/Suínos | Cortinas                                | Tiago             |
| Outros              | Aves/Suínos | Acessórios em Geral                     | Wagner            |
| Controles           | Aves/Suínos | EDGE                                    | Marcos D.         |
| Controles           | Aves/Suínos | Linha CA                                | Marcos D.         |
| Controles           | Aves/Suínos | Painéis em Geral                        | Sheila            |
| Controles           | Aves/Suínos | Inobram                                 | Marcos D.         |
| PSS                 | Aves        | Galpões Metálicos                       | Dilmar            |

---
tags: [referência, fluxo, engenharia, bitin, ccm, windchill, sap]
status: ativo
atualizado: 2026-07-08
ref: POP_ENG_7.3.7_001 / POP_ENG_7.3.7_002
---

# Fluxo de Engenharia — Códigos e Documentos

---

## 1. Criação de Material Novo → CCM → SAP

```
Solicitante identifica necessidade de novo material
        ↓
Verifica se já existe material similar no SAP
        ↓ (não existe)
Preenche o template da CCM com os dados do material
        ↓
Encaminha CCM para as áreas conforme tipo de material (ver abaixo)
        ↓
Fiscal valida / determina a NCM
        ↓
Central de Controle e Cadastro recebe a CCM
        ↓
Cadastro no SAP via Winshuttle (MM01)
        ↓
Custos calculam o material
        ↓
CCM concluída → e-mail de conclusão para o solicitante
```

### Quem participa conforme o tipo de material

| Tipo | Fluxo |
| ---- | ----- |
| VERP / HAWA / ROH / HALB Comprado | Solicitante → **Compras** (NCM + dados) → Fiscal → Central → Custos |
| HALB Subcontratado | Solicitante → **Compras** (NCM + dados) → Fiscal → Central → Custos + Lista Técnica |
| HALB Produzido | Solicitante → Fiscal → **Eng. de Processos** (roteiro) → Central → Custos + Lista Técnica + Roteiro |
| FERT | Solicitante → Fiscal → Central → Custos + Lista Técnica |
| ERSA / HIBE / FHMI | Solicitante → Fiscal (se NCM necessário) → Central |
| ZEST / DIEN / UNBW / NLAG | Solicitante → Fiscal (se NCM necessário) → Central |

> [!NOTE] NCM desconhecida
> Quando a NCM não é conhecida, o solicitante entra em contato com o **fiscal** para determinarem juntos antes de enviar a CCM.

---

## 2. Alteração / Liberação → BITin → SAP + Windchill

```
Ocorre uma situação que exige BITin
(alteração de lista técnica, liberação de material,
 mudança de NCM, versão de desenho, etc.)
        ↓
Solicitante elabora o BITin e envia por e-mail
para a Central de Controle e Cadastro
        ↓
Central executa as alterações no SAP
(Winshuttle — MM02, CS02, MM06, etc.)
        ↓
Central cria o Promotion Request no Windchill
e seleciona os aprovadores conforme produto
        ↓
Aprovadores recebem e aprovam
        ↓  (se rework)
Solicitante ajusta o BITin → Check-in → Complete Task
        ↓  (aprovado)
Departamentos executam suas responsabilidades
(Controladoria, PCP, Expedição, etc.)
```

### Responsabilidades pós-aprovação

| O que o BITin pede                           | Quem executa                           |
| -------------------------------------------- | -------------------------------------- |
| Incluir / Excluir / Atualizar lista de preço | Controladoria → TI atualiza SisVen     |
| Precificação (peça / produto / repasse)      | Controladoria                          |
| Atualizar custo                              | Controladoria                          |
| Afeta ordem de cliente — Proteína            | Adm. Comercial → PCP → Expedição       |
| Afeta ordem de cliente — Armazenagem         | DPO → PCP → Expedição                  |
| Afeta ordem de fabricação                    | Engenharia → PCP → Expedição           |
| Transferir estoque                           | Setor que possui o material em estoque |
| Especificações técnicas                      | Compras contata fornecedor             |
| Atualizar BITex                              | DPO atualiza SisVen                    |

---

## 3. Relação entre os sistemas

| Sistema | Função | Alimentado por |
| ------- | ------- | -------------- |
| **CCM** (planilha) | Solicitação e controle de cadastro de novos materiais | Solicitante / Compras / Fiscal |
| **SAP** | ERP — onde os materiais e alterações são cadastrados de fato | Winshuttle (automação) ou manual |
| **Winshuttle** | Automação de lançamentos no SAP via templates Excel | Central de Cadastro |
| **Windchill** | PLM — aprovação formal de BITins e controle de documentos | Central de Cadastro / Solicitante |
| **BITin** (arquivo Excel) | Documento formal de alteração / liberação | Solicitante |
| **STATUS CCM02** | Planilha de controle e acompanhamento das CCMs | Central de Cadastro |

---

## 4. Situações que obrigam emissão de BITin

- Liberação de material, desenho, produto ou processo
- Nacionalização de material
- Alteração em lista técnica
- Alteração de roteiro de fabricação
- Alteração de versão de desenho, instrução de montagem, manuais ou adesivos
- Criação ou alteração de dados básicos e especificações técnicas
- Alteração de NCM
- Eliminação de códigos inutilizados
- Reativação de códigos eliminados
- Liberação de produto para venda (incluir em lista de preço)
- Precificação de materiais

---

## 5. Documentos de referência

| Documento           | Revisão        | Descrição                           |
| ------------------- | -------------- | ----------------------------------- |
| `POP_ENG_7.3.7_001` | Q — 13/10/2025 | Procedimento de Criação de Material |
| `POP_ENG_7.3.7_002` | J — 14/10/2025 | Procedimento BITin                  |

Disponíveis em: [[Documentação]]

