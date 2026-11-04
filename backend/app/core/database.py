"""Conexões síncronas com o PostgreSQL local, com troca opcional de role por perfil."""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from functools import lru_cache

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Connection, Engine

from app.core.config import ConfigurationUnavailableError, get_settings

# Mapa fixo: o nome do role nunca vem de dado do cliente nem é montado a partir dele
PROFILE_ROLES = {
    "DIRETORIA": "perfil_diretoria",
    "ATENDIMENTO": "perfil_atendimento",
    "PERDAS": "perfil_perdas",
    "OPERACAO": "perfil_operacao",
    "ADMIN_TI": "perfil_admin_ti",
}

current_profile: ContextVar[str | None] = ContextVar("current_profile", default=None)


class MissingProfileError(RuntimeError):
    """Conexão com roles ligada pedida sem perfil definido para a requisição."""


class UnknownProfileError(ValueError):
    """Perfil fora dos 5 conhecidos."""


def role_for_profile(profile: str | None) -> str:
    if profile is None:
        raise MissingProfileError("Perfil não definido para a conexão")
    try:
        return PROFILE_ROLES[profile]
    except KeyError:
        raise UnknownProfileError("Perfil desconhecido") from None


def _execute_set_local_role(dbapi_connection, role: str) -> None:
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute(f'SET LOCAL ROLE "{role}"')
    finally:
        cursor.close()


def _apply_profile_role(connection: Connection) -> None:
    role = role_for_profile(current_profile.get())
    _execute_set_local_role(connection.connection.dbapi_connection, role)


def install_role_listener(engine: Engine) -> None:
    """Roda SET LOCAL ROLE no início de cada transação do engine."""
    event.listen(engine, "begin", _apply_profile_role)


def _create_engine(url: str | None, name: str) -> Engine:
    if url is None:
        raise ConfigurationUnavailableError(f"{name} não configurada")
    return create_engine(
        url,
        connect_args={"connect_timeout": 5, "options": "-c statement_timeout=5000"},
    )


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Engine do dono (DATABASE_URL), criado sob demanda e reutilizado."""
    return _create_engine(get_settings().database_url, "DATABASE_URL")


@lru_cache(maxsize=1)
def get_portal_app_engine() -> Engine:
    """Engine do portal_app, com troca de role a cada transação."""
    engine = _create_engine(
        get_settings().portal_app_database_url, "PORTAL_APP_DATABASE_URL"
    )
    install_role_listener(engine)
    return engine


@lru_cache(maxsize=1)
def get_portal_auth_engine() -> Engine:
    """Engine do portal_auth, só para login e conta atual."""
    return _create_engine(
        get_settings().portal_auth_database_url, "PORTAL_AUTH_DATABASE_URL"
    )


@contextmanager
def get_connection() -> Iterator[Connection]:
    """Entrega uma conexão que volta ao pool ao sair do bloco."""
    if get_settings().use_db_roles:
        # Recusa cedo: sem perfil, nunca cai em outro usuário do banco
        role_for_profile(current_profile.get())
        engine = get_portal_app_engine()
    else:
        engine = get_engine()
    with engine.connect() as connection:
        yield connection


@contextmanager
def get_auth_connection() -> Iterator[Connection]:
    """Conexão para login, conta atual e troca de senha."""
    engine = get_portal_auth_engine() if get_settings().use_db_roles else get_engine()
    with engine.connect() as connection:
        yield connection


@contextmanager
def get_owner_connection() -> Iterator[Connection]:
    """Conexão do dono (DATABASE_URL), para scripts administrativos."""
    with get_engine().connect() as connection:
        yield connection
