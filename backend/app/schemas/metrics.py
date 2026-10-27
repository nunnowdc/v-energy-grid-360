"""DTOs do endpoint de indicadores gerais."""

from pydantic import BaseModel, ConfigDict


class MetricsSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    inicio: str
    fim: str
    receita_faturada: float | None
    consumo_kwh: float | None
    preco_medio_kwh: float | None
    ucs_faturadas: int | None
    faturas: int | None
    faturas_atrasadas: int | None


class MonthlyMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mes_referencia: str
    receita_faturada: float | None
    consumo_kwh: float | None


class MetricsSeries(BaseModel):
    model_config = ConfigDict(extra="forbid")

    atual: list[MonthlyMetrics]
    anterior: list[MonthlyMetrics]


class ClassRevenue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    classe: str
    receita_faturada: float | None
    receita_faturada_anterior: float | None


class GeneralMetricsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    atual: MetricsSummary
    anterior: MetricsSummary
    mensal: MetricsSeries
    por_classe: list[ClassRevenue]
