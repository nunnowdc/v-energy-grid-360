"""Cria manualmente a primeira conta ADMIN_TI, sem alterar contas existentes.

Pré-requisitos: tabela usuarios criada pelo SQL controlado, DATABASE_URL configurada
e BOOTSTRAP_ADMIN_PASSWORD no ambiente ou em backend/.env.local caso a conta não exista.
Execute a partir de backend/: python -m scripts.bootstrap_admin_ti
"""

import os
import sys
from datetime import UTC, datetime
from uuid import uuid4

from dotenv import dotenv_values
from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError

from app.core import config
from app.core.database import get_connection
from app.repositories.users import UsersRepository
from app.security.passwords import hash_password

ADMIN_EMAIL = "adminti.vgrid360@visagio.com"
PASSWORD_VARIABLE = "BOOTSTRAP_ADMIN_PASSWORD"


def get_bootstrap_password() -> str | None:
    """Lê a senha sem alterar o ambiente; o processo tem prioridade sobre .env.local."""
    if PASSWORD_VARIABLE in os.environ:
        return os.environ[PASSWORD_VARIABLE]
    return dotenv_values(config.ENV_LOCAL_PATH, interpolate=False).get(
        PASSWORD_VARIABLE
    )


def bootstrap_admin(connection: Connection, password: str | None) -> bool:
    """Cria a conta se ausente; retorna False sem alterar a existente."""
    with connection.begin():
        users = UsersRepository(connection)
        if users.get_by_email(ADMIN_EMAIL) is not None:
            return False
        if password is None:
            raise ValueError("Senha inicial não informada")
        senha_hash = hash_password(password)
        return users.insert_if_absent(
            id=uuid4(),
            nome="admin_ti",
            email=ADMIN_EMAIL,
            senha_hash=senha_hash,
            perfil="ADMIN_TI",
            criado_em=datetime.now(UTC).replace(tzinfo=None),
        )


def main() -> int:
    """Executa o bootstrap sem divulgar senha ou detalhes de conexão."""
    try:
        with get_connection() as connection:
            created = bootstrap_admin(connection, get_bootstrap_password())
    except ValueError:
        print("Configuração ou senha inicial inválida.", file=sys.stderr)
        return 2
    except (SQLAlchemyError, RuntimeError):
        print("Não foi possível acessar a tabela de usuários.", file=sys.stderr)
        return 1

    print("Conta ADMIN_TI criada." if created else "Conta ADMIN_TI já existente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
