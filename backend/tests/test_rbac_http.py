"""Autorização HTTP dos endpoints registrados pelo perfil persistido."""

from contextlib import nullcontext
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
import pytest
from fastapi import APIRouter, Depends, FastAPI
from fastapi.testclient import TestClient

from app.controllers.filters import get_filter_repository
from app.main import app
from app.security.dependencies import (
    authorize_business_route,
    get_user_repository,
)
from app.security.permissions import PUBLIC_ROUTES, ROUTE_PERMISSIONS
from app.security.tokens import COOKIE_NAME, issue_token

USER_ID = UUID("550e8400-e29b-41d4-a716-446655440000")
SECRET = "segredo-sintetico-para-testes-com-mais-de-32-caracteres"
PROFILES = ("DIRETORIA", "ATENDIMENTO", "PERDAS", "OPERACAO", "ADMIN_TI")
ALL = frozenset(PROFILES)
DIRECTORS = frozenset({"DIRETORIA", "ADMIN_TI"})
UC = frozenset({"ATENDIMENTO", "PERDAS", "ADMIN_TI"})
LOSSES = frozenset({"PERDAS", "ADMIN_TI"})
NETWORK = frozenset({"DIRETORIA", "OPERACAO", "ADMIN_TI"})

# Entradas independentes do mapa de produção; cada método e caminho é exercitado.
CASES = (
    ("GET", "/api/filters/options", ALL),
    ("GET", "/api/metrics/general?inicio=bad&fim=bad", DIRECTORS),
    ("GET", "/api/metrics/revenue-variance?inicio_p0=bad", DIRECTORS),
    ("GET", "/api/network/continuity?inicio=bad&fim=bad", NETWORK),
    ("GET", "/api/uc/INVALID/360", UC),
    ("GET", "/api/inspections/queue?pagina=0", LOSSES),
    ("GET", "/api/inspections/queue/export?bairro=sem_municipio", LOSSES),
    ("GET", "/api/inspections/orders?bairro=sem_municipio", LOSSES),
    ("POST", "/api/inspections/order", LOSSES),
    ("PATCH", "/api/inspections/OI-INVALID", LOSSES),
    ("DELETE", "/api/inspections/OI-INVALID", LOSSES),
    ("POST", "/api/ai/ask", ALL),
    ("GET", "/api/ai/insights/teste/entidade", ALL),
    ("POST", "/api/ai/feedback", ALL),
    ("GET", "/api/ai/audit/nao-existe", frozenset({"ADMIN_TI"})),
)


class FakeUsers:
    def __init__(self) -> None:
        self.profile = "ADMIN_TI"
        self.exists = True

    def get_by_id(self, user_id):
        if not self.exists or user_id != USER_ID:
            return None
        return {
            "id": USER_ID,
            "nome": "Pessoa Fictícia",
            "email": "pessoa@example.invalid",
            "perfil": self.profile,
        }


@pytest.fixture
def session_client(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", SECRET)
    users = FakeUsers()
    app.dependency_overrides[get_user_repository] = lambda: nullcontext(users)
    client = TestClient(app, raise_server_exceptions=False)
    try:
        yield client, users
    finally:
        app.dependency_overrides.clear()


def _call(client, method, path):
    if method in {"POST", "PATCH"}:
        return client.request(method, path, json={})
    return client.request(method, path)


def test_filters_requires_authentication_before_gold_query() -> None:
    response = TestClient(app).get("/api/filters/options")
    assert response.status_code == 401


@pytest.mark.parametrize("method,path,_allowed", CASES)
def test_all_business_methods_require_a_valid_cookie(method, path, _allowed):
    assert _call(TestClient(app), method, path).status_code == 401


@pytest.mark.parametrize("method,path,allowed", CASES)
@pytest.mark.parametrize("profile", PROFILES)
def test_persisted_profile_controls_each_business_route(
    session_client, method, path, allowed, profile, monkeypatch
):
    client, users = session_client
    users.profile = profile
    client.cookies.set(COOKIE_NAME, issue_token(USER_ID))

    if method == "GET" and "/api/ai/insights/" in path:
        from src.insights.service import InsightsService

        monkeypatch.setattr(
            InsightsService,
            "obter",
            lambda _self, tela, entidade_id: {
                "tela": tela,
                "entidade_id": entidade_id,
                "insight_texto": "Resultado fictício",
            },
        )
    if method == "GET" and "/api/ai/audit/" in path:
        import psycopg2

        monkeypatch.setattr(
            psycopg2,
            "connect",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("teste")),
        )

    response = _call(client, method, path)
    if profile in allowed:
        assert response.status_code not in {401, 403}
    else:
        assert response.status_code == 403
        assert response.json() == {"detail": "Acesso não permitido"}


def test_profile_changes_in_database_apply_without_new_token(session_client):
    client, users = session_client
    client.cookies.set(COOKIE_NAME, issue_token(USER_ID))
    users.profile = "ATENDIMENTO"
    assert client.get("/api/metrics/general?inicio=bad&fim=bad").status_code == 403
    users.profile = "DIRETORIA"
    assert client.get("/api/metrics/general?inicio=bad&fim=bad").status_code != 403
    assert client.get("/api/inspections/queue?pagina=0").status_code == 403


def test_claimed_profile_cannot_override_persisted_profile(session_client):
    client, users = session_client
    users.profile = "ATENDIMENTO"
    token = jwt.encode(
        {
            "sub": str(USER_ID),
            "perfil": "ADMIN_TI",
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(minutes=15),
        },
        SECRET,
        algorithm="HS256",
    )
    client.cookies.set(COOKIE_NAME, token)
    assert client.get("/api/metrics/general?inicio=bad&fim=bad").status_code == 403


@pytest.mark.parametrize("profile", PROFILES)
def test_auth_endpoints_preserve_shared_and_admin_permissions(session_client, profile):
    client, users = session_client
    users.profile = profile
    client.cookies.set(COOKIE_NAME, issue_token(USER_ID))
    assert client.get("/api/auth/me").status_code == 200
    assert client.patch("/api/auth/password", json={}).status_code == 422
    assert client.post("/api/auth/users", json={}).status_code == (
        422 if profile == "ADMIN_TI" else 403
    )
    assert client.post("/api/auth/logout").status_code == 204


def test_authorized_business_response_retains_contract(session_client):
    from test_filters_http import GoldOptionsFake

    client, users = session_client
    users.profile = "OPERACAO"
    client.cookies.set(COOKIE_NAME, issue_token(USER_ID))
    app.dependency_overrides[get_filter_repository] = lambda: nullcontext(
        GoldOptionsFake()
    )
    response = client.get("/api/filters/options")
    assert response.status_code == 200
    assert response.json()["classes"] == ["RESIDENCIAL", "RURAL"]


def test_write_origin_is_independent_of_rbac(session_client):
    client, users = session_client
    users.profile = "PERDAS"
    client.cookies.set(COOKIE_NAME, issue_token(USER_ID))
    for origin in ("http://localhost:5173", "http://127.0.0.1:8000"):
        assert (
            client.post(
                "/api/inspections/order", json={}, headers={"Origin": origin}
            ).status_code
            == 422
        )
    assert client.post("/api/inspections/order", json={}).status_code == 422
    response = client.post(
        "/api/inspections/order",
        json={},
        headers={"Origin": "http://example.invalid"},
    )
    assert response.status_code == 403
    assert response.json() == {"detail": "Origem não autorizada"}


def test_similar_paths_and_different_methods_do_not_inherit_permission(session_client):
    client, users = session_client
    users.profile = "ADMIN_TI"
    client.cookies.set(COOKIE_NAME, issue_token(USER_ID))
    assert client.get("/api/metrics/general-extra").status_code == 404
    assert client.post("/api/metrics/general", json={}).status_code == 405


def test_invalid_expired_and_unknown_user_are_unauthenticated(session_client):
    client, users = session_client
    client.cookies.set(COOKIE_NAME, "invalid-jwt")
    assert client.get("/api/filters/options").status_code == 401
    expired = jwt.encode(
        {
            "sub": str(USER_ID),
            "iat": datetime.now(UTC) - timedelta(hours=1),
            "exp": datetime.now(UTC) - timedelta(minutes=45),
        },
        SECRET,
        algorithm="HS256",
    )
    client.cookies.set(COOKIE_NAME, expired)
    assert client.get("/api/filters/options").status_code == 401
    users.exists = False
    client.cookies.set(COOKIE_NAME, issue_token(USER_ID))
    assert client.get("/api/filters/options").status_code == 401


def test_public_routes_stay_public_without_cookie():
    client = TestClient(app)
    for path in ("/api/health", "/api/docs", "/api/redoc", "/api/openapi.json"):
        assert client.get(path).status_code == 200
    assert client.post("/api/auth/login", json={}).status_code == 422


def test_registered_routes_match_approved_matrix():
    implemented = {
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        for method in operations
    }
    documentation_routes = {
        ("GET", "/api/docs"),
        ("GET", "/api/openapi.json"),
        ("GET", "/api/redoc"),
    }
    assert (
        implemented
        == set(PUBLIC_ROUTES | ROUTE_PERMISSIONS.keys()) - documentation_routes
    )


def test_openapi_documents_authentication_and_permission_errors():
    paths = app.openapi()["paths"]
    for method, path in ROUTE_PERMISSIONS:
        if path.startswith("/api/auth/"):
            continue
        operation = paths[path][method.lower()]
        assert {"401", "403"} <= set(operation["responses"])


def test_unmapped_route_is_denied_even_for_admin(session_client):
    client, _users = session_client
    isolated = FastAPI()
    router = APIRouter(dependencies=[Depends(authorize_business_route)])

    @router.get("/unmapped")
    def unmapped():
        return {"ok": True}

    isolated.include_router(router)
    isolated.dependency_overrides[get_user_repository] = app.dependency_overrides[
        get_user_repository
    ]
    client = TestClient(isolated)
    client.cookies.set(COOKIE_NAME, issue_token(USER_ID))
    assert client.get("/unmapped").status_code == 403
