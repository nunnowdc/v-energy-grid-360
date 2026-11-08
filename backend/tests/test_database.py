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


# --- Troca de role por perfil (sem tocar no PostgreSQL)

from sqlalchemy import create_engine

from app.core import database
from app.core.database import (
    MissingProfileError,
    UnknownProfileError,
    current_profile,
    install_role_listener,
    role_for_profile,
)


@pytest.fixture
def sqlite_engine(monkeypatch: pytest.MonkeyPatch):
    executed: list[str] = []
    monkeypatch.setattr(
        database,
        "_execute_set_local_role",
        lambda _dbapi_connection, role: executed.append(role),
    )
    engine = create_engine("sqlite://")
    install_role_listener(engine)
    return engine, executed


@pytest.mark.parametrize(
    ("profile", "role"),
    [
        ("DIRETORIA", "perfil_diretoria"),
        ("ATENDIMENTO", "perfil_atendimento"),
        ("PERDAS", "perfil_perdas"),
        ("OPERACAO", "perfil_operacao"),
        ("ADMIN_TI", "perfil_admin_ti"),
    ],
)
def test_role_map_covers_the_five_profiles(profile: str, role: str) -> None:
    assert role_for_profile(profile) == role


def test_unknown_profile_is_an_error() -> None:
    with pytest.raises(UnknownProfileError):
        role_for_profile("ROOT")


def test_listener_sets_role_from_context_var_on_begin(sqlite_engine) -> None:
    engine, executed = sqlite_engine
    token = current_profile.set("PERDAS")
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            connection.execute(text("SELECT 2"))
    finally:
        current_profile.reset(token)

    assert executed == ["perfil_perdas"]


def test_listener_runs_again_for_each_transaction(sqlite_engine) -> None:
    engine, executed = sqlite_engine
    token = current_profile.set("OPERACAO")
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            connection.commit()
            connection.execute(text("SELECT 1"))
    finally:
        current_profile.reset(token)

    assert executed == ["perfil_operacao", "perfil_operacao"]


def test_listener_refuses_connection_without_profile(sqlite_engine) -> None:
    engine, executed = sqlite_engine

    with pytest.raises(MissingProfileError):
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

    assert executed == []


def test_listener_refuses_unknown_profile(sqlite_engine) -> None:
    engine, executed = sqlite_engine
    token = current_profile.set("ROOT")
    try:
        with pytest.raises(UnknownProfileError):
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
    finally:
        current_profile.reset(token)

    assert executed == []


def test_get_connection_with_roles_requires_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        database,
        "get_settings",
        lambda: config.Settings("local", "h", 1, (), use_db_roles=True),
    )

    with pytest.raises(MissingProfileError):
        with get_connection():
            pass


def test_connections_use_the_right_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    engines = {name: create_engine("sqlite://") for name in ("owner", "app", "auth")}
    monkeypatch.setattr(database, "get_engine", lambda: engines["owner"])
    monkeypatch.setattr(database, "get_portal_app_engine", lambda: engines["app"])
    monkeypatch.setattr(database, "get_portal_auth_engine", lambda: engines["auth"])

    def used(factory) -> object:
        with factory() as connection:
            return connection.engine

    monkeypatch.setattr(
        database, "get_settings", lambda: config.Settings("l", "h", 1, ())
    )
    assert used(database.get_connection) is engines["owner"]
    assert used(database.get_auth_connection) is engines["owner"]
    assert used(database.get_owner_connection) is engines["owner"]

    monkeypatch.setattr(
        database,
        "get_settings",
        lambda: config.Settings("l", "h", 1, (), use_db_roles=True),
    )
    token = current_profile.set("ADMIN_TI")
    try:
        assert used(database.get_connection) is engines["app"]
    finally:
        current_profile.reset(token)
    assert used(database.get_auth_connection) is engines["auth"]
    assert used(database.get_owner_connection) is engines["owner"]
