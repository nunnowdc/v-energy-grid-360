"""Borda HTTP da comparação fixa de receita."""

from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from typing import Annotated

from app.core.database import get_connection
from app.repositories.revenue import RevenueRepository
from app.schemas.metrics import RevenueVarianceResponse
from app.services.revenue import (
    InvalidRevenueFilterError,
    RevenueMetadataUnavailableError,
    get_revenue_variance,
)
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.exc import InterfaceError, OperationalError, TimeoutError

router = APIRouter()


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
) -> RevenueVarianceResponse:
    """Expõe a comparação Gold com recorte geográfico opcional."""
    if any(
        key not in {"municipio", "bairro", "classe"} for key in request.query_params
    ) or any(
        len(request.query_params.getlist(key)) > 1
        for key in ("municipio", "bairro", "classe")
    ):
        raise HTTPException(status_code=422, detail="Parâmetros inválidos")
    try:
        with repository_context as repository:
            return RevenueVarianceResponse.model_validate(
                get_revenue_variance(
                    repository, municipio or None, bairro or None, classe or None
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
