"""Credenciais e dados públicos da conta autenticada."""

from app.repositories.users import UsersRepository
from app.security.passwords import verify_password


class InvalidCredentials(Exception):
    """Email ou senha não confere com uma conta existente."""


def authenticate_user(
    users: UsersRepository, email: str, password: str
) -> dict[str, object]:
    user = users.get_by_email(email)
    if user is None or not verify_password(password, user["senha_hash"]):
        raise InvalidCredentials
    return user
