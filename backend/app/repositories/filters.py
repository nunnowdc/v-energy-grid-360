"""Consultas de leitura das opções de filtros na Gold."""

from sqlalchemy import text
from sqlalchemy.engine import Connection


class FiltersRepository:
    def __init__(self, connection: Connection) -> None:
        self.connection = connection

    def get_competencias(self) -> list[str]:
        rows = self.connection.execute(
            text(
                "SELECT DISTINCT competencia, mes_referencia "
                "FROM dim_competencia WHERE mes_referencia IS NOT NULL "
                "ORDER BY competencia, mes_referencia"
            )
        )
        return [row.mes_referencia for row in rows]

    def get_municipio_bairro_pairs(self) -> list[tuple[str, str | None]]:
        rows = self.connection.execute(
            text(
                "SELECT DISTINCT municipio, bairro FROM dim_unidade_consumidora "
                "WHERE municipio IS NOT NULL ORDER BY municipio, bairro"
            )
        )
        return [(row.municipio, row.bairro) for row in rows]

    def get_classes(self) -> list[str]:
        rows = self.connection.execute(
            text(
                "SELECT DISTINCT classe FROM dim_unidade_consumidora "
                "WHERE classe IS NOT NULL ORDER BY classe"
            )
        )
        return list(rows.scalars())

    def get_alimentadores(self) -> list[str]:
        rows = self.connection.execute(
            text(
                "SELECT DISTINCT alimentador FROM dim_alimentador "
                "WHERE alimentador IS NOT NULL ORDER BY alimentador"
            )
        )
        return list(rows.scalars())

    def get_alimentador_municipio_pairs(self) -> list[tuple[str, str]]:
        rows = self.connection.execute(
            text(
                "SELECT DISTINCT alimentador, municipio "
                "FROM dim_unidade_consumidora "
                "WHERE alimentador IS NOT NULL AND municipio IS NOT NULL "
                "ORDER BY alimentador, municipio"
            )
        )
        return [(row.alimentador, row.municipio) for row in rows]

    def get_causas(self) -> list[str]:
        rows = self.connection.execute(
            text(
                "SELECT DISTINCT causa FROM fact_ocorrencias "
                "WHERE causa IS NOT NULL ORDER BY causa"
            )
        )
        return list(rows.scalars())
