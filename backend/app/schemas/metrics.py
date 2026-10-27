"""DTOs da comparação fixa de receita publicada pela Gold."""

from pydantic import BaseModel, ConfigDict


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
