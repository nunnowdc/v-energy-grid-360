"""Contrato estrutural da tabela operacional de usuários, sem DDL."""

from pathlib import Path

from app.entities.user import Usuario
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql.sqltypes import DateTime, String

SQL_PATH = Path(__file__).resolve().parents[1] / "sql" / "usuarios.sql"


def test_user_model_has_only_the_approved_six_columns() -> None:
    table = Usuario.__table__

    assert table.name == "usuarios"
    assert list(table.columns.keys()) == [
        "id",
        "nome",
        "email",
        "senha_hash",
        "perfil",
        "criado_em",
    ]
    assert isinstance(table.c.id.type, UUID)
    assert table.c.id.primary_key
    assert all(not column.nullable for column in table.columns)
    assert [
        (name, table.c[name].type.length)
        for name in ("nome", "email", "senha_hash", "perfil")
    ] == [
        ("nome", 150),
        ("email", 255),
        ("senha_hash", 255),
        ("perfil", 30),
    ]
    assert all(
        isinstance(table.c[name].type, String)
        for name in ("nome", "email", "senha_hash", "perfil")
    )
    assert isinstance(table.c.criado_em.type, DateTime)
    assert not table.c.criado_em.type.timezone


def test_user_ddl_is_controlled_and_does_not_touch_gold() -> None:
    ddl = SQL_PATH.read_text(encoding="utf-8").upper()

    assert "CREATE TABLE IF NOT EXISTS USUARIOS" in ddl
    for forbidden in ("DROP ", "TRUNCATE ", "DELETE ", "ALTER ", "FILA_INSPECAO"):
        assert forbidden not in ddl
