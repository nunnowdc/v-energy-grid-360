"""Evolução das avaliações do agente contra o golden set (REQ-AI-08)."""

from typing import Any

from app.repositories.agent_evaluations import AgentEvaluationsRepository

# Execuções mostradas na evolução: as 30 mais recentes
LIMITE_EXECUCOES = 30


def get_agent_evaluations(repository: AgentEvaluationsRepository) -> dict[str, Any]:
    """Execuções em ordem de data e os casos da última; vazio antes da primeira."""
    if not repository.has_tables():
        return {"execucoes": [], "casos": []}
    runs = repository.get_runs(LIMITE_EXECUCOES)
    cases = repository.get_cases(runs[-1]["id"]) if runs else []
    return {"execucoes": runs, "casos": cases}
