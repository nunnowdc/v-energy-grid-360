"""Integridade das ordens em banco PostgreSQL descartável, separado da Gold."""

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from threading import Event
from time import monotonic, sleep
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from sqlalchemy import create_engine, insert, select, text, update
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import IntegrityError, ProgrammingError

from app.core.config import get_settings
from app.repositories.inspection_orders import ORDENS_INSPECAO

ADMIN_DE_TESTE = "550e8400-e29b-41d4-a716-446655440000"


@pytest.fixture(scope="module")
def orders_engine() -> Iterator[Engine]:
    """Cria e remove somente um banco com nome exclusivo para este teste."""
    database_url = get_settings().database_url
    if not database_url:
        pytest.skip("PostgreSQL local não configurado")
    main_url = make_url(database_url)
    if main_url.database != "v_energy" or main_url.host not in {
        None,
        "localhost",
        "127.0.0.1",
        "::1",
    }:
        pytest.skip("Teste exige PostgreSQL local com v_energy como origem")

    test_name = f"v_energy_orders_test_{uuid4().hex[:12]}"
    admin_url = main_url.set(drivername="postgresql", database="postgres")
    admin_dsn = admin_url.render_as_string(hide_password=False)
    test_url = main_url.set(database=test_name)
    with psycopg.connect(admin_dsn, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(test_name)))
        engine = create_engine(
            test_url,
            connect_args={"connect_timeout": 5, "options": "-c statement_timeout=5000"},
        )
        try:
            # Na ordem do setup: as ordens, as contas e a autoria, que liga as duas
            pasta_sql = Path(__file__).resolve().parents[1] / "sql"
            with engine.connect() as connection:
                for arquivo in (
                    "ordens_inspecao.sql",
                    "usuarios.sql",
                    "ordens_inspecao_autoria.sql",
                ):
                    connection.exec_driver_sql(
                        (pasta_sql / arquivo).read_text(encoding="utf-8")
                    )
            # A mesma conta sintética que o conftest põe na sessão dos testes
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO usuarios (id, nome, email, senha_hash, perfil, "
                        "criado_em) VALUES (:id, 'Administrador de teste', "
                        "'admin@example.invalid', 'sem-senha', 'ADMIN_TI', now())"
                    ),
                    {"id": ADMIN_DE_TESTE},
                )
            yield engine
        finally:
            engine.dispose()
            admin.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(test_name)))


def test_checks_reject_invalid_states_and_results(orders_engine: Engine) -> None:
    invalid = [
        {"id_uc": "INVALIDA", "status": "ABERTA"},
        {"id_uc": "UC900001", "status": "DESCONHECIDA"},
        {"id_uc": "UC900002", "status": "CONCLUIDA", "concluida_em": datetime.now(UTC)},
        {
            "id_uc": "UC900003",
            "status": "CONCLUIDA",
            "resultado": "OUTRO",
            "concluida_em": datetime.now(UTC),
        },
        {"id_uc": "UC900004", "status": "CONCLUIDA", "resultado": "SEM_IRREGULARIDADE"},
        {"id_uc": "UC900005", "status": "ABERTA", "resultado": "SEM_IRREGULARIDADE"},
        {"id_uc": "UC900006", "status": "CANCELADA", "concluida_em": datetime.now(UTC)},
    ]
    for values in invalid:
        with pytest.raises(IntegrityError), orders_engine.begin() as connection:
            connection.execute(insert(ORDENS_INSPECAO).values(**values))


def test_only_one_active_order_and_multiple_historical_orders(
    orders_engine: Engine,
) -> None:
    uc = "UC900010"
    with orders_engine.begin() as connection:
        first_id = connection.execute(
            insert(ORDENS_INSPECAO).values(id_uc=uc, status="ABERTA")
        ).inserted_primary_key[0]
    with pytest.raises(IntegrityError), orders_engine.begin() as connection:
        connection.execute(insert(ORDENS_INSPECAO).values(id_uc=uc, status="EM_CAMPO"))

    with orders_engine.begin() as connection:
        connection.execute(
            update(ORDENS_INSPECAO)
            .where(ORDENS_INSPECAO.c.id == first_id)
            .values(status="CANCELADA", atualizada_em=datetime.now(UTC))
        )
        connection.execute(insert(ORDENS_INSPECAO).values(id_uc=uc, status="ABERTA"))
        connection.execute(
            insert(ORDENS_INSPECAO).values(
                id_uc=uc,
                status="CONCLUIDA",
                resultado="IRREGULARIDADE_CONFIRMADA",
                concluida_em=datetime.now(UTC),
            )
        )
    with orders_engine.connect() as connection:
        statuses = (
            connection.execute(
                select(ORDENS_INSPECAO.c.status).where(ORDENS_INSPECAO.c.id_uc == uc)
            )
            .scalars()
            .all()
        )
    assert sorted(statuses) == ["ABERTA", "CANCELADA", "CONCLUIDA"]


def test_timestamps_and_committed_order_survive_reconnection(
    orders_engine: Engine,
) -> None:
    before = datetime.now(UTC)
    with orders_engine.begin() as connection:
        order_id = connection.execute(
            insert(ORDENS_INSPECAO).values(id_uc="UC900020", status="ABERTA")
        ).inserted_primary_key[0]
    orders_engine.dispose()
    with orders_engine.connect() as connection:
        row = connection.execute(
            select(ORDENS_INSPECAO).where(ORDENS_INSPECAO.c.id == order_id)
        ).one()
    assert row.id == order_id
    assert row.criada_em.tzinfo is not None
    assert row.atualizada_em.tzinfo is not None
    assert abs((row.criada_em.astimezone(UTC) - before).total_seconds()) < 5
    assert row.concluida_em is None


def test_partial_unique_index_blocks_concurrent_active_insert(
    orders_engine: Engine,
) -> None:
    started = Event()
    worker_pid: list[int] = []

    def competing_insert() -> str:
        try:
            with orders_engine.begin() as connection:
                worker_pid.append(
                    connection.execute(text("SELECT pg_backend_pid()")).scalar_one()
                )
                started.set()
                connection.execute(
                    insert(ORDENS_INSPECAO).values(id_uc="UC900030", status="EM_CAMPO")
                )
        except IntegrityError:
            return "conflict"
        return "inserted"

    with orders_engine.connect() as first:
        transaction = first.begin()
        first.execute(insert(ORDENS_INSPECAO).values(id_uc="UC900030", status="ABERTA"))
        with ThreadPoolExecutor(max_workers=1) as executor:
            competing = executor.submit(competing_insert)
            assert started.wait(timeout=2)
            try:
                deadline = monotonic() + 2
                while monotonic() < deadline:
                    blocked = first.execute(
                        text(
                            "SELECT wait_event_type = 'Lock' FROM pg_stat_activity "
                            "WHERE pid = :pid"
                        ),
                        {"pid": worker_pid[0]},
                    ).scalar_one_or_none()
                    if blocked:
                        break
                    sleep(0.02)
                assert blocked, "a segunda conexão não aguardou a transação ativa"
            finally:
                transaction.commit()
            assert competing.result(timeout=5) == "conflict"
    with orders_engine.connect() as connection:
        count = connection.execute(
            select(text("count(*)"))
            .select_from(ORDENS_INSPECAO)
            .where(ORDENS_INSPECAO.c.id_uc == "UC900030")
        ).scalar_one()
    assert count == 1


def test_script_fails_on_existing_structure_without_erasing_it(
    orders_engine: Engine,
) -> None:
    ddl = (
        Path(__file__).resolve().parents[1] / "sql" / "ordens_inspecao.sql"
    ).read_text(encoding="utf-8")
    with pytest.raises(ProgrammingError), orders_engine.connect() as connection:
        connection.exec_driver_sql(ddl)
    with orders_engine.connect() as connection:
        assert connection.execute(
            text("SELECT to_regclass('public.ordens_inspecao') IS NOT NULL")
        ).scalar_one()


def test_author_must_be_an_existing_account(orders_engine: Engine) -> None:
    desconhecida = uuid4()
    for author in ("criada_por", "atualizada_por"):
        with pytest.raises(IntegrityError), orders_engine.begin() as connection:
            connection.execute(
                insert(ORDENS_INSPECAO).values(
                    id_uc="UC900099", status="CANCELADA", **{author: desconhecida}
                )
            )
    with orders_engine.begin() as connection:
        connection.execute(
            insert(ORDENS_INSPECAO).values(
                id_uc="UC900099", status="CANCELADA", criada_por=ADMIN_DE_TESTE
            )
        )
