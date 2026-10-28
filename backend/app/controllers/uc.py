"""Borda HTTP da Visão 360 da unidade consumidora."""

from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from typing import Annotated

from app.core.database import get_connection
from app.exceptions.uc import (
    GoldUnavailableError,
    InvalidPaginationError,
    InvalidUCIdError,
    UCNotFoundError,
)
from app.repositories.uc import UCRepository
from app.schemas.uc import UC360Response
from app.services.uc import get_visao_360
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.exc import (
    InterfaceError,
    OperationalError,
    SQLAlchemyError,
    TimeoutError,
)

router = APIRouter()


@contextmanager
def _uc_repository_context() -> Iterator[UCRepository]:
    """Abre uma conexão Gold apenas durante a composição da resposta."""
    with get_connection() as connection:
        yield UCRepository(connection)


def get_uc_repository() -> AbstractContextManager[UCRepository]:
    """Fornece o contexto sem abrir conexão antes da validação HTTP."""
    return _uc_repository_context()


@router.get(
    "/uc/{uc_id}/360",
    response_model=UC360Response,
    responses={
        404: {
            "description": "UC não encontrada",
            "content": {
                "application/json": {
                    "example": {"detail": "Unidade consumidora não encontrada"}
                }
            },
        },
        503: {
            "description": "Gold indisponível",
            "content": {
                "application/json": {"example": {"detail": "Gold indisponível"}}
            },
        },
    },
)
def read_uc_360(
    repository_context: Annotated[
        AbstractContextManager[UCRepository], Depends(get_uc_repository)
    ],
    uc_id: str = Path(pattern=r"^UC[0-9]{6}$"),
    pagina_faturas: int = Query(default=1, ge=1),
    pagina_interrupcoes: int = Query(default=1, ge=1),
    pagina_chamados: int = Query(default=1, ge=1),
    pagina_leituras: int = Query(default=1, ge=1),
    limite: int = Query(default=20, ge=1, le=50),
) -> dict[str, object]:
    """Consulta a UC exata e devolve as quatro abas e os cartões aprovados."""
    try:
        with repository_context as repository:
            return get_visao_360(
                uc_id,
                pagina_faturas,
                pagina_interrupcoes,
                pagina_chamados,
                pagina_leituras,
                limite,
                repository,
            )
    except UCNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (InvalidUCIdError, InvalidPaginationError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (
        GoldUnavailableError,
        InterfaceError,
        OperationalError,
        TimeoutError,
    ) as exc:
        raise HTTPException(status_code=503, detail="Gold indisponível") from exc
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Erro interno") from None
    except RuntimeError as exc:
        if str(exc) != "DATABASE_URL não configurada":
            raise
        raise HTTPException(status_code=503, detail="Gold indisponível") from exc
