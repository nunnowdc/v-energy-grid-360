"""Fluxo HTTP da página com Gold sintética e ordens em PostgreSQL descartável."""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.controllers.inspections import (
    get_inspections_repository,
    get_order_repositories,
)
from app.main import app
from app.repositories.inspections import InspectionsRepository

pytest_plugins = ("test_inspection_orders_postgres",)


@pytest.fixture(scope="module")
def page_engine(orders_engine: Engine) -> Engine:
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
        units = [
            ("UC902101", "Recife", "Boa Viagem", "RESIDENCIAL", 1, 100.5),
            ("UC902102", "Recife", "Boa Viagem", "RESIDENCIAL", 2, 200.5),
            ("UC902103", "Recife", "Boa Viagem", "RESIDENCIAL", 3, 300.5),
            ("UC902104", "Olinda", "Bairro Novo", "COMERCIAL", 4, 400.5),
        ]
        for uc, municipio, bairro, classe, priority, energy in units:
            connection.execute(
                text(
                    "INSERT INTO dim_unidade_consumidora "
                    "(id_uc, municipio, bairro, classe) "
                    "VALUES (:uc, :municipio, :bairro, :classe)"
                ),
                {"uc": uc, "municipio": municipio, "bairro": bairro, "classe": classe},
            )
            connection.execute(
                text(
                    "INSERT INTO fila_inspecao "
                    "(id_uc, data_referencia, prioridade, score, motivo_suspeita, "
                    "kwh_recuperavel_estimado_ano, municipio, bairro, classe) "
                    "VALUES (:uc, :reference, :priority, 73, 'Motivo sintético', "
                    ":energy, :municipio, :bairro, :classe)"
                ),
                {
                    "uc": uc,
                    "reference": date(2026, 6, 1),
                    "priority": priority,
                    "energy": energy,
                    "municipio": municipio,
                    "bairro": bairro,
                    "classe": classe,
                },
            )
        connection.execute(
            text(
                "INSERT INTO dim_unidade_consumidora "
                "(id_uc, municipio, bairro, classe) VALUES "
                "('UC902105', 'Recife', 'Boa Viagem', 'RESIDENCIAL')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO ordens_inspecao (id_uc, status, resultado, concluida_em) "
                "VALUES ('UC902105', 'CONCLUIDA', 'SEM_IRREGULARIDADE', now())"
            )
        )
    return orders_engine


@contextmanager
def _client(engine: Engine) -> Iterator[TestClient]:
    @contextmanager
    def repositories():  # type: ignore[no-untyped-def]
        with engine.connect() as connection:
            gold = InspectionsRepository(connection)
            yield gold, gold.orders

    @contextmanager
    def queue_repository():  # type: ignore[no-untyped-def]
        with engine.connect() as connection:
            yield InspectionsRepository(connection)

    app.dependency_overrides[get_order_repositories] = lambda: repositories()
    app.dependency_overrides[get_inspections_repository] = lambda: queue_repository()
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_page_flow_filters_cards_and_history(page_engine: Engine) -> None:
    recife = "municipio=Recife&bairro=Boa%20Viagem&classe=RESIDENCIAL"
    with _client(page_engine) as client:
        queue_url = f"/api/inspections/queue?{recife}&limite=1"
        first_page = client.get(queue_url).json()
        assert first_page["total"] == first_page["resumo"]["ucs"] == 3
        assert first_page["resumo"]["kwh_recuperavel_estimado_ano"] == 601.5
        assert first_page["data_referencia"] == "2026-06-01"
        assert first_page["itens"][0]["ordem_aberta"] is None
        assert set(first_page["itens"][0]) == {
            "prioridade",
            "id_uc",
            "score",
            "motivo_suspeita",
            "kwh_recuperavel_estimado_ano",
            "municipio",
            "bairro",
            "classe",
            "ordem_aberta",
        }
        second_page = client.get(f"{queue_url}&pagina=2").json()
        assert second_page["itens"][0]["id_uc"] == "UC902102"
        assert second_page["resumo"] == first_page["resumo"]

        created = client.post(
            "/api/inspections/order",
            json={"ids_uc": ["UC902101", "UC902102", "UC902103", "UC902104"]},
        )
        assert created.status_code == 201
        ids = {item["id_uc"]: item["id_ordem"] for item in created.json()["ordens"]}
        assert len(ids) == 4
        for item in created.json()["ordens"]:
            stamp = datetime.fromisoformat(item["criada_em"])
            assert stamp.utcoffset() is not None
            assert stamp.astimezone(ZoneInfo("America/Recife")).tzinfo is not None
            assert set(item) == {
                "id_ordem",
                "id_uc",
                "municipio",
                "bairro",
                "status",
                "resultado",
                "criada_em",
                "criada_por_nome",
                "atualizada_por_nome",
            }

        duplicate = client.post("/api/inspections/order", json={"ids_uc": ["UC902101"]})
        assert duplicate.status_code == 409
        initial_orders = client.get(f"/api/inspections/orders?{recife}").json()["itens"]
        assert (
            len(
                [
                    item
                    for item in initial_orders
                    if item["status"] in {"ABERTA", "EM_CAMPO"}
                ]
            )
            == 3
        )
        assert [
            item["id_uc"] for item in initial_orders if item["status"] == "CONCLUIDA"
        ] == ["UC902105"]
        assert client.get(queue_url).json()["itens"][0]["ordem_aberta"] == {
            "id_ordem": ids["UC902101"],
            "status": "ABERTA",
        }

        for uc in ("UC902101", "UC902102"):
            assert (
                client.patch(
                    f"/api/inspections/{ids[uc]}", json={"status": "EM_CAMPO"}
                ).status_code
                == 200
            )
        for uc, result in (
            ("UC902101", "IRREGULARIDADE_CONFIRMADA"),
            ("UC902102", "SEM_IRREGULARIDADE"),
        ):
            assert (
                client.patch(
                    f"/api/inspections/{ids[uc]}",
                    json={"status": "CONCLUIDA", "resultado": result},
                ).status_code
                == 200
            )
        assert (
            client.delete(f"/api/inspections/{ids['UC902103']}").json()["status"]
            == "CANCELADA"
        )

        orders = client.get(f"/api/inspections/orders?{recife}")
        assert orders.status_code == 200
        statuses = {item["id_uc"]: item["status"] for item in orders.json()["itens"]}
        assert statuses == {
            "UC902101": "CONCLUIDA",
            "UC902102": "CONCLUIDA",
            "UC902103": "CANCELADA",
            "UC902105": "CONCLUIDA",
        }
        concluded = [
            item for item in orders.json()["itens"] if item["status"] == "CONCLUIDA"
        ]
        assert len(concluded) == 3
        assert (
            sum(item["resultado"] == "IRREGULARIDADE_CONFIRMADA" for item in concluded)
            == 1
        )
        assert not any(
            item["status"] in {"ABERTA", "EM_CAMPO"} for item in orders.json()["itens"]
        )
        assert (
            client.get("/api/inspections/orders?municipio=Olinda").json()["itens"][0][
                "id_uc"
            ]
            == "UC902104"
        )
        after = client.get(queue_url).json()
        assert after["resumo"] == first_page["resumo"]
        assert after["itens"][0]["ordem_aberta"] is None
        assert (
            client.post(
                "/api/inspections/order", json={"ids_uc": ["UC902101"]}
            ).status_code
            == 201
        )

        history = client.get(f"/api/inspections/orders?{recife}").json()["itens"]
        assert any(item["id_uc"] == "UC902105" for item in history)


def test_openapi_lists_five_routes_and_errors() -> None:
    with TestClient(app) as client:
        paths = client.get("/api/openapi.json").json()["paths"]
    assert "get" in paths["/api/inspections/queue"]
    assert "post" in paths["/api/inspections/order"]
    assert "get" in paths["/api/inspections/orders"]
    assert "patch" in paths["/api/inspections/{id}"]
    assert "delete" in paths["/api/inspections/{id}"]
    for path, method in (
        ("/api/inspections/order", "post"),
        ("/api/inspections/{id}", "patch"),
        ("/api/inspections/{id}", "delete"),
    ):
        assert "409" in paths[path][method]["responses"]
