"""Dependências reutilizáveis de identidade e origem local."""

from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from typing import Annotated

from app.core.database import get_connection
from app.repositories.users import UsersRepository
from app.security.tokens import COOKIE_NAME, InvalidSessionToken, read_subject
from fastapi import Cookie, Depends, HTTPException
from sqlalchemy.exc import InterfaceError, OperationalError, TimeoutError

ALLOWED_WRITE_ORIGINS = frozenset(
    {
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000",
    }
)


@contextmanager
def _user_repository_context() -> Iterator[UsersRepository]:
    with get_connection() as connection:
        yield UsersRepository(connection)


def get_user_repository() -> AbstractContextManager[UsersRepository]:
    """Entrega o repository de usuários com conexão fechada ao sair do contexto."""
    return _user_repository_context()


def get_current_user(
    repository_context: Annotated[
        AbstractContextManager[UsersRepository], Depends(get_user_repository)
    ],
    token: Annotated[str | None, Cookie(alias=COOKIE_NAME)] = None,
) -> dict[str, object]:
    """Valida o cookie e recarrega a conta atual antes de liberar uma rota."""
    if token is None:
        raise HTTPException(status_code=401, detail="Não autenticado")
    try:
        user_id = read_subject(token)
    except InvalidSessionToken as exc:
        raise HTTPException(status_code=401, detail="Não autenticado") from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503, detail="Autenticação indisponível"
        ) from exc

    try:
        with repository_context as users:
            user = users.get_by_id(user_id)
    except (InterfaceError, OperationalError, TimeoutError, RuntimeError) as exc:
        raise HTTPException(
            status_code=503, detail="Autenticação indisponível"
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Erro interno") from exc

    if user is None:
        raise HTTPException(status_code=401, detail="Não autenticado")
    return user


def require_admin_ti(
    user: Annotated[dict[str, object], Depends(get_current_user)],
) -> dict[str, object]:
    """Protege o cadastro administrativo antes do RBAC geral do Ticket 04."""
    if user["perfil"] != "ADMIN_TI":
        raise HTTPException(status_code=403, detail="Acesso não permitido")
    return user
