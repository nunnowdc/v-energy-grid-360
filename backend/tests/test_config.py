from pathlib import Path

import pytest

from app.core import config
from app.core.config import get_settings


def test_default_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(config, "ENV_LOCAL_PATH", tmp_path / "missing.env.local")
    for name in ("APP_ENV", "APP_HOST", "APP_PORT", "CORS_ORIGINS", "DATABASE_URL"):
        monkeypatch.delenv(name, raising=False)

    settings = get_settings()

    assert settings.environment == "local"
    assert settings.host == "127.0.0.1"
    assert settings.port == 8000
    assert settings.cors_origins == (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    )
    assert settings.database_url is None


def test_local_file_is_loaded_independent_of_cwd(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    local_file = tmp_path / "backend" / ".env.local"
    local_file.parent.mkdir()
    local_file.write_text(
        "APP_ENV=from-file\n"
        "APP_HOST=localhost\n"
        "APP_PORT=8123\n"
        "CORS_ORIGINS=http://localhost:5174\n"
        "DATABASE_URL=postgresql+psycopg:///example_gold\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(config, "ENV_LOCAL_PATH", local_file)
    monkeypatch.chdir(tmp_path)
    for name in ("APP_ENV", "APP_HOST", "APP_PORT", "CORS_ORIGINS", "DATABASE_URL"):
        monkeypatch.delenv(name, raising=False)

    settings = get_settings()

    assert settings.environment == "from-file"
    assert settings.host == "localhost"
    assert settings.port == 8123
    assert settings.cors_origins == ("http://localhost:5174",)
    assert settings.database_url == "postgresql+psycopg:///example_gold"
    assert config.ENV_LOCAL_PATH.is_absolute()


def test_system_environment_takes_priority_over_local_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    local_file = tmp_path / ".env.local"
    local_file.write_text(
        "APP_PORT=8123\nDATABASE_URL=postgresql+psycopg:///from_file\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(config, "ENV_LOCAL_PATH", local_file)
    monkeypatch.setenv("APP_PORT", "9000")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg:///from_system")

    settings = get_settings()

    assert settings.port == 9000
    assert settings.database_url == "postgresql+psycopg:///from_system"
    assert "from_system" not in repr(settings)


def test_config_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("APP_HOST", "localhost")
    monkeypatch.setenv("APP_PORT", "9000")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5174")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg:///v_energy")

    settings = get_settings()

    assert settings.environment == "test"
    assert settings.host == "localhost"
    assert settings.port == 9000
    assert settings.cors_origins == ("http://localhost:5174",)
    assert settings.database_url == "postgresql+psycopg:///v_energy"
    assert "v_energy" not in repr(settings)


def test_database_url_requires_psycopg(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite:///local.db")

    with pytest.raises(ValueError, match="DATABASE_URL"):
        get_settings()


@pytest.mark.parametrize("port", ["0", "65536", "invalid"])
def test_invalid_port(monkeypatch: pytest.MonkeyPatch, port: str) -> None:
    monkeypatch.setenv("APP_PORT", port)

    with pytest.raises(ValueError):
        get_settings()


@pytest.mark.parametrize(
    "origin",
    [
        "https://example.com",
        "http://localhost:5173/",
        "http://user:pass@localhost:5173",
    ],
)
def test_cors_rejects_invalid_origin(
    monkeypatch: pytest.MonkeyPatch, origin: str
) -> None:
    monkeypatch.setenv("CORS_ORIGINS", origin)

    with pytest.raises(ValueError, match="Origem CORS local inválida"):
        get_settings()


def test_cors_rejects_empty_list(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", " ")

    with pytest.raises(ValueError, match="pelo menos uma origem local"):
        get_settings()


@pytest.mark.parametrize(
    ("database_url", "expected"),
    [
        (
            "postgresql://usuario:senha@localhost:5433/exemplo?sslmode=require",
            "postgresql+psycopg://usuario:senha@localhost:5433/exemplo?sslmode=require",
        ),
        (
            "postgresql+psycopg://usuario:senha@localhost:5433/exemplo?sslmode=require",
            "postgresql+psycopg://usuario:senha@localhost:5433/exemplo?sslmode=require",
        ),
        ("postgresql:///exemplo", "postgresql+psycopg:///exemplo"),
        ("postgresql+psycopg:///exemplo", "postgresql+psycopg:///exemplo"),
    ],
)
def test_database_url_preserves_structure_for_both_schemes(
    monkeypatch: pytest.MonkeyPatch, database_url: str, expected: str
) -> None:
    monkeypatch.setenv("DATABASE_URL", database_url)

    settings = get_settings()

    assert settings.database_url == expected


def test_database_url_preserves_credentials_port_and_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from sqlalchemy.engine import make_url

    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://usuario:senha%40teste@localhost:5433/exemplo"
        "?sslmode=require&application_name=portal",
    )

    settings = get_settings()
    parsed = make_url(settings.database_url)

    assert parsed.drivername == "postgresql+psycopg"
    assert parsed.username == "usuario"
    assert parsed.password == "senha@teste"
    assert parsed.host == "localhost"
    assert parsed.port == 5433
    assert parsed.database == "exemplo"
    assert dict(parsed.query) == {"sslmode": "require", "application_name": "portal"}
    assert "senha" not in repr(settings)


@pytest.mark.parametrize(
    "database_url",
    [
        "mysql:///exemplo",
        "postgresql://",
        "postgresql+psycopg:///",
        "postgresql://localhost/",
        "postgresql:exemplo",
    ],
)
def test_database_url_rejects_invalid_scheme_or_missing_database(
    monkeypatch: pytest.MonkeyPatch, database_url: str
) -> None:
    monkeypatch.setenv("DATABASE_URL", database_url)

    with pytest.raises(ValueError, match="DATABASE_URL"):
        get_settings()
