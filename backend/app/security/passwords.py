"""Hash e verificação de senhas operacionais."""

from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

_PASSWORD_HASH = PasswordHash((Argon2Hasher(),))


def validate_new_password(password: str) -> None:
    """Valida apenas o comprimento mínimo aprovado para uma nova senha."""
    if len(password) < 8:
        raise ValueError("A senha deve ter pelo menos 8 caracteres")


def hash_password(password: str) -> str:
    """Gera um hash Argon2id de uma nova senha válida."""
    validate_new_password(password)
    return _PASSWORD_HASH.hash(password)


def verify_password(password: str, stored_hash: str) -> bool:
    """Confere a senha fornecida contra o hash armazenado."""
    return _PASSWORD_HASH.verify(password, stored_hash)
