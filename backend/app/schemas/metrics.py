"""DTOs dos indicadores gerais e da comparação de receita."""

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


class RevenuePeriod(BaseModel):
    model_config = ConfigDict(extra="forbid")

    inicio: str
    fim: str


class RevenueMeasures(BaseModel):
    model_config = ConfigDict(extra="forbid")

    receita_p0: float | None
    receita_p1: float | None
    kwh_p0: float | None
    kwh_p1: float | None
    ucs_p0: int | None
    ucs_p1: int | None
    preco_p0: float | None
    preco_p1: float | None
    efeito_volume: float | None
    efeito_preco: float | None


class RevenueGDGroup(RevenueMeasures):
    possui_gd: bool


class RevenueDetailRow(RevenueMeasures):
    nome: str


class RevenueDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nivel: str
    linhas: list[RevenueDetailRow]


class RevenueVarianceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    periodo_p0: RevenuePeriod
    periodo_p1: RevenuePeriod
    total: RevenueMeasures
    por_gd: list[RevenueGDGroup]
    detalhamento: RevenueDetail
