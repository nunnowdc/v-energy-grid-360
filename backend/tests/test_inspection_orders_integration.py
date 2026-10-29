"""POST de ordens com Gold sintética e escrita somente em banco descartável."""

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import date
from threading import Barrier, Lock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import insert, text, update
from sqlalchemy.engine import Engine

from app.controllers.inspections import (
    get_inspections_repository,
    get_order_repositories,
)
from app.main import app
from app.repositories.inspection_orders import (
    ORDENS_INSPECAO,
    InspectionOrdersRepository,
)
from app.repositories.inspections import InspectionsRepository

pytest_plugins = ("test_inspection_orders_postgres",)


@pytest.fixture(scope="module")
def synthetic_engine(orders_engine: Engine) -> Engine:
    """Adiciona apenas tabelas Gold sintéticas ao banco descartável do teste."""
    with orders_engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE dim_unidade_consumidora ("
            "id_uc TEXT PRIMARY KEY, municipio TEXT, bairro TEXT, classe TEXT)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE fila_inspecao ("
            "id_uc TEXT PRIMARY KEY, data_referencia DATE NOT NULL, "
            "prioridade INTEGER NOT NULL, score INTEGER NOT NULL, "
            "motivo_suspeita TEXT NOT NULL, "
            "kwh_recuperavel_estimado_ano DOUBLE PRECISION NOT NULL, "
            "municipio TEXT NOT NULL, bairro TEXT NOT NULL, classe TEXT NOT NULL)"
        )
        units = [f"UC900{number:03d}" for number in range(101, 109)]
        units.append("UC900199")
        connection.execute(
            text(
                "INSERT INTO dim_unidade_consumidora "
                "(id_uc, municipio, bairro, classe) "
                "VALUES (:id_uc, :municipio, :bairro, :classe)"
            ),
            [
                {
                    "id_uc": uc,
                    "municipio": "Recife",
                    "bairro": "Boa Viagem",
                    "classe": "RESIDENCIAL",
                }
                for uc in units
            ],
        )
        connection.execute(
            text(
                "INSERT INTO fila_inspecao (id_uc, data_referencia, prioridade, "
                "score, motivo_suspeita, kwh_recuperavel_estimado_ano, "
                "municipio, bairro, classe) VALUES "
                "(:id_uc, :data_referencia, :prioridade, :score, :motivo, "
                ":kwh, :municipio, :bairro, :classe)"
            ),
            [
                {
                    "id_uc": uc,
                    "data_referencia": date(2026, 6, 1),
                    "prioridade": index,
                    "score": 70,
                    "motivo": "Motivo sintético",
                    "kwh": 120.5,
                    "municipio": "Recife",
                    "bairro": "Boa Viagem",
                    "classe": "RESIDENCIAL",
                }
                for index, uc in enumerate(units[:-1], start=1)
            ],
        )
    return orders_engine


@contextmanager
def _post_repositories(
    engine: Engine,
) -> Iterator[tuple[InspectionsRepository, InspectionOrdersRepository]]:
    with engine.connect() as connection:
        gold = InspectionsRepository(connection)
        yield gold, gold.orders


@contextmanager
def _queue_repository(engine: Engine) -> Iterator[InspectionsRepository]:
    with engine.connect() as connection:
        yield InspectionsRepository(connection)


def test_post_batch_persists_and_queue_reflects_active_order(
    synthetic_engine: Engine,
) -> None:
    app.dependency_overrides[get_order_repositories] = lambda: _post_repositories(
        synthetic_engine
    )
    app.dependency_overrides[get_inspections_repository] = lambda: _queue_repository(
        synthetic_engine
    )
    try:
        client = TestClient(app)
        response = client.post(
            "/api/inspections/order", json={"ids_uc": ["UC900101", "UC900102"]}
        )
        queue = client.get("/api/inspections/queue")
        with synthetic_engine.begin() as connection:
            connection.execute(
                update(ORDENS_INSPECAO)
                .where(ORDENS_INSPECAO.c.id_uc == "UC900101")
                .values(status="CANCELADA")
            )
        after_closing = client.get("/api/inspections/queue")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    orders = response.json()["ordens"]
    assert [row["id_uc"] for row in orders] == ["UC900101", "UC900102"]
    assert all(row["status"] == "ABERTA" and row["resultado"] is None for row in orders)
    assert all(row["criada_em"].endswith(("Z", "+00:00")) for row in orders)
    assert queue.status_code == 200
    assert queue.json()["resumo"] == {
        "ucs": 8,
        "kwh_recuperavel_estimado_ano": 964.0,
    }
    active = {row["id_uc"]: row["ordem_aberta"] for row in queue.json()["itens"]}
    assert active["UC900101"] == {
        "id_ordem": orders[0]["id_ordem"],
        "status": "ABERTA",
    }
    assert active["UC900102"] == {
        "id_ordem": orders[1]["id_ordem"],
        "status": "ABERTA",
    }
    assert active["UC900104"] is None
    first_item = next(
        row for row in queue.json()["itens"] if row["id_uc"] == "UC900101"
    )
    assert first_item["prioridade"] == 1
    assert first_item["score"] == 70
    assert first_item["motivo_suspeita"] == "Motivo sintético"
    assert first_item["kwh_recuperavel_estimado_ano"] == 120.5
    closed_item = next(
        row for row in after_closing.json()["itens"] if row["id_uc"] == "UC900101"
    )
    assert closed_item["ordem_aberta"] is None
    with synthetic_engine.connect() as connection:
        assert (
            connection.execute(text("SELECT count(*) FROM fila_inspecao")).scalar_one()
            == 8
        )


def test_invalid_and_active_mixed_batches_leave_no_partial_rows(
    synthetic_engine: Engine,
) -> None:
    with synthetic_engine.begin() as connection:
        connection.execute(
            insert(ORDENS_INSPECAO).values(id_uc="UC900103", status="EM_CAMPO")
        )
    app.dependency_overrides[get_order_repositories] = lambda: _post_repositories(
        synthetic_engine
    )
    try:
        client = TestClient(app)
        missing = client.post(
            "/api/inspections/order", json={"ids_uc": ["UC900104", "UC900299"]}
        )
        outside = client.post(
            "/api/inspections/order", json={"ids_uc": ["UC900104", "UC900199"]}
        )
        active = client.post(
            "/api/inspections/order", json={"ids_uc": ["UC900104", "UC900103"]}
        )
    finally:
        app.dependency_overrides.clear()
    assert missing.status_code == 422
    assert outside.status_code == 422
    assert active.status_code == 409
    assert "UC900103" in active.json()["detail"]
    with synthetic_engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT count(*) FROM ordens_inspecao WHERE id_uc = 'UC900104'")
            ).scalar_one()
            == 0
        )


def test_operational_failure_rolls_back_inserted_order(
    synthetic_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = InspectionOrdersRepository.insert_orders

    def fail_after_first(self: InspectionOrdersRepository, ids_uc: list[str]):
        original(self, ids_uc[:1])
        raise RuntimeError("falha operacional sintética")

    monkeypatch.setattr(InspectionOrdersRepository, "insert_orders", fail_after_first)
    app.dependency_overrides[get_order_repositories] = lambda: _post_repositories(
        synthetic_engine
    )
    try:
        response = TestClient(app).post(
            "/api/inspections/order", json={"ids_uc": ["UC900105", "UC900106"]}
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 500
    assert response.json() == {"detail": "Erro interno"}
    with synthetic_engine.connect() as connection:
        assert (
            connection.execute(
                text(
                    "SELECT count(*) FROM ordens_inspecao WHERE id_uc IN ('UC900105','UC900106')"
                )
            ).scalar_one()
            == 0
        )


def test_concurrent_post_requests_create_only_one_active_order(
    synthetic_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    barrier = Barrier(2)
    lock = Lock()
    calls = 0
    original = InspectionOrdersRepository.get_active_orders

    def synchronized_check(self: InspectionOrdersRepository, ids_uc: list[str]):
        nonlocal calls
        rows = original(self, ids_uc)
        if ids_uc == ["UC900107"] and not rows:
            with lock:
                calls += 1
                wait = calls <= 2
            if wait:
                barrier.wait(timeout=3)
        return rows

    monkeypatch.setattr(
        InspectionOrdersRepository, "get_active_orders", synchronized_check
    )
    app.dependency_overrides[get_order_repositories] = lambda: _post_repositories(
        synthetic_engine
    )

    def post():
        return TestClient(app).post(
            "/api/inspections/order", json={"ids_uc": ["UC900107"]}
        )

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            responses = list(executor.map(lambda _: post(), range(2)))
    finally:
        app.dependency_overrides.clear()
    assert sorted(response.status_code for response in responses) == [201, 409]
    assert "UC900107" in next(
        response.json()["detail"]
        for response in responses
        if response.status_code == 409
    )
    with synthetic_engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT count(*) FROM ordens_inspecao WHERE id_uc = 'UC900107'")
            ).scalar_one()
            == 1
        )
