"""Mapeamento da tabela operacional de usuários."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base do mapeamento operacional de usuários."""


class Usuario(Base):
    """Conta pré-cadastrada do Portal."""

    __tablename__ = "usuarios"
    __table_args__ = (
        UniqueConstraint("email", name="usuarios_email_key"),
        CheckConstraint(
            "perfil IN ('DIRETORIA', 'ATENDIMENTO', 'PERDAS', 'OPERACAO', 'ADMIN_TI')",
            name="usuarios_perfil_check",
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    perfil: Mapped[str] = mapped_column(String(30), nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False
    )
