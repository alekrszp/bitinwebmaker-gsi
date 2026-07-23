# Release v0.14.0 — Aba Preenchimento + agente vira aplicativo de verdade + logo v2

Release criado a partir da tag `v0.14.0`.

## Resumo

Rodada em cima da v0.13.0 (agente SAP local): trouxe de volta o preenchimento em massa como uma
aba própria pro modo manual, transformou o agente num aplicativo Windows de verdade (achável
pela busca, só 1 instância, desinstala como qualquer programa), redesenhou a logo do zero, e
corrigiu 2 bugs reais só encontrados testando o `.exe` compilado de verdade nesta máquina — não
apareciam em nenhum teste automatizado.

## O que fecha nesta versão

### Aba "Preenchimento" (bulk-fill sem agente)

Simétrica à aba "Automação" (só existe SEM o agente conectado): reúne o preenchimento em massa
que tinha ficado pra trás quando ZBPP009/Lista Técnica viraram uma única aba BITin. 2 sub-abas
dentro de uma página só (troca local, sem navegar de rota) — "Códigos de alteração" (grade
De/Para + colar do SAP) e "Lista Técnica" — cada uma dona do próprio carregamento/salvamento,
sempre buscando o `materiais[]` mais recente do servidor ao trocar de sub-aba (evita duas
cópias locais divergentes escrevendo no mesmo array).

### Validação "de"/"para" incompleto

Nada barrava salvar/enviar um campo de `dados_basicos` com só um dos dois lados preenchido.
Agora: aviso em tempo real nas duas telas que editam isso (aba BITin e Preenchimento) + bloqueio
real no backend no envio.

### Agente SAP vira um aplicativo de verdade

- **Atalho no Menu Iniciar** — o agente agora aparece na busca do Windows/barra de tarefas.
- **Entrada em Programas e Recursos** — desinstala como qualquer aplicativo real.
- **Só 1 instância por vez** — mutex nomeado do Windows; abrir de novo com o agente já rodando
  só traz a janela existente pra frente, não cria um processo/janela duplicados.

### Redesign da logo (v2)

Crachá com gradiente, visor de vidro fosco no rosto, olhos em cápsula que piscam achatando
(solo ou os dois juntos, em ordem e timing sorteados por instância, pra não sincronizar entre
os vários lugares onde a logo aparece na tela). 3 leituras de status no mesmo desenho —
conectado (verde), desligado (vermelho), neutro (laranja). Favicon da aba do navegador e um
toast curto agora também refletem o status de conexão.

### "Fazer manualmente" definitivo

Persistido por BITin (`localStorage`) — escolher manual não pergunta de novo pra aquele BITin,
nem dispara mais o toast de conexão nele.

## Bugs reais corrigidos

- **CORS do agente só liberava as portas de dev do Vite** — qualquer deploy real (fora de
  `localhost`) ficaria bloqueado, mesmo bug que o backend principal já tinha corrigido antes
  (`docs/DEPLOY.md`). Agora aceita `BITIN_AGENTE_CORS_ORIGENS`.
- **`SetForegroundWindow` derrubava o agente com "Unhandled exception in script"** ao tentar
  trazer a janela de uma instância já aberta pra frente — só acontecia no `.exe` empacotado de
  verdade (nunca rodando o código-fonte direto). Achado compilando e instalando o agente de
  verdade nesta máquina pra verificar a feature; corrigido com a técnica padrão do Win32
  (`AttachThreadInput`), reproduzido e confirmado corrigido com o `.exe` real de novo depois.
- "Acessar bitin" (agente confirmado conectado no gate) reaproveitava sem querer o mesmo
  callback de "Fazer manualmente" — marcava o BITin como manual pra sempre por engano mesmo com
  o agente funcionando.
- `InstalarAgenteCard.tsx` tinha "Já instalado?"/"Verificar conexão" duplicados com o gate (a
  tela anterior) — removidos de lá.
- 3 funções órfãs em `frontend/src/lib/sapAgent.ts` (nunca chamadas por nenhuma tela) removidas.

## Validação

- Suíte Python completa (`tests/` + `sap-agent/tests/`, 426 testes) verde.
- `npx tsc --noEmit`, `npx oxlint`, `npx vitest run`, build de produção — sem erros/avisos.
- **Testado de verdade nesta máquina**: compilado `AgenteSAP.exe`/`Instalador.exe` reais via
  PyInstaller, instalado de verdade (`%LOCALAPPDATA%\AgenteSAP`), confirmado atalho real no
  Menu Iniciar, entrada real em Programas e Recursos, protocolo `bitinsap://` registrado, só 1
  instância (2ª tentativa mostra a janela existente e sai limpo, exit code 0), e desinstalação
  real limpando tudo (atalho + registro + protocolo) antes/depois confirmados via registro do
  Windows.
