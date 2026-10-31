"""DTOs públicos da autenticação."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

Perfil = Literal["DIRETORIA", "ATENDIMENTO", "PERDAS", "OPERACAO", "ADMIN_TI"]


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    senha: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized or len(normalized) > 255:
            raise ValueError("Email inválido")
        return normalized


class AuthUser(BaseModel):
    id: UUID
    nome: str
    email: str
    perfil: Perfil
