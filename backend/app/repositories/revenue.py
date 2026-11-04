"""Agregações somente leitura da decomposição de receita Gold."""

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.engine import Connection


@dataclass(frozen=True)
class RevenuePeriods:
    """Meses (yyyy-MM) do período base (P0) e do comparado (P1)."""

    p0_inicio: str
    p0_fim: str
    p1_inicio: str
    p1_fim: str


# Mesma conta da Gold (05_gold_receita.py → agg_receita_preco_volume), feita por
# célula município × bairro × classe × GD a partir de agg_receita_mensal, para
# qualquer par de períodos. UCs = UCs faturadas no último mês de cada período
# (na base, toda UC ativa é faturada todo mês: igual às UCs distintas do período)
_CELLS = (
    "WITH celulas AS ("
    " SELECT municipio, bairro, classe, possui_gd,"
    " COALESCE(SUM(receita_faturada) FILTER (WHERE mes_referencia BETWEEN :p0_inicio AND :p0_fim), 0) AS receita_p0,"
    " COALESCE(SUM(receita_faturada) FILTER (WHERE mes_referencia BETWEEN :p1_inicio AND :p1_fim), 0) AS receita_p1,"
    " COALESCE(SUM(consumo_kwh) FILTER (WHERE mes_referencia BETWEEN :p0_inicio AND :p0_fim), 0) AS kwh_p0,"
    " COALESCE(SUM(consumo_kwh) FILTER (WHERE mes_referencia BETWEEN :p1_inicio AND :p1_fim), 0) AS kwh_p1,"
    " COALESCE(SUM(ucs_faturadas) FILTER (WHERE mes_referencia = :p0_fim), 0) AS ucs_p0,"
    " COALESCE(SUM(ucs_faturadas) FILTER (WHERE mes_referencia = :p1_fim), 0) AS ucs_p1"
    " FROM agg_receita_mensal"
    " WHERE (mes_referencia BETWEEN :p0_inicio AND :p0_fim"
    " OR mes_referencia BETWEEN :p1_inicio AND :p1_fim){predicate}"
    " GROUP BY municipio, bairro, classe, possui_gd"
    "), medidas AS ("
    " SELECT *,"
    # Segmento sem consumo no período base: toda a variação é volume, como na Gold
    " CASE WHEN kwh_p0 > 0 THEN (kwh_p1 - kwh_p0) * receita_p0 / kwh_p0"
    " ELSE receita_p1 - receita_p0 END AS efeito_volume"
    " FROM celulas"
    ") "
)
_SUMS = (
    "SUM(receita_p0) AS receita_p0, "
    "SUM(receita_p1) AS receita_p1, "
    "SUM(kwh_p0) AS kwh_p0, "
    "SUM(kwh_p1) AS kwh_p1, "
    "SUM(ucs_p0) AS ucs_p0, "
    "SUM(ucs_p1) AS ucs_p1, "
    "SUM(efeito_volume) AS efeito_volume, "
    "SUM(receita_p1 - receita_p0 - efeito_volume) AS efeito_preco"
)
_DETAIL_COLUMNS = {"municipio", "bairro", "classe"}


def _where(
    municipio: str | None, bairro: str | None, classe: str | None
) -> tuple[str, dict[str, str]]:
    predicates: list[str] = []
    parameters: dict[str, str] = {}
    for field, value in (
        ("municipio", municipio),
        ("bairro", bairro),
        ("classe", classe),
    ):
        if value is not None:
            predicates.append(f"{field} = :{field}")
            parameters[field] = value
    return "".join(f" AND {predicate}" for predicate in predicates), parameters


def _query(
    select: str,
    periods: RevenuePeriods,
    municipio: str | None,
    bairro: str | None,
    classe: str | None,
) -> tuple[str, dict[str, str]]:
    predicate, parameters = _where(municipio, bairro, classe)
    sql = _CELLS.format(predicate=predicate) + select
    return sql, {**parameters, **vars(periods)}


class RevenueRepository:
    def __init__(self, connection: Connection) -> None:
        self.connection = connection

    def get_calendar(self) -> tuple[str | None, str | None]:
        """Primeiro e último mês (yyyy-MM) da série mensal de receita."""
        row = self.connection.execute(
            text(
                "SELECT MIN(mes_referencia) AS primeiro, "
                "MAX(mes_referencia) AS ultimo FROM agg_receita_mensal"
            )
        ).one()
        return row.primeiro, row.ultimo

    def get_total(
        self,
        periods: RevenuePeriods,
        municipio: str | None = None,
        bairro: str | None = None,
        classe: str | None = None,
    ) -> dict[str, object]:
        sql, parameters = _query(
            f"SELECT {_SUMS} FROM medidas", periods, municipio, bairro, classe
        )
        row = self.connection.execute(text(sql), parameters).mappings().one()
        return dict(row)

    def get_by_gd(
        self,
        periods: RevenuePeriods,
        municipio: str | None = None,
        bairro: str | None = None,
        classe: str | None = None,
    ) -> list[dict[str, object]]:
        sql, parameters = _query(
            f"SELECT possui_gd, {_SUMS} FROM medidas GROUP BY possui_gd",
            periods,
            municipio,
            bairro,
            classe,
        )
        rows = self.connection.execute(text(sql), parameters).mappings()
        return [dict(row) for row in rows]

    def get_by_municipio(self, periods: RevenuePeriods) -> list[dict[str, object]]:
        sql, parameters = _query(
            f"SELECT municipio AS nome, {_SUMS} FROM medidas GROUP BY municipio",
            periods,
            None,
            None,
            None,
        )
        rows = self.connection.execute(text(sql), parameters).mappings()
        return [dict(row) for row in rows]

    def get_detail(
        self,
        periods: RevenuePeriods,
        level: str,
        municipio: str | None = None,
        bairro: str | None = None,
        classe: str | None = None,
    ) -> list[dict[str, object]]:
        if level not in _DETAIL_COLUMNS:
            raise ValueError("Nível de detalhamento inválido")
        sql, parameters = _query(
            f"SELECT {level} AS nome, {_SUMS} FROM medidas GROUP BY {level}",
            periods,
            municipio,
            bairro,
            classe,
        )
        rows = self.connection.execute(text(sql), parameters).mappings()
        return [dict(row) for row in rows]

    def has_municipio(self, municipio: str) -> bool:
        return (
            self.connection.execute(
                text(
                    "SELECT 1 FROM dim_unidade_consumidora "
                    "WHERE municipio = :municipio LIMIT 1"
                ),
                {"municipio": municipio},
            ).scalar_one_or_none()
            is not None
        )

    def has_bairro(self, municipio: str, bairro: str) -> bool:
        return (
            self.connection.execute(
                text(
                    "SELECT 1 FROM dim_unidade_consumidora "
                    "WHERE municipio = :municipio AND bairro = :bairro LIMIT 1"
                ),
                {"municipio": municipio, "bairro": bairro},
            ).scalar_one_or_none()
            is not None
        )

    def has_classe(self, classe: str) -> bool:
        return (
            self.connection.execute(
                text(
                    "SELECT 1 FROM dim_unidade_consumidora "
                    "WHERE classe = :classe LIMIT 1"
                ),
                {"classe": classe},
            ).scalar_one_or_none()
            is not None
        )
