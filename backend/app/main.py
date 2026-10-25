"""Ponto de entrada da API."""

from app.controllers.health import router as health_router
from app.core.config import get_settings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

settings = get_settings()
app = FastAPI(title="V-Energy Grid 360 API")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins)
app.include_router(health_router, prefix="/api")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.host, port=settings.port)
