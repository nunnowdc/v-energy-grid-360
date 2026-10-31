"""Contratos HTTP de cadastro administrativo e troca da própria senha."""

from contextlib import nullcontext
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.main import app
from app.security.dependencies import get_user_repository
from app.security.passwords import hash_password, verify_password

ADMIN_ID = UUID("550e8400-e29b-41d4-a716-446655440000")
SECRET = "segredo-sintetico-para-testes-com-mais-de-32-caracteres"


class FakeUsers:
    def __init__(self) -> None:
        self.users = {
            ADMIN_ID: {
                "id": ADMIN_ID,
                "nome": "Admin Teste",
                "email": "admin@example.invalid",
                "perfil": "ADMIN_TI",
                "senha_hash": hash_password("senha antiga"),
            }
        }

    def get_by_email(self, email):
        return next((u for u in self.users.values() if u["email"] == email), None)

    def get_by_id(self, user_id):
        return self.users.get(user_id)

    def create(self, *, id, nome, email, senha_hash, perfil, criado_em):
        if self.get_by_email(email):
            return None
        self.users[id] = {
            "id": id,
            "nome": nome,
            "email": email,
            "senha_hash": senha_hash,
            "perfil": perfil,
            "criado_em": criado_em,
        }
        return self.users[id]

    def transaction(self):
        return nullcontext()

    def get_by_id_for_update(self, user_id):
        return self.get_by_id(user_id)

    def update_password(self, user_id, new_hash):
        self.users[user_id]["senha_hash"] = new_hash


@pytest.fixture
def auth_client(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", SECRET)
    users = FakeUsers()
    app.dependency_overrides[get_user_repository] = lambda: nullcontext(users)
    try:
        yield TestClient(app), users
    finally:
        app.dependency_overrides.clear()


def _login(client):
    return client.post(
        "/api/auth/login",
        json={"email": "admin@example.invalid", "senha": "senha antiga"},
    )


def test_admin_creates_user_with_public_response_and_normalized_email(auth_client):
    client, users = auth_client
    assert _login(client).status_code == 200

    response = client.post(
        "/api/auth/users",
        json={
            "nome": "Pessoa Teste",
            "email": "  PESSOA@EXAMPLE.INVALID  ",
            "perfil": "PERDAS",
            "senha": "senha inicial",
        },
    )

    assert response.status_code == 201
    assert set(response.json()) == {"id", "nome", "email", "perfil"}
    assert response.json()["email"] == "pessoa@example.invalid"
    stored = users.get_by_email("pessoa@example.invalid")
    assert stored is not None
    assert stored["senha_hash"].startswith("$argon2id$")
    assert verify_password("senha inicial", stored["senha_hash"])


def test_password_change_preserves_session_and_replaces_hash(auth_client):
    client, users = auth_client
    assert _login(client).status_code == 200
    cookie = client.cookies.get("vgrid360_access_token")
    previous_hash = users.get_by_id(ADMIN_ID)["senha_hash"]

    response = client.patch(
        "/api/auth/password",
        json={"senha_atual": "senha antiga", "nova_senha": "senha nova 123"},
    )

    assert response.status_code == 204
    assert response.content == b""
    assert "set-cookie" not in response.headers
    assert client.cookies.get("vgrid360_access_token") == cookie
    assert client.get("/api/auth/me").status_code == 200
    assert users.get_by_id(ADMIN_ID)["senha_hash"] != previous_hash
    assert _login(client).status_code == 401
    assert (
        client.post(
            "/api/auth/login",
            json={"email": "admin@example.invalid", "senha": "senha nova 123"},
        ).status_code
        == 200
    )


def test_user_creation_requires_admin_session(auth_client):
    client, users = auth_client
    body = {
        "nome": "Pessoa Teste",
        "email": "pessoa@example.invalid",
        "perfil": "PERDAS",
        "senha": "senha inicial",
    }
    assert client.post("/api/auth/users", json=body).status_code == 401
    for profile in ("DIRETORIA", "ATENDIMENTO", "PERDAS", "OPERACAO"):
        users.users[ADMIN_ID]["perfil"] = profile
        assert _login(client).status_code == 200
        assert client.post("/api/auth/users", json=body).status_code == 403
    assert users.get_by_email("pessoa@example.invalid") is None


def test_duplicate_email_returns_409_after_normalization(auth_client):
    client, users = auth_client
    assert _login(client).status_code == 200
    body = {
        "nome": "Pessoa Teste",
        "email": "pessoa@example.invalid",
        "perfil": "PERDAS",
        "senha": "senha inicial",
    }
    assert client.post("/api/auth/users", json=body).status_code == 201
    body["email"] = "  PESSOA@EXAMPLE.INVALID  "
    response = client.post("/api/auth/users", json=body)
    assert response.status_code == 409
    assert response.json() == {"detail": "Email já cadastrado"}
    assert len(users.users) == 2


@pytest.mark.parametrize(
    "change",
    [
        {"senha": "curta"},
        {"perfil": "DESCONHECIDO"},
        {"email": "sem-arroba"},
        {"email": "x" * 255 + "@"},
        {"nome": ""},
    ],
)
def test_invalid_creation_returns_422_without_new_user(auth_client, change):
    client, users = auth_client
    assert _login(client).status_code == 200
    body = {
        "nome": "Pessoa Teste",
        "email": "pessoa@example.invalid",
        "perfil": "PERDAS",
        "senha": "senha inicial",
    } | change
    response = client.post("/api/auth/users", json=body)
    assert response.status_code == 422
    if "senha" in change:
        assert change["senha"] not in response.text
    assert len(users.users) == 1


@pytest.mark.parametrize(
    "origin, expected",
    [
        (None, 201),
        ("http://localhost:5173", 201),
        ("http://127.0.0.1:5173", 201),
        ("http://127.0.0.1:8000", 201),
        ("http://localhost:5174", 403),
    ],
)
def test_origin_rules_apply_to_admin_creation(auth_client, origin, expected):
    client, users = auth_client
    assert _login(client).status_code == 200
    headers = {"Origin": origin} if origin is not None else {}
    response = client.post(
        "/api/auth/users",
        headers=headers,
        json={
            "nome": "Pessoa Teste",
            "email": "pessoa@example.invalid",
            "perfil": "PERDAS",
            "senha": "senha inicial",
        },
    )
    assert response.status_code == expected
    assert (users.get_by_email("pessoa@example.invalid") is not None) == (
        expected == 201
    )


def test_password_change_requires_current_password_and_valid_input(auth_client):
    client, users = auth_client
    assert (
        client.patch(
            "/api/auth/password",
            json={"senha_atual": "senha antiga", "nova_senha": "senha nova 123"},
        ).status_code
        == 401
    )
    assert _login(client).status_code == 200
    original_hash = users.get_by_id(ADMIN_ID)["senha_hash"]
    response = client.patch(
        "/api/auth/password",
        json={"senha_atual": "incorreta", "nova_senha": "senha nova 123"},
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "Senha atual inválida"}
    invalid = client.patch(
        "/api/auth/password",
        json={"senha_atual": "senha antiga", "nova_senha": "curta"},
    )
    assert invalid.status_code == 422
    assert "curta" not in invalid.text
    assert users.get_by_id(ADMIN_ID)["senha_hash"] == original_hash


@pytest.mark.parametrize(
    "profile", ("DIRETORIA", "ATENDIMENTO", "PERDAS", "OPERACAO", "ADMIN_TI")
)
def test_all_profiles_can_change_their_own_password(auth_client, profile):
    client, users = auth_client
    users.users[ADMIN_ID]["perfil"] = profile
    assert _login(client).status_code == 200
    assert (
        client.patch(
            "/api/auth/password",
            json={"senha_atual": "senha antiga", "nova_senha": "senha nova 123"},
        ).status_code
        == 204
    )
    assert verify_password("senha nova 123", users.get_by_id(ADMIN_ID)["senha_hash"])


def test_unknown_origin_rejects_password_change_without_modification(auth_client):
    client, users = auth_client
    assert _login(client).status_code == 200
    original_hash = users.get_by_id(ADMIN_ID)["senha_hash"]
    response = client.patch(
        "/api/auth/password",
        headers={"Origin": "http://localhost:5174"},
        json={"senha_atual": "senha antiga", "nova_senha": "senha nova 123"},
    )
    assert response.status_code == 403
    assert users.get_by_id(ADMIN_ID)["senha_hash"] == original_hash


def test_openapi_documents_new_contracts(auth_client):
    client, _ = auth_client
    paths = client.get("/api/openapi.json").json()["paths"]
    assert "post" in paths["/api/auth/users"]
    assert "patch" in paths["/api/auth/password"]


def test_database_failure_during_creation_returns_safe_503(auth_client, monkeypatch):
    client, users = auth_client
    assert _login(client).status_code == 200

    def fail(**_kwargs):
        raise OperationalError("INSERT segredo", None, RuntimeError("credencial"))

    monkeypatch.setattr(users, "create", fail)
    response = client.post(
        "/api/auth/users",
        json={
            "nome": "Pessoa Teste",
            "email": "pessoa@example.invalid",
            "perfil": "PERDAS",
            "senha": "senha inicial",
        },
    )
    assert response.status_code == 503
    assert "segredo" not in response.text
    assert "credencial" not in response.text


def test_database_failure_during_password_change_preserves_old_hash(
    auth_client, monkeypatch
):
    client, users = auth_client
    assert _login(client).status_code == 200
    original_hash = users.get_by_id(ADMIN_ID)["senha_hash"]

    def fail(_user_id, _new_hash):
        raise OperationalError("UPDATE segredo", None, RuntimeError("credencial"))

    monkeypatch.setattr(users, "update_password", fail)
    response = client.patch(
        "/api/auth/password",
        json={"senha_atual": "senha antiga", "nova_senha": "senha nova 123"},
    )
    assert response.status_code == 503
    assert "segredo" not in response.text
    assert "credencial" not in response.text
    assert users.get_by_id(ADMIN_ID)["senha_hash"] == original_hash


def test_unexpected_creation_failure_returns_safe_500(auth_client, monkeypatch):
    client, users = auth_client
    assert _login(client).status_code == 200

    def fail(**_kwargs):
        raise ValueError("detalhe interno sensível")

    monkeypatch.setattr(users, "create", fail)
    response = client.post(
        "/api/auth/users",
        json={
            "nome": "Pessoa Teste",
            "email": "pessoa@example.invalid",
            "perfil": "PERDAS",
            "senha": "senha inicial",
        },
    )
    assert response.status_code == 500
    assert response.json() == {"detail": "Erro interno"}


def test_unexpected_runtime_error_during_creation_returns_500(auth_client, monkeypatch):
    client, users = auth_client
    assert _login(client).status_code == 200

    def fail(**_kwargs):
        raise RuntimeError("detalhe interno sintético")

    monkeypatch.setattr(users, "create", fail)
    response = client.post(
        "/api/auth/users",
        json={
            "nome": "Pessoa Teste",
            "email": "pessoa@example.invalid",
            "perfil": "PERDAS",
            "senha": "senha inicial",
        },
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "Erro interno"}


def test_unexpected_runtime_error_during_password_change_returns_500(
    auth_client, monkeypatch
):
    client, users = auth_client
    assert _login(client).status_code == 200

    def fail(_user_id, _new_hash):
        raise RuntimeError("detalhe interno sintético")

    monkeypatch.setattr(users, "update_password", fail)
    response = client.patch(
        "/api/auth/password",
        json={"senha_atual": "senha antiga", "nova_senha": "senha nova 123"},
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "Erro interno"}
