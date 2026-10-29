"""Borda HTTP dos indicadores gerais e da comparação de receita."""

from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.exc import InterfaceError, OperationalError, TimeoutError

from app.core.database import get_connection
from app.repositories.metrics import MetricsRepository
from app.repositories.revenue import RevenueRepository
from app.schemas.metrics import GeneralMetricsResponse, RevenueVarianceResponse
from app.services.metrics import (
    CALENDAR_UNAVAILABLE_DETAIL,
    CalendarUnavailableError,
    InvalidMetricsParametersError,
    get_general_metrics,
    validate_metrics_period,
)
from app.services.revenue import (
    InvalidRevenueFilterError,
    RevenueMetadataUnavailableError,
    get_revenue_variance,
)

router = APIRouter()


# ==========================================================
# Indicadores gerais
# ==========================================================


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


@contextmanager
def _revenue_repository_context() -> Iterator[RevenueRepository]:
    with get_connection() as connection:
        yield RevenueRepository(connection)


def get_revenue_repository() -> AbstractContextManager[RevenueRepository]:
    """Fornece a conexão Gold somente durante a requisição."""
    return _revenue_repository_context()


@router.get(
    "/metrics/revenue-variance",
    response_model=RevenueVarianceResponse,
    responses={
        500: {
            "description": "Falha inesperada",
            "content": {"application/json": {"example": {"detail": "Erro interno"}}},
        },
        503: {
            "description": "Gold indisponível ou metadados de comparação inválidos",
            "content": {
                "application/json": {
                    "examples": {
                        "conexao": {"value": {"detail": "Gold indisponível"}},
                        "metadados": {
                            "value": {
                                "detail": "Dados Gold indisponíveis para comparação de receita"
                            }
                        },
                    }
                }
            },
        },
    },
)
def read_revenue_variance(
    request: Request,
    repository_context: Annotated[
        AbstractContextManager[RevenueRepository], Depends(get_revenue_repository)
    ],
    municipio: str | None = Query(default=None),
    bairro: str | None = Query(default=None),
    classe: str | None = Query(default=None),
    inicio_p0: str | None = Query(
        default=None, description="Primeiro mês (yyyy-MM) do período base"
    ),
    fim_p0: str | None = Query(
        default=None, description="Último mês (yyyy-MM) do período base"
    ),
    inicio_p1: str | None = Query(
        default=None, description="Primeiro mês (yyyy-MM) do período comparado"
    ),
    fim_p1: str | None = Query(
        default=None, description="Último mês (yyyy-MM) do período comparado"
    ),
) -> RevenueVarianceResponse:
    """Expõe a comparação Gold com recorte geográfico e períodos opcionais.

    Os dois períodos têm o mesmo tamanho (1 a 24 meses) e o comparado vem depois
    do base. Sem períodos, compara o primeiro ano da base com os últimos 12 meses.
    """
    allowed = (
        "municipio",
        "bairro",
        "classe",
        "inicio_p0",
        "fim_p0",
        "inicio_p1",
        "fim_p1",
    )

    if any(key not in allowed for key in request.query_params) or any(
        len(request.query_params.getlist(key)) > 1 for key in allowed
    ):
        raise HTTPException(status_code=422, detail="Parâmetros inválidos")

    try:
        with repository_context as repository:
            return RevenueVarianceResponse.model_validate(
                get_revenue_variance(
                    repository,
                    municipio or None,
                    bairro or None,
                    classe or None,
                    inicio_p0 or None,
                    fim_p0 or None,
                    inicio_p1 or None,
                    fim_p1 or None,
                )
            )

    except InvalidRevenueFilterError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RevenueMetadataUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail="Dados Gold indisponíveis para comparação de receita",
        ) from exc
    except (InterfaceError, OperationalError, TimeoutError) as exc:
        raise HTTPException(status_code=503, detail="Gold indisponível") from exc
    except RuntimeError as exc:
        if str(exc) == "DATABASE_URL não configurada":
            raise HTTPException(status_code=503, detail="Gold indisponível") from exc
        raise HTTPException(status_code=500, detail="Erro interno") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Erro interno") from exc
