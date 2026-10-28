"""Agregações somente leitura da decomposição de receita Gold."""

from sqlalchemy import text
from sqlalchemy.engine import Connection

_SUMS = (
    "SUM(receita_p0) AS receita_p0, "
    "SUM(receita_p1) AS receita_p1, "
    "SUM(kwh_p0) AS kwh_p0, "
    "SUM(kwh_p1) AS kwh_p1, "
    "SUM(ucs_p0) AS ucs_p0, "
    "SUM(ucs_p1) AS ucs_p1, "
    "SUM(efeito_volume) AS efeito_volume, "
    "SUM(efeito_preco) AS efeito_preco"
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
    return (" WHERE " + " AND ".join(predicates) if predicates else ""), parameters


class RevenueRepository:
    def __init__(self, connection: Connection) -> None:
        self.connection = connection

    def get_periods(self) -> list[tuple[str, str]]:
        rows = self.connection.execute(
            text("SELECT DISTINCT periodo_p0, periodo_p1 FROM agg_receita_preco_volume")
        )
        return [(row.periodo_p0, row.periodo_p1) for row in rows]

    def get_total(
        self,
        municipio: str | None = None,
        bairro: str | None = None,
        classe: str | None = None,
    ) -> dict[str, object]:
        predicate, parameters = _where(municipio, bairro, classe)
        row = (
            self.connection.execute(
                text(f"SELECT {_SUMS} FROM agg_receita_preco_volume{predicate}"),
                parameters,
            )
            .mappings()
            .one()
        )
        return dict(row)

    def get_by_gd(
        self,
        municipio: str | None = None,
        bairro: str | None = None,
        classe: str | None = None,
    ) -> list[dict[str, object]]:
        predicate, parameters = _where(municipio, bairro, classe)
        rows = self.connection.execute(
            text(
                f"SELECT possui_gd, {_SUMS} "
                f"FROM agg_receita_preco_volume{predicate} GROUP BY possui_gd"
            ),
            parameters,
        ).mappings()
        return [dict(row) for row in rows]

    def get_by_municipio(self) -> list[dict[str, object]]:
        rows = self.connection.execute(
            text(
                f"SELECT municipio AS nome, {_SUMS} "
                "FROM agg_receita_preco_volume GROUP BY municipio"
            )
        ).mappings()
        return [dict(row) for row in rows]

    def get_detail(
        self,
        level: str,
        municipio: str | None = None,
        bairro: str | None = None,
        classe: str | None = None,
    ) -> list[dict[str, object]]:
        if level not in _DETAIL_COLUMNS:
            raise ValueError("Nível de detalhamento inválido")
        predicate, parameters = _where(municipio, bairro, classe)
        rows = self.connection.execute(
            text(
                f"SELECT {level} AS nome, {_SUMS} "
                f"FROM agg_receita_preco_volume{predicate} GROUP BY {level}"
            ),
            parameters,
        ).mappings()
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
