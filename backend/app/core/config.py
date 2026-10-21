"""Configuração local da API, sem dependências de infraestrutura."""

import os
from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Settings:
    environment: str
    host: str
    port: int
    cors_origins: tuple[str, ...]


def get_settings() -> Settings:
    """Lê as opções simples do ambiente ao iniciar a aplicação."""
    environment = os.getenv("APP_ENV", "local")
    host = os.getenv("APP_HOST", "127.0.0.1")
    port = int(os.getenv("APP_PORT", "8000"))
    if not 1 <= port <= 65535:
        raise ValueError("APP_PORT deve estar entre 1 e 65535")

    origins = tuple(
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
        if origin.strip()
    )
    if not origins:
        raise ValueError("CORS_ORIGINS deve conter pelo menos uma origem local")
    for origin in origins:
        parsed = urlsplit(origin)
        if (
            parsed.scheme != "http"
            or parsed.hostname not in {"localhost", "127.0.0.1"}
            or parsed.path
            or parsed.query
            or parsed.fragment
            or parsed.username is not None
            or parsed.password is not None
            or not parsed.port
        ):
            raise ValueError(f"Origem CORS local inválida: {origin}")

    return Settings(environment, host, port, origins)
