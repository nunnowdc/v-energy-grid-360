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
