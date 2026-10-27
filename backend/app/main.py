"""Ponto de entrada da API."""

from app.controllers.filters import router as filters_router
from app.controllers.health import router as health_router
from app.controllers.metrics import router as metrics_router
from app.controllers.uc import router as uc_router
from app.core.config import get_settings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

settings = get_settings()
app = FastAPI(
    title="V-Energy Grid 360 API",
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins)
app.include_router(health_router, prefix="/api")
app.include_router(filters_router, prefix="/api")
app.include_router(metrics_router, prefix="/api")
app.include_router(uc_router, prefix="/api")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.host, port=settings.port)
