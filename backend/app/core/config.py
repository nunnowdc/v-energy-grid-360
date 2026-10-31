"""Configuração local da API, sem dependências de infraestrutura."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import dotenv_values
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

ENV_LOCAL_PATH = Path(__file__).resolve().parents[2] / ".env.local"


@dataclass(frozen=True)
class Settings:
    environment: str
    host: str
    port: int
    cors_origins: tuple[str, ...]
    database_url: str | None = field(default=None, repr=False)
    jwt_secret_key: str | None = field(default=None, repr=False)


def get_settings() -> Settings:
    """Lê o ambiente do sistema antes das opções locais do backend."""
    local_values = dotenv_values(ENV_LOCAL_PATH, interpolate=False)

    def value(name: str, default: str) -> str:
        if name in os.environ:
            return os.environ[name]
        local_value = local_values.get(name)
        return default if local_value is None else local_value

    environment = value("APP_ENV", "local")
    host = value("APP_HOST", "127.0.0.1")
    port = int(value("APP_PORT", "8000"))
    if not 1 <= port <= 65535:
        raise ValueError("APP_PORT deve estar entre 1 e 65535")

    origins = tuple(
        origin.strip()
        for origin in value(
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

    database_url = value("DATABASE_URL", "") or None
    if database_url:
        try:
            parsed_database_url = make_url(database_url)
        except (ArgumentError, ValueError):
            raise ValueError("DATABASE_URL inválida") from None
        if (
            parsed_database_url.drivername
            not in {
                "postgresql",
                "postgresql+psycopg",
            }
            or not parsed_database_url.database
        ):
            raise ValueError(
                "DATABASE_URL deve usar postgresql ou postgresql+psycopg e indicar o banco"
            )
        # O SQLAlchemy precisa do driver no esquema; o agente de IA usa a forma sem ele
        database_url = parsed_database_url.set(
            drivername="postgresql+psycopg"
        ).render_as_string(hide_password=False)

    jwt_secret_key = value("JWT_SECRET_KEY", "") or None
    return Settings(environment, host, port, origins, database_url, jwt_secret_key)
