"""Borda HTTP da fila de inspeção Gold."""

from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response
from sqlalchemy.exc import InterfaceError, OperationalError, TimeoutError

from app.core.database import get_connection
from app.repositories.inspection_orders import InspectionOrdersRepository
from app.repositories.inspections import InspectionsRepository
from app.schemas.inspections import (
    CompleteOrderRequest,
    CreateOrdersRequest,
    CreateOrdersResponse,
    InspectionOrder,
    ListOrdersResponse,
    OrderTransitionRequest,
    QueueResponse,
)
from app.services.inspections import (
    ActiveOrderConflictError,
    InvalidOrderBatchError,
    InvalidOrderTransitionError,
    InvalidQueueFilterError,
    OrderNotFoundError,
    QueueSnapshotUnavailableError,
    change_inspection_order,
    create_inspection_orders,
    get_inspection_queue,
    get_inspection_queue_export,
    list_inspection_orders,
)
from app.services.inspections_export import build_queue_workbook

router = APIRouter()


@contextmanager
def _inspections_repository_context() -> Iterator[InspectionsRepository]:
    with get_connection() as connection:
        yield InspectionsRepository(connection)


def get_inspections_repository() -> AbstractContextManager[InspectionsRepository]:
    """Adquire a conexão Gold apenas após a validação HTTP."""
    return _inspections_repository_context()


@contextmanager
def _order_repositories_context() -> Iterator[
    tuple[InspectionsRepository, InspectionOrdersRepository]
]:
    with get_connection() as connection:
        gold = InspectionsRepository(connection)
        yield gold, gold.orders


def get_order_repositories() -> AbstractContextManager[
    tuple[InspectionsRepository, InspectionOrdersRepository]
]:
    """Compartilha uma conexão para leituras Gold e escrita operacional."""
    return _order_repositories_context()


@router.post(
    "/inspections/order",
    status_code=201,
    response_model=CreateOrdersResponse,
    responses={
        422: {"description": "Lote inválido, UC inexistente ou fora da fila"},
        409: {"description": "UC já possui ordem ativa"},
        503: {"description": "PostgreSQL ou fila Gold indisponível"},
        500: {"description": "Erro interno"},
    },
)
def create_orders(
    body: CreateOrdersRequest,
    repository_context: Annotated[
        AbstractContextManager[
            tuple[InspectionsRepository, InspectionOrdersRepository]
        ],
        Depends(get_order_repositories),
    ],
) -> CreateOrdersResponse:
    try:
        with repository_context as (gold, orders):
            result = create_inspection_orders(gold, orders, body.ids_uc)
            return CreateOrdersResponse.model_validate(result)
    except InvalidOrderBatchError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ActiveOrderConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except QueueSnapshotUnavailableError as exc:
        raise HTTPException(status_code=503, detail="Fila Gold indisponível") from exc
    except (InterfaceError, OperationalError, TimeoutError) as exc:
        raise HTTPException(status_code=503, detail="Banco indisponível") from exc
    except RuntimeError as exc:
        if str(exc) == "DATABASE_URL não configurada":
            raise HTTPException(status_code=503, detail="Banco indisponível") from exc
        raise HTTPException(status_code=500, detail="Erro interno") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Erro interno") from exc


@router.get(
    "/inspections/orders",
    response_model=ListOrdersResponse,
    responses={
        422: {"description": "Filtros inválidos"},
        503: {"description": "Gold ou PostgreSQL indisponível"},
        500: {"description": "Erro interno"},
    },
)
def read_inspection_orders(
    repository_context: Annotated[
        AbstractContextManager[
            tuple[InspectionsRepository, InspectionOrdersRepository]
        ],
        Depends(get_order_repositories),
    ],
    request: Request,
    municipio: str | None = None,
    bairro: str | None = None,
    classe: str | None = None,
) -> ListOrdersResponse:
    allowed = {"municipio", "bairro", "classe"}
    if any(
        key not in allowed or len(request.query_params.getlist(key)) != 1
        for key in request.query_params
    ):
        raise HTTPException(status_code=422, detail="Parâmetro inválido ou repetido")
    try:
        with repository_context as (gold, orders):
            result = list_inspection_orders(gold, orders, municipio, bairro, classe)
            return ListOrdersResponse.model_validate(result)
    except InvalidQueueFilterError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except QueueSnapshotUnavailableError as exc:
        raise HTTPException(status_code=503, detail="Gold indisponível") from exc
    except (InterfaceError, OperationalError, TimeoutError) as exc:
        raise HTTPException(status_code=503, detail="Gold indisponível") from exc
    except RuntimeError as exc:
        if str(exc) == "DATABASE_URL não configurada":
            raise HTTPException(status_code=503, detail="Gold indisponível") from exc
        raise HTTPException(status_code=500, detail="Erro interno") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Erro interno") from exc


def _change_order(
    external_id: str,
    status: str,
    resultado: str | None,
    repository_context: AbstractContextManager[
        tuple[InspectionsRepository, InspectionOrdersRepository]
    ],
) -> InspectionOrder:
    order_id = int(external_id[3:])
    if order_id > 2**63 - 1 or f"OI-{order_id:05d}" != external_id:
        raise HTTPException(status_code=422, detail="ID de ordem inválido")
    try:
        with repository_context as (_, orders):
            result = change_inspection_order(orders, order_id, status, resultado)
            return InspectionOrder.model_validate(result)
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Ordem não encontrada") from exc
    except InvalidOrderTransitionError as exc:
        raise HTTPException(
            status_code=409, detail="Transição de ordem inválida"
        ) from exc
    except QueueSnapshotUnavailableError as exc:
        raise HTTPException(status_code=503, detail="Gold indisponível") from exc
    except (InterfaceError, OperationalError, TimeoutError) as exc:
        raise HTTPException(status_code=503, detail="Banco indisponível") from exc
    except RuntimeError as exc:
        if str(exc) == "DATABASE_URL não configurada":
            raise HTTPException(status_code=503, detail="Banco indisponível") from exc
        raise HTTPException(status_code=500, detail="Erro interno") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Erro interno") from exc


@router.patch(
    "/inspections/{id}",
    response_model=InspectionOrder,
    responses={
        404: {"description": "Ordem não encontrada"},
        409: {"description": "Transição inválida ou concorrente"},
        503: {"description": "PostgreSQL indisponível"},
        500: {"description": "Erro interno"},
    },
)
def update_inspection_order(
    body: OrderTransitionRequest,
    repository_context: Annotated[
        AbstractContextManager[
            tuple[InspectionsRepository, InspectionOrdersRepository]
        ],
        Depends(get_order_repositories),
    ],
    id: str = Path(pattern=r"^OI-[0-9]{5,19}$"),
) -> InspectionOrder:
    return _change_order(
        id,
        body.status,
        body.resultado if isinstance(body, CompleteOrderRequest) else None,
        repository_context,
    )


@router.delete(
    "/inspections/{id}",
    response_model=InspectionOrder,
    responses={
        404: {"description": "Ordem não encontrada"},
        409: {"description": "Transição inválida ou concorrente"},
        503: {"description": "PostgreSQL indisponível"},
        500: {"description": "Erro interno"},
    },
)
def cancel_inspection_order(
    repository_context: Annotated[
        AbstractContextManager[
            tuple[InspectionsRepository, InspectionOrdersRepository]
        ],
        Depends(get_order_repositories),
    ],
    id: str = Path(pattern=r"^OI-[0-9]{5,19}$"),
) -> InspectionOrder:
    return _change_order(id, "CANCELADA", None, repository_context)


@router.get(
    "/inspections/queue",
    response_model=QueueResponse,
    responses={
        422: {"description": "Filtros ou paginação inválidos"},
        503: {
            "description": "Gold indisponível ou snapshot da fila vazio",
            "content": {
                "application/json": {
                    "examples": {
                        "conexao": {"value": {"detail": "Gold indisponível"}},
                        "snapshot": {"value": {"detail": "Fila Gold indisponível"}},
                    }
                }
            },
        },
        500: {"description": "Erro interno"},
    },
)
def read_inspection_queue(
    repository_context: Annotated[
        AbstractContextManager[InspectionsRepository],
        Depends(get_inspections_repository),
    ],
    request: Request,
    municipio: str | None = None,
    bairro: str | None = None,
    classe: str | None = None,
    pagina: int = Query(default=1, ge=1),
    limite: int = Query(default=20, ge=1, le=50),
) -> QueueResponse:
    allowed = {"municipio", "bairro", "classe", "pagina", "limite"}
    if any(
        key not in allowed or len(request.query_params.getlist(key)) != 1
        for key in request.query_params
    ):
        raise HTTPException(status_code=422, detail="Parâmetro inválido ou repetido")
    if bairro and not municipio:
        raise HTTPException(status_code=422, detail="Bairro exige município")

    try:
        with repository_context as repository:
            result = get_inspection_queue(
                repository, municipio, bairro, classe, pagina, limite
            )
            return QueueResponse.model_validate(result)
    except InvalidQueueFilterError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except QueueSnapshotUnavailableError as exc:
        raise HTTPException(status_code=503, detail="Fila Gold indisponível") from exc
    except (InterfaceError, OperationalError, TimeoutError) as exc:
        raise HTTPException(status_code=503, detail="Gold indisponível") from exc
    except RuntimeError as exc:
        if str(exc) == "DATABASE_URL não configurada":
            raise HTTPException(status_code=503, detail="Gold indisponível") from exc
        raise HTTPException(status_code=500, detail="Erro interno") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Erro interno") from exc


XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get(
    "/inspections/queue/export",
    response_class=Response,
    responses={
        200: {
            "description": "Fila inteira do recorte em Excel, para a equipe de campo",
            "content": {XLSX_MEDIA_TYPE: {}},
        },
        422: {"description": "Filtros inválidos"},
        503: {"description": "Gold indisponível ou snapshot da fila vazio"},
        500: {"description": "Erro interno"},
    },
)
def export_inspection_queue(
    repository_context: Annotated[
        AbstractContextManager[InspectionsRepository],
        Depends(get_inspections_repository),
    ],
    request: Request,
    municipio: str | None = None,
    bairro: str | None = None,
    classe: str | None = None,
) -> Response:
    allowed = {"municipio", "bairro", "classe"}
    if any(
        key not in allowed or len(request.query_params.getlist(key)) != 1
        for key in request.query_params
    ):
        raise HTTPException(status_code=422, detail="Parâmetro inválido ou repetido")
    if bairro and not municipio:
        raise HTTPException(status_code=422, detail="Bairro exige município")

    try:
        with repository_context as repository:
            export = get_inspection_queue_export(repository, municipio, bairro, classe)
    except InvalidQueueFilterError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except QueueSnapshotUnavailableError as exc:
        raise HTTPException(status_code=503, detail="Fila Gold indisponível") from exc
    except (InterfaceError, OperationalError, TimeoutError) as exc:
        raise HTTPException(status_code=503, detail="Gold indisponível") from exc
    except RuntimeError as exc:
        if str(exc) == "DATABASE_URL não configurada":
            raise HTTPException(status_code=503, detail="Gold indisponível") from exc
        raise HTTPException(status_code=500, detail="Erro interno") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Erro interno") from exc

    filename = f"fila-inspecao_{export['data_referencia'].isoformat()}.xlsx"
    return Response(
        content=build_queue_workbook(export),
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
