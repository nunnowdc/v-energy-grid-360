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


def test_local_cors() -> None:
    response = client.get("/api/health", headers={"Origin": "http://localhost:5173"})

    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_unknown_cors_origin() -> None:
    response = client.get("/api/health", headers={"Origin": "http://example.com"})

    assert "access-control-allow-origin" not in response.headers
