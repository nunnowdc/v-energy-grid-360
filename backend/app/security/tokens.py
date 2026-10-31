"""Emissão e validação de JWT para a sessão local."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from app.core.config import ConfigurationUnavailableError, get_settings

COOKIE_NAME = "vgrid360_access_token"
TOKEN_LIFETIME_SECONDS = 900
ALGORITHM = "HS256"


class InvalidSessionToken(Exception):
    """O cookie não contém uma sessão verificável."""


def _secret() -> str:
    secret = get_settings().jwt_secret_key
    if not secret:
        raise ConfigurationUnavailableError("JWT_SECRET_KEY não configurada")
    return secret


def issue_token(user_id: UUID) -> str:
    """Assina um token com identidade estável e expiração de 15 minutos."""
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": str(user_id),
            "iat": now,
            "exp": now + timedelta(seconds=TOKEN_LIFETIME_SECONDS),
        },
        _secret(),
        algorithm=ALGORITHM,
    )


def read_subject(token: str) -> UUID:
    """Valida assinatura, algoritmo, expiração e formato do sujeito."""
    try:
        payload = jwt.decode(
            token,
            _secret(),
            algorithms=[ALGORITHM],
            options={"require": ["sub", "iat", "exp"]},
        )
        if (
            not isinstance(payload["sub"], str)
            or not isinstance(payload["iat"], int)
            or not isinstance(payload["exp"], int)
        ):
            raise InvalidSessionToken
        return UUID(payload["sub"])
    except (jwt.PyJWTError, ValueError, KeyError, TypeError) as exc:
        raise InvalidSessionToken from exc
