"""Composição da comparação fixa de receita para o Portal."""

from collections.abc import Mapping

from app.repositories.revenue import RevenueRepository

_EXPECTED_P0 = "2022-07 a 2023-06"
_EXPECTED_P1 = "2025-07 a 2026-06"
_ADDITIVE_FIELDS = (
    "receita_p0",
    "receita_p1",
    "kwh_p0",
    "kwh_p1",
    "ucs_p0",
    "ucs_p1",
    "efeito_volume",
    "efeito_preco",
)


class RevenueMetadataUnavailableError(Exception):
    """Períodos da agregação Gold ausentes ou incompatíveis."""


class InvalidRevenueFilterError(Exception):
    """Filtro categórico incompatível com o catálogo Gold."""


def _measures(row: Mapping[str, object] | None) -> dict[str, object]:
    values = {
        field: row[field] if row is not None else None for field in _ADDITIVE_FIELDS
    }
    for period in ("p0", "p1"):
        revenue = values[f"receita_{period}"]
        consumption = values[f"kwh_{period}"]
        values[f"preco_{period}"] = (
            revenue / consumption
            if isinstance(revenue, (int, float))
            and isinstance(consumption, (int, float))
            and consumption > 0
            else None
        )
    return values


def _municipality_order(row: Mapping[str, object]) -> tuple[bool, float, str]:
    current = row["kwh_p1"]
    previous = row["kwh_p0"]
    difference = (
        current - previous
        if isinstance(current, (int, float)) and isinstance(previous, (int, float))
        else None
    )
    return (
        difference is None,
        difference if difference is not None else 0.0,
        str(row["nome"]),
    )


def get_revenue_variance(
    repository: RevenueRepository,
    municipio: str | None = None,
    bairro: str | None = None,
    classe: str | None = None,
) -> dict[str, object]:
    """Organiza medidas Gold no mesmo recorte para total, GD e detalhe."""
    periods = repository.get_periods()
    if periods != [(_EXPECTED_P0, _EXPECTED_P1)]:
        raise RevenueMetadataUnavailableError
    if bairro is not None and municipio is None:
        raise InvalidRevenueFilterError("Bairro exige município")
    if municipio is not None and not repository.has_municipio(municipio):
        raise InvalidRevenueFilterError("Município inválido")
    if bairro is not None and not repository.has_bairro(municipio, bairro):
        raise InvalidRevenueFilterError("Bairro incompatível com município")
    if classe is not None and not repository.has_classe(classe):
        raise InvalidRevenueFilterError("Classe inválida")

    level = (
        "classe"
        if bairro is not None
        else "bairro"
        if municipio is not None
        else "municipio"
    )
    if municipio is None and bairro is None and classe is None:
        total = repository.get_total()
        by_gd_rows = repository.get_by_gd()
        detail_rows = repository.get_by_municipio()
    else:
        total = repository.get_total(municipio=municipio, bairro=bairro, classe=classe)
        by_gd_rows = repository.get_by_gd(
            municipio=municipio, bairro=bairro, classe=classe
        )
        detail_rows = repository.get_detail(
            level, municipio=municipio, bairro=bairro, classe=classe
        )

    by_gd = {row["possui_gd"]: row for row in by_gd_rows}
    return {
        "periodo_p0": {"inicio": "2022-07", "fim": "2023-06"},
        "periodo_p1": {"inicio": "2025-07", "fim": "2026-06"},
        "total": _measures(total),
        "por_gd": [
            {"possui_gd": status, **_measures(by_gd.get(status))}
            for status in (False, True)
        ],
        "detalhamento": {
            "nivel": level,
            "linhas": [
                {"nome": row["nome"], **_measures(row)}
                for row in sorted(detail_rows, key=_municipality_order)
            ],
        },
    }
