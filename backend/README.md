# API do V-Energy Grid 360

## Instalação

Requer Python 3.11 ou superior. A partir de `backend/`:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Execução

```bash
python -m app.main
```

A API usa `127.0.0.1:8000` por padrão. Consulte `GET http://127.0.0.1:8000/health`,
`http://127.0.0.1:8000/docs` e `http://127.0.0.1:8000/openapi.json`.

OPCIONALMENTE, configure `APP_ENV`, `APP_HOST`, `APP_PORT` e `CORS_ORIGINS` antes de
iniciar (basta configurar as variáveis no ambiente ou em um arquivo .env dentro de `backend/`). `CORS_ORIGINS` é uma lista de origens HTTP locais separadas por vírgula;
por padrão aceita `localhost:5173` e `127.0.0.1:5173`.
