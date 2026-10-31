"""Cadastro e troca de senha contra PostgreSQL descartável."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import UTC, datetime
from uuid import UUID

import pytest
from app.entities.user import Usuario
from app.main import app
from app.repositories.users import UsersRepository
from app.security.dependencies import get_user_repository
from app.security.passwords import hash_password, verify_password
from app.security.tokens import COOKIE_NAME, issue_token
from fastapi.testclient import TestClient
from sqlalchemy import func, insert, select
from test_users_postgres import _apply_ddl

pytest_plugins = ["test_users_postgres"]

ADMIN_ID = UUID("550e8400-e29b-41d4-a716-446655440000")


@pytest.fixture
def database_client(users_engine, monkeypatch):
    _apply_ddl(users_engine)
    monkeypatch.setenv(
        "JWT_SECRET_KEY", "segredo-sintetico-para-testes-com-mais-de-32-caracteres"
    )
    with users_engine.begin() as connection:
        connection.execute(
            insert(Usuario.__table__).values(
                id=ADMIN_ID,
                nome="Admin Fictício",
                email="admin@example.invalid",
                senha_hash=hash_password("senha antiga"),
                perfil="ADMIN_TI",
                criado_em=datetime.now(UTC).replace(tzinfo=None),
            )
        )

    @contextmanager
    def repository_context():
        with users_engine.connect() as connection:
            yield UsersRepository(connection)

    app.dependency_overrides[get_user_repository] = lambda: repository_context()
    try:
        client = TestClient(app)
        client.cookies.set(COOKIE_NAME, issue_token(ADMIN_ID))
        yield client, users_engine
    finally:
        app.dependency_overrides.clear()


def test_cadastro_e_troca_de_senha_persistem(database_client):
    client, engine = database_client
    response = client.post(
        "/api/auth/users",
        json={
            "nome": "Pessoa Fictícia",
            "email": "  PESSOA@EXAMPLE.INVALID ",
            "perfil": "PERDAS",
            "senha": "senha inicial",
        },
    )
    assert response.status_code == 201
    created_id = UUID(response.json()["id"])
    with engine.connect() as connection:
        stored = UsersRepository(connection).get_by_id(created_id)
    assert stored is not None
    assert stored["email"] == "pessoa@example.invalid"
    assert stored["criado_em"] is not None
    assert verify_password("senha inicial", stored["senha_hash"])

    changed = client.patch(
        "/api/auth/password",
        json={"senha_atual": "senha antiga", "nova_senha": "senha nova 123"},
    )
    assert changed.status_code == 204
    with engine.connect() as connection:
        admin = UsersRepository(connection).get_by_id(ADMIN_ID)
    assert verify_password("senha nova 123", admin["senha_hash"])
    assert client.get("/api/auth/me").status_code == 200


def test_concurrent_duplicate_email_returns_one_conflict(database_client):
    client, engine = database_client
    token = client.cookies.get(COOKIE_NAME)
    body = {
        "nome": "Pessoa Fictícia",
        "email": "pessoa@example.invalid",
        "perfil": "PERDAS",
        "senha": "senha inicial",
    }

    def attempt(_):
        request_client = TestClient(app)
        request_client.cookies.set(COOKIE_NAME, token)
        return request_client.post("/api/auth/users", json=body).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(attempt, range(2)))
    assert sorted(statuses) == [201, 409]
    with engine.connect() as connection:
        count = connection.execute(
            select(func.count())
            .select_from(Usuario.__table__)
            .where(Usuario.email == "pessoa@example.invalid")
        ).scalar_one()
    assert count == 1


def test_password_update_failure_rolls_back(database_client, monkeypatch):
    client, engine = database_client
    with engine.connect() as connection:
        previous_hash = UsersRepository(connection).get_by_id(ADMIN_ID)["senha_hash"]
    original_update = UsersRepository.update_password

    def fail_after_update(self, user_id, new_hash):
        original_update(self, user_id, new_hash)
        raise RuntimeError("Falha sintética após UPDATE")

    monkeypatch.setattr(UsersRepository, "update_password", fail_after_update)
    response = client.patch(
        "/api/auth/password",
        json={"senha_atual": "senha antiga", "nova_senha": "senha nova 123"},
    )
    assert response.status_code == 503
    assert "UPDATE" not in response.text
    with engine.connect() as connection:
        current_hash = UsersRepository(connection).get_by_id(ADMIN_ID)["senha_hash"]
    assert current_hash == previous_hash
