"""Bootstrap e integridade de usuários em PostgreSQL descartável."""

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

import psycopg
import pytest
from psycopg import sql
from sqlalchemy import create_engine, insert, select, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import IntegrityError, ProgrammingError

from app.core.config import get_settings
from app.entities.user import Usuario
from app.repositories.users import UsersRepository
from app.security.passwords import verify_password
from scripts.bootstrap_admin_ti import ADMIN_EMAIL, bootstrap_admin

SQL_PATH = Path(__file__).resolve().parents[1] / "sql" / "usuarios.sql"


@pytest.fixture
def users_engine() -> Iterator[Engine]:
    """Cria e remove um banco exclusivo, sem escrever no v_energy."""
    database_url = get_settings().database_url
    if not database_url:
        pytest.skip("PostgreSQL local não configurado")
    main_url = make_url(database_url)
    if main_url.database != "v_energy" or main_url.host not in {
        None,
        "localhost",
        "127.0.0.1",
        "::1",
    }:
        pytest.skip("Teste exige v_energy local apenas como origem da conexão")

    test_name = f"v_energy_users_test_{uuid4().hex[:12]}"
    admin_url = main_url.set(drivername="postgresql", database="postgres")
    test_url = main_url.set(database=test_name)
    try:
        admin_connection = psycopg.connect(
            admin_url.render_as_string(hide_password=False), autocommit=True
        )
    except psycopg.Error:
        raise RuntimeError("PostgreSQL de teste indisponível") from None

    with admin_connection as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(test_name)))
        engine = create_engine(test_url, connect_args={"connect_timeout": 5})
        try:
            yield engine
        finally:
            engine.dispose()
            admin.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(test_name)))


def _apply_ddl(engine: Engine) -> None:
    with engine.connect() as connection:
        connection.exec_driver_sql(SQL_PATH.read_text(encoding="utf-8"))


def test_bootstrap_requires_existing_table(users_engine: Engine) -> None:
    with users_engine.connect() as connection, pytest.raises(ProgrammingError):
        bootstrap_admin(connection, "senha ficticia 123")
    _apply_ddl(users_engine)


def test_postgres_table_has_six_fields_and_approved_constraints(
    users_engine: Engine,
) -> None:
    _apply_ddl(users_engine)
    with users_engine.connect() as connection:
        columns = connection.execute(
            text(
                "SELECT column_name, data_type, character_maximum_length, is_nullable "
                "FROM information_schema.columns WHERE table_schema='public' "
                "AND table_name='usuarios' ORDER BY ordinal_position"
            )
        ).all()
        constraints = set(
            connection.execute(
                text(
                    "SELECT constraint_type FROM information_schema.table_constraints "
                    "WHERE table_schema='public' AND table_name='usuarios'"
                )
            ).scalars()
        )
    assert columns == [
        ("id", "uuid", None, "NO"),
        ("nome", "character varying", 150, "NO"),
        ("email", "character varying", 255, "NO"),
        ("senha_hash", "character varying", 255, "NO"),
        ("perfil", "character varying", 30, "NO"),
        ("criado_em", "timestamp without time zone", None, "NO"),
    ]
    assert {"PRIMARY KEY", "UNIQUE", "CHECK"} <= constraints


def test_bootstrap_creates_once_and_keeps_all_existing_data(
    users_engine: Engine,
) -> None:
    _apply_ddl(users_engine)
    with users_engine.connect() as connection:
        assert bootstrap_admin(connection, "senha ficticia 123")
    with users_engine.connect() as connection:
        first = UsersRepository(connection).get_by_email(ADMIN_EMAIL)
        assert first is not None
        assert first["nome"] == "admin_ti"
        assert first["perfil"] == "ADMIN_TI"
        assert isinstance(first["id"], UUID)
        assert isinstance(first["criado_em"], datetime)
        assert verify_password("senha ficticia 123", first["senha_hash"])
        assert first["senha_hash"] != "senha ficticia 123"
    with users_engine.connect() as connection:
        assert not bootstrap_admin(connection, None)
    with users_engine.connect() as connection:
        assert UsersRepository(connection).get_by_email(ADMIN_EMAIL) == first


def test_bootstrap_rejects_short_password_without_partial_account(
    users_engine: Engine,
) -> None:
    _apply_ddl(users_engine)
    with (
        users_engine.connect() as connection,
        pytest.raises(ValueError, match="8 caracteres"),
    ):
        bootstrap_admin(connection, "curta")
    with users_engine.connect() as connection:
        assert UsersRepository(connection).get_by_email(ADMIN_EMAIL) is None


def test_bootstrap_requires_password_when_account_is_absent(
    users_engine: Engine,
) -> None:
    _apply_ddl(users_engine)
    with (
        users_engine.connect() as connection,
        pytest.raises(ValueError, match="não informada"),
    ):
        bootstrap_admin(connection, None)
    with users_engine.connect() as connection:
        assert UsersRepository(connection).get_by_email(ADMIN_EMAIL) is None


def test_all_five_approved_profiles_are_accepted(users_engine: Engine) -> None:
    _apply_ddl(users_engine)
    profiles = ("DIRETORIA", "ATENDIMENTO", "PERDAS", "OPERACAO", "ADMIN_TI")
    with users_engine.begin() as connection:
        for position, profile in enumerate(profiles):
            connection.execute(
                insert(Usuario.__table__).values(
                    id=uuid4(),
                    nome="Pessoa fictícia",
                    email=f"perfil{position}@example.invalid",
                    senha_hash="hash ficticio",
                    perfil=profile,
                    criado_em=datetime.now(),
                )
            )
    with users_engine.connect() as connection:
        stored = set(connection.execute(select(Usuario.perfil)).scalars())
    assert stored == set(profiles)


def test_email_unique_and_profile_domain(users_engine: Engine) -> None:
    _apply_ddl(users_engine)
    with users_engine.begin() as connection:
        connection.execute(
            insert(Usuario.__table__).values(
                id=uuid4(),
                nome="Teste",
                email="unico@example.invalid",
                senha_hash="hash ficticio",
                perfil="PERDAS",
                criado_em=datetime.now(),
            )
        )
    with pytest.raises(IntegrityError), users_engine.begin() as connection:
        connection.execute(
            insert(Usuario.__table__).values(
                id=uuid4(),
                nome="Outro",
                email="unico@example.invalid",
                senha_hash="hash ficticio",
                perfil="OPERACAO",
                criado_em=datetime.now(),
            )
        )
    with pytest.raises(IntegrityError), users_engine.begin() as connection:
        connection.execute(
            insert(Usuario.__table__).values(
                id=uuid4(),
                nome="Outro",
                email="invalido@example.invalid",
                senha_hash="hash ficticio",
                perfil="DESCONHECIDO",
                criado_em=datetime.now(),
            )
        )


def test_concurrent_bootstrap_creates_one_account(users_engine: Engine) -> None:
    _apply_ddl(users_engine)

    def attempt() -> bool:
        with users_engine.connect() as connection:
            return bootstrap_admin(connection, "senha ficticia 123")

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: attempt(), range(2)))
    assert sorted(outcomes) == [False, True]
    with users_engine.connect() as connection:
        count = connection.execute(
            select(text("count(*)"))
            .select_from(Usuario.__table__)
            .where(Usuario.email == ADMIN_EMAIL)
        ).scalar_one()
    assert count == 1
