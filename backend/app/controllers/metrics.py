"""Borda HTTP inicial dos indicadores gerais."""

from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.exc import InterfaceError, OperationalError, TimeoutError

from app.core.database import get_connection
from app.repositories.metrics import MetricsRepository
from app.schemas.metrics import GeneralMetricsResponse
from app.services.metrics import (
    CALENDAR_UNAVAILABLE_DETAIL,
    CalendarUnavailableError,
    InvalidMetricsParametersError,
    get_general_metrics,
    validate_metrics_period,
)

router = APIRouter()


@contextmanager
def _metrics_repository_context() -> Iterator[MetricsRepository]:
    with get_connection() as connection:
        yield MetricsRepository(connection)


def get_metrics_repository() -> AbstractContextManager[MetricsRepository]:
    return _metrics_repository_context()


@router.get(
    "/metrics/general",
    response_model=GeneralMetricsResponse,
    responses={
        422: {"description": "Parâmetros inválidos"},
        503: {
            "description": "Gold ou recorte temporal indisponível",
            "content": {
                "application/json": {
                    "examples": {
                        "gold": {"value": {"detail": "Gold indisponível"}},
                        "calendario": {
                            "value": {"detail": CALENDAR_UNAVAILABLE_DETAIL}
                        },
                    }
                }
            },
        },
        500: {"description": "Erro interno"},
    },
)
def read_general_metrics(
    repository_context: Annotated[
        AbstractContextManager[MetricsRepository], Depends(get_metrics_repository)
    ],
    request: Request,
    inicio: str | None = None,
    fim: str | None = None,
    municipio: str | None = None,
    classe: str | None = None,
) -> GeneralMetricsResponse:
    allowed = {"inicio", "fim", "municipio", "classe"}
    if any(
        key not in allowed or len(request.query_params.getlist(key)) != 1
        for key in request.query_params
    ):
        raise HTTPException(status_code=422, detail="Parâmetro inválido ou repetido")
    try:
        validate_metrics_period(inicio, fim)
        with repository_context as repository:
            result = get_general_metrics(repository, inicio, fim, municipio, classe)
            return GeneralMetricsResponse.model_validate(result)
    except CalendarUnavailableError as exc:
        raise HTTPException(
            status_code=503, detail=CALENDAR_UNAVAILABLE_DETAIL
        ) from exc
    except InvalidMetricsParametersError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (InterfaceError, OperationalError, TimeoutError) as exc:
        raise HTTPException(status_code=503, detail="Gold indisponível") from exc
    except RuntimeError as exc:
        if str(exc) == "DATABASE_URL não configurada":
            raise HTTPException(status_code=503, detail="Gold indisponível") from exc
        raise HTTPException(status_code=500, detail="Erro interno") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Erro interno") from exc
