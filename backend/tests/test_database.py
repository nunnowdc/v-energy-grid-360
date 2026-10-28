"""Conectividade de leitura e ciclo de vida da conexão PostgreSQL."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core import config
from app.core.config import get_settings
from app.core.database import get_connection, get_engine
from app.main import app


def test_health_does_not_need_database_url(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(config, "ENV_LOCAL_PATH", tmp_path / "missing.env.local")

    assert get_settings().database_url is None

    response = TestClient(app).get("/api/health")

    assert response.status_code == 200


@pytest.mark.skipif(
    not get_settings().database_url, reason="DATABASE_URL não configurada"
)
def test_postgresql_connection_is_reused_and_closed() -> None:
    assert get_engine() is get_engine()

    with get_connection() as connection:
        assert connection.execute(text("SELECT :value"), {"value": 1}).scalar_one() == 1
        assert connection.exec_driver_sql("SHOW statement_timeout").scalar_one() == "5s"
        assert not connection.closed

    assert connection.closed
