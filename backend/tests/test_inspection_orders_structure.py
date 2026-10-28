"""Contrato estrutural da persistência operacional, sem executar DDL."""

from pathlib import Path

from sqlalchemy import insert
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.sqltypes import BigInteger, DateTime, Text

from app.repositories.inspection_orders import ORDENS_INSPECAO

SQL_PATH = Path(__file__).resolve().parents[1] / "sql" / "ordens_inspecao.sql"


def test_operational_sql_defines_order_integrity_without_touching_gold() -> None:
    sql = SQL_PATH.read_text(encoding="utf-8")

    assert "\nBEGIN;\n" in sql
    assert sql.rstrip().endswith("COMMIT;")
    assert "CREATE TABLE ordens_inspecao (" in sql
    assert "IF NOT EXISTS" not in sql
    assert "id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY" in sql
    assert "id_uc TEXT NOT NULL CHECK (id_uc ~ '^UC[0-9]{6}$')" in sql
    assert "status IN ('ABERTA', 'EM_CAMPO', 'CONCLUIDA', 'CANCELADA')" in sql
    assert "resultado IN ('IRREGULARIDADE_CONFIRMADA', 'SEM_IRREGULARIDADE')" in sql
    assert "status = 'CONCLUIDA'" in sql
    assert "AND resultado IS NOT NULL" in sql
    assert "concluida_em IS NOT NULL" in sql
    assert "status <> 'CONCLUIDA' AND resultado IS NULL AND concluida_em IS NULL" in sql
    assert "CREATE UNIQUE INDEX ordens_inspecao_uc_ativa_uidx" in sql
    assert "ON ordens_inspecao (id_uc)" in sql
    assert "WHERE status IN ('ABERTA', 'EM_CAMPO')" in sql
    for timestamp in ("criada_em", "atualizada_em", "concluida_em"):
        assert f"{timestamp} TIMESTAMPTZ" in sql
    for prohibited in ("DROP ", "TRUNCATE ", "DELETE ", "REFERENCES "):
        assert prohibited not in sql.upper()
    assert "fila_inspecao" not in sql
    assert "fact_inspecoes" not in sql


def test_core_mapping_targets_operational_table_without_database_access() -> None:
    assert ORDENS_INSPECAO.name == "ordens_inspecao"
    assert list(ORDENS_INSPECAO.columns.keys()) == [
        "id",
        "id_uc",
        "status",
        "resultado",
        "criada_em",
        "atualizada_em",
        "concluida_em",
    ]
    assert isinstance(ORDENS_INSPECAO.c.id.type, BigInteger)
    assert isinstance(ORDENS_INSPECAO.c.id_uc.type, Text)
    assert ORDENS_INSPECAO.c.id.primary_key
    assert ORDENS_INSPECAO.c.resultado.nullable
    assert ORDENS_INSPECAO.c.concluida_em.nullable
    assert all(
        isinstance(ORDENS_INSPECAO.c[name].type, DateTime)
        and ORDENS_INSPECAO.c[name].type.timezone
        for name in ("criada_em", "atualizada_em", "concluida_em")
    )

    statement = insert(ORDENS_INSPECAO).values(id_uc="UC123456", status="ABERTA")
    compiled = statement.compile(dialect=postgresql.dialect())
    assert "ordens_inspecao" in str(compiled)
    assert "UC123456" not in str(compiled)
