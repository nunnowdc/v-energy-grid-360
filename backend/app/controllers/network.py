"""Borda HTTP da Continuidade da Rede."""

from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.exc import InterfaceError, OperationalError, TimeoutError

from app.core.database import get_connection
from app.repositories.network import NetworkRepository
from app.schemas.network import NetworkContinuityResponse
from app.services.metrics import (
    CALENDAR_UNAVAILABLE_DETAIL,
    InvalidMetricsParametersError,
    validate_metrics_period,
    validate_previous_period,
)
from app.services.network import (
    InvalidNetworkFilterError,
    NetworkCalendarUnavailableError,
    NetworkGoldUnavailableError,
    get_continuity,
)

router = APIRouter()


@contextmanager
def _network_repository_context() -> Iterator[NetworkRepository]:
    with get_connection() as connection:
        yield NetworkRepository(connection)


def get_network_repository() -> AbstractContextManager[NetworkRepository]:
    return _network_repository_context()


@router.get(
    "/network/continuity",
    response_model=NetworkContinuityResponse,
    responses={
        422: {"description": "Parâmetro inválido ou repetido"},
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
def read_network_continuity(
    repository_context: Annotated[
        AbstractContextManager[NetworkRepository], Depends(get_network_repository)
    ],
    request: Request,
    inicio: str | None = Query(
        default=None,
        description=(
            "Início do período comparado (yyyy-MM), informado com fim. "
            "Sem datas, usa os últimos 12 meses disponíveis na Gold."
        ),
    ),
    fim: str | None = Query(
        default=None,
        description="Fim do período comparado (yyyy-MM); duração de 1 a 24 meses.",
    ),
    inicio_anterior: str | None = Query(
        default=None,
        description=(
            "Início do período base (yyyy-MM), informado com fim_anterior. "
            "Sem datas, usa os 12 meses imediatamente anteriores ao comparado; "
            "com apenas o comparado informado, deriva a base imediatamente anterior."
        ),
    ),
    fim_anterior: str | None = Query(
        default=None,
        description=(
            "Fim do período base (yyyy-MM). Base e comparado têm a mesma duração "
            "de 1 a 24 meses, sem sobreposição; quando ambos são informados, "
            "podem ser não consecutivos."
        ),
    ),
    municipio: str | None = Query(
        default=None, description="Seleciona alimentadores que atendem ao município."
    ),
    alimentador: str | None = Query(
        default=None, description="Código do alimentador; DEC/FEC do circuito inteiro."
    ),
    causa: str | None = Query(
        default=None, description="Filtra somente as ocorrências, sem alterar DEC/FEC."
    ),
) -> NetworkContinuityResponse:
    allowed = {
        "inicio",
        "fim",
        "inicio_anterior",
        "fim_anterior",
        "municipio",
        "alimentador",
        "causa",
    }
    if any(
        key not in allowed or len(request.query_params.getlist(key)) != 1
        for key in request.query_params
    ):
        raise HTTPException(status_code=422, detail="Parâmetro inválido ou repetido")

    try:
        start, _, size = validate_metrics_period(inicio, fim)
        validate_previous_period(inicio_anterior, fim_anterior, start, size)
        with repository_context as repository:
            result = get_continuity(
                repository,
                inicio,
                fim,
                inicio_anterior,
                fim_anterior,
                municipio,
                alimentador,
                causa,
            )
            return NetworkContinuityResponse.model_validate(result)
    except InvalidNetworkFilterError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except InvalidMetricsParametersError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except NetworkCalendarUnavailableError as exc:
        raise HTTPException(
            status_code=503, detail=CALENDAR_UNAVAILABLE_DETAIL
        ) from exc
    except NetworkGoldUnavailableError as exc:
        raise HTTPException(status_code=503, detail="Gold indisponível") from exc
    except (InterfaceError, OperationalError, TimeoutError) as exc:
        raise HTTPException(status_code=503, detail="Gold indisponível") from exc
    except RuntimeError as exc:
        if str(exc) == "DATABASE_URL não configurada":
            raise HTTPException(status_code=503, detail="Gold indisponível") from exc
        raise HTTPException(status_code=500, detail="Erro interno") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Erro interno") from exc
