<#
Prepara o V-Energy Grid 360 para rodar neste computador (Windows), fazendo os
passos 1 a 9 do "Como executar" do README: banco no Docker, arquivos de
configuração, ambiente Python, carga da Gold, tabelas da IA, tabelas das ordens
de inspeção e dos usuários, conta de administrador e dependências do frontend.

Pode rodar de novo quantas vezes quiser: o que já está pronto é pulado. Rode de
novo depois de um git pull, para instalar dependências novas.

Uso, a partir da raiz do repositório:
    powershell -ExecutionPolicy Bypass -File .\setup.ps1
    powershell -ExecutionPolicy Bypass -File .\setup.ps1 -RecarregarGold

Salvo em UTF-8 com BOM, para o Windows PowerShell 5.1 mostrar os acentos.
#>
param(
    # Recarrega as tabelas da Gold. Com um .zip em data/, extrai o .zip de novo
    [switch]$RecarregarGold,
    # Container, porta e volume do banco no Docker
    [string]$Container = 'postgres-venergy',
    [int]$Porta = 5433,
    [string]$Volume = 'pgdata-v_energy',
    # Senha do banco, para não perguntar (opcional)
    [string]$Senha = '',
    # Senha da conta de administrador do portal, para não perguntar (opcional)
    [string]$SenhaAdmin = ''
)

$ErrorActionPreference = 'Stop'
$Raiz = $PSScriptRoot
Set-Location -LiteralPath $Raiz
. (Join-Path $Raiz 'scripts\funcoes-setup.ps1')

# As mesmas 15 tabelas que o scripts/carga_banco_local.py carrega
$TabelasGold = @(
    'dim_unidade_consumidora', 'dim_alimentador', 'dim_medidor', 'dim_geracao_distribuida',
    'dim_competencia', 'fact_faturamento', 'fact_leituras', 'fact_ocorrencias',
    'fact_atendimentos', 'fact_inspecoes', 'fila_inspecao', 'agg_receita_mensal',
    'agg_receita_preco_volume', 'agg_continuidade_alimentador', 'agg_continuidade_alimentador_anual'
)

$EnvRaiz = Join-Path $Raiz '.env'
$EnvBackend = Join-Path $Raiz 'backend\.env.local'
$PastaVenv = Join-Path $Raiz 'backend\.venv'
$Py = Join-Path $PastaVenv 'Scripts\python.exe'
$PastaDados = Join-Path $Raiz 'data'
# A primeira conta do portal, a mesma do backend\scripts\bootstrap_admin_ti.py
$EmailAdmin = 'adminti.vgrid360@visagio.com'

Write-Host 'V-Energy Grid 360 · setup' -ForegroundColor Cyan

if ($env:OS -ne 'Windows_NT') {
    Falhar 'O setup.ps1 é para Windows. No macOS e no Linux, use: bash setup.sh'
}

# Dentro do backend\.venv, alguns arquivos ficam uns 130 caracteres abaixo da raiz,
# e o Windows não carrega DLLs com caminho maior que 260
if ($Raiz.Length -gt 120) {
    Falhar "O caminho da pasta do repositório é longo demais ($($Raiz.Length) caracteres, o máximo é 120): $Raiz. Mova a pasta para um lugar mais curto, como C:\Users\SEU_USUARIO\Documents\v-energy-grid-360, e rode de novo."
}

# ---------------------------------------------------------------------------
Escrever-Titulo '1/9 Programas necessários'

$PythonBase = $null
foreach ($candidato in @(@('python'), @('py', '-3'))) {
    if (-not (Get-Command $candidato[0] -ErrorAction SilentlyContinue)) { continue }
    $extra = @($candidato | Select-Object -Skip 1)
    $versao = Ler-Saida $candidato[0] ($extra + @('-c', 'import sys; print(sys.version_info[0] * 100 + sys.version_info[1])'))
    if ($versao -match '^\d+$' -and [int]$versao -ge 311) {
        $PythonBase = @{ Programa = $candidato[0]; Extra = $extra; Versao = '{0}.{1}' -f [math]::Floor([int]$versao / 100), ([int]$versao % 100) }
        break
    }
}
if (-not $PythonBase) {
    Falhar 'Python 3.11 ou superior não encontrado. Instale em https://www.python.org/downloads/ marcando "Add python.exe to PATH", feche e abra o VS Code e rode de novo.'
}
# Algumas dependências (psycopg2-binary, torch) só existem para o Python x64. Num
# notebook com processador ARM (Snapdragon), o Python x64 roda por emulação
$plataforma = Ler-Saida $PythonBase.Programa ($PythonBase.Extra + @('-c', 'import sysconfig; print(sysconfig.get_platform())'))
if ($plataforma -ne 'win-amd64') {
    Falhar "O Python $($PythonBase.Versao) instalado é o de $plataforma, e o projeto precisa do Python x64. Em https://www.python.org/downloads/windows/, baixe o `"Windows installer (64-bit)`" (mesmo em notebook com processador ARM, como os Snapdragon), instale marcando `"Add python.exe to PATH`" e rode de novo."
}
Escrever-Ok "Python $($PythonBase.Versao)"

$versaoNode = Ler-Saida 'node' @('--version')
if (-not $versaoNode) {
    Falhar 'Node.js não encontrado. Instale a versão LTS em https://nodejs.org/, feche e abra o VS Code e rode de novo.'
}
if ([version]($versaoNode.TrimStart('v')) -lt [version]'20.0') {
    Falhar "O Node.js instalado é o $versaoNode, e o projeto precisa do 20 ou superior. Instale a versão LTS em https://nodejs.org/."
}
if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
    Falhar 'O npm não foi encontrado. Reinstale o Node.js (https://nodejs.org/) com as opções padrão.'
}
Escrever-Ok "Node.js $versaoNode"

Garantir-Docker
Escrever-Ok 'Docker ligado'

# ---------------------------------------------------------------------------
Escrever-Titulo '2/9 Senha do banco'

$ContainerNovo = -not (Container-Existe $Container)
$conexao = Ler-Conexao $EnvRaiz
if (-not $conexao) { $conexao = Ler-Conexao $EnvBackend }

if ($conexao) {
    $SenhaBanco = $conexao.Senha
    Escrever-Ok 'Senha lida dos arquivos de configuração'
}
elseif ($Senha) {
    $SenhaBanco = $Senha
}
else {
    if ($ContainerNovo) {
        Write-Host '   Escolha uma senha para o banco. O mais simples é usar só letras e números.'
    }
    else {
        Write-Host "   O container $Container já existe. Digite a senha usada quando ele foi criado."
    }
    $segura = Read-Host '   Senha' -AsSecureString
    $SenhaBanco = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($segura))
}
# Aspas, barra invertida e espaços quebram a senha no comando do Docker
if ($ContainerNovo -and $SenhaBanco -notmatch '^[^\s"\\]{4,}$') {
    Falhar 'Use uma senha com pelo menos 4 caracteres, sem espaços, aspas ou barra invertida.'
}

# ---------------------------------------------------------------------------
Escrever-Titulo '3/9 Banco de dados (PostgreSQL com pgvector no Docker)'

if ($ContainerNovo) {
    if (Testar 'docker' @('volume', 'inspect', $Volume)) {
        Escrever-Aviso "O volume $Volume já existe, então o banco guarda a senha de quando ele foi criado."
    }
    Write-Host '   ... criando o container (na primeira vez, o Docker baixa a imagem)' -ForegroundColor DarkGray
    Executar-Quieto "Criar o container (se a mensagem for 'port is already allocated', rode com -Porta 5434)" 'docker' @(
        'run', '-d', '--name', $Container, '-e', "POSTGRES_PASSWORD=$SenhaBanco", '-e', 'POSTGRES_DB=v_energy',
        '-p', "$($Porta):5432", '-v', "$($Volume):/var/lib/postgresql", 'pgvector/pgvector:pg18'
    )
    Escrever-Ok "Container $Container criado"
}
Ligar-Banco $Container
$PortaBanco = Porta-Do-Container $Container
if (-not $PortaBanco) { Falhar "Não foi possível descobrir a porta do container $Container." }
Escrever-Ok "Banco ligado em localhost:$PortaBanco"

Executar-Quieto 'Ativar as extensões vector e unaccent' 'docker' @(
    'exec', $Container, 'psql', '-q', '-U', 'postgres', '-d', 'v_energy',
    '-c', 'CREATE EXTENSION IF NOT EXISTS vector;', '-c', 'CREATE EXTENSION IF NOT EXISTS unaccent;'
)
Escrever-Ok 'Extensões vector e unaccent'

# ---------------------------------------------------------------------------
Escrever-Titulo '4/9 Ambiente Python (backend\.venv)'

if ((Test-Path -LiteralPath $Py) -and -not (Testar $Py @('-c', 'import sys'))) {
    Escrever-Aviso 'O ambiente Python existente não funciona (a pasta mudou de lugar ou o Python foi trocado). Criando de novo.'
    Remove-Item -LiteralPath $PastaVenv -Recurse -Force
}
$VenvNovo = -not (Test-Path -LiteralPath $Py)
if ($VenvNovo) {
    Executar 'Criar o ambiente Python' $PythonBase.Programa ($PythonBase.Extra + @('-m', 'venv', $PastaVenv))
    Escrever-Ok 'Ambiente criado'
    Write-Host '   ... instalando as dependências (de 5 a 15 minutos na primeira vez)' -ForegroundColor DarkGray
    Executar 'Atualizar o pip' $Py @('-m', 'pip', 'install', '--disable-pip-version-check', '-q', '--upgrade', 'pip')
    Executar 'Instalar as dependências do backend e do agente' $Py @(
        '-m', 'pip', 'install', '--disable-pip-version-check', '-r', 'backend\requirements.txt', '-r', 'ai-agent\requirements.txt'
    )
}
else {
    Write-Host '   ... conferindo as dependências' -ForegroundColor DarkGray
    Executar 'Instalar as dependências do backend e do agente' $Py @(
        '-m', 'pip', 'install', '--disable-pip-version-check', '-q', '-r', 'backend\requirements.txt', '-r', 'ai-agent\requirements.txt'
    )
}
Escrever-Ok 'Dependências do backend e do agente de IA'

# ---------------------------------------------------------------------------
Escrever-Titulo '5/9 Arquivos de configuração'

$SenhaUrl = [System.Uri]::EscapeDataString($SenhaBanco)
$UrlScripts = "postgresql://postgres:$($SenhaUrl)@localhost:$PortaBanco/v_energy"
$UrlBackend = "postgresql+psycopg://postgres:$($SenhaUrl)@localhost:$PortaBanco/v_energy"

# Confere a senha antes de gravar qualquer arquivo
$teste = 'import sys, psycopg2; psycopg2.connect(sys.argv[1]).close()'
if (-not (Testar $Py @('-c', $teste, $UrlScripts))) {
    & $Py -c $teste $UrlScripts
    Falhar "Não foi possível entrar no banco com essa senha. Confira a senha do container $Container e rode de novo."
}
Escrever-Ok 'Senha do banco conferida'

if (-not (Test-Path -LiteralPath $EnvRaiz)) {
    Escrever-Arquivo $EnvRaiz "DATABASE_URL=$UrlScripts`r`n"
    Escrever-Ok '.env criado'
}
else {
    Escrever-Ok '.env já existe (mantido)'
}

$linhaBanco = "DATABASE_URL=$UrlBackend"
if (-not (Test-Path -LiteralPath $EnvBackend)) {
    $texto = Ler-Arquivo (Join-Path $Raiz 'backend\.env.example')
    Escrever-Arquivo $EnvBackend ($texto -replace '(?m)^DATABASE_URL=.*$', $linhaBanco.Replace('$', '$$'))
    Escrever-Ok 'backend\.env.local criado'
}
elseif (-not (Ler-Conexao $EnvBackend)) {
    $texto = Ler-Arquivo $EnvBackend
    Escrever-Arquivo $EnvBackend ($texto -replace '(?m)^DATABASE_URL=.*$', $linhaBanco.Replace('$', '$$'))
    Escrever-Ok 'backend\.env.local: DATABASE_URL preenchido'
}
else {
    Escrever-Ok 'backend\.env.local já existe (mantido)'
}

# Segredo que assina o cookie de login. É gerado uma vez só: com um segredo
# novo, quem estiver logado precisa entrar de novo
if (-not (Ler-Variavel $EnvBackend 'JWT_SECRET_KEY')) {
    $segredo = Ler-Saida $Py @('-c', 'import secrets; print(secrets.token_urlsafe(48))')
    if (-not $segredo) { Falhar 'Não foi possível gerar o JWT_SECRET_KEY.' }
    $linhaSegredo = "JWT_SECRET_KEY=$segredo"
    $texto = Ler-Arquivo $EnvBackend
    if ($texto -match '(?m)^JWT_SECRET_KEY=') {
        $texto = $texto -replace '(?m)^JWT_SECRET_KEY=[^\r\n]*', $linhaSegredo
    }
    else {
        if ($texto -and -not $texto.EndsWith("`n")) { $texto += "`r`n" }
        $texto += "$linhaSegredo`r`n"
    }
    Escrever-Arquivo $EnvBackend $texto
    Escrever-Ok 'backend\.env.local: JWT_SECRET_KEY gerado'
}
else {
    Escrever-Ok 'JWT_SECRET_KEY já definido (mantido)'
}

# ---------------------------------------------------------------------------
Escrever-Titulo '6/9 Carga da Gold'

function Csvs-Da-Gold {
    return @(Get-ChildItem -LiteralPath $PastaDados -Recurse -File -Filter '*.csv' -ErrorAction SilentlyContinue |
        Where-Object { $TabelasGold -contains $_.BaseName })
}

$zips = @(Get-ChildItem -LiteralPath $PastaDados -File -Filter '*.zip' -ErrorAction SilentlyContinue) +
    @(Get-ChildItem -LiteralPath $Raiz -File -Filter '*.zip' -ErrorAction SilentlyContinue)
$csvs = Csvs-Da-Gold

# Com -RecarregarGold e um .zip em data/, a Gold extraída é trocada pela do .zip
if ($RecarregarGold -and $zips.Count -eq 1 -and $csvs.Count -gt 0) {
    $csvs | Remove-Item -Force
    Escrever-Ok 'CSVs da Gold antiga apagados'
    $csvs = @()
}

if ($csvs.Count -eq 0) {
    if ($zips.Count -eq 0) {
        Falhar "Os dados da Gold não estão em data\. Copie o zip da Gold (peça ao time) para $PastaDados e rode de novo."
    }
    if ($zips.Count -gt 1) {
        Falhar ("Há mais de um .zip: " + (($zips | ForEach-Object { $_.FullName }) -join ', ') + '. Deixe só o da Gold mais recente e rode de novo.')
    }
    Write-Host "   ... extraindo $($zips[0].Name)" -ForegroundColor DarkGray
    Executar-Quieto 'Extrair o zip da Gold' $Py @('-c', 'import sys, zipfile; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])', $zips[0].FullName, $PastaDados)
    $csvs = Csvs-Da-Gold
    if ($csvs.Count -eq 0) { Falhar "O zip $($zips[0].Name) não tem os CSVs da Gold." }
    Escrever-Ok "Zip extraído em data\"
}

$repetidos = @($csvs | Group-Object BaseName | Where-Object { $_.Count -gt 1 })
if ($repetidos.Count -gt 0) {
    $lista = ($repetidos | ForEach-Object { $_.Group } | ForEach-Object { $_.FullName }) -join ', '
    Falhar "Há mais de uma cópia da Gold em data\: $lista. Apague a cópia antiga e rode de novo."
}
$faltando = @($TabelasGold | Where-Object { ($csvs | ForEach-Object { $_.BaseName }) -notcontains $_ })
if ($faltando.Count -gt 0) {
    Escrever-Aviso ("Faltam CSVs da Gold: " + ($faltando -join ', '))
}

$linhasCarregadas = Consultar $Container 'SELECT count(*) FROM fact_faturamento'
if ($RecarregarGold -or -not $linhasCarregadas -or $linhasCarregadas -eq '0') {
    Write-Host '   ... carregando a Gold no banco (de 1 a 3 minutos)' -ForegroundColor DarkGray
    Executar 'Carga da Gold' $Py @('scripts\carga_banco_local.py')
    Escrever-Ok 'Gold carregada'
}
else {
    Escrever-Ok "Gold já carregada ($linhasCarregadas faturas). Para carregar de novo, use -RecarregarGold"
}

# ---------------------------------------------------------------------------
Escrever-Titulo '7/9 Tabelas e base de conhecimento da IA'

Executar-Quieto 'Criar as tabelas da IA' $Py @('ai-agent\scripts\criar_tabelas_ia.py')
Push-Location -LiteralPath (Join-Path $Raiz 'ai-agent')
try {
    Executar-Quieto 'Migração da auditoria do agente' $Py @('-m', 'scripts.migracoes.migracao_colunas_opcionais_auditoria_agente')
    Executar-Quieto 'Migração das perguntas certificadas' $Py @('-m', 'scripts.migracoes.migracao_templates_cache_filtro_texto_sem_acento')
}
finally {
    Pop-Location
}
Escrever-Ok 'Tabelas do agente'

$trechos = Consultar $Container 'SELECT count(*) FROM tb_conhecimento_vetorial'
if (-not $trechos -or $trechos -eq '0') {
    Write-Host '   ... indexando os documentos do RAG (na primeira vez, baixa o modelo de embeddings, cerca de 500 MB)' -ForegroundColor DarkGray
    Push-Location -LiteralPath (Join-Path $Raiz 'ai-agent')
    try {
        Executar-Quieto 'Indexação do RAG' $Py @('-m', 'src.rag.indexar_tudo')
    }
    finally {
        Pop-Location
    }
    $trechos = Consultar $Container 'SELECT count(*) FROM tb_conhecimento_vetorial'
}
Escrever-Ok "Base de conhecimento do RAG ($trechos trechos)"

# ---------------------------------------------------------------------------
Escrever-Titulo '8/9 Tabelas das ordens de inspeção e dos usuários'

if ((Consultar $Container "SELECT to_regclass('public.ordens_inspecao') IS NOT NULL") -eq 't') {
    Escrever-Ok 'Tabela ordens_inspecao já existe (mantida, com as ordens que houver)'
}
else {
    Executar-Quieto 'Copiar o script das ordens para o container' 'docker' @('cp', 'backend\sql\ordens_inspecao.sql', "$($Container):/tmp/ordens_inspecao.sql")
    Executar-Quieto 'Criar a tabela ordens_inspecao' 'docker' @(
        'exec', $Container, 'psql', '-q', '-U', 'postgres', '-d', 'v_energy', '-v', 'ON_ERROR_STOP=1', '-f', '/tmp/ordens_inspecao.sql'
    )
    Escrever-Ok 'Tabela ordens_inspecao criada'
}

if ((Consultar $Container "SELECT to_regclass('public.usuarios') IS NOT NULL") -eq 't') {
    Escrever-Ok 'Tabela usuarios já existe (mantida, com as contas que houver)'
}
else {
    Executar-Quieto 'Copiar o script dos usuários para o container' 'docker' @('cp', 'backend\sql\usuarios.sql', "$($Container):/tmp/usuarios.sql")
    Executar-Quieto 'Criar a tabela usuarios' 'docker' @(
        'exec', $Container, 'psql', '-q', '-U', 'postgres', '-d', 'v_energy', '-v', 'ON_ERROR_STOP=1', '-f', '/tmp/usuarios.sql'
    )
    Escrever-Ok 'Tabela usuarios criada'
}

# A conta ADMIN_TI é a única criada aqui: as outras contas são criadas por ela
if ((Consultar $Container "SELECT count(*) FROM usuarios WHERE email = '$EmailAdmin'") -eq '1') {
    Escrever-Ok "Conta de administrador já existe ($EmailAdmin, mantida)"
}
else {
    # O bootstrap lê a senha do backend\.env.local. Sem ela lá, a senha digitada vai
    # só para o processo do bootstrap, sem ser gravada em arquivo
    $senhaConta = $SenhaAdmin
    if (-not $senhaConta -and -not (Ler-Variavel $EnvBackend 'BOOTSTRAP_ADMIN_PASSWORD')) {
        Write-Host "   Escolha a senha da conta de administrador do portal ($EmailAdmin)."
        Write-Host '   Ela precisa de pelo menos 8 caracteres. Guarde: é com ela que você entra no portal.'
        $senhaConta = Ler-Senha '   Senha'
        if ((Ler-Senha '   Repita a senha') -ne $senhaConta) {
            Falhar 'As duas senhas digitadas são diferentes. Rode o setup de novo.'
        }
    }
    if ($senhaConta -and $senhaConta.Length -lt 8) {
        Falhar 'A senha da conta de administrador precisa de pelo menos 8 caracteres. Rode o setup de novo.'
    }
    $senhaAnterior = $env:BOOTSTRAP_ADMIN_PASSWORD
    if ($senhaConta) { $env:BOOTSTRAP_ADMIN_PASSWORD = $senhaConta }
    Push-Location -LiteralPath (Join-Path $Raiz 'backend')
    try {
        Executar-Quieto 'Criar a conta de administrador' $Py @('-m', 'scripts.bootstrap_admin_ti')
    }
    finally {
        Pop-Location
        $env:BOOTSTRAP_ADMIN_PASSWORD = $senhaAnterior
    }
    Escrever-Ok "Conta de administrador criada ($EmailAdmin)"
}

# Quem fez cada coisa: as ordens e a auditoria do agente apontam para a conta que agiu.
# Precisa da tabela usuarios, por isso vem depois dela. Rodar de novo não muda nada
Executar-Quieto 'Copiar o script da autoria das ordens para o container' 'docker' @('cp', 'backend\sql\ordens_inspecao_autoria.sql', "$($Container):/tmp/ordens_inspecao_autoria.sql")
Executar-Quieto 'Ligar as ordens às contas' 'docker' @(
    'exec', $Container, 'psql', '-q', '-U', 'postgres', '-d', 'v_energy', '-v', 'ON_ERROR_STOP=1', '-f', '/tmp/ordens_inspecao_autoria.sql'
)
Push-Location -LiteralPath (Join-Path $Raiz 'ai-agent')
try {
    Executar-Quieto 'Ligar a auditoria do agente às contas' $Py @('-m', 'scripts.migracoes.migracao_usuario_auditoria_agente')
}
finally {
    Pop-Location
}
Escrever-Ok 'Ordens e auditoria do agente ligadas às contas'

# ---------------------------------------------------------------------------
Escrever-Titulo '9/9 Dependências do frontend'

Push-Location -LiteralPath (Join-Path $Raiz 'frontend')
try {
    Write-Host '   ... npm install' -ForegroundColor DarkGray
    # --no-save: instala as versões do package-lock.json sem regravar o arquivo (outra
    # versão do npm mudaria o arquivo, e ele apareceria modificado no Git)
    Executar 'Instalar as dependências do frontend' 'npm.cmd' @('install', '--no-save', '--no-audit', '--no-fund', '--loglevel', 'error')
}
finally {
    Pop-Location
}
Escrever-Ok 'Dependências do frontend'

# ---------------------------------------------------------------------------
Escrever-Titulo 'Pronto'

$chaveOpenRouter = Ler-Variavel $EnvBackend 'OPENROUTER_API_KEY'
$chave9router = Ler-Variavel $EnvBackend 'NINEROUTER_API_KEY'
if (-not $chaveOpenRouter -and -not $chave9router) {
    Escrever-Aviso 'O agente de IA ainda não tem chave de LLM: ele vai responder "serviço indisponível".'
    Escrever-Aviso 'Para ligar o agente, preencha o backend\.env.local como no passo 3 do README.'
}
elseif ($chave9router -and -not (Get-Command 9router.cmd -ErrorAction SilentlyContinue)) {
    Escrever-Aviso 'O backend\.env.local usa o 9router, mas ele não está instalado. Instale com: npm install -g 9router'
}

Write-Host ''
Write-Host 'Para ligar o portal:' -ForegroundColor Green
Write-Host '    powershell -ExecutionPolicy Bypass -File .\iniciar.ps1'
Write-Host ''
Write-Host "Para entrar no portal, use $EmailAdmin e a senha da conta de administrador." -ForegroundColor Green
