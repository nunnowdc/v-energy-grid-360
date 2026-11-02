"""DTOs das avaliações do agente contra o golden set."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AgentEvaluationRun(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    executada_em: datetime
    # Modelo que respondeu (o primário do OpenRouter ou o de reserva do 9router)
    modelo: str | None
    total_casos: int
    casos_aprovados: int
    # Percentuais de 0 a 100; nulos quando a execução não tem caso daquele tipo
    taxa_execucao: float | None
    taxa_component_match: float | None
    taxa_abstencao: float | None
    tokens_medio: float | None
    duracao_ms: float


class AgentEvaluationCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Id do golden set, ex.: "TC-001"
    caso_id: str
    # sql, rag ou recusa: o que o caso espera do agente
    tipo: str
    pergunta: str
    selo: str
    passou: bool
    # Por que passou ou falhou, em uma frase
    motivo: str
    sql_gerado: str | None
    tokens: int
    tempo_ms: float


class AgentEvaluationsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # As 30 mais recentes, da mais antiga para a mais nova; vazia antes da primeira
    execucoes: list[AgentEvaluationRun]
    # Os casos da última execução, na ordem do golden set
    casos: list[AgentEvaluationCase]
