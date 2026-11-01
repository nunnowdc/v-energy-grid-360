"""Contrato HTTP das transições e do cancelamento de ordens."""

from contextlib import nullcontext
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.controllers.inspections import get_order_repositories
from app.main import app


class OrdersFake:
    def __init__(self, status: str = "ABERTA") -> None:
        self.row = {
            "id": 1,
            "id_uc": "UC123456",
            "municipio": "Recife",
            "bairro": "Boa Viagem",
            "status": status,
            "resultado": None,
            "criada_em": datetime(2026, 10, 28, 13, 44, tzinfo=UTC),
        }

    def transaction(self):
        return nullcontext()

    def get_order(self, order_id: int):
        return self.row if order_id == 1 else None

    def update_if_status(
        self, order_id, expected_status, status, resultado, *, user_id
    ):
        if self.row["status"] != expected_status:
            return False
        self.row["status"] = status
        self.row["resultado"] = resultado
        self.updated_by = user_id
        return True


def request(method: str, path: str, body=None, orders=None):
    app.dependency_overrides[get_order_repositories] = lambda: nullcontext(
        (object(), orders or OrdersFake())
    )
    try:
        if body is None:
            return TestClient(app).request(method, path)
        return TestClient(app).request(method, path, json=body)
    finally:
        app.dependency_overrides.clear()


def test_patch_moves_open_order_to_field_with_frontend_schema() -> None:
    response = request("PATCH", "/api/inspections/OI-00001", {"status": "EM_CAMPO"})
    assert response.status_code == 200
    assert response.json() == {
        "id_ordem": "OI-00001",
        "id_uc": "UC123456",
        "municipio": "Recife",
        "bairro": "Boa Viagem",
        "status": "EM_CAMPO",
        "resultado": None,
        "criada_em": "2026-10-28T13:44:00Z",
    }


def test_patch_concludes_order_with_either_canonical_result() -> None:
    for result in ("IRREGULARIDADE_CONFIRMADA", "SEM_IRREGULARIDADE"):
        response = request(
            "PATCH",
            "/api/inspections/OI-00001",
            {"status": "CONCLUIDA", "resultado": result},
            OrdersFake("EM_CAMPO"),
        )
        assert response.status_code == 200
        assert response.json()["status"] == "CONCLUIDA"
        assert response.json()["resultado"] == result


def test_delete_cancels_open_or_field_order_and_returns_same_schema() -> None:
    for status in ("ABERTA", "EM_CAMPO"):
        response = request(
            "DELETE", "/api/inspections/OI-00001", orders=OrdersFake(status)
        )
        assert response.status_code == 200
        assert response.json()["status"] == "CANCELADA"
        assert response.json()["resultado"] is None
        assert set(response.json()) == {
            "id_ordem",
            "id_uc",
            "municipio",
            "bairro",
            "status",
            "resultado",
            "criada_em",
        }


def test_incompatible_repeated_and_terminal_transitions_return_409() -> None:
    cases = [
        ("PATCH", "ABERTA", {"status": "CONCLUIDA", "resultado": "SEM_IRREGULARIDADE"}),
        ("PATCH", "EM_CAMPO", {"status": "EM_CAMPO"}),
        ("PATCH", "CONCLUIDA", {"status": "EM_CAMPO"}),
        ("PATCH", "CANCELADA", {"status": "EM_CAMPO"}),
        ("DELETE", "CONCLUIDA", None),
        ("DELETE", "CANCELADA", None),
    ]
    for method, status, body in cases:
        response = request(
            method, "/api/inspections/OI-00001", body, OrdersFake(status)
        )
        assert response.status_code == 409


def test_invalid_body_and_order_id_return_422() -> None:
    invalid_bodies = [
        {},
        {"status": "CONCLUIDA"},
        {"status": "CONCLUIDA", "resultado": "OUTRO"},
        {"status": "EM_CAMPO", "resultado": "SEM_IRREGULARIDADE"},
        {"status": "ABERTA"},
        {"status": "EM_CAMPO", "extra": 1},
    ]
    for body in invalid_bodies:
        assert request("PATCH", "/api/inspections/OI-00001", body).status_code == 422
    for order_id in ("1", "OI-1", "OI-000001", "OI-9999999999999999999"):
        assert request("DELETE", f"/api/inspections/{order_id}").status_code == 422


def test_unknown_order_returns_404() -> None:
    assert (
        request(
            "PATCH", "/api/inspections/OI-00002", {"status": "EM_CAMPO"}
        ).status_code
        == 404
    )
    assert request("DELETE", "/api/inspections/OI-00002").status_code == 404


def test_conditional_update_rejects_concurrent_state_change() -> None:
    class RaceOrders(OrdersFake):
        def update_if_status(self, order_id, expected_status, status, resultado, **_):
            self.row["status"] = "CANCELADA"
            return False

    response = request(
        "PATCH", "/api/inspections/OI-00001", {"status": "EM_CAMPO"}, RaceOrders()
    )
    assert response.status_code == 409


def test_openapi_documents_mutations_and_errors() -> None:
    paths = TestClient(app).get("/api/openapi.json").json()["paths"]
    for method in ("patch", "delete"):
        responses = paths["/api/inspections/{id}"][method]["responses"]
        assert set(responses) >= {"200", "404", "409", "422", "503", "500"}


def test_patch_and_cancel_record_the_session_account_as_last_author() -> None:
    for method, body in (("PATCH", {"status": "EM_CAMPO"}), ("DELETE", None)):
        orders = OrdersFake()
        response = request(method, "/api/inspections/OI-00001", body, orders)

        assert response.status_code == 200
        assert str(orders.updated_by) == "550e8400-e29b-41d4-a716-446655440000"
