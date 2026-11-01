"""Credenciais e dados públicos da conta autenticada."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.repositories.users import UsersRepository
from app.security.passwords import hash_password, verify_password


class InvalidCredentials(Exception):
    """Email ou senha não confere com uma conta existente."""


class DuplicateEmail(Exception):
    """O email normalizado já pertence a outra conta."""


class InvalidCurrentPassword(Exception):
    """A senha atual não confere com a conta autenticada."""


def authenticate_user(
    users: UsersRepository, email: str, password: str
) -> dict[str, object]:
    user = users.get_by_email(email)
    if user is None or not verify_password(password, user["senha_hash"]):
        raise InvalidCredentials
    return user


def create_user(
    users: UsersRepository, *, nome: str, email: str, perfil: str, senha: str
) -> dict[str, object]:
    created = users.create(
        id=uuid4(),
        nome=nome,
        email=email,
        perfil=perfil,
        senha_hash=hash_password(senha),
        criado_em=datetime.now(UTC).replace(tzinfo=None),
    )
    if created is None:
        raise DuplicateEmail
    return created


def change_own_password(
    users: UsersRepository, user_id: UUID, current: str, new: str
) -> None:
    with users.transaction():
        user = users.get_by_id_for_update(user_id)
        if user is None:
            raise InvalidCredentials
        if not verify_password(current, user["senha_hash"]):
            raise InvalidCurrentPassword
        users.update_password(user_id, hash_password(new))
