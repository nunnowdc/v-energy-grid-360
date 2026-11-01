"""Mapeamento Core da tabela operacional; a criação usa SQL explícito e controlado."""

from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Identity,
    MetaData,
    Table,
    Text,
    Uuid,
    func,
    insert,
    text,
    update,
)
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError

ORDENS_INSPECAO = Table(
    "ordens_inspecao",
    MetaData(),
    Column("id", BigInteger, Identity(always=True), primary_key=True),
    Column("id_uc", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("resultado", Text),
    Column(
        "criada_em", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    Column(
        "atualizada_em",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
    Column("concluida_em", DateTime(timezone=True)),
    # Conta da sessão que gerou e que mudou por último (sql/ordens_inspecao_autoria.sql)
    Column("criada_por", Uuid),
    Column("atualizada_por", Uuid),
)


class ActiveOrderRaceError(Exception):
    """O índice parcial rejeitou uma ordem ativa criada em concorrência."""


class InspectionOrdersRepository:
    def __init__(self, connection: Connection) -> None:
        self.connection = connection

    @contextmanager
    def transaction(self) -> Iterator[None]:
        with self.connection.begin():
            yield

    def get_active_orders(self, ids_uc: list[str]) -> list[dict[str, object]]:
        if not ids_uc:
            return []
        rows = self.connection.execute(
            text(
                "SELECT id_uc, id, status FROM ordens_inspecao "
                "WHERE id_uc = ANY(:ids_uc) AND status IN ('ABERTA', 'EM_CAMPO')"
            ),
            {"ids_uc": ids_uc},
        )
        return [dict(row._mapping) for row in rows]

    def list_orders(
        self, municipio: str | None, bairro: str | None, classe: str | None
    ) -> list[dict[str, object]]:
        clauses: list[str] = []
        values: dict[str, str] = {}
        for name, value in (
            ("municipio", municipio),
            ("bairro", bairro),
            ("classe", classe),
        ):
            if value is not None:
                clauses.append(f"uc.{name} = :{name}")
                values[name] = value
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        rows = self.connection.execute(
            text(
                "SELECT o.id, o.id_uc, uc.municipio, uc.bairro, "
                "o.status, o.resultado, o.criada_em "
                "FROM ordens_inspecao AS o "
                "JOIN dim_unidade_consumidora AS uc ON uc.id_uc = o.id_uc"
                f"{where} ORDER BY o.criada_em DESC, o.id DESC"
            ),
            values,
        )
        return [dict(row._mapping) for row in rows]

    def get_order(self, order_id: int) -> dict[str, object] | None:
        row = (
            self.connection.execute(
                text(
                    "SELECT o.id, o.id_uc, uc.municipio, uc.bairro, "
                    "o.status, o.resultado, o.criada_em "
                    "FROM ordens_inspecao AS o "
                    "LEFT JOIN dim_unidade_consumidora AS uc ON uc.id_uc = o.id_uc "
                    "WHERE o.id = :id"
                ),
                {"id": order_id},
            )
            .mappings()
            .one_or_none()
        )
        return dict(row) if row is not None else None

    def update_if_status(
        self,
        order_id: int,
        expected_status: str,
        status: str,
        resultado: str | None,
        *,
        user_id: UUID,
    ) -> bool:
        values: dict[str, object] = {
            "status": status,
            "resultado": resultado,
            "atualizada_em": func.clock_timestamp(),
            "atualizada_por": user_id,
        }
        if status == "CONCLUIDA":
            values["concluida_em"] = func.clock_timestamp()
        result = self.connection.execute(
            update(ORDENS_INSPECAO)
            .where(
                ORDENS_INSPECAO.c.id == order_id,
                ORDENS_INSPECAO.c.status == expected_status,
            )
            .values(**values)
            .returning(ORDENS_INSPECAO.c.id)
        )
        return result.one_or_none() is not None

    def insert_orders(
        self, ids_uc: list[str], *, user_id: UUID
    ) -> list[dict[str, object]]:
        statement = (
            insert(ORDENS_INSPECAO)
            .values(
                [
                    {
                        "id_uc": uc,
                        "status": "ABERTA",
                        "criada_por": user_id,
                        "atualizada_por": user_id,
                    }
                    for uc in ids_uc
                ]
            )
            .returning(
                ORDENS_INSPECAO.c.id,
                ORDENS_INSPECAO.c.id_uc,
                ORDENS_INSPECAO.c.status,
                ORDENS_INSPECAO.c.resultado,
                ORDENS_INSPECAO.c.criada_em,
            )
        )
        try:
            rows = self.connection.execute(statement)
        except IntegrityError as exc:
            constraint = getattr(
                getattr(exc.orig, "diag", None), "constraint_name", None
            )
            if constraint == "ordens_inspecao_uc_ativa_uidx":
                raise ActiveOrderRaceError from exc
            raise
        return [dict(row._mapping) for row in rows]
