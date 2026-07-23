# Registra o protocolo customizado bitinsap:// pra abrir o agente local com 1 clique a partir
# do navegador (botão "Abrir agente SAP" na tela ZBPP009). Roda 1 vez por engenheiro/máquina.
#
# HKEY_CURRENT_USER (não HKEY_LOCAL_MACHINE) -- escopo só do usuário atual, NÃO precisa de
# privilégio de administrador. Ponto crítico confirmado com o usuário: a máquina corporativa
# não tem senha de admin disponível.
#
# Uso:
#   powershell -ExecutionPolicy Bypass -File registrar_protocolo.ps1 -CaminhoExe "C:\caminho\para\AgenteSap.exe"
# (o .exe é gerado via PyInstaller a partir de servidor.py -- ver README.md desta pasta)

param(
    [Parameter(Mandatory = $true)]
    [string]$CaminhoExe
)

if (-not (Test-Path $CaminhoExe)) {
    Write-Error "Executável não encontrado em: $CaminhoExe"
    exit 1
}

$chaveRaiz = "HKCU:\Software\Classes\bitinsap"
$chaveComando = "$chaveRaiz\shell\open\command"

New-Item -Path $chaveRaiz -Force | Out-Null
Set-ItemProperty -Path $chaveRaiz -Name "(default)" -Value "URL:Agente BITin SAP"
Set-ItemProperty -Path $chaveRaiz -Name "URL Protocol" -Value ""

New-Item -Path $chaveComando -Force | Out-Null
# %1 é o parâmetro que o Windows passaria depois de "bitinsap://" (não usado pelo agente hoje,
# mas o placeholder é o padrão de registro de protocolo do Windows).
Set-ItemProperty -Path $chaveComando -Name "(default)" -Value "`"$CaminhoExe`" `"%1`""

Write-Output "Protocolo bitinsap:// registrado para o usuário atual, apontando para: $CaminhoExe"
Write-Output "Teste abrindo bitinsap://abrir em uma aba do navegador."
