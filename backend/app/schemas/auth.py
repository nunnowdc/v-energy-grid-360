"""DTOs públicos da autenticação."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

Perfil = Literal["DIRETORIA", "ATENDIMENTO", "PERDAS", "OPERACAO", "ADMIN_TI"]


def normalize_email(value: str) -> str:
    normalized = value.strip().lower()
    if "@" not in normalized or len(normalized) > 255:
        raise ValueError("Email inválido")
    return normalized


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    senha: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return normalize_email(value)


class CreateUserRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: str = Field(min_length=1, max_length=150)
    email: str
    perfil: Perfil
    senha: str = Field(min_length=8)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return normalize_email(value)


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    senha_atual: str
    nova_senha: str = Field(min_length=8)


class AuthUser(BaseModel):
    id: UUID
    nome: str
    email: str
    perfil: Perfil
