"""Resposta HTTP da Continuidade da Rede."""

from pydantic import BaseModel, ConfigDict, FiniteFloat, NonNegativeInt, PositiveInt


class NetworkPeriod(BaseModel):
    model_config = ConfigDict(extra="forbid")

    inicio: str
    fim: str


class FeederContinuity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alimentador: str
    municipio_principal: str
    total_ucs: PositiveInt
    alimentador_pequeno: bool
    dec: FiniteFloat
    fec: FiniteFloat
    dec_sem_dia_critico: FiniteFloat
    dec_anterior: FiniteFloat


class MonthlyContinuity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mes_referencia: str
    dec: FiniteFloat
    fec: FiniteFloat


class FeederSeries(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alimentador: str
    atual: list[MonthlyContinuity]
    anterior: list[MonthlyContinuity]


class CauseOccurrences(BaseModel):
    model_config = ConfigDict(extra="forbid")

    causa: str
    ocorrencias: NonNegativeInt


class NetworkOccurrences(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total: NonNegativeInt
    total_anterior: NonNegativeInt
    por_causa: list[CauseOccurrences]


class NetworkContinuityResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    periodo: NetworkPeriod
    periodo_anterior: NetworkPeriod
    ranking: list[FeederContinuity]
    serie: FeederSeries | None
    ocorrencias: NetworkOccurrences
