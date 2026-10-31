"""Ponto de entrada da API."""

import os
import sys
from pathlib import Path

from app.controllers.auth import router as auth_router
from app.controllers.filters import router as filters_router
from app.controllers.health import router as health_router
from app.controllers.inspections import router as inspections_router
from app.controllers.metrics import router as metrics_router
from app.controllers.network import router as network_router
from app.controllers.uc import router as uc_router
from app.core.config import ENV_LOCAL_PATH, get_settings
from app.security.dependencies import ALLOWED_WRITE_ORIGINS
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.requests import Request

settings = get_settings()

# O módulo de IA mora em ai-agent/, é importado como o pacote src e lê o banco
# direto do ambiente, na forma sem o driver
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ai-agent"))
if settings.database_url:
    os.environ.setdefault(
        "DATABASE_URL",
        settings.database_url.replace("postgresql+psycopg://", "postgresql://", 1),
    )
# As chaves e o modelo do LLM também vêm do .env.local. Quem já está no
# ambiente, como a DATABASE_URL acima, não é sobrescrito
load_dotenv(ENV_LOCAL_PATH)

from src.api.ai_router import router as ai_router

app = FastAPI(
    title="V-Energy Grid 360 API",
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)


@app.exception_handler(RequestValidationError)
async def safe_auth_validation(request: Request, exc: RequestValidationError):
    """Evita ecoar senhas inválidas nas respostas dos novos endpoints."""
    if request.url.path in {"/api/auth/users", "/api/auth/password"}:
        errors = [
            {key: value for key, value in error.items() if key != "input"}
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=422, content={"detail": jsonable_encoder(errors)}
        )
    return await request_validation_exception_handler(request, exc)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
)


@app.middleware("http")
async def check_write_origin(request: Request, call_next):
    """Aplica a mesma lista local a toda requisição que altera estado."""
    origin = request.headers.get("origin")
    if (
        request.method in {"POST", "PATCH", "DELETE"}
        and origin is not None
        and origin not in ALLOWED_WRITE_ORIGINS
    ):
        return JSONResponse(
            status_code=403, content={"detail": "Origem não autorizada"}
        )
    return await call_next(request)


app.include_router(auth_router, prefix="/api")
app.include_router(health_router, prefix="/api")
app.include_router(filters_router, prefix="/api")
app.include_router(inspections_router, prefix="/api")
app.include_router(metrics_router, prefix="/api")
app.include_router(network_router, prefix="/api")
app.include_router(uc_router, prefix="/api")
app.include_router(ai_router, prefix="/api")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.host, port=settings.port)
