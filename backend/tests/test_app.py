from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert client.get("/health").status_code == 404
    assert client.get("/api/api/health").status_code == 404


def test_openapi_and_docs() -> None:
    schema_response = client.get("/api/openapi.json")

    assert schema_response.status_code == 200
    assert "/api/health" in schema_response.json()["paths"]
    assert "/health" not in schema_response.json()["paths"]
    assert "/api/api/health" not in schema_response.json()["paths"]
    assert "/api/openapi.json" in client.get("/api/docs").text
    assert "/api/openapi.json" in client.get("/api/redoc").text
    for old_path in ("/openapi.json", "/docs", "/redoc"):
        assert client.get(old_path).status_code == 404


def test_openapi_groups_each_existing_operation_once() -> None:
    paths = client.get("/api/openapi.json").json()["paths"]
    expected = {
        ("POST", "/api/auth/login"): "Autenticação e Usuários",
        ("GET", "/api/auth/me"): "Autenticação e Usuários",
        ("POST", "/api/auth/logout"): "Autenticação e Usuários",
        ("POST", "/api/auth/users"): "Autenticação e Usuários",
        ("PATCH", "/api/auth/password"): "Autenticação e Usuários",
        ("GET", "/api/health"): "Health",
        ("GET", "/api/filters/options"): "Filtros",
        ("POST", "/api/inspections/order"): "Fila de Inspeção",
        ("GET", "/api/inspections/orders"): "Fila de Inspeção",
        ("PATCH", "/api/inspections/{id}"): "Fila de Inspeção",
        ("DELETE", "/api/inspections/{id}"): "Fila de Inspeção",
        ("GET", "/api/inspections/queue"): "Fila de Inspeção",
        ("GET", "/api/inspections/queue/export"): "Fila de Inspeção",
        ("GET", "/api/metrics/general"): "Indicadores",
        ("GET", "/api/metrics/revenue-variance"): "Receita",
        ("GET", "/api/network/continuity"): "Continuidade",
        ("GET", "/api/uc/{uc_id}/360"): "Visão 360",
        ("POST", "/api/ai/ask"): "Agente de IA",
        ("GET", "/api/ai/insights/{tela}/{entidade_id}"): "Agente de IA",
        ("GET", "/api/ai/audit/{audit_id}"): "Agente de IA",
        ("POST", "/api/ai/feedback"): "Agente de IA",
        ("GET", "/api/ai/usage"): "Agente de IA",
        ("GET", "/api/ai/evaluations"): "Agente de IA",
    }
    operations = {
        (method.upper(), path): operation
        for path, methods in paths.items()
        for method, operation in methods.items()
    }

    assert operations.keys() == expected.keys()
    for route, operation in operations.items():
        assert operation["tags"] == [expected[route]]
        if route[1] != "/api/health" and not route[1].startswith("/api/auth/"):
            assert {"401", "403"} <= operation["responses"].keys()


def test_local_cors() -> None:
    response = client.get("/api/health", headers={"Origin": "http://localhost:5173"})

    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_unknown_cors_origin() -> None:
    response = client.get("/api/health", headers={"Origin": "http://example.com"})

    assert "access-control-allow-origin" not in response.headers
