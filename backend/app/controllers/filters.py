"""Borda HTTP das opções compartilhadas de filtros."""

from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import InterfaceError, OperationalError, TimeoutError

from app.core.database import get_connection
from app.repositories.filters import FiltersRepository
from app.schemas.filters import FilterOptionsResponse
from app.services.filters import get_filter_options

router = APIRouter()


@contextmanager
def _filter_repository_context() -> Iterator[FiltersRepository]:
    with get_connection() as connection:
        yield FiltersRepository(connection)


def get_filter_repository() -> AbstractContextManager[FiltersRepository]:
    """Fornece a conexão Gold somente durante a requisição."""
    return _filter_repository_context()


@router.get(
    "/filters/options",
    response_model=FilterOptionsResponse,
    responses={
        503: {
            "description": "Gold indisponível",
            "content": {
                "application/json": {"example": {"detail": "Gold indisponível"}}
            },
        },
    },
)
def read_filter_options(
    repository_context: Annotated[
        AbstractContextManager[FiltersRepository], Depends(get_filter_repository)
    ],
) -> dict[str, object]:
    try:
        with repository_context as repository:
            return get_filter_options(repository)
    except (InterfaceError, OperationalError, TimeoutError) as exc:
        raise HTTPException(status_code=503, detail="Gold indisponível") from exc
    except RuntimeError as exc:
        if str(exc) == "DATABASE_URL não configurada":
            raise HTTPException(status_code=503, detail="Gold indisponível") from exc
        raise HTTPException(status_code=500, detail="Erro interno") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Erro interno") from exc
