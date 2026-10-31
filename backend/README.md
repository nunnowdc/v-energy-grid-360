# API do V-Energy Grid 360

## Passo a passo de inicialização local

Partindo da raiz do repositório, com o PostgreSQL local já preparado:

1. Entre em `backend/` e crie o ambiente virtual, caso ainda não exista:

   ```bash
   cd backend
   python3 -m venv .venv
   ```


2. Instale as dependências nesse ambiente:

   ```bash
   .venv/bin/python -m pip install -r requirements.txt
   ```

3. Crie o arquivo `.env.local` a partir do exemplo:

   ```bash
   cp -n .env.example .env.local
   ```

Configure as seguintes variáveis:
- **Banco de dados & Autenticação:**
  - `DATABASE_URL`: Connection string do PostgreSQL
  - `JWT_SECRET_KEY`: Segredo local para assinatura dos tokens JWT.
  - `BOOTSTRAP_ADMIN_PASSWORD`: Senha inicial para a conta `ADMIN_TI` (mínimo de 8 caracteres).

  - `CORS_ORIGINS`: URLs liberadas para o frontend (padrão: `http://localhost:5173,http://127.0.0.1:5173`).

- **Agentes de IA (LLM):**
  - `MODELO_LLM_PRIMARIO`: Identificador do modelo principal a ser utilizado.
  - `OPENROUTER_API_KEY` ou `NINEROUTER_API_KEY`: Chave da API do provedor escolhido (OpenRouter tem precedência; se ambas ficarem vazias, o backend roda em modo de teste).

4. No banco PostgreSQL indicado por `DATABASE_URL`, execute **uma vez** os scripts
   `sql/ordens_inspecao.sql` e `sql/usuarios.sql`. No DBeaver, selecione esse banco,
   abra cada arquivo e execute o script inteiro usando uma Query Tool. Pelo terminal, a partir de
   `backend/`, use os mesmos dados de conexão para os dois comandos:

   ```bash
   psql -h HOST -p PORTA -U USUARIO -d BANCO -v ON_ERROR_STOP=1 -f sql/ordens_inspecao.sql
   psql -h HOST -p PORTA -U USUARIO -d BANCO -v ON_ERROR_STOP=1 -f sql/usuarios.sql
   ```

   Substitua `HOST`, `PORTA`, `USUARIO` e `BANCO` pelos valores da sua conexão;
   `psql` solicitará a senha do PostgreSQL quando necessário. Os scripts não são
   executados pela API. `sql/usuarios.sql` usa `CREATE TABLE IF NOT EXISTS`: ao
   reexecutá-lo, não tenta recriar uma tabela existente, mas também não verifica
   nem corrige diferenças de estrutura. `sql/ordens_inspecao.sql` não usa essa
   cláusula e falha se a tabela já existir; não o rode novamente em uma
   instalação já preparada.

5. Crie a primeira conta administrativa. O bootstrap exige `usuarios` já criada e
   lê a senha de `.env.local` ou da variável do processo (que tem prioridade):

   ```bash
   .venv/bin/python -m scripts.bootstrap_admin_ti
   ```

6. Inicie a API e consulte `/api/health` ou `/api/docs` no endereço informado em
   **Execução** abaixo:

   ```bash
   .venv/bin/python -m app.main
   ```

7. **Opcional** (Verificação do ambiente) Em outro terminal, a partir de `backend/`, execute a suíte de testes:

   ```bash
   .venv/bin/python -m pytest -q
   ```

   Os testes de escrita criam bancos PostgreSQL descartáveis com dados fictícios;
   as consultas de integração à Gold são somente leitura. Veja os pré-requisitos
   de permissão em **Testes com PostgreSQL isolado** abaixo.


`app/core/config.py` lê `backend/.env.local` automaticamente, mesmo quando o comando
é iniciado de outro diretório. Variáveis já definidas no ambiente do sistema têm
prioridade. Reinicie a API após mudar a configuração local.

## Execução

A API usa `127.0.0.1:8000` por padrão. Consulte `GET http://127.0.0.1:8000/api/health`,
`http://127.0.0.1:8000/api/docs`, `http://127.0.0.1:8000/api/redoc` e
`http://127.0.0.1:8000/api/openapi.json`.

`CORS_ORIGINS` aceita origens HTTP locais separadas por vírgula; por padrão, inclui
`http://localhost:5173` e `http://127.0.0.1:5173`.

## Bootstrap da conta administrativa

O script do passo 5 cria somente a conta `admin_ti`
(`adminti.vgrid360@visagio.com`, perfil `ADMIN_TI`) e armazena a senha apenas como
hash Argon2id. Ele é idempotente: se a conta já existir, não altera seus dados
nem redefine a senha. O bootstrap não cria tabelas.

> **Nota**
Após executar o bootstrap com sucesso, a senha inicial pode ser removida do .env.local. A conta permanecerá cadastrada no banco, com a senha armazenada em hash.

## Ordens de inspeção: estrutura operacional

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

Os testes que criam ou alteram dados não inserem UCs, ordens ou usuários fictícios
no banco principal. Os fixtures de `tests/test_inspection_orders_postgres.py` e
`tests/test_users_postgres.py` usam a conexão configurada em `DATABASE_URL` apenas
para identificar o servidor local, criam bancos descartáveis chamados
`v_energy_orders_test_<sufixo>` e `v_energy_users_test_<sufixo>`, aplicam os SQLs
correspondentes nesses bancos, inserem dados **sintéticos** e removem os bancos
ao terminar. Não copiam dados do banco principal. As consultas de integração à
Gold original são somente leitura. A URL deve apontar para o
PostgreSQL local, e o usuário da conexão precisa acessar o banco administrativo
`postgres` e criar/remover bancos (`CREATEDB`).

Com o ambiente virtual ativo e `backend/.env.local` configurado, execute a partir
de `backend/`:

```bash
.venv/bin/python -m pytest -q
```
