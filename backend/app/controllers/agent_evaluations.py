"""Borda HTTP das avaliações do agente contra o golden set, para a tela do Admin TI."""

from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.exc import (
    InterfaceError,
    OperationalError,
    ProgrammingError,
    TimeoutError,
)

from app.core.config import ConfigurationUnavailableError
from app.core.database import get_connection
from app.repositories.agent_evaluations import AgentEvaluationsRepository
from app.schemas.agent_evaluations import AgentEvaluationsResponse
from app.services.agent_evaluations import get_agent_evaluations

router = APIRouter()

EVALUATIONS_UNAVAILABLE_DETAIL = "Avaliações do agente indisponíveis"


@contextmanager
def _agent_evaluations_repository_context() -> Iterator[AgentEvaluationsRepository]:
    with get_connection() as connection:
        yield AgentEvaluationsRepository(connection)


def get_agent_evaluations_repository() -> AbstractContextManager[
    AgentEvaluationsRepository
]:
    """Abre a conexão só depois de validar os parâmetros."""
    return _agent_evaluations_repository_context()


@router.get(
    "/ai/evaluations",
    tags=["Agente de IA"],
    response_model=AgentEvaluationsResponse,
    responses={
        422: {"description": "A rota não recebe parâmetros"},
        503: {"description": EVALUATIONS_UNAVAILABLE_DETAIL},
        500: {"description": "Erro interno"},
    },
)
def read_agent_evaluations(
    request: Request,
    repository_context: Annotated[
        AbstractContextManager[AgentEvaluationsRepository],
        Depends(get_agent_evaluations_repository),
    ],
) -> AgentEvaluationsResponse:
    """Evolução das avaliações do golden set e os casos da última execução.

    Lê o que ai-agent/scripts/avaliar_golden_set.py gravou: não chama o LLM.
    Antes da primeira execução, as listas vêm vazias.
    """
    if request.query_params:
        raise HTTPException(status_code=422, detail="A rota não recebe parâmetros")

    try:
        with repository_context as repository:
            return AgentEvaluationsResponse.model_validate(
                get_agent_evaluations(repository)
            )

    except (
        ConfigurationUnavailableError,
        InterfaceError,
        OperationalError,
        ProgrammingError,
        TimeoutError,
    ) as exc:
        raise HTTPException(
            status_code=503, detail=EVALUATIONS_UNAVAILABLE_DETAIL
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Erro interno") from exc
