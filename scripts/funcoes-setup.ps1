# Funções usadas pelo setup.ps1 e pelo iniciar.ps1, na raiz do repositório.
# Salvo em UTF-8 com BOM, para o Windows PowerShell 5.1 mostrar os acentos.

$Utf8SemBom = New-Object System.Text.UTF8Encoding $false

# Os scripts Python do projeto imprimem emojis. Sem UTF-8, o Python do Windows
# quebra ao escrever esses caracteres quando a saída é capturada
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }

function Escrever-Titulo([string]$texto) {
    Write-Host ''
    Write-Host "== $texto" -ForegroundColor Cyan
}

function Escrever-Ok([string]$texto) {
    Write-Host "   OK  $texto" -ForegroundColor Green
}

function Escrever-Aviso([string]$texto) {
    Write-Host "   !   $texto" -ForegroundColor Yellow
}

function Falhar([string]$texto) {
    Write-Host ''
    Write-Host "ERRO: $texto" -ForegroundColor Red
    exit 1
}

# Roda um programa e para o script se ele falhar
function Executar([string]$descricao, [string]$programa, [string[]]$argumentos) {
    & $programa @argumentos
    if ($LASTEXITCODE -ne 0) {
        Falhar "$descricao falhou (código de saída $LASTEXITCODE). Veja a mensagem acima."
    }
}

# Roda um programa sem mostrar a saída. Se ele falhar, mostra a saída e para o script
function Executar-Quieto([string]$descricao, [string]$programa, [string[]]$argumentos) {
    $anterior = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $saida = & $programa @argumentos 2>&1
    }
    finally {
        $ErrorActionPreference = $anterior
    }
    if ($LASTEXITCODE -ne 0) {
        $saida | ForEach-Object { Write-Host "   $_" }
        Falhar "$descricao falhou (código de saída $LASTEXITCODE). Veja a mensagem acima."
    }
}

# Roda um programa só para saber se dá certo, sem mostrar a saída
function Testar([string]$programa, [string[]]$argumentos) {
    $anterior = $ErrorActionPreference
    $ErrorActionPreference = 'SilentlyContinue'
    try {
        & $programa @argumentos *> $null
        return ($LASTEXITCODE -eq 0)
    }
    catch {
        return $false
    }
    finally {
        $ErrorActionPreference = $anterior
    }
}

# Roda um programa e devolve a saída como texto, ou $null se ele falhar
function Ler-Saida([string]$programa, [string[]]$argumentos) {
    $anterior = $ErrorActionPreference
    $ErrorActionPreference = 'SilentlyContinue'
    try {
        $saida = & $programa @argumentos 2>$null
        if ($LASTEXITCODE -ne 0) { return $null }
        return (($saida | Out-String).Trim())
    }
    catch {
        return $null
    }
    finally {
        $ErrorActionPreference = $anterior
    }
}

function Escrever-Arquivo([string]$caminho, [string]$texto) {
    # Sem BOM: o python-dotenv leria o BOM como parte do primeiro nome
    [System.IO.File]::WriteAllText($caminho, $texto, $Utf8SemBom)
}

function Ler-Arquivo([string]$caminho) {
    return [System.IO.File]::ReadAllText($caminho, [System.Text.Encoding]::UTF8)
}

# Valor de uma variável de um arquivo .env, ou '' se não houver. Se ela aparecer
# mais de uma vez, vale a última, como no python-dotenv do backend
function Ler-Variavel([string]$arquivo, [string]$nome) {
    if (-not (Test-Path -LiteralPath $arquivo)) { return '' }
    $valor = ''
    foreach ($linha in (Ler-Arquivo $arquivo) -split "`r?`n") {
        if ($linha -match "^\s*$nome\s*=\s*(.*)$") {
            $valor = $Matches[1].Trim().Trim('"').Trim("'")
        }
    }
    return $valor
}

# Senha e porta do DATABASE_URL de um arquivo .env, ou $null se o arquivo
# não existir ou ainda tiver os valores do exemplo
function Ler-Conexao([string]$arquivo) {
    $url = Ler-Variavel $arquivo 'DATABASE_URL'
    if ($url -notmatch '^postgresql(\+psycopg)?://[^:]+:([^@]*)@[^:/]+:(\d+)/') { return $null }
    $senha = [System.Uri]::UnescapeDataString($Matches[2])
    if ($senha -eq 'SUA_SENHA' -or $senha -eq '') { return $null }
    return @{ Senha = $senha; Porta = [int]$Matches[3] }
}

# Pede uma senha sem mostrar o que é digitado
function Ler-Senha([string]$pergunta) {
    $segura = Read-Host $pergunta -AsSecureString
    return [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($segura))
}

function Docker-Ligado {
    return (Testar 'docker' @('info'))
}

# Liga o Docker Desktop, se precisar, e espera o motor do Docker responder
function Garantir-Docker {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Falhar 'O Docker não está instalado. Instale o Docker Desktop (https://www.docker.com/products/docker-desktop/), abra uma vez e rode de novo.'
    }
    if (Docker-Ligado) { return }

    $desktop = Join-Path $env:ProgramFiles 'Docker\Docker\Docker Desktop.exe'
    if (Test-Path -LiteralPath $desktop) {
        Write-Host '   ... abrindo o Docker Desktop' -ForegroundColor DarkGray
        Start-Process -FilePath $desktop | Out-Null
    }
    Write-Host '   ... esperando o Docker iniciar (até 3 minutos)' -ForegroundColor DarkGray
    for ($i = 0; $i -lt 90; $i++) {
        if (Docker-Ligado) { return }
        Start-Sleep -Seconds 2
    }
    Falhar 'O Docker não respondeu. Abra o Docker Desktop, espere aparecer "Engine running" e rode de novo.'
}

function Container-Existe([string]$container) {
    $nomes = Ler-Saida 'docker' @('ps', '-a', '--filter', "name=^$container$", '--format', '{{.Names}}')
    return ($nomes -eq $container)
}

function Container-Ligado([string]$container) {
    return ((Ler-Saida 'docker' @('inspect', '-f', '{{.State.Running}}', $container)) -eq 'true')
}

# Espera o PostgreSQL do container aceitar conexões pela rede
function Esperar-Banco([string]$container) {
    for ($i = 0; $i -lt 60; $i++) {
        if (Testar 'docker' @('exec', $container, 'pg_isready', '-h', '127.0.0.1', '-U', 'postgres', '-d', 'v_energy')) { return }
        Start-Sleep -Seconds 2
    }
    Falhar "O banco do container $container não ficou pronto. Veja o motivo com: docker logs $container"
}

function Ligar-Banco([string]$container) {
    if (-not (Container-Ligado $container)) {
        Executar-Quieto 'Ligar o container do banco' 'docker' @('start', $container)
    }
    Esperar-Banco $container
}

# Porta do computador ligada à 5432 do container (ex.: 5433)
function Porta-Do-Container([string]$container) {
    $saida = Ler-Saida 'docker' @('port', $container, '5432/tcp')
    if ($saida -match ':(\d+)') { return [int]$Matches[1] }
    return $null
}

# Resposta de uma consulta SQL no banco do container, ou $null se der erro
function Consultar([string]$container, [string]$sql) {
    return (Ler-Saida 'docker' @('exec', $container, 'psql', '-U', 'postgres', '-d', 'v_energy', '-Atc', $sql))
}

function Url-Responde([string]$url) {
    try {
        $resposta = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 3
        return ($resposta.StatusCode -lt 500)
    }
    catch {
        return $false
    }
}

function Esperar-Url([string]$url, [int]$segundos) {
    $fim = (Get-Date).AddSeconds($segundos)
    while ((Get-Date) -lt $fim) {
        if (Url-Responde $url) { return $true }
        Start-Sleep -Seconds 2
    }
    return $false
}

# Abre uma janela nova do PowerShell rodando um comando numa pasta. O comando vai
# codificado, então caminhos com espaço, acento ou aspas não quebram nada
function Abrir-Janela([string]$titulo, [string]$pasta, [string]$comando) {
    $pastaSegura = $pasta.Replace("'", "''")
    $script = "`$Host.UI.RawUI.WindowTitle = '$titulo'; Set-Location -LiteralPath '$pastaSegura'; $comando"
    $codificado = [Convert]::ToBase64String([System.Text.Encoding]::Unicode.GetBytes($script))
    Start-Process -FilePath 'powershell.exe' -WorkingDirectory $pasta -ArgumentList @('-NoExit', '-ExecutionPolicy', 'Bypass', '-EncodedCommand', $codificado) | Out-Null
}
