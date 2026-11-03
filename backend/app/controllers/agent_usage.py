"""Borda HTTP do uso do agente de IA, para a tela do Admin TI."""

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
from app.repositories.agent_usage import AgentUsageRepository
from app.schemas.agent_usage import AgentUsageResponse
from app.services.agent_usage import (
    InvalidUsageWindowError,
    get_agent_usage,
    validate_days,
)

router = APIRouter()

AUDIT_UNAVAILABLE_DETAIL = "Auditoria do agente indisponível"


@contextmanager
def _agent_usage_repository_context() -> Iterator[AgentUsageRepository]:
    with get_connection() as connection:
        yield AgentUsageRepository(connection)


def get_agent_usage_repository() -> AbstractContextManager[AgentUsageRepository]:
    """Abre a conexão só depois de validar os parâmetros."""
    return _agent_usage_repository_context()


@router.get(
    "/ai/usage",
    tags=["Agente de IA"],
    response_model=AgentUsageResponse,
    responses={
        422: {"description": "Janela de dias inválida"},
        # Também quando a tb_auditoria_agente ainda não foi criada (setup sem a IA)
        503: {"description": AUDIT_UNAVAILABLE_DETAIL},
        500: {"description": "Erro interno"},
    },
)
def read_agent_usage(
    request: Request,
    repository_context: Annotated[
        AbstractContextManager[AgentUsageRepository],
        Depends(get_agent_usage_repository),
    ],
    dias: str | None = None,
) -> AgentUsageResponse:
    """Perguntas feitas ao agente nos últimos 7, 30 ou 90 dias (padrão: 30).

    Os dias são os de Recife e terminam hoje. Lê só a auditoria: não chama o LLM.
    """
    if any(
        key != "dias" or len(request.query_params.getlist(key)) != 1
        for key in request.query_params
    ):
        raise HTTPException(status_code=422, detail="Parâmetro inválido ou repetido")

    try:
        window = validate_days(dias)
        with repository_context as repository:
            return AgentUsageResponse.model_validate(
                get_agent_usage(repository, window)
            )

    except InvalidUsageWindowError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (
        ConfigurationUnavailableError,
        InterfaceError,
        OperationalError,
        ProgrammingError,
        TimeoutError,
    ) as exc:
        raise HTTPException(status_code=503, detail=AUDIT_UNAVAILABLE_DETAIL) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Erro interno") from exc
