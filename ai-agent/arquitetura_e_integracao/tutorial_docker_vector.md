# Postgres + pgvector no Docker (V-Energy Grid 360)

Este guia sobe um PostgreSQL já com a extensão **pgvector** dentro de um container Docker, para o módulo de IA (RAG) do projeto. Não precisa instalar o Postgres no Windows nem compilar nada.

> **Por que Docker?** O instalador do Postgres para Windows não traz o pgvector. A imagem `pgvector/pgvector` já vem com a extensão pronta.

Todos os comandos abaixo funcionam no **Prompt de Comando (cmd)** e no **PowerShell**. Cada comando deve ser colado **em uma linha só**.

---

## 1. Pré-requisitos

- **Docker Desktop** instalado: https://www.docker.com/products/docker-desktop/
- **Python 3.10+** com as bibliotecas do projeto:

```bat
pip install psycopg2-binary python-dotenv
```

Abra o Docker Desktop e espere ele indicar que está rodando (ícone da baleia estável).

Confira no terminal:

```bat
docker --version
docker ps
```

Se o `docker ps` mostrar uma tabela (mesmo vazia), o Docker está funcionando. Se der erro de conexão com o daemon, o Docker Desktop ainda não terminou de iniciar.

---

## 2. Verificar se a porta 5432 já está em uso

Muitas máquinas já têm um Postgres instalado no Windows, ouvindo na porta **5432**. Se o container usar a mesma porta, seus scripts vão conectar no Postgres do Windows (que **não tem pgvector**) e o `CREATE EXTENSION vector` vai falhar.

Para evitar isso, **usamos a porta 5433 no seu computador**. Não precisa checar nada, basta seguir o guia com a 5433.

---

## 3. Criar o container

Troque `SUA_SENHA` pela senha que a equipe vai usar (ela não pode ter espaços):

```bat
docker run -d --name postgres-venergy -e POSTGRES_PASSWORD=SUA_SENHA -e POSTGRES_DB=v_energy -p 5433:5432 -v pgdata-v_energy:/var/lib/postgresql pgvector/pgvector:pg18
```

O que cada parte faz:

| Parte | Significado |
|---|---|
| `--name postgres-venergy` | nome do container |
| `-e POSTGRES_PASSWORD=...` | senha do usuário `postgres` |
| `-e POSTGRES_DB=v_energy` | cria o banco `v_energy` automaticamente |
| `-p 5433:5432` | porta **5433** do seu PC leva à porta 5432 do container |
| `-v pgdata-v_energy:/var/lib/postgresql` | guarda os dados num volume (não se perdem se o container for apagado) |
| `pgvector/pgvector:pg18` | imagem do Postgres 18 com pgvector |

**Atenção:** precisa haver um **espaço** entre a senha e o `-p`. Sem ele, o Docker entende errado o comando e mostra `Unable to find image '5432:5432'`.

Se aparecer `container name "/postgres-venergy" is already in use`, remova o antigo e rode de novo:

```bat
docker rm -f postgres-venergy
```

---

## 4. Conferir se subiu

```bat
docker ps
```

Na linha do `postgres-venergy` deve aparecer `Up` e `0.0.0.0:5433->5432/tcp`.

Se o container não aparecer ou cair logo depois:

```bat
docker logs postgres-venergy
```

---

## 5. Ativar o pgvector no banco

```bat
docker exec -it postgres-venergy psql -U postgres -d v_energy -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

Deve responder `CREATE EXTENSION`. Para confirmar a versão instalada:

```bat
docker exec -it postgres-venergy psql -U postgres -d v_energy -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"
```

Resultado esperado:

```
 extname | extversion
---------+------------
 vector  | 0.8.7
```

> A extensão é **por banco**. Se você criar outro banco, precisa rodar o `CREATE EXTENSION` nele também.

---

## 6. Configurar o `.env`

Na raiz do projeto, crie (ou edite) o arquivo `.env`:

```dotenv
DATABASE_URL=postgresql://postgres:SUA_SENHA@localhost:5433/v_energy
```

Pontos de atenção:

- A porta é **5433**, não 5432.
- A senha é a mesma usada no `docker run`.
- Se algum outro `.env` ou arquivo do código tiver a porta `5432` fixa (por exemplo na pasta do backend), troque também.
- Feche e abra o terminal depois de editar, para o programa ler o `.env` novo.

---

## 7. Rodar os scripts do projeto

Na pasta do projeto, nesta ordem:

```bat
python carga_banco_local.py
python criar_tabelas_ia.py
```

O segundo script cria as tabelas do módulo de IA, incluindo `tb_conhecimento_vetorial` (com a coluna `vector(384)`), `tb_auditoria_agente`, `tb_cache_perguntas_certificadas` e `tb_insights_tela`. Deve terminar com `Tabelas criadas com sucesso.`

Para listar as tabelas criadas:

```bat
docker exec -it postgres-venergy psql -U postgres -d v_energy -c "\dt"
```

---

## 8. Usar o banco no dia a dia

O Docker Desktop precisa estar aberto e o container ligado.

| O que fazer                   | Comando                                                         |
| ----------------------------- | --------------------------------------------------------------- |
| Ver containers ligados        | `docker ps`                                                     |
| Ver todos (inclusive parados) | `docker ps -a`                                                  |
| Ligar o banco                 | `docker start postgres-venergy`                                 |
| Desligar o banco              | `docker stop postgres-venergy`                                  |
| Ver logs                      | `docker logs postgres-venergy`                                  |
| Abrir o terminal SQL          | `docker exec -it postgres-venergy psql -U postgres -d v_energy` |

Depois de reiniciar o computador, abra o Docker Desktop e rode `docker start postgres-venergy`.

### Conexão em Python

```python
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(os.getenv("DATABASE_URL"))
with conn.cursor() as cur:
    cur.execute("SELECT version();")
    print(cur.fetchone())
```

### Conexão no DBeaver / pgAdmin

| Campo | Valor |
|---|---|
| Host | `localhost` |
| Porta | `5433` |
| Banco | `v_energy` |
| Usuário | `postgres` |
| Senha | a definida no `docker run` |

### Se o código roda dentro de outro container

Nesse caso `localhost` aponta para o próprio container. Use `host.docker.internal` no lugar de `localhost` (mantendo a porta 5433). Scripts rodando direto no Windows não precisam disso.

---

## 9. Problemas comuns

| Erro | Causa | Solução |
|---|---|---|
| `Unable to find image '5432:5432'` | faltou espaço antes do `-p` | refazer o comando com espaço entre a senha e `-p` |
| `extension "vector" is not available` | o script está conectando em outro Postgres (porta 5432) | conferir se o `.env` usa `5433` e reiniciar o terminal |
| `container name ... is already in use` | já existe um container com esse nome | `docker rm -f postgres-venergy` e rodar o `docker run` de novo |
| `port is already allocated` | a 5433 está em uso | trocar para outra porta (ex.: `-p 5434:5432`) e ajustar o `.env` |
| `password authentication failed` | senha diferente da usada na criação do volume | usar a senha original, ou recriar o volume (seção 10) |
| `Cannot connect to the Docker daemon` | Docker Desktop fechado | abrir o Docker Desktop e esperar iniciar |
| Container sobe e cai | erro de inicialização | `docker logs postgres-venergy` |

> A senha só é gravada na **primeira** criação do volume. Mudar o `POSTGRES_PASSWORD` num `docker run` seguinte, com o volume já existente, não altera a senha.

---

## 10. Recomeçar do zero (apaga todos os dados)

```bat
docker stop postgres-venergy
docker rm postgres-venergy
docker volume rm pgdata-v_energy
```

Depois, volte ao passo 3.

---

## Resumo rápido

```bat
docker run -d --name postgres-venergy -e POSTGRES_PASSWORD=SUA_SENHA -e POSTGRES_DB=v_energy -p 5433:5432 -v pgdata-v_energy:/var/lib/postgresql pgvector/pgvector:pg18
docker exec -it postgres-venergy psql -U postgres -d v_energy -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

`.env`:

```dotenv
DATABASE_URL=postgresql://postgres:SUA_SENHA@localhost:5433/v_energy
```

```bat
python carga_banco_local.py
python criar_tabelas_ia.py
```
