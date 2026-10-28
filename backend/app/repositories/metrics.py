"""Consultas somente leitura para os indicadores gerais da Gold."""

from datetime import date

from sqlalchemy import text
from sqlalchemy.engine import Connection


class MetricsRepository:
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

    def get_municipios(self) -> list[str]:
        rows = self.connection.execute(
            text(
                "SELECT DISTINCT municipio FROM dim_unidade_consumidora "
                "WHERE municipio IS NOT NULL ORDER BY municipio"
            )
        )
        return list(rows.scalars())

    @staticmethod
    def _filters(
        municipio: str | None, classe: str | None
    ) -> tuple[str, dict[str, str]]:
        clauses = []
        values = {}
        if municipio is not None:
            clauses.append("municipio = :municipio")
            values["municipio"] = municipio
        if classe is not None:
            clauses.append("classe = :classe")
            values["classe"] = classe
        return (" AND " + " AND ".join(clauses) if clauses else "", values)

    def get_monthly_metrics(
        self,
        inicio: date,
        fim: date,
        municipio: str | None = None,
        classe: str | None = None,
    ) -> list[dict[str, object]]:
        filters, values = self._filters(municipio, classe)
        rows = self.connection.execute(
            text(
                "SELECT competencia, SUM(receita_faturada) AS receita_faturada, "
                "SUM(consumo_kwh) AS consumo_kwh, "
                "SUM(ucs_faturadas) AS ucs_faturadas, "
                "SUM(faturas) AS faturas, "
                "SUM(faturas_atrasadas) AS faturas_atrasadas "
                "FROM agg_receita_mensal "
                f"WHERE competencia BETWEEN :inicio AND :fim{filters} "
                "GROUP BY competencia ORDER BY competencia"
            ),
            {"inicio": inicio, "fim": fim, **values},
        )
        return [dict(row._mapping) for row in rows]

    def get_class_revenue(
        self,
        inicio: date,
        fim: date,
        municipio: str | None = None,
        classe: str | None = None,
    ) -> list[dict[str, object]]:
        filters, values = self._filters(municipio, classe)
        rows = self.connection.execute(
            text(
                "SELECT competencia, classe, "
                "SUM(receita_faturada) AS receita_faturada "
                "FROM agg_receita_mensal "
                f"WHERE competencia BETWEEN :inicio AND :fim{filters} "
                "GROUP BY competencia, classe ORDER BY competencia, classe"
            ),
            {"inicio": inicio, "fim": fim, **values},
        )
        return [dict(row._mapping) for row in rows]

    def get_classes(self) -> list[str]:
        rows = self.connection.execute(
            text(
                "SELECT DISTINCT classe FROM dim_unidade_consumidora "
                "WHERE classe IS NOT NULL ORDER BY classe"
            )
        )
        return list(rows.scalars())
