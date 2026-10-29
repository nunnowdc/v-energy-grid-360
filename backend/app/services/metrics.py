"""Composição dos indicadores gerais a partir de agregados Gold."""

import re
from datetime import date

from app.repositories.metrics import MetricsRepository

_PERIOD_PATTERN = re.compile(r"^[0-9]{4}-(0[1-9]|1[0-2])$")
CALENDAR_UNAVAILABLE_DETAIL = (
    "Recorte temporal indisponível: o calendário Gold não possui competências "
    "suficientes para o período solicitado."
)


class CalendarUnavailableError(Exception):
    """Calendário Gold incapaz de formar as duas janelas aprovadas."""


class InvalidMetricsParametersError(ValueError):
    """Parâmetros HTTP inválidos do endpoint de Indicadores."""


def _month_at(index: int) -> date:
    return date(index // 12, index % 12 + 1, 1)


def _month_index(month: date) -> int:
    return month.year * 12 + month.month - 1


def _sum_present(values: list[int | float | None]) -> int | float | None:
    present = [value for value in values if value is not None]
    return sum(present) if present else None


def _parse_month(value: str) -> date:
    if not _PERIOD_PATTERN.fullmatch(value):
        raise InvalidMetricsParametersError("Período inválido")
    try:
        return date.fromisoformat(f"{value}-01")
    except ValueError as exc:
        raise InvalidMetricsParametersError("Período inválido") from exc


def validate_metrics_period(
    inicio: str | None, fim: str | None
) -> tuple[date | None, date | None, int]:
    """Valida a janela informada sem consultar a Gold."""
    if (inicio is None) != (fim is None):
        raise InvalidMetricsParametersError("Informe inicio e fim juntos")
    if inicio is None:
        return None, None, 12
    start = _parse_month(inicio)
    end = _parse_month(fim)
    size = _month_index(end) - _month_index(start) + 1
    # De 1 a 24 meses: com o período anterior, cabe nos 48 meses da base
    if not 1 <= size <= 24:
        raise InvalidMetricsParametersError("Período inválido")
    return start, end, size


def get_general_metrics(
    repository: MetricsRepository,
    inicio: str | None,
    fim: str | None,
    municipio: str | None = None,
    classe: str | None = None,
) -> dict[str, object]:
    """Forma duas janelas consecutivas sem recalcular medidas da Gold."""
    start, end, size = validate_metrics_period(inicio, fim)
    if municipio == "":
        municipio = None
    elif municipio is not None and (
        not municipio.strip() or municipio not in repository.get_municipios()
    ):
        raise InvalidMetricsParametersError("Município inválido")
    classes = repository.get_classes()
    if classe == "":
        classe = None
    elif classe is not None and (not classe.strip() or classe not in classes):
        raise InvalidMetricsParametersError("Classe inválida")
    calendar = repository.get_calendar()
    if not calendar:
        raise CalendarUnavailableError
    months = []
    for month, label in calendar:
        if (
            not isinstance(month, date)
            or month.day != 1
            or label != month.strftime("%Y-%m")
        ):
            raise CalendarUnavailableError
        months.append(month)
    if len(months) != len(set(months)):
        raise CalendarUnavailableError

    last = max(months)
    end = end or last
    # O período pode terminar em qualquer mês da base; sem o anterior, de mesmo
    # tamanho, no calendário, a resposta é 503 (conferido logo abaixo)
    if end > last:
        raise InvalidMetricsParametersError("Período inválido")
    start = start or _month_at(_month_index(end) - size + 1)
    if _month_index(start) != _month_index(end) - size + 1:
        raise InvalidMetricsParametersError("Período inválido")

    first_previous = _month_at(_month_index(start) - size)
    last_previous = _month_at(_month_index(start) - 1)
    required = {
        _month_at(index)
        for index in range(_month_index(first_previous), _month_index(end) + 1)
    }
    if not required.issubset(set(months)):
        raise CalendarUnavailableError

    filters = {}
    if municipio is not None:
        filters["municipio"] = municipio
    if classe is not None:
        filters["classe"] = classe
    monthly_rows = {
        row["competencia"]: row
        for row in repository.get_monthly_metrics(first_previous, end, **filters)
    }
    class_rows = repository.get_class_revenue(first_previous, end, **filters)

    def series(window_start: date, window_end: date) -> list[dict[str, object]]:
        result = []
        for index in range(_month_index(window_start), _month_index(window_end) + 1):
            month = _month_at(index)
            row = monthly_rows.get(month, {})
            result.append(
                {
                    "mes_referencia": month.strftime("%Y-%m"),
                    "receita_faturada": row.get("receita_faturada"),
                    "consumo_kwh": row.get("consumo_kwh"),
                }
            )
        return result

    def summary(window_start: date, window_end: date) -> dict[str, object]:
        rows = [
            monthly_rows.get(_month_at(index))
            for index in range(_month_index(window_start), _month_index(window_end) + 1)
        ]
        receita = _sum_present(
            [row.get("receita_faturada") if row else None for row in rows]
        )
        consumo = _sum_present(
            [row.get("consumo_kwh") if row else None for row in rows]
        )
        return {
            "inicio": window_start.strftime("%Y-%m"),
            "fim": window_end.strftime("%Y-%m"),
            "receita_faturada": receita,
            "consumo_kwh": consumo,
            "preco_medio_kwh": (
                receita / consumo
                if receita is not None and consumo is not None and consumo > 0
                else None
            ),
            "ucs_faturadas": monthly_rows.get(window_end, {}).get("ucs_faturadas"),
            "faturas": _sum_present(
                [row.get("faturas") if row else None for row in rows]
            ),
            "faturas_atrasadas": _sum_present(
                [row.get("faturas_atrasadas") if row else None for row in rows]
            ),
        }

    def revenue_for_class(
        classe: str, window_start: date, window_end: date
    ) -> float | None:
        return _sum_present(
            [
                row["receita_faturada"]
                for row in class_rows
                if row["classe"] == classe
                and window_start <= row["competencia"] <= window_end
            ]
        )

    return {
        "atual": summary(start, end),
        "anterior": summary(first_previous, last_previous),
        "mensal": {
            "atual": series(start, end),
            "anterior": series(first_previous, last_previous),
        },
        "por_classe": [
            {
                "classe": classe,
                "receita_faturada": revenue_for_class(classe, start, end),
                "receita_faturada_anterior": revenue_for_class(
                    classe, first_previous, last_previous
                ),
            }
            for classe in ([classe] if classe is not None else classes)
        ],
    }
