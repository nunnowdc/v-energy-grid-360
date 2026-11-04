"""DTOs da fila de inspeção publicada pela Gold."""

from datetime import date
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints


class QueueSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ucs: int
    kwh_recuperavel_estimado_ano: float


class ActiveOrder(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id_ordem: str
    status: Literal["ABERTA", "EM_CAMPO"]


class QueueItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prioridade: int
    id_uc: str
    score: int
    motivo_suspeita: str
    kwh_recuperavel_estimado_ano: float
    municipio: str
    bairro: str
    classe: str
    ordem_aberta: ActiveOrder | None


class QueueResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data_referencia: date
    resumo: QueueSummary
    pagina: int
    limite: int
    total: int
    itens: list[QueueItem]


UCId = Annotated[str, StringConstraints(pattern=r"^UC[0-9]{6}$")]


class CreateOrdersRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ids_uc: list[UCId] = Field(min_length=1)


class InspectionOrder(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id_ordem: str
    id_uc: str
    municipio: str
    bairro: str
    status: Literal["ABERTA", "EM_CAMPO", "CONCLUIDA", "CANCELADA"]
    resultado: Literal["IRREGULARIDADE_CONFIRMADA", "SEM_IRREGULARIDADE"] | None
    criada_em: AwareDatetime
    # Quem gerou e quem mudou por último; null nas ordens de antes da autoria
    criada_por_nome: str | None
    atualizada_por_nome: str | None


class CreateOrdersResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ordens: list[InspectionOrder]


class ListOrdersResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    itens: list[InspectionOrder]


class SendToFieldRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["EM_CAMPO"]


class CompleteOrderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["CONCLUIDA"]
    resultado: Literal["IRREGULARIDADE_CONFIRMADA", "SEM_IRREGULARIDADE"]


OrderTransitionRequest = SendToFieldRequest | CompleteOrderRequest
