# API do V-Energy Grid 360

## Instalação

Requer Python 3.11 ou superior. A partir de `backend/`:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Se já existe um ambiente virtual em `../.venv`, instale as dependências com
`../.venv/bin/python -m pip install -r requirements.txt` e inicie com
`../.venv/bin/python -m app.main`.

## Configuração local

Copie o exemplo para o arquivo privado do backend, depois ajuste `DATABASE_URL` para
o seu PostgreSQL Gold local:

```bash
cp -n .env.example .env.local
```

O exemplo usa a autenticação local pelo usuário do sistema, sem senha. Se a sua
instalação exigir host, porta e credenciais, configure-os **somente** em
`.env.local`, usando o formato `postgresql+psycopg://USUARIO:SENHA@HOST:5432/BANCO`.
O arquivo é ignorado pelo Git; não coloque credenciais em `.env.example`.

`app/core/config.py` lê `backend/.env.local` automaticamente, mesmo quando o comando
é iniciado de outro diretório. Variáveis já definidas no ambiente do sistema têm
prioridade. Reinicie a API após mudar a configuração local.

## Execução

```bash
.venv/bin/python -m app.main
```

A API usa `127.0.0.1:8000` por padrão. Consulte `GET http://127.0.0.1:8000/api/health`,
`http://127.0.0.1:8000/api/docs`, `http://127.0.0.1:8000/api/redoc` e
`http://127.0.0.1:8000/api/openapi.json`.

`CORS_ORIGINS` aceita origens HTTP locais separadas por vírgula; por padrão, inclui
`localhost:5173` e `127.0.0.1:5173`.

## Ordens de inspeção: estrutura operacional pendente de aplicação

O script [`sql/ordens_inspecao.sql`](sql/ordens_inspecao.sql) prepara a tabela
operacional `ordens_inspecao` e o índice único parcial que impede duas ordens
`ABERTA` ou `EM_CAMPO` para a mesma UC. A tabela é separada das tabelas Gold.
O script **não é executado pela aplicação**. Sua aplicação em cada instalação é
manual e controlada; valide as restrições em um banco de teste isolado antes do
uso operacional.

O script é transacional e falha se a tabela já existir; não usa `IF NOT EXISTS`
para ocultar uma estrutura incompatível. Não contém comandos de remoção de dados.
O banco gera `id` como identidade `BIGINT`; a  API apresentará `id_ordem`
como `OI-` seguido do número com no mínimo cinco dígitos (por exemplo,
`OI-00001`), sem truncar números maiores. Lacunas na sequência são normais após
rollback. Os timestamps `TIMESTAMPTZ` representam instantes UTC; a API
devolverá ISO 8601 com fuso. Transições atualizarão `atualizada_em` e preencherão
`concluida_em` apenas na conclusão.

As restrições SQL validam domínios e coerência dos campos.

## Testes com PostgreSQL isolado

Prefira executar os testes que criam ou alteram ordens em um banco de teste, nunca
inserindo UCs ou ordens fictícias no banco principal. O fixture em
`tests/test_inspection_orders_postgres.py` faz esse isolamento automaticamente:
usa a conexão configurada em `DATABASE_URL` apenas para identificar o servidor
local, cria nele um banco descartável chamado `v_energy_orders_test_<sufixo>`,
aplica `sql/ordens_inspecao.sql` nesse banco, insere dados **sintéticos** que
simulam o uso da fila e das ordens e remove o banco ao terminar. Não copia os
dados do banco principal. As consultas de integração à Gold original são somente
leitura. A URL deve apontar para o banco principal em PostgreSQL local e o usuário da
conexão precisa poder conectar ao banco administrativo `postgres` e criar/remover
bancos (`CREATEDB`).

Com o ambiente virtual ativo e `backend/.env.local` configurado, execute a partir
de `backend/`:

```bash
python -m pytest -q
```
