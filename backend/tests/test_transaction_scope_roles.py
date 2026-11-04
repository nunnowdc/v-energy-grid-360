"""SELECT seguido de escrita com begin() explícito, com roles ligadas (SQLite, sem Postgres)."""

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from app.core import database
from app.repositories.transactions import transaction_scope


@pytest.fixture
def connection(monkeypatch: pytest.MonkeyPatch):
    chamadas: list[str] = []
    monkeypatch.setattr(
        database, "_execute_set_local_role", lambda _conn, role: chamadas.append(role)
    )
    token = database.current_profile.set("PERDAS")
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    database.install_role_listener(engine)
    with engine.connect() as conn:
        conn.chamadas = chamadas  # type: ignore[attr-defined]
        yield conn
    database.current_profile.reset(token)


def test_select_then_scoped_write_applies_role_once_and_persists(connection) -> None:
    connection.execute(text("CREATE TABLE t (v INTEGER)"))
    connection.commit()
    connection.chamadas.clear()

    connection.execute(text("SELECT 1")).scalar_one()
    with transaction_scope(connection):
        connection.execute(text("INSERT INTO t VALUES (1)"))

    assert connection.chamadas == ["perfil_perdas"]
    assert not connection.in_transaction()
    assert connection.execute(text("SELECT COUNT(*) FROM t")).scalar_one() == 1


def test_clean_connection_uses_plain_begin(connection) -> None:
    connection.execute(text("CREATE TABLE t (v INTEGER)"))
    connection.commit()
    connection.chamadas.clear()

    with transaction_scope(connection):
        connection.execute(text("INSERT INTO t VALUES (1)"))

    assert connection.chamadas == ["perfil_perdas"]
    assert connection.execute(text("SELECT COUNT(*) FROM t")).scalar_one() == 1


def test_error_after_select_rolls_back(connection) -> None:
    connection.execute(text("CREATE TABLE t (v INTEGER)"))
    connection.commit()
    connection.execute(text("SELECT 1")).scalar_one()

    with pytest.raises(RuntimeError):
        with transaction_scope(connection):
            connection.execute(text("INSERT INTO t VALUES (1)"))
            raise RuntimeError

    assert connection.execute(text("SELECT COUNT(*) FROM t")).scalar_one() == 0
