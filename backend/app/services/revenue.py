"""Composição da comparação de receita entre dois períodos para o Portal."""

import re
from collections.abc import Mapping

from app.repositories.revenue import RevenuePeriods, RevenueRepository

# Cada período tem 12 meses: mesmos meses do ano dos dois lados, sem sazonalidade
_PERIOD_MONTHS = 12
_MONTH_PATTERN = re.compile(r"^[0-9]{4}-(0[1-9]|1[0-2])$")
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
    """Série mensal Gold ausente ou curta demais para dois períodos."""


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


def _month_index(value: str) -> int:
    year, month = value.split("-")
    return int(year) * 12 + int(month) - 1


def _month_text(index: int) -> str:
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def _periods(
    calendar: tuple[object, object],
    inicio_p0: str | None,
    inicio_p1: str | None,
) -> RevenuePeriods:
    """Sem escolha, compara o primeiro ano da base com os últimos 12 meses."""
    first, last = calendar
    if not all(
        isinstance(month, str) and _MONTH_PATTERN.fullmatch(month) for month in calendar
    ):
        raise RevenueMetadataUnavailableError
    first_index, last_index = _month_index(first), _month_index(last)
    if last_index - first_index + 1 < 2 * _PERIOD_MONTHS:
        raise RevenueMetadataUnavailableError

    if inicio_p0 is None and inicio_p1 is None:
        start_p0, start_p1 = first_index, last_index - _PERIOD_MONTHS + 1
    elif inicio_p0 is None or inicio_p1 is None:
        raise InvalidRevenueFilterError("Informe inicio_p0 e inicio_p1 juntos")
    elif not (
        _MONTH_PATTERN.fullmatch(inicio_p0) and _MONTH_PATTERN.fullmatch(inicio_p1)
    ):
        raise InvalidRevenueFilterError("Período inválido")
    else:
        start_p0, start_p1 = _month_index(inicio_p0), _month_index(inicio_p1)
        # Os dois cabem na base e o comparado vem depois do base, sem sobrepor
        if (
            start_p0 < first_index
            or start_p1 + _PERIOD_MONTHS - 1 > last_index
            or start_p1 < start_p0 + _PERIOD_MONTHS
        ):
            raise InvalidRevenueFilterError("Período inválido")

    return RevenuePeriods(
        p0_inicio=_month_text(start_p0),
        p0_fim=_month_text(start_p0 + _PERIOD_MONTHS - 1),
        p1_inicio=_month_text(start_p1),
        p1_fim=_month_text(start_p1 + _PERIOD_MONTHS - 1),
    )


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
    inicio_p0: str | None = None,
    inicio_p1: str | None = None,
) -> dict[str, object]:
    """Organiza medidas Gold no mesmo recorte para total, GD e detalhe."""
    periods = _periods(repository.get_calendar(), inicio_p0, inicio_p1)
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
        total = repository.get_total(periods)
        by_gd_rows = repository.get_by_gd(periods)
        detail_rows = repository.get_by_municipio(periods)
    else:
        total = repository.get_total(
            periods, municipio=municipio, bairro=bairro, classe=classe
        )
        by_gd_rows = repository.get_by_gd(
            periods, municipio=municipio, bairro=bairro, classe=classe
        )
        detail_rows = repository.get_detail(
            periods, level, municipio=municipio, bairro=bairro, classe=classe
        )

    by_gd = {row["possui_gd"]: row for row in by_gd_rows}
    return {
        "periodo_p0": {"inicio": periods.p0_inicio, "fim": periods.p0_fim},
        "periodo_p1": {"inicio": periods.p1_inicio, "fim": periods.p1_fim},
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
