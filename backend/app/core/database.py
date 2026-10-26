"""Conexão síncrona com a Gold no PostgreSQL local."""

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Connection, Engine

from app.core.config import get_settings


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Cria o engine sob demanda e o reutiliza durante o processo."""
    database_url = get_settings().database_url
    if database_url is None:
        raise RuntimeError("DATABASE_URL não configurada")
    return create_engine(
        database_url,
        connect_args={"connect_timeout": 5, "options": "-c statement_timeout=5000"},
    )


@contextmanager
def get_connection() -> Iterator[Connection]:
    """Entrega uma conexão que volta ao pool ao sair do bloco."""
    with get_engine().connect() as connection:
        yield connection
