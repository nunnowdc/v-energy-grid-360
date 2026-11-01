"""Migração do ai-agent que liga a auditoria às contas, em PostgreSQL descartável."""

import importlib.util
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from test_inspection_orders_postgres import ADMIN_DE_TESTE

pytest_plugins = ("test_inspection_orders_postgres",)

# O pacote scripts do ai-agent tem o mesmo nome do scripts do backend: carrega pelo caminho
_CAMINHO = (
    Path(__file__).resolve().parents[2]
    / "ai-agent"
    / "scripts"
    / "migracoes"
    / "migracao_usuario_auditoria_agente.py"
)
_spec = importlib.util.spec_from_file_location("migracao_usuario_auditoria", _CAMINHO)
migracao = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(migracao)


@pytest.fixture(scope="module")
def audit_engine(orders_engine: Engine) -> Engine:
    """Auditoria como estava antes: user_id em texto, com ids de antes do login."""
    with orders_engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE tb_auditoria_agente ("
            "id UUID PRIMARY KEY, "
            "data_hora TIMESTAMPTZ NOT NULL DEFAULT now(), "
            "user_id VARCHAR(100), perfil VARCHAR(50))"
        )
        connection.execute(
            text(
                "INSERT INTO tb_auditoria_agente (id, user_id) VALUES (:id, :user_id)"
            ),
            [
                {"id": uuid4(), "user_id": "usuario-teste"},
                {"id": uuid4(), "user_id": ADMIN_DE_TESTE},
                {"id": uuid4(), "user_id": str(uuid4())},
                {"id": uuid4(), "user_id": None},
            ],
        )
    return orders_engine


def _aplicar(engine: Engine) -> int:
    conexao = engine.raw_connection()
    try:
        with conexao.cursor() as cur:
            sem_usuario = migracao.aplicar(cur)
        conexao.commit()
        return sem_usuario
    finally:
        conexao.close()


def test_migration_keeps_real_accounts_and_empties_the_rest(
    audit_engine: Engine,
) -> None:
    # Um id de teste em texto e um UUID de conta que não existe
    assert _aplicar(audit_engine) == 2

    with audit_engine.connect() as connection:
        tipo = connection.execute(
            text(
                "SELECT data_type FROM information_schema.columns "
                "WHERE table_name = 'tb_auditoria_agente' AND column_name = 'user_id'"
            )
        ).scalar_one()
        ids = connection.execute(
            text("SELECT user_id FROM tb_auditoria_agente WHERE user_id IS NOT NULL")
        ).scalars()
        assert tipo == "uuid"
        assert [str(user_id) for user_id in ids] == [ADMIN_DE_TESTE]

    # Rodar de novo não muda nada
    assert _aplicar(audit_engine) == 0


def test_after_migration_audit_only_accepts_existing_accounts(
    audit_engine: Engine,
) -> None:
    _aplicar(audit_engine)
    with pytest.raises(IntegrityError), audit_engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO tb_auditoria_agente (id, user_id) VALUES (:id, :user_id)"
            ),
            {"id": uuid4(), "user_id": uuid4()},
        )
    with audit_engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO tb_auditoria_agente (id, user_id, perfil) "
                "VALUES (:id, :user_id, 'ADMIN_TI')"
            ),
            {"id": uuid4(), "user_id": ADMIN_DE_TESTE},
        )
