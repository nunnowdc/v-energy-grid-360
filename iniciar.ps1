<#
Liga o V-Energy Grid 360 para o dia a dia, depois do setup.ps1: liga o banco no
Docker e abre uma janela para o backend, outra para o frontend e, se o agente
usar o 9router, outra para ele. No fim, abre o portal no navegador.

Para desligar, feche as janelas (ou aperte Ctrl + C em cada uma).

Uso, a partir da raiz do repositório:
    powershell -ExecutionPolicy Bypass -File .\iniciar.ps1

Salvo em UTF-8 com BOM, para o Windows PowerShell 5.1 mostrar os acentos.
#>
param(
    # Container do banco no Docker
    [string]$Container = 'postgres-venergy',
    # Não abre o navegador no fim
    [switch]$SemNavegador
)

$ErrorActionPreference = 'Stop'
$Raiz = $PSScriptRoot
Set-Location -LiteralPath $Raiz
. (Join-Path $Raiz 'scripts\funcoes-setup.ps1')

$EnvBackend = Join-Path $Raiz 'backend\.env.local'
$Py = Join-Path $Raiz 'backend\.venv\Scripts\python.exe'
$Portal = 'http://localhost:5173'

Write-Host 'V-Energy Grid 360 · iniciar' -ForegroundColor Cyan

$faltando = @()
if (-not (Test-Path -LiteralPath $Py)) { $faltando += 'backend\.venv' }
if (-not (Test-Path -LiteralPath $EnvBackend)) { $faltando += 'backend\.env.local' }
if (-not (Test-Path -LiteralPath (Join-Path $Raiz 'frontend\.env.local'))) { $faltando += 'frontend\.env.local' }
if (-not (Test-Path -LiteralPath (Join-Path $Raiz 'frontend\node_modules'))) { $faltando += 'frontend\node_modules' }
if ($faltando.Count -gt 0) {
    Falhar ("Falta preparar o projeto (" + ($faltando -join ', ') + "). Rode antes: powershell -ExecutionPolicy Bypass -File .\setup.ps1")
}

# ---------------------------------------------------------------------------
Escrever-Titulo 'Banco de dados'

Garantir-Docker
if (-not (Container-Existe $Container)) {
    Falhar "O container $Container não existe. Rode antes: powershell -ExecutionPolicy Bypass -File .\setup.ps1"
}
Ligar-Banco $Container
Escrever-Ok "Banco ligado em localhost:$(Porta-Do-Container $Container)"

# ---------------------------------------------------------------------------
Escrever-Titulo '9router'

$chave9router = Ler-Variavel $EnvBackend 'NINEROUTER_API_KEY'
$url9router = Ler-Variavel $EnvBackend 'NINEROUTER_BASE_URL'
if (-not $chave9router) {
    Escrever-Ok 'Não usado (sem NINEROUTER_API_KEY no backend\.env.local)'
}
elseif ($url9router -notmatch '^https?://(localhost|127\.0\.0\.1):(\d+)') {
    Escrever-Ok 'Não é local (NINEROUTER_BASE_URL aponta para outro endereço)'
}
else {
    $modelos9router = "http://127.0.0.1:$($Matches[2])/v1/models"
    if (Url-Responde $modelos9router) {
        Escrever-Ok 'Já estava ligado'
    }
    elseif (-not (Get-Command 9router.cmd -ErrorAction SilentlyContinue)) {
        Escrever-Aviso 'O 9router não está instalado. Instale com "npm install -g 9router"; até lá, o agente de IA não responde.'
    }
    else {
        Abrir-Janela 'V-Energy - 9router' $Raiz '9router.cmd --no-browser'
        if (Esperar-Url $modelos9router 60) { Escrever-Ok 'Ligado em outra janela' }
        else { Escrever-Aviso 'O 9router não respondeu em 1 minuto. Veja a janela dele.' }
    }
}

# ---------------------------------------------------------------------------
Escrever-Titulo 'Backend'

$portaBackend = Ler-Variavel $EnvBackend 'APP_PORT'
if (-not $portaBackend) { $portaBackend = '8000' }
$saudeBackend = "http://127.0.0.1:$portaBackend/api/health"
if (Url-Responde $saudeBackend) {
    Escrever-Ok "Já estava ligado em http://127.0.0.1:$portaBackend"
}
else {
    Abrir-Janela 'V-Energy - backend' (Join-Path $Raiz 'backend') ("& '" + $Py.Replace("'", "''") + "' -m app.main")
    Write-Host '   ... esperando a API responder (até 3 minutos na primeira vez)' -ForegroundColor DarkGray
    if (-not (Esperar-Url $saudeBackend 180)) {
        Falhar 'O backend não respondeu. Veja o erro na janela "V-Energy - backend".'
    }
    Escrever-Ok "Ligado em outra janela: http://127.0.0.1:$portaBackend/api/docs"
}

# ---------------------------------------------------------------------------
Escrever-Titulo 'Frontend'

if (Url-Responde $Portal) {
    Escrever-Ok "Já estava ligado em $Portal"
}
else {
    Abrir-Janela 'V-Energy - frontend' (Join-Path $Raiz 'frontend') 'npm.cmd run dev'
    if (-not (Esperar-Url $Portal 90)) {
        Falhar 'O frontend não respondeu. Veja o erro na janela "V-Energy - frontend".'
    }
    Escrever-Ok "Ligado em outra janela: $Portal"
}

# ---------------------------------------------------------------------------
Write-Host ''
Write-Host "Portal no ar: $Portal" -ForegroundColor Green
Write-Host 'Para desligar, feche as janelas do backend e do frontend (ou aperte Ctrl + C nelas).'
if (-not $SemNavegador) {
    Start-Process $Portal | Out-Null
}
