"""Política de senha para contas operacionais."""

import pytest

from app.security.passwords import hash_password, validate_new_password, verify_password


def test_password_is_argon2id_and_verifies_only_the_correct_secret() -> None:
    stored = hash_password("senha ficticia 123")

    assert stored.startswith("$argon2id$")
    assert stored != "senha ficticia 123"
    assert verify_password("senha ficticia 123", stored)
    assert not verify_password("senha incorreta", stored)


def test_new_password_requires_eight_characters_only() -> None:
    with pytest.raises(ValueError, match="8 caracteres"):
        validate_new_password("1234567")

    validate_new_password("12345678")
    assert hash_password("12345678").startswith("$argon2id$")
