"""DTOs das opções compartilhadas de filtros."""

from pydantic import BaseModel, ConfigDict


class MunicipalityOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: str
    bairros: list[str]


class FeederOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    codigo: str
    municipios: list[str]


class FilterOptionsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    competencias: list[str]
    municipios: list[MunicipalityOption]
    classes: list[str]
    alimentadores: list[FeederOption]
    causas: list[str]
