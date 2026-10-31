"""Contrato HTTP da autenticação básica com contas sintéticas."""

from contextlib import contextmanager, nullcontext
from uuid import UUID

import pytest
from app.main import app
from app.security.passwords import hash_password
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

USER_ID = UUID("550e8400-e29b-41d4-a716-446655440000")
SECRET = "segredo-sintetico-para-testes-com-mais-de-32-caracteres"


class FakeUsers:
    def __init__(self) -> None:
        self.user = {
            "id": USER_ID,
            "nome": "Usuário Teste",
            "email": "usuario@exemplo.com",
            "perfil": "ATENDIMENTO",
            "senha_hash": hash_password("senha-ficticia"),
        }
        self.lookups: list[str] = []

    def get_by_email(self, email: str):
        self.lookups.append(email)
        return self.user if email == self.user["email"] else None

    def get_by_id(self, user_id: UUID):
        return self.user if user_id == self.user["id"] else None


@pytest.fixture
def auth_client(monkeypatch):
    from app.security.dependencies import get_user_repository

    monkeypatch.setenv("JWT_SECRET_KEY", SECRET)
    users = FakeUsers()
    app.dependency_overrides[get_user_repository] = lambda: nullcontext(users)
    try:
        yield TestClient(app), users
    finally:
        app.dependency_overrides.clear()


def test_login_normaliza_email_e_define_cookie_sem_expor_token(auth_client) -> None:
    client, users = auth_client

    response = client.post(
        "/api/auth/login",
        json={"email": "  USUARIO@EXEMPLO.COM  ", "senha": "senha-ficticia"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": str(USER_ID),
        "nome": "Usuário Teste",
        "email": "usuario@exemplo.com",
        "perfil": "ATENDIMENTO",
    }
    assert users.lookups == ["usuario@exemplo.com"]
    cookie = response.headers["set-cookie"]
    assert "vgrid360_access_token=" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert "Max-Age=900" in cookie
    assert "Path=/" in cookie
    assert "Secure" not in cookie


def test_me_recarrega_perfil_e_logout_remove_cookie(auth_client) -> None:
    client, users = auth_client
    assert (
        client.post(
            "/api/auth/login",
            json={"email": "usuario@exemplo.com", "senha": "senha-ficticia"},
        ).status_code
        == 200
    )
    users.user["perfil"] = "PERDAS"

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["perfil"] == "PERDAS"

    logout = client.post("/api/auth/logout")
    assert logout.status_code == 204
    assert logout.content == b""
    assert "vgrid360_access_token=" in logout.headers["set-cookie"]
    assert client.get("/api/auth/me").status_code == 401


@pytest.mark.parametrize(
    "email, senha",
    [
        ("ausente@exemplo.com", "senha-ficticia"),
        ("usuario@exemplo.com", "senha-incorreta"),
    ],
)
def test_login_invalido_nao_revela_existencia_da_conta(
    auth_client, email, senha
) -> None:
    client, _ = auth_client
    response = client.post("/api/auth/login", json={"email": email, "senha": senha})
    assert response.status_code == 401
    assert response.json() == {"detail": "Credenciais inválidas"}
    assert "set-cookie" not in response.headers


@pytest.mark.parametrize(
    "body",
    [
        {"email": "invalido", "senha": "senha-ficticia"},
        {"email": "x" * 245 + "@exemplo.com", "senha": "senha-ficticia"},
        {"email": "usuario@exemplo.com"},
        {"email": "usuario@exemplo.com", "senha": "senha", "extra": 1},
    ],
)
def test_login_payload_invalido_retorna_422(auth_client, body) -> None:
    client, users = auth_client
    assert client.post("/api/auth/login", json=body).status_code == 422
    assert users.lookups == []


@pytest.mark.parametrize(
    "origin",
    [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000",
    ],
)
def test_login_aceita_origins_aprovadas(auth_client, origin) -> None:
    client, _ = auth_client
    response = client.post(
        "/api/auth/login",
        headers={"Origin": origin},
        json={"email": "usuario@exemplo.com", "senha": "senha-ficticia"},
    )
    assert response.status_code == 200


def test_origin_desconhecida_rejeita_login_e_logout(auth_client) -> None:
    client, users = auth_client
    response = client.post(
        "/api/auth/login",
        headers={"Origin": "http://localhost:5174"},
        json={"email": "usuario@exemplo.com", "senha": "senha-ficticia"},
    )
    assert response.status_code == 403
    assert users.lookups == []
    assert (
        client.post(
            "/api/auth/logout", headers={"Origin": "http://localhost:5174"}
        ).status_code
        == 403
    )


def test_origin_desconhecida_rejeita_escrita_existente_sem_rbac(auth_client) -> None:
    client, _ = auth_client
    response = client.post(
        "/api/inspections/order", headers={"Origin": "http://localhost:5174"}
    )
    assert response.status_code == 403


def test_cookie_ausente_nao_abre_banco(auth_client) -> None:
    client, users = auth_client
    assert client.get("/api/auth/me").status_code == 401
    assert client.post("/api/auth/logout").status_code == 401
    assert users.lookups == []


def test_login_com_cookie_previo_exige_credenciais_novas(auth_client) -> None:
    client, _ = auth_client
    valid = {"email": "usuario@exemplo.com", "senha": "senha-ficticia"}
    assert client.post("/api/auth/login", json=valid).status_code == 200
    previous_cookie = client.cookies.get("vgrid360_access_token")
    rejected = client.post(
        "/api/auth/login", json={**valid, "senha": "senha-incorreta"}
    )
    assert rejected.status_code == 401
    assert "set-cookie" not in rejected.headers
    assert client.cookies.get("vgrid360_access_token") == previous_cookie


def test_cors_permita_credenciais_apenas_ao_frontend(auth_client) -> None:
    client, _ = auth_client
    for origin in ("http://localhost:5173", "http://127.0.0.1:5173"):
        response = client.options(
            "/api/auth/login",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == origin
        assert response.headers["access-control-allow-credentials"] == "true"

    rejected = client.options(
        "/api/auth/login",
        headers={
            "Origin": "http://localhost:5174",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert rejected.status_code == 400


def test_falha_de_banco_retorna_503_sem_detalhes_e_fecha_contexto(
    auth_client, monkeypatch
) -> None:
    from app.security.dependencies import get_user_repository

    client, _ = auth_client
    closed = []

    @contextmanager
    def failing_repository():
        try:
            raise OperationalError("SELECT senha_hash", None, RuntimeError("segredo"))
            yield  # pragma: no cover
        finally:
            closed.append(True)

    app.dependency_overrides[get_user_repository] = lambda: failing_repository()
    response = client.post(
        "/api/auth/login",
        json={"email": "usuario@exemplo.com", "senha": "senha-ficticia"},
    )
    assert response.status_code == 503
    assert "segredo" not in response.text
    assert "SELECT" not in response.text
    assert closed == [True]


def test_erro_inesperado_retorna_500_sem_detalhes(auth_client) -> None:
    from app.security.dependencies import get_user_repository

    client, _ = auth_client

    @contextmanager
    def failing_repository():
        raise ValueError("falha interna com segredo")
        yield  # pragma: no cover

    app.dependency_overrides[get_user_repository] = lambda: failing_repository()
    response = client.post(
        "/api/auth/login",
        json={"email": "usuario@exemplo.com", "senha": "senha-ficticia"},
    )
    assert response.status_code == 500
    assert "segredo" not in response.text


def test_me_com_banco_indisponivel_retorna_503_e_fecha_contexto(auth_client) -> None:
    from app.security.dependencies import get_user_repository

    client, _ = auth_client
    assert (
        client.post(
            "/api/auth/login",
            json={"email": "usuario@exemplo.com", "senha": "senha-ficticia"},
        ).status_code
        == 200
    )
    closed = []

    @contextmanager
    def failing_repository():
        try:
            raise OperationalError("SELECT senha_hash", None, RuntimeError("segredo"))
            yield  # pragma: no cover
        finally:
            closed.append(True)

    app.dependency_overrides[get_user_repository] = lambda: failing_repository()
    response = client.get("/api/auth/me")
    assert response.status_code == 503
    assert "segredo" not in response.text
    assert "SELECT" not in response.text
    assert closed == [True]


def test_conexoes_sao_liberadas_em_login_me_e_logout(auth_client) -> None:
    from app.security.dependencies import get_user_repository

    client, users = auth_client
    closed = []

    @contextmanager
    def tracked_repository():
        try:
            yield users
        finally:
            closed.append(True)

    app.dependency_overrides[get_user_repository] = lambda: tracked_repository()
    assert (
        client.post(
            "/api/auth/login",
            json={"email": "usuario@exemplo.com", "senha": "senha-ficticia"},
        ).status_code
        == 200
    )
    assert client.get("/api/auth/me").status_code == 200
    assert client.post("/api/auth/logout").status_code == 204
    assert closed == [True, True, True]


def test_openapi_e_rotas_publicas(auth_client) -> None:
    client, _ = auth_client
    paths = client.get("/api/openapi.json").json()["paths"]
    assert all(
        path in paths
        for path in ("/api/auth/login", "/api/auth/me", "/api/auth/logout")
    )
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/docs").status_code == 200
    assert client.get("/api/redoc").status_code == 200
