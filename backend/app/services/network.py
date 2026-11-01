"""Composição da resposta padrão de Continuidade a partir da Gold."""

from datetime import date
from math import fsum, isfinite

from app.repositories.network import NetworkRepository
from app.services.metrics import (
    CALENDAR_UNAVAILABLE_DETAIL,
    InvalidMetricsParametersError,
    validate_metrics_period,
    validate_previous_period,
)


class NetworkCalendarUnavailableError(Exception):
    """Calendário Gold incapaz de formar as duas janelas padrão."""


class NetworkGoldUnavailableError(Exception):
    """Medidas obrigatórias da Gold ausentes ou inconsistentes."""


class InvalidNetworkFilterError(ValueError):
    """Filtro de Continuidade fora do catálogo Gold aprovado."""


def _month_index(month: date) -> int:
    return month.year * 12 + month.month - 1


def _month_at(index: int) -> date:
    return date(index // 12, index % 12 + 1, 1)


def _number(row: dict[str, object], key: str) -> float:
    value = row.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise NetworkGoldUnavailableError
    number = float(value)
    if not isfinite(number) or number < 0:
        raise NetworkGoldUnavailableError
    return number


def _sum_window(rows: list[dict[str, object]]) -> dict[str, float]:
    totals = {}
    for key in ("dec", "fec", "dec_sem_dia_critico", "fec_sem_dia_critico"):
        try:
            total = fsum(_number(row, key) for row in rows)
        except OverflowError as exc:
            raise NetworkGoldUnavailableError from exc
        if not isfinite(total):
            raise NetworkGoldUnavailableError
        totals[key] = total
    return totals


def get_continuity(
    repository: NetworkRepository,
    inicio: str | None = None,
    fim: str | None = None,
    inicio_anterior: str | None = None,
    fim_anterior: str | None = None,
    municipio: str | None = None,
    alimentador: str | None = None,
    causa: str | None = None,
) -> dict[str, object]:
    """Compara janelas escolhidas ou os últimos 12 meses com os 12 anteriores."""
    compared_start, compared_end, size = validate_metrics_period(inicio, fim)
    chosen_previous = validate_previous_period(
        inicio_anterior, fim_anterior, compared_start, size
    )
    calendar = repository.get_calendar()
    if not calendar:
        raise NetworkCalendarUnavailableError(CALENDAR_UNAVAILABLE_DETAIL)
    months = set()
    for month, label in calendar:
        if (
            not isinstance(month, date)
            or month.day != 1
            or label != month.strftime("%Y-%m")
            or month in months
        ):
            raise NetworkCalendarUnavailableError(CALENDAR_UNAVAILABLE_DETAIL)
        months.add(month)

    first_index = _month_index(min(months))
    last = max(months)
    compared_end = compared_end or last
    if compared_end > last:
        raise InvalidMetricsParametersError("Período inválido")
    if compared_start is None:
        compared_start_index = _month_index(compared_end) - size + 1
        if compared_start_index < first_index:
            raise NetworkCalendarUnavailableError(CALENDAR_UNAVAILABLE_DETAIL)
        compared_start = _month_at(compared_start_index)
    if chosen_previous is None:
        previous_start_index = _month_index(compared_start) - size
        if previous_start_index < first_index:
            raise NetworkCalendarUnavailableError(CALENDAR_UNAVAILABLE_DETAIL)
        previous_start = _month_at(previous_start_index)
    else:
        previous_start = chosen_previous
    previous_end = _month_at(_month_index(previous_start) + size - 1)
    required = {
        _month_at(index)
        for start in (previous_start, compared_start)
        for index in range(_month_index(start), _month_index(start) + size)
    }
    if not required.issubset(months):
        raise NetworkCalendarUnavailableError(CALENDAR_UNAVAILABLE_DETAIL)

    catalog_feeders = repository.get_feeders()
    if not catalog_feeders or len(catalog_feeders) != len(set(catalog_feeders)):
        raise NetworkGoldUnavailableError
    if municipio == "":
        municipio = None
    elif municipio is not None and (
        not municipio.strip() or municipio not in repository.get_municipios()
    ):
        raise InvalidNetworkFilterError("Município inválido")
    if alimentador == "":
        alimentador = None
    elif alimentador is not None and (
        not alimentador.strip() or alimentador not in catalog_feeders
    ):
        raise InvalidNetworkFilterError("Alimentador inválido")
    if causa == "":
        causa = None
    elif causa is not None and (
        not causa.strip() or causa not in repository.get_causas()
    ):
        raise InvalidNetworkFilterError("Causa inválida")

    feeders = catalog_feeders
    if municipio is not None:
        associated = {
            feeder
            for feeder, city in repository.get_alimentador_municipio_pairs()
            if city == municipio
        }
        if alimentador is not None and alimentador not in associated:
            raise InvalidNetworkFilterError("Município e alimentador incompatíveis")
        feeders = [feeder for feeder in feeders if feeder in associated]
    if alimentador is not None:
        feeders = [alimentador]

    if not feeders:
        return {
            "periodo": {
                "inicio": compared_start.strftime("%Y-%m"),
                "fim": compared_end.strftime("%Y-%m"),
            },
            "periodo_anterior": {
                "inicio": previous_start.strftime("%Y-%m"),
                "fim": previous_end.strftime("%Y-%m"),
            },
            "ranking": [],
            "serie": None,
            "ocorrencias": {"total": 0, "total_anterior": 0, "por_causa": []},
        }

    monthly = repository.get_monthly(previous_start, previous_end)
    monthly += repository.get_monthly(compared_start, compared_end)
    by_feeder: dict[str, dict[date, dict[str, object]]] = {
        feeder: {} for feeder in feeders
    }
    for row in monthly:
        feeder = row.get("alimentador")
        if feeder in catalog_feeders and feeder not in feeders:
            continue
        month = row.get("competencia")
        if (
            not isinstance(feeder, str)
            or feeder not in by_feeder
            or not isinstance(month, date)
            or month not in required
            or month in by_feeder[feeder]
            or row.get("mes_referencia") != month.strftime("%Y-%m")
        ):
            raise NetworkGoldUnavailableError
        by_feeder[feeder][month] = row

    ranked: list[tuple[float, dict[str, object]]] = []
    for feeder in feeders:
        rows_by_month = by_feeder[feeder]
        if set(rows_by_month) != required:
            raise NetworkGoldUnavailableError
        previous_rows = [
            rows_by_month[_month_at(index)]
            for index in range(
                _month_index(previous_start), _month_index(previous_end) + 1
            )
        ]
        compared_rows = [
            rows_by_month[_month_at(index)]
            for index in range(
                _month_index(compared_start), _month_index(compared_end) + 1
            )
        ]
        for period_rows in (previous_rows, compared_rows):
            denominators = [row.get("total_ucs") for row in period_rows]
            if (
                any(
                    not isinstance(value, int) or isinstance(value, bool) or value <= 0
                    for value in denominators
                )
                or len(set(denominators)) != 1
            ):
                raise NetworkGoldUnavailableError
        current = _sum_window(compared_rows)
        previous = _sum_window(previous_rows)
        latest = rows_by_month[compared_end]
        municipio_principal = latest.get("municipio_principal")
        small = latest.get("alimentador_pequeno")
        if not isinstance(municipio_principal, str) or not isinstance(small, bool):
            raise NetworkGoldUnavailableError
        ranked.append(
            (
                current["dec"],
                {
                    "alimentador": feeder,
                    "municipio_principal": municipio_principal,
                    "total_ucs": latest["total_ucs"],
                    "alimentador_pequeno": small,
                    "dec": round(current["dec"], 6),
                    "fec": round(current["fec"], 6),
                    "dec_sem_dia_critico": round(current["dec_sem_dia_critico"], 6),
                    "dec_anterior": round(previous["dec"], 6),
                },
            )
        )
    ranked.sort(key=lambda item: (-item[0], item[1]["alimentador"]))
    ranking = [item[1] for item in ranked]
    selected = ranking[0]["alimentador"]
    selected_months = by_feeder[selected]

    def series(start: date, end: date) -> list[dict[str, object]]:
        return [
            {
                "mes_referencia": selected_months[_month_at(index)]["mes_referencia"],
                "dec": _number(selected_months[_month_at(index)], "dec"),
                "fec": _number(selected_months[_month_at(index)], "fec"),
            }
            for index in range(_month_index(start), _month_index(end) + 1)
        ]

    total = 0
    total_previous = 0
    causes: dict[str, int] = {}
    occurrence_rows = repository.get_occurrence_counts(
        previous_start, previous_end, feeders, causa
    )
    occurrence_rows += repository.get_occurrence_counts(
        compared_start, compared_end, feeders, causa
    )
    for row in occurrence_rows:
        month = row.get("competencia")
        cause = row.get("causa")
        count = row.get("ocorrencias")
        if (
            not isinstance(month, date)
            or month not in required
            or not isinstance(cause, str)
            or not isinstance(count, int)
            or isinstance(count, bool)
            or count < 0
        ):
            raise NetworkGoldUnavailableError
        if month >= compared_start:
            total += count
            causes[cause] = causes.get(cause, 0) + count
        else:
            total_previous += count

    return {
        "periodo": {
            "inicio": compared_start.strftime("%Y-%m"),
            "fim": compared_end.strftime("%Y-%m"),
        },
        "periodo_anterior": {
            "inicio": previous_start.strftime("%Y-%m"),
            "fim": previous_end.strftime("%Y-%m"),
        },
        "ranking": ranking,
        "serie": {
            "alimentador": selected,
            "atual": series(compared_start, compared_end),
            "anterior": series(previous_start, previous_end),
        },
        "ocorrencias": {
            "total": total,
            "total_anterior": total_previous,
            "por_causa": [
                {"causa": cause, "ocorrencias": count}
                for cause, count in sorted(
                    causes.items(), key=lambda item: (-item[1], item[0])
                )
            ],
        },
    }
