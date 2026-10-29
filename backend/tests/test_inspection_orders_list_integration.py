"""Listagem histórica com ordens sintéticas em PostgreSQL descartável."""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import insert, select, text
from sqlalchemy.engine import Engine

from app.controllers.inspections import get_order_repositories
from app.main import app
from app.repositories.inspection_orders import ORDENS_INSPECAO
from app.repositories.inspections import InspectionsRepository

pytest_plugins = ("test_inspection_orders_postgres",)


@pytest.fixture(scope="module")
def historical_engine(orders_engine: Engine) -> Engine:
    """A Gold sintética contém cadastro, mas nenhuma fila de suspeitas."""
    with orders_engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE dim_unidade_consumidora ("
            "id_uc TEXT PRIMARY KEY, municipio TEXT, bairro TEXT, classe TEXT)"
        )
        connection.execute(
            text(
                "INSERT INTO dim_unidade_consumidora "
                "(id_uc, municipio, bairro, classe) VALUES "
                "(:id_uc, :municipio, :bairro, :classe)"
            ),
            [
                {
                    "id_uc": "UC900201",
                    "municipio": "Recife",
                    "bairro": "Boa Viagem",
                    "classe": "RESIDENCIAL",
                },
                {
                    "id_uc": "UC900202",
                    "municipio": "Recife",
                    "bairro": "Centro",
                    "classe": "COMERCIAL",
                },
                {
                    "id_uc": "UC900203",
                    "municipio": "Olinda",
                    "bairro": "Bairro Novo",
                    "classe": "RESIDENCIAL",
                },
                {
                    "id_uc": "UC900204",
                    "municipio": "Recife",
                    "bairro": "Boa Viagem",
                    "classe": "COMERCIAL",
                },
            ],
        )
        same_time = datetime(2026, 10, 28, 13, 44, tzinfo=UTC)
        connection.execute(
            insert(ORDENS_INSPECAO),
            [
                {
                    "id_uc": "UC900201",
                    "status": "ABERTA",
                    "resultado": None,
                    "concluida_em": None,
                    "criada_em": datetime(2026, 10, 27, 10, tzinfo=UTC),
                },
                {
                    "id_uc": "UC900202",
                    "status": "EM_CAMPO",
                    "resultado": None,
                    "concluida_em": None,
                    "criada_em": datetime(2026, 10, 28, 10, tzinfo=UTC),
                },
                {
                    "id_uc": "UC900203",
                    "status": "CONCLUIDA",
                    "resultado": "IRREGULARIDADE_CONFIRMADA",
                    "concluida_em": datetime(2026, 10, 28, 16, tzinfo=UTC),
                    "criada_em": same_time,
                },
                {
                    "id_uc": "UC900204",
                    "status": "CANCELADA",
                    "resultado": None,
                    "concluida_em": None,
                    "criada_em": same_time,
                },
            ],
        )
    return orders_engine


def _request(engine: Engine, query: str = ""):
    from contextlib import contextmanager

    @contextmanager
    def repositories():
        with engine.connect() as connection:
            gold = InspectionsRepository(connection)
            yield gold, gold.orders

    app.dependency_overrides[get_order_repositories] = lambda: repositories()
    try:
        return TestClient(app).get("/api/inspections/orders" + query)
    finally:
        app.dependency_overrides.clear()


def test_historical_orders_include_all_states_without_queue_dependency(
    historical_engine: Engine,
) -> None:
    with historical_engine.connect() as connection:
        before_orders = connection.execute(select(ORDENS_INSPECAO.c.id)).all()
        before_uc = connection.execute(
            text("SELECT count(*) FROM dim_unidade_consumidora")
        ).scalar_one()

    response = _request(historical_engine)
    assert response.status_code == 200
    items = response.json()["itens"]
    assert [item["status"] for item in items] == [
        "CANCELADA",
        "CONCLUIDA",
        "EM_CAMPO",
        "ABERTA",
    ]
    assert [item["id_uc"] for item in items] == [
        "UC900204",
        "UC900203",
        "UC900202",
        "UC900201",
    ]
    assert items[1]["resultado"] == "IRREGULARIDADE_CONFIRMADA"
    assert items[0]["resultado"] is None
    assert all(item["criada_em"].endswith(("Z", "+00:00")) for item in items)
    assert all(
        set(item)
        == {
            "id_ordem",
            "id_uc",
            "municipio",
            "bairro",
            "status",
            "resultado",
            "criada_em",
        }
        for item in items
    )
    assert len({item["id_ordem"] for item in items}) == 4

    with historical_engine.connect() as connection:
        assert connection.execute(select(ORDENS_INSPECAO.c.id)).all() == before_orders
        assert (
            connection.execute(
                text("SELECT count(*) FROM dim_unidade_consumidora")
            ).scalar_one()
            == before_uc
        )


@pytest.mark.parametrize(
    ("query", "ids"),
    [
        ("?municipio=Recife", {"UC900201", "UC900202", "UC900204"}),
        ("?bairro=Boa%20Viagem&municipio=Recife", {"UC900201", "UC900204"}),
        ("?classe=RESIDENCIAL", {"UC900201", "UC900203"}),
        ("?municipio=Recife&classe=COMERCIAL", {"UC900202", "UC900204"}),
        ("?municipio=Recife&bairro=Boa%20Viagem&classe=COMERCIAL", {"UC900204"}),
        (
            "?municipio=&bairro=&classe=",
            {"UC900201", "UC900202", "UC900203", "UC900204"},
        ),
    ],
)
def test_orders_filters_use_uc_dimension(
    historical_engine: Engine, query: str, ids: set[str]
) -> None:
    response = _request(historical_engine, query)
    assert response.status_code == 200
    assert {item["id_uc"] for item in response.json()["itens"]} == ids


def test_valid_empty_selection_and_invalid_pair(historical_engine: Engine) -> None:
    assert _request(historical_engine, "?municipio=Olinda&classe=COMERCIAL").json() == {
        "itens": []
    }
    assert (
        _request(
            historical_engine, "?municipio=Recife&bairro=Bairro%20Novo"
        ).status_code
        == 422
    )
