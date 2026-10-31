"""Persistência da tabela operacional de usuários."""

from datetime import datetime
from uuid import UUID

from app.entities.user import Usuario
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Connection


class UsersRepository:
    """Consultas e escrita de contas na conexão recebida."""

    def __init__(self, connection: Connection) -> None:
        self.connection = connection

    def get_by_email(self, email: str) -> dict | None:
        row = (
            self.connection.execute(
                select(Usuario.__table__).where(Usuario.email == email)
            )
            .mappings()
            .one_or_none()
        )
        return dict(row) if row is not None else None

    def get_by_id(self, user_id: UUID) -> dict | None:
        row = (
            self.connection.execute(
                select(Usuario.__table__).where(Usuario.id == user_id)
            )
            .mappings()
            .one_or_none()
        )
        return dict(row) if row is not None else None

    def transaction(self):
        """Mantém leitura bloqueante e atualização na mesma transação."""
        return self.connection.begin()

    def get_by_id_for_update(self, user_id: UUID) -> dict | None:
        row = (
            self.connection.execute(
                select(Usuario.__table__).where(Usuario.id == user_id).with_for_update()
            )
            .mappings()
            .one_or_none()
        )
        return dict(row) if row is not None else None

    def update_password(self, user_id: UUID, senha_hash: str) -> None:
        self.connection.execute(
            update(Usuario.__table__)
            .where(Usuario.id == user_id)
            .values(senha_hash=senha_hash)
        )

    def create(
        self,
        *,
        id: UUID,
        nome: str,
        email: str,
        senha_hash: str,
        perfil: str,
        criado_em: datetime,
    ) -> dict | None:
        statement = (
            insert(Usuario.__table__)
            .values(
                id=id,
                nome=nome,
                email=email,
                senha_hash=senha_hash,
                perfil=perfil,
                criado_em=criado_em,
            )
            .on_conflict_do_nothing(index_elements=[Usuario.email])
            .returning(Usuario.__table__)
        )
        with self.connection.begin():
            row = self.connection.execute(statement).mappings().one_or_none()
        return dict(row) if row is not None else None

    def insert_if_absent(
        self,
        *,
        id: UUID,
        nome: str,
        email: str,
        senha_hash: str,
        perfil: str,
        criado_em: datetime,
    ) -> bool:
        """Insere sem sobrescrever a conta que venceu uma corrida pelo email."""
        statement = (
            insert(Usuario.__table__)
            .values(
                id=id,
                nome=nome,
                email=email,
                senha_hash=senha_hash,
                perfil=perfil,
                criado_em=criado_em,
            )
            .on_conflict_do_nothing(index_elements=[Usuario.email])
            .returning(Usuario.id)
        )
        return self.connection.execute(statement).scalar_one_or_none() is not None
