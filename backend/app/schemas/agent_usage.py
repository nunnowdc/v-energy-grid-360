"""DTOs do uso do agente de IA, lido da auditoria de cada pergunta."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AgentUsageSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    perguntas: int
    # Selos certificada e gerada_confiavel: responderam com uma consulta aos dados
    respondidas_com_dados: int
    # Selo documental_rag: responderam com o glossário e as regras de negócio
    respondidas_com_documentos: int
    # Selo recusa_honesta: preferiram não responder a arriscar um número errado
    recusas: int
    # Selo erro_bloqueado: o agente falhou no meio do caminho
    erros: int
    # Nulos quando não houve pergunta no período
    tempo_medio_ms: float | None
    tempo_p95_ms: float | None
    tokens_medio: float | None
    tokens_total: int
    avaliacoes_uteis: int
    avaliacoes_inuteis: int


class AgentUsageDay(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Dia no horário de Recife
    dia: date
    perguntas: int
    # Com dados ou com documentos
    respondidas: int
    recusas: int
    erros: int
    tempo_medio_ms: float | None
    tokens_medio: float | None


class AgentQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # O mesmo id de GET /api/ai/audit/{audit_id}, com o passo a passo da resposta
    id: UUID
    data_hora: datetime
    pergunta: str
    # Nulo nas perguntas de antes do login
    perfil: str | None
    selo: str
    tempo_ms: float
    tokens: int
    # 1 (útil), -1 (inútil) ou nulo (sem avaliação)
    avaliacao: int | None


class AgentUsageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    inicio: date
    fim: date
    resumo: AgentUsageSummary
    # Um item por dia da janela, do mais antigo ao mais recente
    por_dia: list[AgentUsageDay]
    # Mais recentes primeiro
    ultimas: list[AgentQuestion]
