# V-Energy Grid 360

Portal interno da V-Energy: Indicadores, Receita, Visão 360, Fila de inspeção, Continuidade e um agente de IA que responde perguntas sobre os dados.

## Como executar

Este guia parte de um computador com Windows, macOS ou Linux e o VS Code aberto, e vai até o portal rodando com dados e com o agente de IA respondendo. São dois caminhos:

- **Jeito rápido (recomendado):** faça o passo 0 e rode dois scripts, que fazem todo o resto: `setup.ps1` e `iniciar.ps1` no Windows, `setup.sh` e `iniciar.sh` no macOS e no Linux.
- **Passo a passo manual:** os mesmos passos, um comando por vez. Serve para entender o que o setup faz ou para refazer só uma parte.

Na primeira vez, leva de 20 a 40 minutos, quase tudo em downloads.

O portal tem quatro partes:

| Parte | Onde roda | Endereço |
|---|---|---|
| Banco PostgreSQL com pgvector (camada Gold, tabelas da IA e ordens de inspeção) | Container Docker `postgres-venergy` | `localhost:5433` |
| Backend (FastAPI), que também roda o agente de IA | Terminal, na pasta `backend/` | `http://127.0.0.1:8000` |
| Frontend (React) | Terminal, na pasta `frontend/` | `http://localhost:5173` |
| 9router (opcional), roteador local de LLMs para o agente | Terminal | `http://localhost:20128` |

Todos os comandos partem da **raiz do repositório** (a pasta `v-energy-grid-360/`), a não ser quando o próprio passo tem um `cd`. Eles são escritos para o **PowerShell** do Windows; quando o comando muda no macOS e no Linux, a versão deles aparece no comentário ao lado.

### 0. Antes de começar

#### 0.1. Abra o terminal do VS Code

1. No VS Code, abra **Terminal > New Terminal** (atalho `` Ctrl + ` ``).
2. **No Windows**, confira se o terminal é o **PowerShell**: o nome aparece à direita, acima do terminal. Se for outro, clique na seta ao lado do `+` e escolha **PowerShell**. No macOS e no Linux, o terminal padrão (zsh ou bash) serve.

Sempre que instalar um programa novo, feche e abra o VS Code de novo, para o terminal enxergar o programa.

#### 0.2. Instale os programas

Siga a parte do seu sistema. Os programas são os mesmos: Git, Python 3.11 ou superior, Node.js 20 ou superior, Docker e, opcionalmente, o DBeaver.

**Windows**

| Programa | Onde baixar | Na instalação |
|---|---|---|
| Git | https://git-scm.com/downloads | Pode aceitar todas as opções padrão |
| Python 3.11 ou superior (o time usa o 3.12) | https://www.python.org/downloads/ | Na primeira tela, marque **Add python.exe to PATH**. Use o instalador **64-bit (x64)**, mesmo em notebook com processador ARM (Snapdragon): algumas dependências não existem para o Python ARM |
| Node.js 20 ou superior (versão LTS) | https://nodejs.org/ | Pode aceitar todas as opções padrão |
| Docker Desktop | https://www.docker.com/products/docker-desktop/ | Aceite o uso do WSL 2. Se ele pedir para instalar o WSL, abra o PowerShell **como administrador**, rode `wsl --install --no-distribution` e reinicie o computador |
| DBeaver Community (opcional, recomendado) | https://dbeaver.io/download/ | Pode aceitar todas as opções padrão. Serve para ver as tabelas e rodar SQL com uma interface |

Depois de instalar, abra o **Docker Desktop**, aceite os termos e espere aparecer **Engine running** no canto inferior esquerdo.

Confira no terminal do VS Code (cada comando deve mostrar uma versão):

```powershell
git --version
python --version
node --version
npm --version
docker --version
```

- O `python --version` deve mostrar 3.11 ou mais, e o `node --version`, 20 ou mais.
- Se o `python` abrir a Microsoft Store, desligue os atalhos dele em **Configurações > Aplicativos > Configurações avançadas de aplicativos > Aliases de execução de aplicativo** (as opções `python.exe` e `python3.exe`) e abra o VS Code de novo.

**macOS**

| Programa | Como instalar |
|---|---|
| Git | Rode `git --version` no terminal. Se ainda não estiver instalado, o macOS oferece instalar as ferramentas de linha de comando: aceite |
| Python 3.12 | Instalador do macOS em https://www.python.org/downloads/, ou `brew install python@3.12` se você usa o [Homebrew](https://brew.sh/). Em Mac com processador **Intel**, use o 3.11 ou o 3.12: o `torch`, usado pelo agente, não existe para versões mais novas nesses Macs |
| Node.js 20 ou superior (versão LTS) | Instalador do macOS em https://nodejs.org/, ou `brew install node@22` |
| Docker Desktop | https://www.docker.com/products/docker-desktop/. Escolha a versão do seu processador (**Apple Silicon** para M1, M2, M3 e M4, ou **Intel**) |
| DBeaver Community (opcional, recomendado) | https://dbeaver.io/download/ |

Depois de instalar, abra o **Docker Desktop** e espere aparecer **Engine running**. Confira no terminal:

```bash
git --version
python3 --version
node --version
npm --version
docker --version
```

**Linux (Ubuntu ou Debian)**

Instale o Git, o Python com o `venv` e o curl:

```bash
sudo apt update
sudo apt install git python3 python3-venv curl
```

O Node.js do `apt` costuma ser antigo (no Ubuntu 24.04, é o 18). Instale o 20 ou superior pelo [nvm](https://github.com/nvm-sh/nvm):

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
# feche e abra o terminal
nvm install 22
```

Para o Docker, instale o Docker Engine seguindo https://docs.docker.com/engine/install/ (ou o Docker Desktop para Linux) e libere o seu usuário para usar o Docker sem `sudo`:

```bash
sudo usermod -aG docker $USER
```

Depois desse comando, saia da sessão e entre de novo (ou reinicie o computador). Para conferir, `docker run --rm hello-world` deve funcionar sem `sudo`. Confira as versões como no macOS, acima.

Em outras distribuições, instale os mesmos programas pelo gerenciador de pacotes dela.

#### 0.3. Baixe o repositório

```powershell
cd ~\Documents    # macOS/Linux: cd ~/Documents (ou outra pasta da sua escolha)
git clone https://github.com/nunnowdc/v-energy-grid-360.git
```

No Windows, clone numa pasta de caminho curto, como a `Documents`. O caminho até a pasta do repositório deve ter no máximo 120 caracteres: com mais que isso, o Windows não consegue carregar partes do Python dentro do `backend\.venv`.

Abra a pasta no VS Code: **File > Open Folder...**, escolha `Documents\v-energy-grid-360` e abra um terminal novo (`` Ctrl + ` ``). Ele já começa na raiz do repositório, que é de onde partem os próximos comandos.

A branch `main` é a versão entregue. Para trabalhar com o código mais recente do time, mude para a `dev`:

```powershell
git checkout dev
```

#### 0.4. Separe os dados da Gold

Você precisa do zip da camada Gold (`exports_gold.zip`), que o time compartilha por um canal privado. Ele **não fica no GitHub**, porque tem dados pessoais de clientes.

Copie o zip para a pasta `data/` do repositório. Ela é ignorada pelo Git, então nada do que estiver ali sobe para o GitHub.

- **No jeito rápido**, é só isso: o setup extrai o zip sozinho.
- **No passo a passo manual**, extraia o zip para `data/exports_gold/`:
  1. no Explorador de Arquivos do Windows, clique com o botão direito no zip e escolha **Extrair Tudo...**;
  2. em destino, escreva o caminho da pasta `data\exports_gold` do repositório (por exemplo, `C:\Users\SEU_USUARIO\Documents\v-energy-grid-360\data\exports_gold`) e clique em **Extrair**.

  No macOS e no Linux, a partir da raiz: `python3 -m zipfile -e data/exports_gold.zip data/exports_gold`.

  Se for criada uma subpasta dentro de `exports_gold`, pode deixar: o script procura os CSVs em todas as subpastas de `data/`.

No macOS, o Safari às vezes extrai o zip sozinho ao baixar, e o que aparece em **Downloads** é uma pasta. Nesse caso, copie a pasta inteira para `data/`: nos dois caminhos, os CSVs são encontrados em qualquer subpasta.

### Jeito rápido: setup e iniciar

Depois do passo 0, dois scripts na raiz do repositório fazem todo o resto. Cada um tem uma versão para o Windows (`.ps1`) e outra para o macOS e o Linux (`.sh`), que fazem a mesma coisa:

| | Windows (PowerShell) | macOS e Linux |
|---|---|---|
| Preparar | `powershell -ExecutionPolicy Bypass -File .\setup.ps1` | `bash setup.sh` |
| Ligar o portal | `powershell -ExecutionPolicy Bypass -File .\iniciar.ps1` | `bash iniciar.sh` |

No Windows, o `powershell -ExecutionPolicy Bypass -File` deixa o script rodar só daquela vez, sem mudar nenhuma configuração do Windows. Escrever `.\setup.ps1` direto pode dar o erro "a execução de scripts foi desabilitada neste sistema". No macOS e no Linux, rode com `bash`, não com `sh`, e **sem** `sudo`.

#### Preparar: setup

Rode uma vez para preparar tudo, e de novo depois de cada `git pull`:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1    # macOS/Linux: bash setup.sh
```

O setup faz os passos 1, 2 e 4 a 9 do passo a passo manual:

1. confere o Python, o Node.js e o Docker, e liga o Docker se ele estiver fechado;
2. cria o container do banco e ativa as extensões;
3. cria o ambiente Python e instala as dependências do backend e do agente;
4. cria os três arquivos de configuração;
5. extrai o zip da Gold e carrega a Gold no banco;
6. cria as tabelas da IA e a base de conhecimento do RAG;
7. cria a tabela das ordens de inspeção;
8. instala as dependências do frontend.

Como ele se comporta:

- **Senha:** na primeira vez, ele pede uma senha para o banco. O mais simples é usar só letras e números. Depois, ele lê a senha dos arquivos de configuração.
- **Tempo:** na primeira vez leva de 15 a 30 minutos, quase tudo em downloads (dependências do Python, imagem do banco, modelo do RAG). Nas próximas, um ou dois minutos.
- **Rodar de novo é seguro:** o que já está pronto é pulado. O setup **nunca** apaga as ordens de inspeção nem muda um arquivo de configuração que já existe, só completa o `DATABASE_URL` se ele ainda estiver com o valor do exemplo.
- **Se algo der errado,** ele para com `ERRO:` e diz o que fazer. Corrija e rode de novo: ele continua de onde parou.

| Windows | macOS e Linux | Quando usar |
|---|---|---|
| `-RecarregarGold` | `--recarregar-gold` | Chegou uma Gold nova: troque o zip de `data/` pelo novo e rode o setup com essa opção, por exemplo `bash setup.sh --recarregar-gold` |
| `-Porta 5434` | `--porta 5434` | Na primeira vez, se a porta 5433 já estiver em uso no seu computador |

#### Ligar o agente de IA: uma vez

O setup não tem como criar a chave do LLM. Siga o [passo 3](#3-provedor-de-ia-llm), que preenche o `backend/.env.local` com a chave do OpenRouter ou do 9router. Sem a chave, o portal funciona, mas o agente responde "O serviço de IA está temporariamente indisponível".

#### Ligar o portal: iniciar

Todo dia, para usar o portal:

```powershell
powershell -ExecutionPolicy Bypass -File .\iniciar.ps1    # macOS/Linux: bash iniciar.sh
```

O iniciar:

- liga o Docker e o banco, se estiverem desligados;
- liga o backend, o frontend e, se o agente usa o 9router e ele estiver desligado, o 9router;
- espera tudo responder e abre o portal no navegador, em http://localhost:5173.

Se uma parte já estiver ligada, ele só avisa e não liga de novo.

- **No Windows,** cada parte abre na sua própria janela. Para desligar, feche as janelas **V-Energy - backend** e **V-Energy - frontend** (ou aperte `Ctrl + C` nelas).
- **No macOS e no Linux,** tudo roda no mesmo terminal, que passa a mostrar as mensagens do backend e do frontend (elas também ficam em `.logs/`). Deixe o terminal aberto. Para desligar, aperte `Ctrl + C` nele.

O banco pode continuar ligado.

Depois, confira se tudo funciona com o [passo 10](#10-confira-se-tudo-funciona).

### Passo a passo manual

São os mesmos passos que o setup e o iniciar fazem, um comando por vez.

### 1. Banco de dados

#### 1.1. Crie o container

Escolha uma senha para o banco. Use só letras e números: assim ela entra nas URLs do passo 2 sem precisar de ajuste. Rode, trocando `SUA_SENHA` pela senha escolhida:

```powershell
docker run -d --name postgres-venergy -e POSTGRES_PASSWORD=SUA_SENHA -e POSTGRES_DB=v_energy -p 5433:5432 -v pgdata-v_energy:/var/lib/postgresql pgvector/pgvector:pg18
```

- Na primeira vez, o Docker baixa a imagem do PostgreSQL 18 com o pgvector. No fim, ele mostra um código longo, que é o ID do container.
- A porta no seu computador é a **5433**, para não confundir com um PostgreSQL já instalado no Windows, que usa a 5432 e não tem o pgvector.
- Os dados ficam no volume `pgdata-v_energy`. Desligar o container ou o computador não apaga nada.

Confira se o container está ligado:

```powershell
docker ps
```

A linha do `postgres-venergy` deve mostrar `Up` e `0.0.0.0:5433->5432/tcp`.

#### 1.2. Ative as extensões

```powershell
docker exec postgres-venergy psql -U postgres -d v_energy -c "CREATE EXTENSION IF NOT EXISTS vector;" -c "CREATE EXTENSION IF NOT EXISTS unaccent;"
```

Deve aparecer `CREATE EXTENSION` duas vezes:

- `vector` é a busca por similaridade do RAG do agente;
- `unaccent` deixa o agente comparar nomes sem acento ("Sao Lourenco" encontra "São Lourenço").

#### 1.3. Conecte o DBeaver (opcional)

Com o DBeaver você vê as tabelas e roda as consultas de conferência dos próximos passos.

1. **Database > New Database Connection**, escolha **PostgreSQL** e clique em **Next**.
2. Preencha:

   | Campo | Valor |
   |---|---|
   | Host | `localhost` |
   | Port | `5433` |
   | Database | `v_energy` |
   | Username | `postgres` |
   | Password | a senha do passo 1.1 (marque **Save password**) |

3. Clique em **Test Connection**. Na primeira vez, o DBeaver oferece baixar o driver do PostgreSQL: aceite. Deve aparecer **Connected**.
4. Clique em **Finish**.

Como usar:

- **As tabelas** ficam em **v_energy > Schemas > public > Tables**. Depois de criar ou carregar tabelas, clique na conexão e aperte `F5` para atualizar a lista.
- **Para escrever SQL**, selecione a conexão e abra **SQL Editor > New SQL script** (`Ctrl + ]`).
- **Para rodar**, use `Ctrl + Enter` para a consulta onde está o cursor e `Alt + X` para o script inteiro.

Sem o DBeaver, as mesmas consultas rodam pelo terminal:

```powershell
docker exec postgres-venergy psql -U postgres -d v_energy -c "SELECT count(*) FROM fact_faturamento;"
```

Para abrir um terminal SQL interativo, use `docker exec -it postgres-venergy psql -U postgres -d v_energy`, e saia com `\q`.

### 2. Arquivos de configuração

O projeto lê três arquivos de configuração. Todos ficam fora do Git: **nunca suba senhas nem chaves**.

| Arquivo | Quem lê |
|---|---|
| `.env` (na raiz) | Scripts de carga e de preparação da IA (passos 5 e 6) |
| `backend/.env.local` | Backend e agente de IA |
| `frontend/.env.local` | Frontend |

#### 2.1. `.env` da raiz

No **Explorer** do VS Code, clique com o botão direito numa área vazia, abaixo dos arquivos, escolha **New File...** e dê o nome `.env`. Escreva nele uma linha, com a senha do passo 1.1, e salve (`Ctrl + S`):

```dotenv
DATABASE_URL=postgresql://postgres:SUA_SENHA@localhost:5433/v_energy
```

#### 2.2. `backend/.env.local`

Crie o arquivo a partir do exemplo:

```powershell
cp backend/.env.example backend/.env.local
```

Abra o `backend/.env.local` e troque a linha do `DATABASE_URL` por esta, com a senha do passo 1.1:

```dotenv
DATABASE_URL=postgresql+psycopg://postgres:SUA_SENHA@localhost:5433/v_energy
```

Repare no `+psycopg`, que não existe no `.env` da raiz: é o nome do driver que o backend usa. As outras linhas podem ficar como estão. As chaves de LLM são preenchidas no passo 3.

Se a senha tiver caracteres especiais, escreva-os codificados nas duas URLs:

| Caractere | Escreva |
|---|---|
| `#` | `%23` |
| `@` | `%40` |
| `%` | `%25` |
| `/` | `%2F` |
| `:` | `%3A` |

#### 2.3. `frontend/.env.local`

```powershell
cp frontend/.env.example frontend/.env.local
```

Os valores do exemplo já servem:

- `VITE_PERFIL_TESTE` define o perfil do usuário de teste enquanto o login não existe. Os perfis são `DIRETORIA`, `ATENDIMENTO`, `PERDAS`, `OPERACAO` e `ADMIN_TI`, e o `ADMIN_TI` vê todas as telas.
- `VITE_USAR_DADOS_EXEMPLO=true` mostra dados de exemplo nas rotas que o backend ainda não tem (hoje, só a Continuidade).

Depois de mudar qualquer `.env`, reinicie o que lê o arquivo (backend ou frontend).

### 3. Provedor de IA (LLM)

O agente de IA precisa de pelo menos um provedor de LLM. Sem nenhum, o resto do portal funciona normalmente, e o agente responde "O serviço de IA está temporariamente indisponível".

O agente tenta primeiro o **OpenRouter** e, se ele falhar ou não estiver configurado, usa o **9router**. Configure um dos dois, ou os dois.

#### Opção A: OpenRouter (na nuvem)

1. Entre em https://openrouter.ai e crie uma conta.
2. Em https://openrouter.ai/settings/keys, clique em **Create Key** e copie a chave. Ela só aparece uma vez.
3. Em https://openrouter.ai/models, escolha um modelo e copie o ID dele, no formato `provedor/modelo`. Os modelos terminados em `:free` não gastam crédito, mas têm limite de pedidos por dia.
4. No `backend/.env.local`, preencha:

   ```dotenv
   OPENROUTER_API_KEY=sua-chave-do-openrouter
   MODELO_LLM_PRIMARIO=provedor/modelo
   ```

#### Opção B: 9router (roteador local, usado pelo time)

O 9router roda na sua máquina, recebe os pedidos do agente e repassa para os provedores que você conectar. Quando um provedor falha ou fica sem cota, ele passa para o próximo.

1. Instale (uma vez só):

   ```powershell
   npm install -g 9router
   ```

2. Ligue o 9router num **terminal só para ele** e deixe esse terminal aberto:

   ```powershell
   9router --host 127.0.0.1
   ```

   O `--host 127.0.0.1` deixa o 9router acessível só no seu computador. Sem ele, qualquer um na mesma rede (Wi-Fi da faculdade, por exemplo) alcança o 9router. O iniciar já liga o 9router assim.

3. Abra o painel em http://localhost:20128/dashboard.
4. Em **Providers**, conecte pelo menos um provedor. Por exemplo, para o Gemini, crie uma chave gratuita em https://aistudio.google.com/apikey e adicione no painel.
5. Em **Combos**, clique em **Create New**, dê o nome `venergy`, adicione os modelos em ordem de preferência e salve.
6. Copie a API key que o painel mostra, junto do endereço `http://localhost:20128/v1`.
7. No `backend/.env.local`, preencha:

   ```dotenv
   NINEROUTER_API_KEY=sua-chave-do-9router
   NINEROUTER_BASE_URL=http://localhost:20128/v1/chat/completions
   MODELO_LLM_FALLBACK=venergy
   ```

Para conferir se o 9router está respondendo, rode o comando abaixo. A lista deve incluir o `venergy`:

```powershell
curl.exe http://localhost:20128/v1/models
```

### 4. Ambiente Python

Um ambiente virtual só, em `backend/.venv`, serve para o backend, o agente de IA e os scripts dos passos 5 e 6, porque o backend importa o agente da pasta `ai-agent/`.

```powershell
python -m venv backend/.venv    # macOS/Linux: python3 -m venv backend/.venv
backend\.venv\Scripts\Activate.ps1    # macOS/Linux: source backend/.venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt -r ai-agent/requirements.txt
```

- Depois da segunda linha, o terminal mostra `(.venv)` no começo. É assim que você sabe que o ambiente está ativo.
- Se o PowerShell disser que o `Activate.ps1` não pode ser carregado, libere os scripts uma vez com `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, abra um terminal novo e rode a segunda linha de novo.
- A instalação leva de 5 a 15 minutos: o agente usa o `torch` e o `sentence-transformers`, que são grandes.
- **No Linux com processador Intel ou AMD,** antes da última linha, rode `python -m pip install torch --index-url https://download.pytorch.org/whl/cpu`. Sem isso, o `pip` baixa o `torch` com suporte a placa de vídeo NVIDIA, alguns GB a mais que o RAG não usa.
- **No Mac com processador Intel,** acrescente `"numpy<2"` ao fim da última linha: o último `torch` para esses Macs só funciona com o `numpy` 1.x.
- **Os passos 5 a 8 precisam do ambiente ativo.** Em todo terminal novo, ative de novo com `backend\.venv\Scripts\Activate.ps1`, a partir da raiz.
- Opcional: no VS Code, `Ctrl + Shift + P` > **Python: Select Interpreter** > escolha o `backend\.venv`. Com a extensão Python instalada, os terminais novos já abrem com o ambiente ativo.

Para conferir a instalação:

```powershell
python -c "import fastapi, langgraph, sentence_transformers; print('ok')"
```

### 5. Carga da Gold

Com os CSVs extraídos em `data/exports_gold/` (passo 0.4) e o ambiente ativo:

```powershell
python scripts/carga_banco_local.py
```

- O script cria as 15 tabelas da Gold e carrega cerca de 5 milhões de linhas. Leva de 1 a 3 minutos.
- Depois da carga, ele roda o **Data Quality Gate**: 29 verificações do contrato da Gold, como chaves únicas, nenhum registro órfão e totais que fecham. Deve aparecer `Data Quality Gate aprovado com sucesso!`.
- No fim, aparece `Carga concluída com sucesso no PostgreSQL!` e `Total de linhas importadas: 4,997,681`.
- Se aparecer `FALHA NO DATA QUALITY GATE`, a Gold está incompleta ou desatualizada. Peça ao time a versão mais recente e repita a carga.
- Deixe só uma cópia dos CSVs da Gold em `data/`. Com duas, o script não avisa e pode carregar a antiga.
- Não use as opções `--reset-data` e `--update-release`. Elas apagam **todos** os CSVs de `data/`, inclusive os dados brutos do case, e tentam baixar a Gold do GitHub.

Para conferir (no DBeaver ou no terminal):

```sql
SELECT count(*) FROM fact_faturamento;   -- 2152336
SELECT count(*) FROM dim_unidade_consumidora;   -- 45000
```

### 6. Tabelas e base de conhecimento da IA

Com o ambiente ativo, a partir da raiz:

```powershell
python ai-agent/scripts/criar_tabelas_ia.py
cd ai-agent
python -m scripts.migracoes.migracao_colunas_opcionais_auditoria_agente
python -m scripts.migracoes.migracao_templates_cache_filtro_texto_sem_acento
python -m src.rag.indexar_tudo
cd ..
```

| Comando | O que faz | Termina com |
|---|---|---|
| `criar_tabelas_ia.py` | Cria as 4 tabelas do agente: base de conhecimento (`tb_conhecimento_vetorial`), auditoria (`tb_auditoria_agente`), perguntas certificadas (`tb_cache_perguntas_certificadas`) e insights (`tb_insights_tela`) | `Tabelas criadas com sucesso.` |
| `migracao_colunas_opcionais_auditoria_agente` | Acrescenta à auditoria o usuário, o perfil, as tentativas de SQL e os trechos do RAG usados | `Migração concluída com sucesso.` |
| `migracao_templates_cache_filtro_texto_sem_acento` | Grava as perguntas certificadas, que respondem sem gerar SQL novo | `Migração concluída com sucesso.` |
| `indexar_tudo` | Coloca os documentos do projeto (glossário, dicionário da Gold, regras do setor elétrico, relatórios da Engenharia de Dados) na base de conhecimento do RAG | `INDEXAÇÃO COMPLETA CONCLUÍDA COM SUCESSO` |

- Na primeira vez, o `indexar_tudo` baixa o modelo de embeddings (cerca de 500 MB), então precisa de internet. As linhas `INFO` e os avisos do download são normais.
- Os quatro comandos podem rodar de novo sem duplicar nada.

Para conferir:

```sql
SELECT count(*) FROM tb_conhecimento_vetorial;   -- mais de 200 trechos
```

### 7. Tabela das ordens de inspeção

Na Fila de inspeção, o analista de perdas gera ordens de inspeção para as UCs suspeitas e acompanha cada uma até a conclusão. As ordens ficam na tabela `ordens_inspecao`, que **não vem com a Gold**: crie uma vez, por um dos dois caminhos.

**Pelo terminal:**

```powershell
docker cp backend/sql/ordens_inspecao.sql postgres-venergy:/tmp/ordens_inspecao.sql
docker exec postgres-venergy psql -U postgres -d v_energy -v ON_ERROR_STOP=1 -f /tmp/ordens_inspecao.sql
```

O primeiro comando copia o arquivo para dentro do container, e o segundo executa o arquivo. A saída deve ser `BEGIN`, `CREATE TABLE`, `CREATE INDEX` e `COMMIT`.

**Pelo DBeaver:**

1. **File > Open File...** e escolha `backend/sql/ordens_inspecao.sql`.
2. Na barra do editor, escolha a conexão `v_energy` como fonte de dados ativa (**Active datasource**, `Ctrl + 9`).
3. Rode o script inteiro com `Alt + X`.

<details>
<summary>O que o script cria</summary>

O arquivo [`backend/sql/ordens_inspecao.sql`](backend/sql/ordens_inspecao.sql) é a versão oficial. Se ele mudar, vale o arquivo.

```sql
BEGIN;

CREATE TABLE ordens_inspecao (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_uc TEXT NOT NULL CHECK (id_uc ~ '^UC[0-9]{6}$'),
    status TEXT NOT NULL CHECK (status IN ('ABERTA', 'EM_CAMPO', 'CONCLUIDA', 'CANCELADA')),
    resultado TEXT,
    criada_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizada_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    concluida_em TIMESTAMPTZ,
    CONSTRAINT ordem_conclusao_coerente CHECK (
        (status = 'CONCLUIDA'
         AND resultado IS NOT NULL
         AND resultado IN ('IRREGULARIDADE_CONFIRMADA', 'SEM_IRREGULARIDADE')
         AND concluida_em IS NOT NULL)
        OR
        (status <> 'CONCLUIDA' AND resultado IS NULL AND concluida_em IS NULL)
    )
);

CREATE UNIQUE INDEX ordens_inspecao_uc_ativa_uidx
    ON ordens_inspecao (id_uc)
    WHERE status IN ('ABERTA', 'EM_CAMPO');

COMMIT;
```

- **Situações:** cada ordem está `ABERTA`, `EM_CAMPO`, `CONCLUIDA` ou `CANCELADA`.
- **Resultado:** só a ordem concluída tem resultado (`IRREGULARIDADE_CONFIRMADA` ou `SEM_IRREGULARIDADE`) e data de conclusão.
- **Uma ativa por UC:** o índice único impede duas ordens abertas ou em campo para a mesma UC.
- **Número:** o portal mostra o `id` como `OI-00001`, `OI-00002`...

</details>

- O script roda uma vez só. Se a tabela já existe, ele para com `relation "ordens_inspecao" already exists` e não muda nada. De propósito, ele não apaga nem recria a tabela (veja [`backend/README.md`](backend/README.md)).
- No Git Bash (não no PowerShell), comece o segundo comando com `MSYS_NO_PATHCONV=1 `, senão ele troca o `/tmp/...` por um caminho do Windows.

Para conferir (deve dar `0`, porque ainda não há ordens):

```sql
SELECT count(*) FROM ordens_inspecao;
```

**Para zerar as ordens** (por exemplo, depois de testar a Fila de inspeção), rode o comando abaixo. Ele apaga **todas** as ordens, sem volta, e a numeração recomeça em `OI-00001`. A fila de UCs suspeitas vem da Gold e não muda.

```sql
TRUNCATE ordens_inspecao RESTART IDENTITY;
```

Pelo terminal:

```powershell
docker exec postgres-venergy psql -U postgres -d v_energy -c "TRUNCATE ordens_inspecao RESTART IDENTITY;"
```

### 8. Backend

Com o ambiente ativo:

```powershell
cd backend
python -m app.main
```

- Quando aparecer `Uvicorn running on http://127.0.0.1:8000`, a API está no ar.
- **Deixe esse terminal aberto.** Fechar o terminal, ou apertar `Ctrl + C`, desliga a API.
- Para conferir, abra http://127.0.0.1:8000/api/health no navegador. Deve aparecer `{"status":"ok"}`.
- As rotas ficam documentadas em http://127.0.0.1:8000/api/docs, onde também dá para testar cada uma.

### 9. Frontend

Abra **outro terminal** (clique no `+` do terminal do VS Code). Ele já começa na raiz:

```powershell
cd frontend
npm ci
npm run dev
```

- O `npm ci` baixa as dependências e só é preciso na primeira vez e quando o `package-lock.json` mudar. Ele instala exatamente as versões do `package-lock.json`, sem mudar o arquivo. Com o `npm install`, uma versão do npm diferente da do time pode regravar o `package-lock.json`, e ele aparece como modificado no Git.
- Quando aparecer `Local: http://localhost:5173/`, abra esse endereço no navegador.
- **Deixe esse terminal aberto também.** O frontend chama o backend pela porta 8000, então os dois precisam estar ligados.

### 10. Confira se tudo funciona

Com o perfil `ADMIN_TI` (o padrão), todas as telas aparecem no menu:

| Tela | O que deve aparecer |
|---|---|
| Indicadores | KPIs com valores, não "Algo deu errado no servidor" |
| Receita | A ponte de receita entre os dois períodos e a tabela por município |
| Visão 360 | Busque `UC100000`: aparecem o cadastro, o consumo e as faturas da UC |
| Fila de inspeção | A lista de UCs suspeitas. Se gerar ordens para testar, zere depois (passo 7) |
| Continuidade | Dados de exemplo, até a rota real existir no backend |
| Agente de IA (botão no topo) | Pergunte "Qual o faturamento de Recife em 2024?": a resposta traz cerca de R$ 68,56 milhões (68.560.067,39), e a tela vai para os Indicadores de Recife em 2024 |

### Dia a dia

O jeito mais fácil é o iniciar:

```powershell
powershell -ExecutionPolicy Bypass -File .\iniciar.ps1    # macOS/Linux: bash iniciar.sh
```

Sem ele, ligue as partes, cada uma no seu terminal:

1. Abra o Docker Desktop. Se o container não ligar sozinho, rode `docker start postgres-venergy`.
2. Se usa o 9router, rode `9router` num terminal e deixe aberto.
3. **Backend:**

   ```powershell
   backend\.venv\Scripts\Activate.ps1    # macOS/Linux: source backend/.venv/bin/activate
   cd backend
   python -m app.main
   ```

4. **Frontend**, em outro terminal:

   ```powershell
   cd frontend
   npm run dev
   ```

Para desligar, aperte `Ctrl + C` em cada terminal. O banco pode continuar ligado; se quiser desligar, rode `docker stop postgres-venergy`.

Depois de um `git pull`:

1. rode o setup de novo. Ele instala só as dependências que mudaram e pula o resto;
2. reinicie o backend, porque ele não recarrega sozinho. No Windows, feche a janela dele e rode o iniciar; no macOS e no Linux, aperte `Ctrl + C` no terminal do iniciar e rode o iniciar de novo. Sem o iniciar, aperte `Ctrl + C` no terminal do backend e rode `python -m app.main` de novo.

Sem o setup:

- se o `frontend/package-lock.json` mudou, rode `npm ci` em `frontend/`;
- se um `requirements.txt` mudou, rode de novo a última linha do passo 4.

### Gold nova

Quando a Engenharia de Dados publicar uma Gold nova:

- **Com o setup:** troque o zip de `data/` pelo novo, rode `powershell -ExecutionPolicy Bypass -File .\setup.ps1 -RecarregarGold` (macOS/Linux: `bash setup.sh --recarregar-gold`) e reinicie o backend.
- **Sem o setup:**

1. apague a pasta `data/exports_gold/`, com a Gold antiga;
2. extraia o zip novo para `data/exports_gold/`, como no passo 0.4;
3. com o ambiente ativo, rode de novo o passo 5;
4. reinicie o backend.

A carga apaga e recria só as 15 tabelas da Gold. As ordens de inspeção e as tabelas da IA continuam como estavam.

### Recomeçar o banco do zero

Os comandos abaixo apagam o banco inteiro: Gold, tabelas da IA e **todas as ordens de inspeção**.

```powershell
docker rm -f postgres-venergy
docker volume rm pgdata-v_energy
```

Depois, rode o setup (ele cria o container de novo com a senha que já está no `.env`), ou refaça os passos 1, 5, 6 e 7. Os arquivos de configuração e o ambiente Python continuam valendo.

### Testes

Com o ambiente Python ativo:

| Parte | Onde | Comando |
|---|---|---|
| Frontend | `frontend/` | `npm run lint`, `npm test` e `npm run build` |
| Backend | `backend/` | `python -m pytest -q` (alguns testes usam o banco local; veja [`backend/README.md`](backend/README.md)) |
| Agente de IA | raiz | `python -m pytest ai-agent/tests ai-agent/security/tests` (veja [`ai-agent/tests/README.md`](ai-agent/tests/README.md)) |
| Validador de qualidade da Gold | raiz | `python -m pytest tests` (o Quality Gate em si já roda em toda carga, no passo 5) |

### Problemas comuns

| O que aparece | Causa | O que fazer |
|---|---|---|
| `a execução de scripts foi desabilitada neste sistema` ao rodar o setup ou o iniciar | O script foi chamado direto (`.\setup.ps1`) | Use o comando completo: `powershell -ExecutionPolicy Bypass -File .\setup.ps1` |
| O setup para com `Não foi possível entrar no banco com essa senha` | A senha digitada, ou a do `.env`, é diferente da usada quando o container foi criado | Rode de novo com a senha certa. Se não lembrar, recomece o banco do zero |
| O setup para com `port is already allocated` | A porta 5433 já está em uso | `powershell -ExecutionPolicy Bypass -File .\setup.ps1 -Porta 5434` (macOS/Linux: `bash setup.sh --porta 5434`) |
| O setup para com `O caminho da pasta do repositório é longo demais`, ou aparece `Filename too long` ou `DLL load failed` | No Windows, o caminho até a pasta tem mais de 120 caracteres | Mova a pasta para um lugar mais curto (ex.: `Documents`) e rode o setup de novo |
| O setup para com `o projeto precisa do Python x64` | No Windows, o Python instalado é o ARM ou o de 32 bits | Instale o Python pelo "Windows installer (64-bit)" (passo 0.2) e rode de novo |
| `python` abre a Microsoft Store | O atalho do Windows vem antes do Python instalado | Passo 0.2: desligue os aliases de execução do Python |
| `Rode com: bash setup.sh`, ou erros de sintaxe ao rodar o `setup.sh` | O script foi chamado com `sh` | Use `bash setup.sh` |
| O setup para com `está sem o módulo venv` | No Ubuntu e no Debian, o `venv` vem num pacote separado | Rode o `sudo apt install` que a mensagem mostra e rode o setup de novo |
| O setup para com `precisa do 20 ou superior` | O Node.js é antigo (o do `apt` costuma ser) | Instale o Node 22 pelo `nvm` (passo 0.2) |
| O setup para com `Seu usuário não tem permissão para usar o Docker`, ou aparece `permission denied ... docker.sock` | No Linux, o usuário não está no grupo `docker` | `sudo usermod -aG docker $USER`, saia da sessão e entre de novo |
| O setup para com `precisa do Python 3.11 ou 3.12` | Mac com processador Intel e Python 3.13 ou mais novo | Instale o Python 3.12 (passo 0.2) e rode de novo |
| `error during connect` ou `Cannot connect to the Docker daemon` | O Docker está fechado ou ainda iniciando | Abra o Docker Desktop e espere o **Engine running**. No Linux com Docker Engine: `sudo systemctl start docker` |
| `container name "/postgres-venergy" is already in use` | O container já existe | Ligue com `docker start postgres-venergy`, ou recomece do zero |
| `port is already allocated` | A porta 5433 já está em uso | Troque para `-p 5434:5432` no `docker run` e use a 5434 nas duas URLs do passo 2 |
| `password authentication failed` | A senha das URLs é diferente da do `docker run` | Confira o `.env` e o `backend/.env.local`. A senha só é gravada quando o volume é criado: para trocar, recomece do zero |
| `extension "vector" is not available` | A URL aponta para outro PostgreSQL (porta 5432) | Use a porta 5433 nas duas URLs |
| `Nenhum CSV correspondente às tabelas Gold foi identificado` | O zip não foi extraído | Extraia o zip para `data/exports_gold/` (passo 0.4) |
| `FALHA NO DATA QUALITY GATE` | A Gold carregada está incompleta ou desatualizada | Peça a Gold mais recente ao time e repita o passo 5 |
| `Activate.ps1 não pode ser carregado` | Política de execução do PowerShell | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` e um terminal novo |
| `ModuleNotFoundError` ao rodar um script ou o backend | O ambiente Python não está ativo | `backend\.venv\Scripts\Activate.ps1` a partir da raiz (macOS/Linux: `source backend/.venv/bin/activate`) |
| `relation "ordens_inspecao" does not exist`, ou a Fila de inspeção dá erro ao listar ou gerar ordens | Falta a tabela das ordens | Passo 7 |
| `function unaccent(...) does not exist` no passo a passo do agente | Falta a extensão `unaccent` | Passo 1.2 |
| O agente responde "O serviço de IA está temporariamente indisponível" | Não há chave de LLM no `backend/.env.local`, ou o 9router está fechado | Passo 3, depois reinicie o backend |
| As telas mostram "Algo deu errado no servidor" ou "Não foi possível conectar ao servidor" | O backend está desligado | Passo 8 |
| `error while attempting to bind on address ('127.0.0.1', 8000)` | Já há um backend rodando em outro terminal | Feche o outro terminal ou aperte `Ctrl + C` nele |

## Suposições e decisões do time

O que o time precisou decidir ou supor por conta própria, registrado aqui como o case pede. Os itens marcados com ⚠️ ainda estão em alinhamento.

### Perfis de acesso

| Perfil (`role`) | Quem usa | Telas |
|---|---|---|
| `DIRETORIA` | Diretoria, incluindo o diretor comercial | Indicadores, Receita, Continuidade |
| `ATENDIMENTO` | Atendentes do call center | Visão 360 |
| `PERDAS` | Gerente e analistas de perdas | Fila de inspeção, Visão 360 |
| `OPERACAO` | Gerência de operação | Continuidade |
| `ADMIN_TI` | Conta técnica da TI e dos desenvolvedores | Todas, mais a criação de contas |

- Diretor e diretor comercial usam o mesmo perfil, `DIRETORIA`.
- A Diretoria também vê a Continuidade, porque acompanha a qualidade do serviço, que gera multas regulatórias.
- Perdas também vê a Visão 360, para investigar a unidade consumidora suspeita.
- A Diretoria não vê a Visão 360 (dados pessoais de clientes) nem a Fila de inspeção (ações operacionais), seguindo a LGPD e o princípio do menor privilégio.
- `ADMIN_TI` não é um cargo do case: é uma conta técnica para administrar o portal.
- As contas são pré-cadastradas pelo `ADMIN_TI`, sem cadastro público. A troca de senha é opcional.
- O chat da IA fica disponível para todos os perfis e responde só com dados agregados, nunca com dados pessoais.

### Dados e telas

- **Receita:** sem escolha, compara o primeiro ano da base (jul/2022 a jun/2023) com os últimos 12 meses (jul/2025 a jun/2026), a pergunta do case. Os períodos podem ser trocados no filtro, e a conta é a mesma da Gold, refeita a partir da receita mensal.
- **Volume:** é o consumo medido nas leituras, porque as faturas não trazem kWh.
- **"Hoje":** é o último mês da base (jun/2026), nunca a data do computador.
- **Períodos:** Indicadores, Receita e Continuidade comparam um "Período base" com um "Comparado com", de mesmo tamanho (1 a 24 meses), e os KPIs mostram sempre o comparado. Sem escolha, Indicadores e Continuidade mostram os últimos 12 meses contra os 12 anteriores. Quando os dois períodos cobrem meses diferentes do ano, a tela avisa que parte da variação pode ser da estação.
- **Gold:** no MVP, é um retrato fixo carregado no PostgreSQL local, sem atualização.
- **Decomposição preço × volume:** usa a fórmula publicada na Gold: efeito-volume = (kWh P1 − kWh P0) × preço P0, e efeito-preço = (preço P1 − preço P0) × kWh P1. A decomposição de Shapley do diagnóstico fica fora do MVP.
- **Filtros:** um valor por filtro. A Continuidade filtra por alimentador e causa: o município limita os alimentadores mostrados, e a causa filtra só as ocorrências. DEC e FEC são sempre do alimentador inteiro, nunca de um município ou de uma causa.
- ⚠️ **Motivo da suspeita:** a Fila de inspeção ainda não filtra por motivo, porque a Gold guarda vários motivos no mesmo texto. Depende de uma lista de motivos da Engenharia de Dados.
- **Dados de exemplo:** enquanto o backend não tem todas as rotas, o frontend usa dados de exemplo (MSW), só no `npm run dev`. Eles nunca vêm da base real (veja `frontend/README.md`).

## Fluxo de trabalho (Git Flow)

### Branches

| Branch | Função |
|---|---|
| `main` | Versão estável e entregável. Só recebe código vindo da `dev`. |
| `dev` | Integração do trabalho do time. Recebe as branches de task. |
| `feature/*`, `fix/*`, `refactor/*`, `docs/*` | Uma branch por task, sempre criada a partir da `dev`. |

```
feature/minha-task ──PR──► dev ──PR──► main
```

### Nomenclatura das branches de task

- `feature/<descricao>`: nova funcionalidade (ex.: `feature/camada-silver`)
- `fix/<descricao>`: correção de bug (ex.: `fix/calculo-dec-fec`)
- `refactor/<descricao>`: melhoria no código sem mudar o comportamento (ex.: `refactor/funcoes-limpeza-silver`)
- `docs/<descricao>`: documentação (ex.: `docs/dicionario-de-dados`)

Use letras minúsculas e hífens, sem espaços nem acentos.

### Passo a passo de uma task

1. Atualize a `dev` e crie a sua branch a partir dela:
   ```bash
   git checkout dev
   git pull
   git checkout -b feature/minha-task
   ```
2. Faça commits pequenos e descritivos:
   ```bash
   git add .
   git commit -m "Descreve o que foi feito"
   ```
3. Envie a branch para o GitHub:
   ```bash
   git push -u origin feature/minha-task
   ```
4. Abra um **Pull Request** de `feature/minha-task` para a **`dev`**.
5. Depois de aprovado, faça o merge e apague a branch da task.

### Regras de Pull Request

- Ninguém faz commit direto na `main` nem na `dev`: tudo entra via PR.
- Todo PR precisa de **no mínimo 2 aprovações** antes do merge.
- Quando a `dev` estiver estável, abre-se um PR da **`dev` para a `main`**, que segue a mesma regra de 2 aprovações.
- Antes de abrir o PR, atualize sua branch com a `dev` (`git pull origin dev`) e resolva eventuais conflitos.
