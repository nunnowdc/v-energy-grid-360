# Funções usadas pelo setup.sh e pelo iniciar.sh (macOS e Linux), na raiz do repositório.
# Compatível com o bash 3.2, que é o que vem no macOS.

# Os scripts Python do projeto imprimem emojis e acentos
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8

if [ -t 1 ]; then
    COR_TITULO=$'\033[36m'
    COR_OK=$'\033[32m'
    COR_AVISO=$'\033[33m'
    COR_ERRO=$'\033[31m'
    COR_DETALHE=$'\033[90m'
    COR_FIM=$'\033[0m'
else
    COR_TITULO='' COR_OK='' COR_AVISO='' COR_ERRO='' COR_DETALHE='' COR_FIM=''
fi

escrever_titulo() {
    echo ''
    echo "${COR_TITULO}== $1${COR_FIM}"
}

escrever_ok() {
    echo "${COR_OK}   OK  $1${COR_FIM}"
}

escrever_aviso() {
    echo "${COR_AVISO}   !   $1${COR_FIM}"
}

escrever_detalhe() {
    echo "${COR_DETALHE}   ... $1${COR_FIM}"
}

falhar() {
    echo ''
    echo "${COR_ERRO}ERRO: $1${COR_FIM}"
    exit 1
}

# Roda um programa e para o script se ele falhar
executar() {
    local descricao="$1"
    shift
    "$@"
    local codigo=$?
    if [ $codigo -ne 0 ]; then
        falhar "$descricao falhou (código de saída $codigo). Veja a mensagem acima."
    fi
}

# Roda um programa sem mostrar a saída. Se ele falhar, mostra a saída e para o script
executar_quieto() {
    local descricao="$1"
    shift
    local saida
    saida=$("$@" 2>&1)
    local codigo=$?
    if [ $codigo -ne 0 ]; then
        echo "$saida" | sed 's/^/   /'
        falhar "$descricao falhou (código de saída $codigo). Veja a mensagem acima."
    fi
}

# Roda um programa só para saber se dá certo, sem mostrar a saída
testar() {
    "$@" >/dev/null 2>&1
}

existe_comando() {
    command -v "$1" >/dev/null 2>&1
}

# Valor de uma variável de um arquivo .env, ou vazio se não houver
ler_variavel() {
    [ -f "$1" ] || return 0
    grep -E "^[[:space:]]*$2[[:space:]]*=" "$1" | head -n 1 | tr -d '\r' |
        sed -e 's/^[^=]*=//' -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' \
            -e 's/^["'"'"']*//' -e 's/["'"'"']*$//'
}

# Lê a senha do DATABASE_URL de um arquivo .env para SENHA_LIDA. Falha (código 1)
# se o arquivo não existir ou ainda tiver os valores do exemplo. Precisa do
# PYTHON_BASE, para decodificar a senha
ler_conexao() {
    local url
    url=$(ler_variavel "$1" 'DATABASE_URL')
    local padrao='^postgresql(\+psycopg)?://[^:]+:([^@]*)@[^:/]+:([0-9]+)/'
    [[ $url =~ $padrao ]] || return 1
    SENHA_LIDA=$("$PYTHON_BASE" -c 'import sys, urllib.parse; print(urllib.parse.unquote(sys.argv[1]))' "${BASH_REMATCH[2]}")
    [ -n "$SENHA_LIDA" ] && [ "$SENHA_LIDA" != 'SUA_SENHA' ]
}

docker_ligado() {
    testar docker info
}

# Liga o Docker, se precisar, e espera o motor do Docker responder
garantir_docker() {
    if ! existe_comando docker; then
        if [ "$(uname -s)" = 'Darwin' ]; then
            falhar 'O Docker não está instalado. Instale o Docker Desktop (https://www.docker.com/products/docker-desktop/), abra uma vez e rode de novo.'
        fi
        falhar 'O Docker não está instalado. Veja no passo 0.2 do README como instalar e rode de novo.'
    fi
    docker_ligado && return 0

    if [ "$(uname -s)" = 'Darwin' ]; then
        escrever_detalhe 'abrindo o Docker Desktop'
        open -a Docker >/dev/null 2>&1
        escrever_detalhe 'esperando o Docker iniciar (até 3 minutos)'
        local i=0
        while [ $i -lt 90 ]; do
            docker_ligado && return 0
            sleep 2
            i=$((i + 1))
        done
        falhar 'O Docker não respondeu. Abra o Docker Desktop, espere aparecer "Engine running" e rode de novo.'
    fi

    # Linux: sem permissão no socket, esperar não adianta
    if docker info 2>&1 | grep -qi 'permission denied'; then
        falhar "Seu usuário não tem permissão para usar o Docker. Rode: sudo usermod -aG docker $(id -un) . Depois saia da sessão e entre de novo (ou reinicie o computador) e rode de novo."
    fi
    # Docker Desktop para Linux, se estiver instalado
    if existe_comando systemctl; then
        systemctl --user start docker-desktop >/dev/null 2>&1
    fi
    escrever_detalhe 'esperando o Docker responder (até 1 minuto)'
    local i=0
    while [ $i -lt 30 ]; do
        docker_ligado && return 0
        sleep 2
        i=$((i + 1))
    done
    falhar 'O Docker não está ligado. Ligue com: sudo systemctl start docker (ou abra o Docker Desktop) e rode de novo.'
}

container_existe() {
    [ "$(docker ps -a --filter "name=^$1\$" --format '{{.Names}}' 2>/dev/null)" = "$1" ]
}

container_ligado() {
    [ "$(docker inspect -f '{{.State.Running}}' "$1" 2>/dev/null)" = 'true' ]
}

# Espera o PostgreSQL do container aceitar conexões pela rede
esperar_banco() {
    local i=0
    while [ $i -lt 60 ]; do
        testar docker exec "$1" pg_isready -h 127.0.0.1 -U postgres -d v_energy && return 0
        sleep 2
        i=$((i + 1))
    done
    falhar "O banco do container $1 não ficou pronto. Veja o motivo com: docker logs $1"
}

ligar_banco() {
    if ! container_ligado "$1"; then
        executar_quieto 'Ligar o container do banco' docker start "$1"
    fi
    esperar_banco "$1"
}

# Porta do computador ligada à 5432 do container (ex.: 5433)
porta_do_container() {
    docker port "$1" 5432/tcp 2>/dev/null | head -n 1 | sed -n 's/.*:\([0-9][0-9]*\)$/\1/p'
}

# Resposta de uma consulta SQL no banco do container, ou vazio se der erro
consultar() {
    docker exec "$1" psql -U postgres -d v_energy -Atc "$2" 2>/dev/null
}

url_responde() {
    local codigo
    codigo=$(curl -s -o /dev/null -m 3 -w '%{http_code}' "$1" 2>/dev/null)
    [ -n "$codigo" ] && [ "$codigo" != '000' ] && [ "$codigo" -lt 500 ]
}

# Espera uma URL responder. Com um PID no terceiro argumento, desiste antes se
# o processo morrer
esperar_url() {
    local fim=$((SECONDS + $2))
    while [ $SECONDS -lt $fim ]; do
        url_responde "$1" && return 0
        if [ -n "$3" ] && ! kill -0 "$3" 2>/dev/null; then
            return 1
        fi
        sleep 2
    done
    return 1
}

abrir_navegador() {
    if [ "$(uname -s)" = 'Darwin' ]; then
        open "$1" >/dev/null 2>&1
    elif existe_comando xdg-open; then
        xdg-open "$1" >/dev/null 2>&1 &
    fi
}
