"""Leituras da Gold para a Continuidade da Rede."""

from datetime import date

from sqlalchemy import bindparam, text
from sqlalchemy.engine import Connection

from app.repositories.filters import FiltersRepository


class NetworkRepository:
    def __init__(self, connection: Connection) -> None:
        self.connection = connection

    def get_calendar(self) -> list[tuple[date, str]]:
        rows = self.connection.execute(
            text(
                "SELECT competencia, mes_referencia "
                "FROM dim_competencia ORDER BY competencia"
            )
        )
        return [(row.competencia, row.mes_referencia) for row in rows]

    def get_feeders(self) -> list[str]:
        rows = self.connection.execute(
            text("SELECT alimentador FROM dim_alimentador ORDER BY alimentador")
        )
        return list(rows.scalars())

    def get_municipios(self) -> list[str]:
        pairs = FiltersRepository(self.connection).get_municipio_bairro_pairs()
        return sorted({municipio for municipio, _ in pairs})

    def get_alimentador_municipio_pairs(self) -> list[tuple[str, str]]:
        return FiltersRepository(self.connection).get_alimentador_municipio_pairs()

    def get_causas(self) -> list[str]:
        return FiltersRepository(self.connection).get_causas()

    def get_monthly(self, inicio: date, fim: date) -> list[dict[str, object]]:
        rows = self.connection.execute(
            text(
                "SELECT alimentador, competencia, mes_referencia, total_ucs, "
                "municipio_principal, alimentador_pequeno, dec, fec, "
                "dec_sem_dia_critico, fec_sem_dia_critico "
                "FROM agg_continuidade_alimentador "
                "WHERE competencia BETWEEN :inicio AND :fim "
                "ORDER BY alimentador, competencia"
            ),
            {"inicio": inicio, "fim": fim},
        )
        return [dict(row._mapping) for row in rows]

    def get_occurrence_counts(
        self, inicio: date, fim: date, feeders: list[str], causa: str | None = None
    ) -> list[dict[str, object]]:
        if not feeders:
            return []
        sql = (
            "SELECT competencia, causa, COUNT(*) AS ocorrencias "
            "FROM fact_ocorrencias "
            "WHERE competencia BETWEEN :inicio AND :fim "
            "AND alimentador IN :feeders "
        )
        if causa is not None:
            sql += "AND causa = :causa "
        sql += "GROUP BY competencia, causa ORDER BY competencia, causa"
        statement = text(sql).bindparams(bindparam("feeders", expanding=True))
        parameters = {"inicio": inicio, "fim": fim, "feeders": feeders}
        if causa is not None:
            parameters["causa"] = causa
        rows = self.connection.execute(
            statement,
            parameters,
        )
        return [dict(row._mapping) for row in rows]
