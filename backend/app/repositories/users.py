"""Persistência da tabela operacional de usuários."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError

from app.entities.user import Usuario
from app.repositories.transactions import transaction_scope


def _is_duplicate_email(exc: IntegrityError) -> bool:
    diag = getattr(exc.orig, "diag", None)
    constraint = getattr(diag, "constraint_name", None)
    return constraint == "usuarios_email_key" or "usuarios_email_key" in str(exc.orig)


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
        return transaction_scope(self.connection)

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
            .returning(Usuario.id, Usuario.nome)
        )
        try:
            with transaction_scope(self.connection):
                row = self.connection.execute(statement).mappings().one()
        except IntegrityError as exc:
            if _is_duplicate_email(exc):
                return None
            raise
        # Só id e nome voltam do banco; senha_hash nunca é devolvida
        return {"id": row["id"], "nome": row["nome"], "email": email, "perfil": perfil}

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
