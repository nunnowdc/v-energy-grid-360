"""JWTs sintéticos e rejeições na borda HTTP."""

from contextlib import nullcontext
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
import pytest
from app.core import config
from app.main import app
from app.security.dependencies import get_user_repository
from app.security.tokens import COOKIE_NAME, issue_token
from fastapi.testclient import TestClient

SECRET = "segredo-sintetico-para-testes-com-mais-de-32-caracteres"
USER_ID = UUID("550e8400-e29b-41d4-a716-446655440000")


class FakeUsers:
    def __init__(self) -> None:
        self.lookups = []

    def get_by_id(self, user_id):
        self.lookups.append(user_id)
        if user_id == USER_ID:
            return {
                "id": USER_ID,
                "nome": "Usuário Teste",
                "email": "usuario@exemplo.com",
                "perfil": "ATENDIMENTO",
                "senha_hash": "hash-que-nao-deve-sair",
            }
        return None


@pytest.fixture
def session_client(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", SECRET)
    users = FakeUsers()
    app.dependency_overrides[get_user_repository] = lambda: nullcontext(users)
    try:
        yield TestClient(app), users
    finally:
        app.dependency_overrides.clear()


def test_token_assinado_tem_sub_iat_e_exp_de_15_minutos(monkeypatch) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", SECRET)
    token = issue_token(USER_ID)
    payload = jwt.decode(token, SECRET, algorithms=["HS256"])

    assert payload["sub"] == str(USER_ID)
    assert payload["exp"] - payload["iat"] == 900
    assert jwt.get_unverified_header(token)["alg"] == "HS256"


def test_segredo_local_pode_vir_do_arquivo_com_prioridade_do_ambiente(
    monkeypatch, tmp_path
) -> None:
    local_file = tmp_path / ".env.local"
    local_file.write_text("JWT_SECRET_KEY=segredo-ficticio-do-arquivo\n")
    monkeypatch.setattr(config, "ENV_LOCAL_PATH", local_file)
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    settings = config.get_settings()
    assert settings.jwt_secret_key == "segredo-ficticio-do-arquivo"
    assert settings.jwt_secret_key not in repr(settings)

    monkeypatch.setenv("JWT_SECRET_KEY", SECRET)
    assert config.get_settings().jwt_secret_key == SECRET


@pytest.mark.parametrize(
    "kind",
    [
        "tampered",
        "expired",
        "malformed",
        "none",
        "wrong_algorithm",
        "bad_sub",
        "missing_claim",
        "unknown_user",
    ],
)
def test_me_rejeita_token_nao_verificavel(session_client, kind) -> None:
    client, users = session_client
    now = datetime.now(UTC)
    payload = {
        "sub": str(USER_ID),
        "iat": now,
        "exp": now + timedelta(minutes=15),
    }
    if kind == "expired":
        payload["iat"] = now - timedelta(minutes=20)
        payload["exp"] = now - timedelta(minutes=5)
    elif kind == "bad_sub":
        payload["sub"] = "nao-e-uuid"
    elif kind == "missing_claim":
        del payload["iat"]
    elif kind == "unknown_user":
        payload["sub"] = str(uuid4())

    token = jwt.encode(payload, SECRET, algorithm="HS256")
    if kind == "tampered":
        token = jwt.encode(payload, SECRET + "-outra", algorithm="HS256")
    elif kind == "none":
        token = jwt.encode(payload, key="", algorithm="none")
    elif kind == "wrong_algorithm":
        token = jwt.encode(payload, SECRET, algorithm="HS384")
    elif kind == "malformed":
        token = "partes.invalidas"

    client.cookies.set(COOKIE_NAME, token)
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert "hash" not in response.text
    if kind != "unknown_user":
        assert users.lookups == []


def test_logout_nao_revoga_token_ja_emitido(session_client) -> None:
    client, _ = session_client
    token = issue_token(USER_ID)
    client.cookies.set(COOKIE_NAME, token)
    response = client.post("/api/auth/logout")
    assert response.status_code == 204
    assert response.content == b""

    # Logout só expira o cookie do navegador; uma cópia ainda válida autentica.
    client.cookies.set(COOKIE_NAME, token)
    assert client.get("/api/auth/me").status_code == 200


def test_logout_com_cookie_expirado_retorna_401(session_client) -> None:
    client, _ = session_client
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": str(USER_ID),
            "iat": now - timedelta(minutes=20),
            "exp": now - timedelta(minutes=5),
        },
        SECRET,
        algorithm="HS256",
    )
    client.cookies.set(COOKIE_NAME, token)
    assert client.post("/api/auth/logout").status_code == 401


def test_segredo_ausente_nao_gera_chave_de_fallback(
    session_client, monkeypatch
) -> None:
    client, _ = session_client
    monkeypatch.setenv("JWT_SECRET_KEY", "")
    client.cookies.set(COOKIE_NAME, "token-ficticio")
    assert client.get("/api/auth/me").status_code == 503
