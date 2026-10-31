#!/usr/bin/env bash
# Liga o V-Energy Grid 360 para o dia a dia, depois do setup.sh (macOS e Linux):
# liga o banco no Docker e, neste mesmo terminal, o backend, o frontend e, se o
# agente usar o 9router, o 9router. No fim, abre o portal no navegador e mostra
# as mensagens do que ele ligou. No Windows, use o iniciar.ps1.
#
# Deixe o terminal aberto. Para desligar, aperte Ctrl + C.
#
# Uso, a partir da raiz do repositório:
#     bash iniciar.sh
#     bash iniciar.sh --sem-navegador

if [ -z "$BASH_VERSION" ]; then
    echo 'Rode com: bash iniciar.sh'
    exit 1
fi

CONTAINER='postgres-venergy'
SEM_NAVEGADOR=0

while [ $# -gt 0 ]; do
    case "$1" in
        --container) CONTAINER="$2"; shift ;;
        --sem-navegador) SEM_NAVEGADOR=1 ;;
        *) echo "Opção desconhecida: $1 (as opções são --sem-navegador e --container)"; exit 1 ;;
    esac
    shift
done

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$RAIZ" || exit 1
. "$RAIZ/scripts/funcoes-setup.sh"

ENV_BACKEND="$RAIZ/backend/.env.local"
PY="$RAIZ/backend/.venv/bin/python"
PORTAL='http://localhost:5173'
# As mensagens de cada parte ficam aqui (arquivos .log, ignorados pelo Git)
PASTA_LOGS="$RAIZ/.logs"

echo "${COR_TITULO}V-Energy Grid 360 · iniciar${COR_FIM}"

case "$(uname -s)" in
    Darwin | Linux) ;;
    *) falhar 'O iniciar.sh é para macOS e Linux. No Windows, use: powershell -ExecutionPolicy Bypass -File .\iniciar.ps1' ;;
esac

FALTANDO=''
[ -e "$PY" ] || FALTANDO="$FALTANDO backend/.venv"
[ -e "$ENV_BACKEND" ] || FALTANDO="$FALTANDO backend/.env.local"
[ -e "$RAIZ/frontend/.env.local" ] || FALTANDO="$FALTANDO frontend/.env.local"
[ -d "$RAIZ/frontend/node_modules" ] || FALTANDO="$FALTANDO frontend/node_modules"
if [ -n "$FALTANDO" ]; then
    falhar "Falta preparar o projeto (${FALTANDO# }). Rode antes: bash setup.sh"
fi

# Partes ligadas por este script, no formato PID:nome, e os arquivos de log delas
PARTES=''
LOGS=''
PID_TAIL=''

# Cada parte roda no seu próprio grupo de processos, então o sinal chega também
# aos processos filhos (o vite do npm, por exemplo)
parar_grupo() {
    kill -TERM -- "-$1" 2>/dev/null || kill -TERM "$1" 2>/dev/null
}

desligar() {
    trap - INT TERM HUP
    if [ -n "$PARTES" ]; then
        echo ''
        echo 'Desligando...'
        [ -n "$PID_TAIL" ] && kill "$PID_TAIL" 2>/dev/null
        for parte in $PARTES; do
            parar_grupo "${parte%%:*}"
        done
        wait 2>/dev/null
        # Alguns processos (o 9router, por exemplo) levam uns segundos para fechar
        local i=0 vivos
        while [ $i -lt 10 ]; do
            vivos=0
            for parte in $PARTES; do
                kill -0 -- "-${parte%%:*}" 2>/dev/null && vivos=1
            done
            [ $vivos -eq 0 ] && break
            sleep 1
            i=$((i + 1))
        done
    fi
    exit "${1:-0}"
}

# Liga um comando em segundo plano, numa pasta, com a saída num arquivo de log
ligar() {
    local nome="$1" pasta="$2"
    shift 2
    mkdir -p "$PASTA_LOGS"
    local log="$PASTA_LOGS/$nome.log"
    : > "$log"
    set -m
    (cd "$pasta" && exec "$@") >> "$log" 2>&1 &
    ULTIMO_PID=$!
    set +m
    PARTES="$PARTES $ULTIMO_PID:$nome"
    # Relativo à raiz, para o tail não quebrar com espaços no caminho
    LOGS="$LOGS .logs/$nome.log"
    ULTIMO_LOG="$log"
}

# Desliga a última parte ligada e tira ela das listas
desistir_da_ultima() {
    parar_grupo "$ULTIMO_PID"
    wait "$ULTIMO_PID" 2>/dev/null
    PARTES="${PARTES% *}"
    LOGS="${LOGS% *}"
}

# Mostra o fim do log de uma parte que não subiu e para tudo
falhar_parte() {
    echo ''
    echo "   Últimas linhas de $2:"
    tail -n 30 "$2" | sed 's/^/   | /'
    echo ''
    echo "${COR_ERRO}ERRO: $1${COR_FIM}"
    desligar 1
}

trap 'desligar 0' INT TERM HUP

# ---------------------------------------------------------------------------
escrever_titulo 'Banco de dados'

garantir_docker
if ! container_existe "$CONTAINER"; then
    falhar "O container $CONTAINER não existe. Rode antes: bash setup.sh"
fi
ligar_banco "$CONTAINER"
escrever_ok "Banco ligado em localhost:$(porta_do_container "$CONTAINER")"

# ---------------------------------------------------------------------------
escrever_titulo '9router'

CHAVE_9ROUTER="$(ler_variavel "$ENV_BACKEND" 'NINEROUTER_API_KEY')"
URL_9ROUTER="$(ler_variavel "$ENV_BACKEND" 'NINEROUTER_BASE_URL')"
PADRAO_LOCAL='^https?://(localhost|127\.0\.0\.1):([0-9]+)'
if [ -z "$CHAVE_9ROUTER" ]; then
    escrever_ok 'Não usado (sem NINEROUTER_API_KEY no backend/.env.local)'
elif ! [[ $URL_9ROUTER =~ $PADRAO_LOCAL ]]; then
    escrever_ok 'Não é local (NINEROUTER_BASE_URL aponta para outro endereço)'
else
    MODELOS_9ROUTER="http://127.0.0.1:${BASH_REMATCH[2]}/v1/models"
    if url_responde "$MODELOS_9ROUTER"; then
        escrever_ok 'Já estava ligado'
    elif ! existe_comando 9router; then
        escrever_aviso 'O 9router não está instalado. Instale com "npm install -g 9router"; até lá, o agente de IA não responde.'
    else
        # O 9router fecha sozinho quando a entrada dele acaba, e o tail a mantém
        # aberta. O --host 127.0.0.1 deixa ele acessível só neste computador
        ligar 9router "$RAIZ" bash -c 'tail -f /dev/null | 9router --no-browser --host 127.0.0.1 --skip-update'
        if esperar_url "$MODELOS_9ROUTER" 60 "$ULTIMO_PID"; then
            escrever_ok 'Ligado'
        else
            desistir_da_ultima
            escrever_aviso "O 9router não subiu; até ele subir, o agente de IA não responde. Veja as mensagens em $ULTIMO_LOG"
        fi
    fi
fi

# ---------------------------------------------------------------------------
escrever_titulo 'Backend'

PORTA_BACKEND="$(ler_variavel "$ENV_BACKEND" 'APP_PORT')"
[ -n "$PORTA_BACKEND" ] || PORTA_BACKEND=8000
SAUDE_BACKEND="http://127.0.0.1:$PORTA_BACKEND/api/health"
if url_responde "$SAUDE_BACKEND"; then
    escrever_ok "Já estava ligado em http://127.0.0.1:$PORTA_BACKEND"
else
    ligar backend "$RAIZ/backend" "$PY" -m app.main
    escrever_detalhe 'esperando a API responder (até 3 minutos na primeira vez)'
    if ! esperar_url "$SAUDE_BACKEND" 180 "$ULTIMO_PID"; then
        falhar_parte 'O backend não subiu. Veja as mensagens acima.' "$ULTIMO_LOG"
    fi
    escrever_ok "Ligado: http://127.0.0.1:$PORTA_BACKEND/api/docs"
fi

# ---------------------------------------------------------------------------
escrever_titulo 'Frontend'

if url_responde "$PORTAL"; then
    escrever_ok "Já estava ligado em $PORTAL"
else
    ligar frontend "$RAIZ/frontend" npm run dev
    if ! esperar_url "$PORTAL" 90 "$ULTIMO_PID"; then
        falhar_parte 'O frontend não subiu. Veja as mensagens acima.' "$ULTIMO_LOG"
    fi
    escrever_ok "Ligado: $PORTAL"
fi

# ---------------------------------------------------------------------------
echo ''
echo "${COR_OK}Portal no ar: $PORTAL${COR_FIM}"
[ $SEM_NAVEGADOR -eq 1 ] || abrir_navegador "$PORTAL"

if [ -z "$PARTES" ]; then
    echo 'Tudo já estava ligado.'
    exit 0
fi

echo 'Deixe este terminal aberto. Para desligar, aperte Ctrl + C.'
echo "As mensagens do que foi ligado aparecem abaixo (e ficam em $PASTA_LOGS)."
echo ''
# Mostra as mensagens novas até o Ctrl + C. Se uma parte cair, avisa e desliga as outras
# shellcheck disable=SC2086 # LOGS é uma lista de caminhos sem espaço
tail -n 0 -f $LOGS &
PID_TAIL=$!
while true; do
    for parte in $PARTES; do
        if ! kill -0 "${parte%%:*}" 2>/dev/null; then
            sleep 1
            echo ''
            echo "${COR_ERRO}O ${parte#*:} parou. Veja as mensagens acima.${COR_FIM}"
            desligar 1
        fi
    done
    sleep 2
done
