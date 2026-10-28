"""Contrato HTTP da criação atômica de ordens de inspeção."""

from contextlib import nullcontext
from datetime import UTC, date, datetime

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.main import app


class GoldFake:
    def get_snapshot_date(self) -> date:
        return date(2026, 6, 1)

    def get_existing_uc_ids(self, ids: list[str]) -> set[str]:
        return set(ids)

    def get_eligible_units(self, ids: list[str]) -> list[dict[str, str]]:
        return [
            {"id_uc": uc, "municipio": "Recife", "bairro": "Boa Viagem"} for uc in ids
        ]


class OrdersFake:
    def __init__(self) -> None:
        self.created: list[str] = []
        self.active: list[dict[str, object]] = []

    def transaction(self):
        return nullcontext()

    def get_active_orders(self, ids: list[str]) -> list[dict[str, object]]:
        return [row for row in self.active if row["id_uc"] in ids]

    def insert_orders(self, ids: list[str]) -> list[dict[str, object]]:
        self.created.extend(ids)
        return [
            {
                "id": index,
                "id_uc": uc,
                "status": "ABERTA",
                "resultado": None,
                "criada_em": datetime(2026, 10, 28, 13, 44, tzinfo=UTC),
            }
            for index, uc in enumerate(ids, start=1)
        ]


def test_post_order_creates_one_order_with_frontend_contract() -> None:
    from app.controllers.inspections import get_order_repositories

    app.dependency_overrides[get_order_repositories] = lambda: nullcontext(
        (GoldFake(), OrdersFake())
    )
    try:
        response = TestClient(app).post(
            "/api/inspections/order", json={"ids_uc": ["UC123456"]}
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json() == {
        "ordens": [
            {
                "id_ordem": "OI-00001",
                "id_uc": "UC123456",
                "municipio": "Recife",
                "bairro": "Boa Viagem",
                "status": "ABERTA",
                "resultado": None,
                "criada_em": "2026-10-28T13:44:00Z",
            }
        ]
    }


def post_orders(payload, gold=None, orders=None):
    from app.controllers.inspections import get_order_repositories

    app.dependency_overrides[get_order_repositories] = lambda: nullcontext(
        (gold or GoldFake(), orders or OrdersFake())
    )
    try:
        return TestClient(app).post("/api/inspections/order", json=payload)
    finally:
        app.dependency_overrides.clear()


def test_post_order_creates_all_requested_orders_in_input_order() -> None:
    response = post_orders({"ids_uc": ["UC123456", "UC123457"]})

    assert response.status_code == 201
    assert [order["id_uc"] for order in response.json()["ordens"]] == [
        "UC123456",
        "UC123457",
    ]
    assert [order["id_ordem"] for order in response.json()["ordens"]] == [
        "OI-00001",
        "OI-00002",
    ]


def test_order_id_does_not_truncate_after_five_digits() -> None:
    class LargeIdentity(OrdersFake):
        def insert_orders(self, ids):
            rows = super().insert_orders(ids)
            rows[0]["id"] = 123456
            return rows

    response = post_orders({"ids_uc": ["UC123456"]}, orders=LargeIdentity())
    assert response.status_code == 201
    assert response.json()["ordens"][0]["id_ordem"] == "OI-123456"


def test_invalid_body_and_malformed_identifiers_return_422() -> None:
    for body in (
        {"ids_uc": []},
        {"ids_uc": "UC123456"},
        {"ids_uc": ["UC123"]},
        {"ids_uc": [123456]},
        {"ids_uc": ["UC123456"], "extra": True},
    ):
        assert post_orders(body).status_code == 422


def test_duplicate_ids_return_422_without_inserting() -> None:
    orders = OrdersFake()
    response = post_orders({"ids_uc": ["UC123456", "UC123456"]}, orders=orders)
    assert response.status_code == 422
    assert orders.created == []


def test_nonexistent_or_ineligible_uc_returns_422_without_partial_creation() -> None:
    class MissingUc(GoldFake):
        def get_existing_uc_ids(self, ids):
            return {"UC123456"}

    class OutsideQueue(GoldFake):
        def get_eligible_units(self, ids):
            return super().get_eligible_units(["UC123456"])

    for gold in (MissingUc(), OutsideQueue()):
        orders = OrdersFake()
        response = post_orders(
            {"ids_uc": ["UC123456", "UC123457"]}, gold=gold, orders=orders
        )
        assert response.status_code == 422
        assert orders.created == []


def test_active_uc_returns_409_with_ids_and_no_partial_creation() -> None:
    orders = OrdersFake()
    orders.active = [{"id_uc": "UC123457", "id": 9, "status": "EM_CAMPO"}]
    response = post_orders({"ids_uc": ["UC123456", "UC123457"]}, orders=orders)
    assert response.status_code == 409
    assert response.json() == {"detail": "Já existe ordem ativa para as UCs: UC123457"}
    assert orders.created == []


def test_operational_failure_returns_generic_500_without_internal_details() -> None:
    class BrokenOrders(OrdersFake):
        def insert_orders(self, ids):
            raise RuntimeError("segredo SQL interno")

    response = post_orders({"ids_uc": ["UC123456"]}, orders=BrokenOrders())
    assert response.status_code == 500
    assert response.json() == {"detail": "Erro interno"}
    assert "segredo" not in response.text


def test_empty_gold_snapshot_returns_503_without_inserting() -> None:
    class EmptyGold(GoldFake):
        def get_snapshot_date(self):
            return None

    orders = OrdersFake()
    response = post_orders({"ids_uc": ["UC123456"]}, gold=EmptyGold(), orders=orders)
    assert response.status_code == 503
    assert response.json() == {"detail": "Fila Gold indisponível"}
    assert orders.created == []


def test_postgres_unavailable_returns_503_without_internal_details() -> None:
    class BrokenGold(GoldFake):
        def get_snapshot_date(self):
            raise OperationalError("SELECT secret", {}, ConnectionError("private"))

    response = post_orders({"ids_uc": ["UC123456"]}, gold=BrokenGold())
    assert response.status_code == 503
    assert response.json() == {"detail": "Banco indisponível"}
    assert "secret" not in response.text
