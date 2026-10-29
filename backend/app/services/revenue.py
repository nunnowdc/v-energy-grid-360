"""Composição da comparação de receita entre dois períodos para o Portal."""

import re
from collections.abc import Mapping

from app.repositories.revenue import RevenuePeriods, RevenueRepository

# Sem escolha, 12 meses de cada lado; escolhidos, até 24 meses, o mesmo tamanho nos dois
_DEFAULT_MONTHS = 12
_MAX_MONTHS = 24
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
    fim_p0: str | None,
    inicio_p1: str | None,
    fim_p1: str | None,
) -> RevenuePeriods:
    """Sem escolha, compara o primeiro ano da base com os últimos 12 meses."""
    first, last = calendar
    if not all(
        isinstance(month, str) and _MONTH_PATTERN.fullmatch(month) for month in calendar
    ):
        raise RevenueMetadataUnavailableError
    first_index, last_index = _month_index(first), _month_index(last)
    if last_index - first_index + 1 < 2 * _DEFAULT_MONTHS:
        raise RevenueMetadataUnavailableError

    chosen = (inicio_p0, fim_p0, inicio_p1, fim_p1)
    if all(month is None for month in chosen):
        return RevenuePeriods(
            p0_inicio=_month_text(first_index),
            p0_fim=_month_text(first_index + _DEFAULT_MONTHS - 1),
            p1_inicio=_month_text(last_index - _DEFAULT_MONTHS + 1),
            p1_fim=_month_text(last_index),
        )
    if any(month is None for month in chosen):
        raise InvalidRevenueFilterError(
            "Informe inicio_p0, fim_p0, inicio_p1 e fim_p1 juntos"
        )
    if not all(_MONTH_PATTERN.fullmatch(month) for month in chosen):
        raise InvalidRevenueFilterError("Período inválido")

    start_p0, end_p0, start_p1, end_p1 = (_month_index(month) for month in chosen)
    size = end_p0 - start_p0 + 1
    # Mesmo tamanho dos dois lados, dentro da base, com o comparado depois do base
    if (
        not 1 <= size <= _MAX_MONTHS
        or end_p1 - start_p1 + 1 != size
        or start_p0 < first_index
        or start_p1 <= end_p0
        or end_p1 > last_index
    ):
        raise InvalidRevenueFilterError("Período inválido")
    return RevenuePeriods(
        *(_month_text(index) for index in (start_p0, end_p0, start_p1, end_p1))
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
    fim_p0: str | None = None,
    inicio_p1: str | None = None,
    fim_p1: str | None = None,
) -> dict[str, object]:
    """Organiza medidas Gold no mesmo recorte para total, GD e detalhe."""
    periods = _periods(repository.get_calendar(), inicio_p0, fim_p0, inicio_p1, fim_p1)
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
