from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock, patch

import pytest

from ai_agent.tests import conftest


def test_fixture_faz_fallback_se_postgres_nao_estiver_disponivel(monkeypatch):
    monkeypatch.setenv("TEST_DATABASE_URL", "postgresql://localhost/v_energy_test_db")
    monkeypatch.setattr(conftest, "_testar_conexao_postgres", lambda _: False)

    fixture = conftest.postgres_test_info.__wrapped__()

    assert next(fixture) == {"disponivel": False, "db_url": None, "schema": None}


def test_fixture_propaga_falha_no_ddl_apos_conexao(monkeypatch):
    monkeypatch.setenv("TEST_DATABASE_URL", "postgresql://localhost/v_energy_test_db")
    monkeypatch.setattr(conftest, "_testar_conexao_postgres", lambda _: True)

    setup_cursor = MagicMock()
    setup_cursor.__enter__.return_value = setup_cursor
    setup_cursor.execute.side_effect = [None, None, RuntimeError("DDL indisponível")]
    setup_connection = MagicMock()
    setup_connection.closed = 0
    setup_connection.cursor.return_value = setup_cursor

    cleanup_cursor = MagicMock()
    cleanup_cursor.__enter__.return_value = cleanup_cursor
    cleanup_connection = MagicMock()
    cleanup_connection.closed = 0
    cleanup_connection.cursor.return_value = cleanup_cursor

    postgres_driver = types.ModuleType("psycopg2")
    postgres_driver.connect = MagicMock(
        side_effect=[setup_connection, cleanup_connection]
    )
    postgres_driver.sql = types.SimpleNamespace(
        SQL=lambda statement: types.SimpleNamespace(
            format=lambda *args: statement
        ),
        Identifier=lambda identifier: identifier,
    )

    with patch.dict(sys.modules, {"psycopg2": postgres_driver}):
        fixture = conftest.postgres_test_info.__wrapped__()
        with pytest.raises(RuntimeError, match="Falha ao preparar schema PostgreSQL"):
            next(fixture)

    postgres_driver.connect.assert_any_call(
        "postgresql://localhost/v_energy_test_db"
    )
    assert setup_cursor.execute.call_count == 3
    assert cleanup_cursor.execute.call_count == 1
