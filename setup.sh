#!/usr/bin/env bash
# Prepara o V-Energy Grid 360 para rodar neste computador (macOS ou Linux),
# fazendo os passos 1 a 9 do "Como executar" do README: banco no Docker, arquivos
# de configuração, ambiente Python, carga da Gold, tabelas da IA, tabela das
# ordens de inspeção e dependências do frontend. No Windows, use o setup.ps1.
#
# Pode rodar de novo quantas vezes quiser: o que já está pronto é pulado. Rode de
# novo depois de um git pull, para instalar dependências novas.
#
# Uso, a partir da raiz do repositório:
#     bash setup.sh
#     bash setup.sh --recarregar-gold

# Precisa do bash (no Ubuntu, "sh setup.sh" roda outro interpretador)
if [ -z "$BASH_VERSION" ]; then
    echo 'Rode com: bash setup.sh'
    exit 1
fi

RECARREGAR_GOLD=0
CONTAINER='postgres-venergy'
PORTA=5433
VOLUME='pgdata-v_energy'
SENHA=''

while [ $# -gt 0 ]; do
    case "$1" in
        --recarregar-gold) RECARREGAR_GOLD=1 ;;
        --container) CONTAINER="$2"; shift ;;
        --porta) PORTA="$2"; shift ;;
        --volume) VOLUME="$2"; shift ;;
        --senha) SENHA="$2"; shift ;;
        *) echo "Opção desconhecida: $1 (as opções são --recarregar-gold, --porta, --container, --volume e --senha)"; exit 1 ;;
    esac
    shift
done

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$RAIZ" || exit 1
. "$RAIZ/scripts/funcoes-setup.sh"

# As mesmas 15 tabelas que o scripts/carga_banco_local.py carrega
TABELAS_GOLD='dim_unidade_consumidora dim_alimentador dim_medidor dim_geracao_distribuida
dim_competencia fact_faturamento fact_leituras fact_ocorrencias
fact_atendimentos fact_inspecoes fila_inspecao agg_receita_mensal
agg_receita_preco_volume agg_continuidade_alimentador agg_continuidade_alimentador_anual'

ENV_RAIZ="$RAIZ/.env"
ENV_BACKEND="$RAIZ/backend/.env.local"
ENV_FRONTEND="$RAIZ/frontend/.env.local"
PASTA_VENV="$RAIZ/backend/.venv"
PY="$PASTA_VENV/bin/python"
PASTA_DADOS="$RAIZ/data"

echo "${COR_TITULO}V-Energy Grid 360 · setup${COR_FIM}"

SISTEMA="$(uname -s)"
case "$SISTEMA" in
    Darwin | Linux) ;;
    *) falhar 'O setup.sh é para macOS e Linux. No Windows, use: powershell -ExecutionPolicy Bypass -File .\setup.ps1' ;;
esac

if [ "$(id -u)" = '0' ]; then
    falhar 'Não rode o setup com sudo nem como root: os arquivos ficariam sem permissão para o seu usuário. Rode só: bash setup.sh'
fi

# ---------------------------------------------------------------------------
escrever_titulo '1/9 Programas necessários'

PYTHON_BASE=''
for candidato in python3.12 python3.13 python3.11 python3 python3.14 python; do
    existe_comando "$candidato" || continue
    versao=$("$candidato" -c 'import sys; print(sys.version_info[0] * 100 + sys.version_info[1])' 2>/dev/null)
    case "$versao" in '' | *[!0-9]*) continue ;; esac
    if [ "$versao" -ge 311 ]; then
        PYTHON_BASE="$(command -v "$candidato")"
        VERSAO_PYTHON="$((versao / 100)).$((versao % 100))"
        break
    fi
done
if [ -z "$PYTHON_BASE" ]; then
    if [ "$SISTEMA" = 'Darwin' ]; then
        falhar 'Python 3.11 ou superior não encontrado. Instale o Python 3.12 em https://www.python.org/downloads/ (ou com: brew install python@3.12), abra um terminal novo e rode de novo.'
    fi
    falhar 'Python 3.11 ou superior não encontrado. No Ubuntu/Debian: sudo apt install python3 python3-venv. Depois, rode de novo.'
fi

# No Mac com processador Intel, o torch (usado pelo RAG) só existe até o Python 3.12
ARQUITETURA_PYTHON=$("$PYTHON_BASE" -c 'import platform; print(platform.machine())')
MAC_INTEL=0
if [ "$SISTEMA" = 'Darwin' ] && [ "$ARQUITETURA_PYTHON" = 'x86_64' ]; then
    MAC_INTEL=1
    if [ "${VERSAO_PYTHON#3.}" -gt 12 ]; then
        falhar "Neste Mac com processador Intel, o agente de IA precisa do Python 3.11 ou 3.12, e o encontrado é o $VERSAO_PYTHON. Instale o 3.12 (https://www.python.org/downloads/ ou brew install python@3.12) e rode de novo."
    fi
fi

# No Ubuntu e no Debian, o venv vem num pacote separado
if ! testar "$PYTHON_BASE" -c 'import venv, ensurepip'; then
    falhar "O Python $VERSAO_PYTHON está sem o módulo venv. No Ubuntu/Debian, instale com: sudo apt install python$VERSAO_PYTHON-venv . Depois, rode de novo."
fi
escrever_ok "Python $VERSAO_PYTHON ($PYTHON_BASE)"

if ! existe_comando node; then
    falhar 'Node.js não encontrado. Instale a versão 20 ou superior (veja o passo 0.2 do README), abra um terminal novo e rode de novo.'
fi
VERSAO_NODE="$(node --version 2>/dev/null)"
MAIOR_NODE="${VERSAO_NODE#v}"
MAIOR_NODE="${MAIOR_NODE%%.*}"
case "$MAIOR_NODE" in '' | *[!0-9]*) MAIOR_NODE=0 ;; esac
if [ "$MAIOR_NODE" -lt 20 ]; then
    falhar "O Node.js instalado é o $VERSAO_NODE, e o projeto precisa do 20 ou superior. Veja no passo 0.2 do README como instalar."
fi
if ! existe_comando npm; then
    falhar 'O npm não foi encontrado. Instale o Node.js de novo (veja o passo 0.2 do README).'
fi
escrever_ok "Node.js $VERSAO_NODE"

if ! existe_comando curl; then
    falhar 'O curl não foi encontrado. No Ubuntu/Debian, instale com: sudo apt install curl'
fi

garantir_docker
escrever_ok 'Docker ligado'

# ---------------------------------------------------------------------------
escrever_titulo '2/9 Senha do banco'

CONTAINER_NOVO=0
container_existe "$CONTAINER" || CONTAINER_NOVO=1

if ler_conexao "$ENV_RAIZ" || ler_conexao "$ENV_BACKEND"; then
    SENHA_BANCO="$SENHA_LIDA"
    escrever_ok 'Senha lida dos arquivos de configuração'
elif [ -n "$SENHA" ]; then
    SENHA_BANCO="$SENHA"
else
    if [ ! -t 0 ]; then
        falhar 'Não dá para perguntar a senha aqui. Rode de novo com: bash setup.sh --senha SUA_SENHA'
    fi
    if [ $CONTAINER_NOVO -eq 1 ]; then
        echo '   Escolha uma senha para o banco. O mais simples é usar só letras e números.'
    else
        echo "   O container $CONTAINER já existe. Digite a senha usada quando ele foi criado."
    fi
    read -r -s -p '   Senha: ' SENHA_BANCO
    echo ''
fi
# Aspas, barra invertida e espaços quebram a senha no comando do Docker
if [ $CONTAINER_NOVO -eq 1 ]; then
    padrao_senha='^[^[:space:]"\\]{4,}$'
    if ! [[ $SENHA_BANCO =~ $padrao_senha ]]; then
        falhar 'Use uma senha com pelo menos 4 caracteres, sem espaços, aspas ou barra invertida.'
    fi
fi

# ---------------------------------------------------------------------------
escrever_titulo '3/9 Banco de dados (PostgreSQL com pgvector no Docker)'

if [ $CONTAINER_NOVO -eq 1 ]; then
    if testar docker volume inspect "$VOLUME"; then
        escrever_aviso "O volume $VOLUME já existe, então o banco guarda a senha de quando ele foi criado."
    fi
    escrever_detalhe 'criando o container (na primeira vez, o Docker baixa a imagem)'
    executar_quieto "Criar o container (se a mensagem for 'port is already allocated', rode com --porta 5434)" \
        docker run -d --name "$CONTAINER" -e "POSTGRES_PASSWORD=$SENHA_BANCO" -e POSTGRES_DB=v_energy \
        -p "$PORTA:5432" -v "$VOLUME:/var/lib/postgresql" pgvector/pgvector:pg18
    escrever_ok "Container $CONTAINER criado"
fi
ligar_banco "$CONTAINER"
PORTA_BANCO="$(porta_do_container "$CONTAINER")"
[ -n "$PORTA_BANCO" ] || falhar "Não foi possível descobrir a porta do container $CONTAINER."
escrever_ok "Banco ligado em localhost:$PORTA_BANCO"

executar_quieto 'Ativar as extensões vector e unaccent' \
    docker exec "$CONTAINER" psql -q -U postgres -d v_energy \
    -c 'CREATE EXTENSION IF NOT EXISTS vector;' -c 'CREATE EXTENSION IF NOT EXISTS unaccent;'
escrever_ok 'Extensões vector e unaccent'

# ---------------------------------------------------------------------------
escrever_titulo '4/9 Ambiente Python (backend/.venv)'

if [ -e "$PY" ] && ! testar "$PY" -c 'import sys'; then
    escrever_aviso 'O ambiente Python existente não funciona (a pasta mudou de lugar ou o Python foi trocado). Criando de novo.'
    rm -rf "$PASTA_VENV"
fi
PIP_QUIETO='-q'
if [ ! -e "$PY" ]; then
    executar 'Criar o ambiente Python' "$PYTHON_BASE" -m venv "$PASTA_VENV"
    escrever_ok 'Ambiente criado'
    escrever_detalhe 'instalando as dependências (de 5 a 15 minutos na primeira vez)'
    executar 'Atualizar o pip' "$PY" -m pip install --disable-pip-version-check -q --upgrade pip
    PIP_QUIETO=''
else
    escrever_detalhe 'conferindo as dependências'
fi

# No Linux com processador x86_64, o torch padrão do pip vem com CUDA (alguns GB
# a mais). O RAG roda na CPU, então instala a versão só para CPU antes
if [ "$SISTEMA" = 'Linux' ] && [ "$ARQUITETURA_PYTHON" = 'x86_64' ] && ! testar "$PY" -c 'import torch'; then
    executar 'Instalar o torch (versão para CPU)' "$PY" -m pip install --disable-pip-version-check $PIP_QUIETO \
        torch --index-url https://download.pytorch.org/whl/cpu
fi

# No Mac com Intel, o último torch é o 2.2, que só funciona com o numpy 1.x
EXTRA_PIP=''
[ $MAC_INTEL -eq 1 ] && EXTRA_PIP='numpy<2'

executar 'Instalar as dependências do backend e do agente' "$PY" -m pip install --disable-pip-version-check $PIP_QUIETO \
    -r backend/requirements.txt -r ai-agent/requirements.txt $EXTRA_PIP
escrever_ok 'Dependências do backend e do agente de IA'

# ---------------------------------------------------------------------------
escrever_titulo '5/9 Arquivos de configuração'

SENHA_URL=$("$PY" -c 'import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=""))' "$SENHA_BANCO")
URL_SCRIPTS="postgresql://postgres:$SENHA_URL@localhost:$PORTA_BANCO/v_energy"
URL_BACKEND="postgresql+psycopg://postgres:$SENHA_URL@localhost:$PORTA_BANCO/v_energy"

# Confere a senha antes de gravar qualquer arquivo
TESTE_CONEXAO='import sys, psycopg2; psycopg2.connect(sys.argv[1]).close()'
if ! testar "$PY" -c "$TESTE_CONEXAO" "$URL_SCRIPTS"; then
    "$PY" -c "$TESTE_CONEXAO" "$URL_SCRIPTS"
    falhar "Não foi possível entrar no banco com essa senha. Confira a senha do container $CONTAINER e rode de novo."
fi
escrever_ok 'Senha do banco conferida'

if [ ! -e "$ENV_RAIZ" ]; then
    printf 'DATABASE_URL=%s\n' "$URL_SCRIPTS" > "$ENV_RAIZ"
    escrever_ok '.env criado'
else
    escrever_ok '.env já existe (mantido)'
fi

# Copia um .env trocando a linha do DATABASE_URL
gravar_com_banco() {
    executar_quieto "Gravar $2" "$PY" -c '
import re, sys
texto = open(sys.argv[1], encoding="utf-8").read()
texto = re.sub(r"(?m)^DATABASE_URL=.*$", lambda _: sys.argv[3], texto)
open(sys.argv[2], "w", encoding="utf-8", newline="").write(texto)
' "$1" "$2" "DATABASE_URL=$URL_BACKEND"
}

if [ ! -e "$ENV_BACKEND" ]; then
    gravar_com_banco "$RAIZ/backend/.env.example" "$ENV_BACKEND"
    escrever_ok 'backend/.env.local criado'
elif ! ler_conexao "$ENV_BACKEND"; then
    gravar_com_banco "$ENV_BACKEND" "$ENV_BACKEND"
    escrever_ok 'backend/.env.local: DATABASE_URL preenchido'
else
    escrever_ok 'backend/.env.local já existe (mantido)'
fi

if [ ! -e "$ENV_FRONTEND" ]; then
    cp "$RAIZ/frontend/.env.example" "$ENV_FRONTEND"
    escrever_ok 'frontend/.env.local criado'
else
    escrever_ok 'frontend/.env.local já existe (mantido)'
fi

# ---------------------------------------------------------------------------
escrever_titulo '6/9 Carga da Gold'

# Um caminho por linha
csvs_da_gold() {
    [ -d "$PASTA_DADOS" ] || return 0
    find "$PASTA_DADOS" -type f -name '*.csv' | while IFS= read -r arquivo; do
        nome="$(basename "$arquivo" .csv)"
        for tabela in $TABELAS_GOLD; do
            if [ "$nome" = "$tabela" ]; then
                echo "$arquivo"
                break
            fi
        done
    done
}

contar_linhas() {
    if [ -z "$1" ]; then echo 0; else echo "$1" | wc -l | tr -d ' '; fi
}

ZIPS="$( { find "$PASTA_DADOS" -maxdepth 1 -type f -name '*.zip' 2>/dev/null; find "$RAIZ" -maxdepth 1 -type f -name '*.zip'; } )"
QTD_ZIPS="$(contar_linhas "$ZIPS")"
CSVS="$(csvs_da_gold)"

# Com --recarregar-gold e um .zip em data/, a Gold extraída é trocada pela do .zip
if [ $RECARREGAR_GOLD -eq 1 ] && [ "$QTD_ZIPS" -eq 1 ] && [ -n "$CSVS" ]; then
    echo "$CSVS" | while IFS= read -r arquivo; do rm -f "$arquivo"; done
    escrever_ok 'CSVs da Gold antiga apagados'
    CSVS=''
fi

if [ -z "$CSVS" ]; then
    if [ "$QTD_ZIPS" -eq 0 ]; then
        falhar "Os dados da Gold não estão em data/. Copie o zip da Gold (peça ao time) para $PASTA_DADOS e rode de novo."
    fi
    if [ "$QTD_ZIPS" -gt 1 ]; then
        falhar "Há mais de um .zip: $(echo "$ZIPS" | tr '\n' ' '). Deixe só o da Gold mais recente e rode de novo."
    fi
    escrever_detalhe "extraindo $(basename "$ZIPS")"
    mkdir -p "$PASTA_DADOS"
    executar_quieto 'Extrair o zip da Gold' "$PY" -c 'import sys, zipfile; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])' "$ZIPS" "$PASTA_DADOS"
    CSVS="$(csvs_da_gold)"
    [ -n "$CSVS" ] || falhar "O zip $(basename "$ZIPS") não tem os CSVs da Gold."
    escrever_ok 'Zip extraído em data/'
fi

REPETIDOS="$(echo "$CSVS" | while IFS= read -r arquivo; do basename "$arquivo" .csv; done | sort | uniq -d)"
if [ -n "$REPETIDOS" ]; then
    falhar "Há mais de uma cópia da Gold em data/ (tabelas: $(echo "$REPETIDOS" | tr '\n' ' ')). Apague a cópia antiga e rode de novo."
fi
FALTANDO=''
for tabela in $TABELAS_GOLD; do
    echo "$CSVS" | grep -q "/$tabela\.csv\$" || FALTANDO="$FALTANDO $tabela"
done
if [ -n "$FALTANDO" ]; then
    escrever_aviso "Faltam CSVs da Gold:$FALTANDO"
fi

LINHAS_CARREGADAS="$(consultar "$CONTAINER" 'SELECT count(*) FROM fact_faturamento')"
if [ $RECARREGAR_GOLD -eq 1 ] || [ -z "$LINHAS_CARREGADAS" ] || [ "$LINHAS_CARREGADAS" = '0' ]; then
    escrever_detalhe 'carregando a Gold no banco (de 1 a 3 minutos)'
    executar 'Carga da Gold' "$PY" scripts/carga_banco_local.py
    escrever_ok 'Gold carregada'
else
    escrever_ok "Gold já carregada ($LINHAS_CARREGADAS faturas). Para carregar de novo, use --recarregar-gold"
fi

# ---------------------------------------------------------------------------
escrever_titulo '7/9 Tabelas e base de conhecimento da IA'

executar_quieto 'Criar as tabelas da IA' "$PY" ai-agent/scripts/criar_tabelas_ia.py
cd "$RAIZ/ai-agent" || exit 1
executar_quieto 'Migração da auditoria do agente' "$PY" -m scripts.migracoes.migracao_colunas_opcionais_auditoria_agente
executar_quieto 'Migração das perguntas certificadas' "$PY" -m scripts.migracoes.migracao_templates_cache_filtro_texto_sem_acento
cd "$RAIZ" || exit 1
escrever_ok 'Tabelas do agente'

TRECHOS="$(consultar "$CONTAINER" 'SELECT count(*) FROM tb_conhecimento_vetorial')"
if [ -z "$TRECHOS" ] || [ "$TRECHOS" = '0' ]; then
    escrever_detalhe 'indexando os documentos do RAG (na primeira vez, baixa o modelo de embeddings, cerca de 500 MB)'
    cd "$RAIZ/ai-agent" || exit 1
    executar_quieto 'Indexação do RAG' "$PY" -m src.rag.indexar_tudo
    cd "$RAIZ" || exit 1
    TRECHOS="$(consultar "$CONTAINER" 'SELECT count(*) FROM tb_conhecimento_vetorial')"
fi
escrever_ok "Base de conhecimento do RAG ($TRECHOS trechos)"

# ---------------------------------------------------------------------------
escrever_titulo '8/9 Tabela das ordens de inspeção'

if [ "$(consultar "$CONTAINER" "SELECT to_regclass('public.ordens_inspecao') IS NOT NULL")" = 't' ]; then
    escrever_ok 'Tabela ordens_inspecao já existe (mantida, com as ordens que houver)'
else
    executar_quieto 'Copiar o script das ordens para o container' docker cp backend/sql/ordens_inspecao.sql "$CONTAINER:/tmp/ordens_inspecao.sql"
    executar_quieto 'Criar a tabela ordens_inspecao' \
        docker exec "$CONTAINER" psql -q -U postgres -d v_energy -v ON_ERROR_STOP=1 -f /tmp/ordens_inspecao.sql
    escrever_ok 'Tabela ordens_inspecao criada'
fi

# ---------------------------------------------------------------------------
escrever_titulo '9/9 Dependências do frontend'

cd "$RAIZ/frontend" || exit 1
escrever_detalhe 'npm install'
# --no-save: instala as versões do package-lock.json sem regravar o arquivo (outra
# versão do npm mudaria o arquivo, e ele apareceria modificado no Git)
executar 'Instalar as dependências do frontend' npm install --no-save --no-audit --no-fund --loglevel error
cd "$RAIZ" || exit 1
escrever_ok 'Dependências do frontend'

# ---------------------------------------------------------------------------
escrever_titulo 'Pronto'

CHAVE_OPENROUTER="$(ler_variavel "$ENV_BACKEND" 'OPENROUTER_API_KEY')"
CHAVE_9ROUTER="$(ler_variavel "$ENV_BACKEND" 'NINEROUTER_API_KEY')"
if [ -z "$CHAVE_OPENROUTER" ] && [ -z "$CHAVE_9ROUTER" ]; then
    escrever_aviso 'O agente de IA ainda não tem chave de LLM: ele vai responder "serviço indisponível".'
    escrever_aviso 'Para ligar o agente, preencha o backend/.env.local como no passo 3 do README.'
elif [ -n "$CHAVE_9ROUTER" ] && ! existe_comando 9router; then
    escrever_aviso 'O backend/.env.local usa o 9router, mas ele não está instalado. Instale com: npm install -g 9router'
fi

echo ''
echo "${COR_OK}Para ligar o portal:${COR_FIM}"
echo '    bash iniciar.sh'
