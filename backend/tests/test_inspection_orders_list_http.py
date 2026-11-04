"""Contrato HTTP da listagem histórica de ordens de inspeção."""

from contextlib import nullcontext
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.controllers.inspections import get_order_repositories
from app.main import app


class GoldFake:
    def get_catalog(self):
        return [(",", None), ("Recife", "Boa Viagem"), ("Recife", "Centro")], [
            "RESIDENCIAL",
            "COMERCIAL",
        ]


class OrdersFake:
    def list_orders(self, municipio, bairro, classe):
        return [
            {
                "id": 100001,
                "id_uc": "UC123456",
                "municipio": "Recife",
                "bairro": "Boa Viagem",
                "status": "CONCLUIDA",
                "resultado": "SEM_IRREGULARIDADE",
                "criada_em": datetime(2026, 10, 28, 13, 44, tzinfo=UTC),
                "criada_por_nome": "Pessoa que gerou",
                "atualizada_por_nome": "Pessoa que concluiu",
            }
        ]


def get_orders(path: str, gold=None, orders=None):
    app.dependency_overrides[get_order_repositories] = lambda: nullcontext(
        (gold or GoldFake(), orders or OrdersFake())
    )
    try:
        return TestClient(app).get(path)
    finally:
        app.dependency_overrides.clear()


def test_orders_http_contract_and_full_order_id() -> None:
    response = get_orders("/api/inspections/orders")
    assert response.status_code == 200
    assert response.json() == {
        "itens": [
            {
                "id_ordem": "OI-100001",
                "id_uc": "UC123456",
                "municipio": "Recife",
                "bairro": "Boa Viagem",
                "status": "CONCLUIDA",
                "resultado": "SEM_IRREGULARIDADE",
                "criada_em": "2026-10-28T13:44:00Z",
                "criada_por_nome": "Pessoa que gerou",
                "atualizada_por_nome": "Pessoa que concluiu",
            }
        ]
    }


def test_orders_empty_recorte_returns_200() -> None:
    class EmptyOrders(OrdersFake):
        def list_orders(self, municipio, bairro, classe):
            return []

    response = get_orders("/api/inspections/orders", orders=EmptyOrders())
    assert response.status_code == 200
    assert response.json() == {"itens": []}


def test_orders_invalid_queries_return_422() -> None:
    paths = [
        "/api/inspections/orders?bairro=Boa%20Viagem",
        "/api/inspections/orders?municipio=Recife&bairro=Outro",
        "/api/inspections/orders?municipio=Outro",
        "/api/inspections/orders?classe=Outra",
        "/api/inspections/orders?municipio=Recife&municipio=Recife",
        "/api/inspections/orders?desconhecido=1",
        "/api/inspections/orders?pagina=1",
    ]
    assert all(get_orders(path).status_code == 422 for path in paths)


def test_orders_database_unavailable_is_503_without_internal_details() -> None:
    class UnavailableOrders(OrdersFake):
        def list_orders(self, municipio, bairro, classe):
            raise OperationalError("SELECT secret", {}, ConnectionError("private"))

    response = get_orders("/api/inspections/orders", orders=UnavailableOrders())
    assert response.status_code == 503
    assert response.json() == {"detail": "Gold indisponível"}
    assert "secret" not in response.text


def test_orders_unexpected_failure_is_500_without_internal_details() -> None:
    class BrokenOrders(OrdersFake):
        def list_orders(self, municipio, bairro, classe):
            raise ValueError("SQL internal details")

    response = get_orders("/api/inspections/orders", orders=BrokenOrders())
    assert response.status_code == 500
    assert response.json() == {"detail": "Erro interno"}
    assert "SQL" not in response.text


def test_orders_openapi_documents_response_and_errors() -> None:
    operation = (
        TestClient(app)
        .get("/api/openapi.json")
        .json()["paths"]["/api/inspections/orders"]["get"]
    )
    assert set(operation["responses"]) >= {"200", "422", "503", "500"}
    assert {parameter["name"] for parameter in operation["parameters"]} == {
        "municipio",
        "bairro",
        "classe",
        "vgrid360_access_token",
    }
