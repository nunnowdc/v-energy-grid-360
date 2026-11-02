"""Uso do agente de IA no portal, a partir da auditoria de cada pergunta."""

from datetime import date, timedelta
from typing import Any

from app.repositories.agent_usage import AgentUsageRepository

# Janelas que a tela oferece: última semana, último mês e último trimestre
DIAS_PERMITIDOS = (7, 30, 90)
DIAS_PADRAO = 30
# Perguntas mais recentes listadas na tela
LIMITE_ULTIMAS = 20


class InvalidUsageWindowError(ValueError):
    """Janela de dias fora das oferecidas pela tela."""


def validate_days(dias: str | None) -> int:
    if dias is None:
        return DIAS_PADRAO
    if not dias.isdigit() or int(dias) not in DIAS_PERMITIDOS:
        raise InvalidUsageWindowError("Use dias=7, 30 ou 90")
    return int(dias)


def _number_or_none(value: Any) -> float | None:
    return None if value is None else float(value)


def _empty_day(dia: date) -> dict[str, Any]:
    return {
        "dia": dia,
        "perguntas": 0,
        "respondidas": 0,
        "recusas": 0,
        "erros": 0,
        "tempo_medio_ms": None,
        "tokens_medio": None,
    }


def get_agent_usage(repository: AgentUsageRepository, dias: int) -> dict[str, Any]:
    """Resumo, série por dia (inclusive os dias sem perguntas) e as últimas perguntas."""
    fim = repository.get_today()
    inicio = fim - timedelta(days=dias - 1)

    summary = repository.get_summary(inicio, fim)
    by_day = {row["dia"]: row for row in repository.get_daily(inicio, fim)}
    series = []
    for offset in range(dias):
        dia = inicio + timedelta(days=offset)
        row = by_day.get(dia)
        if row is None:
            series.append(_empty_day(dia))
            continue
        series.append(
            {
                **row,
                "tempo_medio_ms": _number_or_none(row["tempo_medio_ms"]),
                "tokens_medio": _number_or_none(row["tokens_medio"]),
            }
        )

    return {
        "inicio": inicio,
        "fim": fim,
        "resumo": {
            **summary,
            "tempo_medio_ms": _number_or_none(summary["tempo_medio_ms"]),
            "tempo_p95_ms": _number_or_none(summary["tempo_p95_ms"]),
            "tokens_medio": _number_or_none(summary["tokens_medio"]),
            "tokens_total": int(summary["tokens_total"]),
        },
        "por_dia": series,
        "ultimas": repository.get_latest(inicio, fim, LIMITE_ULTIMAS),
    }
