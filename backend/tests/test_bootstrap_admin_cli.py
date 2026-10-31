"""Comportamento seguro do bootstrap manual na borda do processo."""

from contextlib import contextmanager

from sqlalchemy.exc import OperationalError

from app.core import config
from scripts import bootstrap_admin_ti


def test_main_reads_password_from_local_file_without_using_current_directory(
    monkeypatch, tmp_path, capsys
) -> None:
    local_file = tmp_path / ".env.local"
    local_file.write_text("BOOTSTRAP_ADMIN_PASSWORD=senha-ficticia-valida\n")
    monkeypatch.setattr(config, "ENV_LOCAL_PATH", local_file)
    monkeypatch.delenv(bootstrap_admin_ti.PASSWORD_VARIABLE, raising=False)
    monkeypatch.chdir(tmp_path / "..")
    received = []

    @contextmanager
    def fake_connection():
        yield object()

    monkeypatch.setattr(bootstrap_admin_ti, "get_connection", fake_connection)
    monkeypatch.setattr(
        bootstrap_admin_ti,
        "bootstrap_admin",
        lambda _connection, password: received.append(password) or True,
    )

    assert bootstrap_admin_ti.main() == 0
    assert received == ["senha-ficticia-valida"]
    output = capsys.readouterr()
    assert "senha-ficticia-valida" not in output.out + output.err


def test_environment_password_takes_precedence_over_local_file(
    monkeypatch, tmp_path
) -> None:
    local_file = tmp_path / ".env.local"
    local_file.write_text("BOOTSTRAP_ADMIN_PASSWORD=senha-do-arquivo\n")
    monkeypatch.setattr(config, "ENV_LOCAL_PATH", local_file)
    monkeypatch.setenv(bootstrap_admin_ti.PASSWORD_VARIABLE, "senha-do-processo")

    assert bootstrap_admin_ti.get_bootstrap_password() == "senha-do-processo"


def test_missing_password_returns_none(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(config, "ENV_LOCAL_PATH", tmp_path / ".env.local")
    monkeypatch.delenv(bootstrap_admin_ti.PASSWORD_VARIABLE, raising=False)

    assert bootstrap_admin_ti.get_bootstrap_password() is None


def test_connection_failure_does_not_print_secret_or_sql(monkeypatch, capsys) -> None:
    marker = "segredo-ficticio-para-teste"
    monkeypatch.setenv(bootstrap_admin_ti.PASSWORD_VARIABLE, marker)

    def unavailable():
        raise OperationalError(
            "SELECT senha_hash FROM usuarios", None, RuntimeError(marker)
        )

    monkeypatch.setattr(bootstrap_admin_ti, "get_connection", unavailable)

    assert bootstrap_admin_ti.main() == 1
    output = capsys.readouterr()
    assert "Não foi possível acessar a tabela de usuários." in output.err
    assert marker not in output.out + output.err
    assert "SELECT" not in output.out + output.err
