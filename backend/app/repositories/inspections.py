"""Consultas somente leitura à fila de inspeção Gold."""

from datetime import date

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.repositories.filters import FiltersRepository
from app.repositories.inspection_orders import InspectionOrdersRepository


class InspectionsRepository:
    def __init__(self, connection: Connection) -> None:
        self.connection = connection
        self.orders = InspectionOrdersRepository(connection)

    def get_existing_uc_ids(self, ids_uc: list[str]) -> set[str]:
        rows = self.connection.execute(
            text(
                "SELECT id_uc FROM dim_unidade_consumidora WHERE id_uc = ANY(:ids_uc)"
            ),
            {"ids_uc": ids_uc},
        )
        return set(rows.scalars())

    def get_eligible_units(self, ids_uc: list[str]) -> list[dict[str, str]]:
        rows = self.connection.execute(
            text(
                "SELECT id_uc, municipio, bairro FROM fila_inspecao "
                "WHERE id_uc = ANY(:ids_uc)"
            ),
            {"ids_uc": ids_uc},
        )
        return [dict(row._mapping) for row in rows]

    def get_catalog(self) -> tuple[list[tuple[str, str | None]], list[str]]:
        catalog = FiltersRepository(self.connection)
        return catalog.get_municipio_bairro_pairs(), catalog.get_classes()

    def get_snapshot_date(self) -> date | None:
        return self.connection.execute(
            text("SELECT MAX(data_referencia) FROM fila_inspecao")
        ).scalar_one()

    @staticmethod
    def _filters(
        municipio: str | None, bairro: str | None, classe: str | None
    ) -> tuple[str, dict[str, str]]:
        clauses: list[str] = []
        values: dict[str, str] = {}
        for name, value in (
            ("municipio", municipio),
            ("bairro", bairro),
            ("classe", classe),
        ):
            if value is not None:
                clauses.append(f"{name} = :{name}")
                values[name] = value
        return (" WHERE " + " AND ".join(clauses) if clauses else "", values)

    def get_summary(
        self, municipio: str | None, bairro: str | None, classe: str | None
    ) -> dict[str, int | float | None]:
        filters, values = self._filters(municipio, bairro, classe)
        row = self.connection.execute(
            text(
                "SELECT COUNT(*) AS ucs, "
                "COUNT(kwh_recuperavel_estimado_ano) AS medidas, "
                "SUM(kwh_recuperavel_estimado_ano) AS kwh_recuperavel_estimado_ano "
                f"FROM fila_inspecao{filters}"
            ),
            values,
        ).one()
        return dict(row._mapping)

    def get_items(
        self,
        municipio: str | None,
        bairro: str | None,
        classe: str | None,
        limite: int,
        offset: int,
    ) -> list[dict[str, object]]:
        filters, values = self._filters(municipio, bairro, classe)
        rows = self.connection.execute(
            text(
                "SELECT prioridade, id_uc, score, motivo_suspeita, "
                "kwh_recuperavel_estimado_ano, municipio, bairro, classe "
                f"FROM fila_inspecao{filters} "
                "ORDER BY prioridade ASC, id_uc ASC "
                "LIMIT :limite OFFSET :offset"
            ),
            {**values, "limite": limite, "offset": offset},
        )
        return [dict(row._mapping) for row in rows]

    def get_export_items(
        self, municipio: str | None, bairro: str | None, classe: str | None
    ) -> list[dict[str, object]]:
        """Fila inteira do recorte para o campo: endereço sim, nome do titular não."""
        filters, values = self._filters(municipio, bairro, classe)
        rows = self.connection.execute(
            text(
                "SELECT prioridade, id_uc, score, motivo_suspeita, "
                "kwh_recuperavel_estimado_ano, municipio, bairro, logradouro, "
                "numero, latitude, longitude, classe "
                f"FROM fila_inspecao{filters} "
                "ORDER BY prioridade ASC, id_uc ASC"
            ),
            values,
        )
        return [dict(row._mapping) for row in rows]
