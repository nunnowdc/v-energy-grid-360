"""Consultas de leitura da auditoria do agente de IA (tb_auditoria_agente)."""

from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

# O dia é o de Recife: uma pergunta às 22h de lá conta no mesmo dia, não no seguinte (UTC)
FUSO = "America/Recife"

# Janela [inicio, fim] em dias de Recife, convertida para instantes: usa a coluna direto
_JANELA = (
    "data_hora >= CAST(:inicio AS timestamp) AT TIME ZONE :fuso "
    "AND data_hora < (CAST(:fim AS timestamp) + interval '1 day') AT TIME ZONE :fuso"
)
_TOKENS = "COALESCE(tokens_prompt, 0) + COALESCE(tokens_resposta, 0)"
# Respondidas: com consulta aos dados (certificada ou gerada) ou com os documentos
_RESPONDIDA = "selo_confianca IN ('certificada', 'gerada_confiavel', 'documental_rag')"


class AgentUsageRepository:
    def __init__(self, connection: Connection) -> None:
        self.connection = connection

    def _params(self, inicio: date, fim: date) -> dict[str, Any]:
        return {"inicio": inicio, "fim": fim, "fuso": FUSO}

    def get_today(self) -> date:
        return self.connection.execute(
            text("SELECT CAST(now() AT TIME ZONE :fuso AS date)"), {"fuso": FUSO}
        ).scalar_one()

    def get_summary(self, inicio: date, fim: date) -> dict[str, Any]:
        row = (
            self.connection.execute(
                text(
                    "SELECT count(*) AS perguntas, "
                    "count(*) FILTER (WHERE selo_confianca IN "
                    "('certificada', 'gerada_confiavel')) AS respondidas_com_dados, "
                    "count(*) FILTER (WHERE selo_confianca = 'documental_rag') "
                    "AS respondidas_com_documentos, "
                    "count(*) FILTER (WHERE selo_confianca = 'recusa_honesta') AS recusas, "
                    "count(*) FILTER (WHERE selo_confianca = 'erro_bloqueado') AS erros, "
                    "avg(tempo_execucao_ms) AS tempo_medio_ms, "
                    "percentile_cont(0.95) WITHIN GROUP (ORDER BY tempo_execucao_ms) "
                    "AS tempo_p95_ms, "
                    f"avg({_TOKENS}) AS tokens_medio, "
                    f"COALESCE(sum({_TOKENS}), 0) AS tokens_total, "
                    "count(*) FILTER (WHERE feedback_usuario = 1) AS avaliacoes_uteis, "
                    "count(*) FILTER (WHERE feedback_usuario = -1) AS avaliacoes_inuteis "
                    f"FROM tb_auditoria_agente WHERE {_JANELA}"
                ),
                self._params(inicio, fim),
            )
            .mappings()
            .one()
        )
        return dict(row)

    def get_daily(self, inicio: date, fim: date) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            text(
                "SELECT CAST(data_hora AT TIME ZONE :fuso AS date) AS dia, "
                "count(*) AS perguntas, "
                f"count(*) FILTER (WHERE {_RESPONDIDA}) AS respondidas, "
                "count(*) FILTER (WHERE selo_confianca = 'recusa_honesta') AS recusas, "
                "count(*) FILTER (WHERE selo_confianca = 'erro_bloqueado') AS erros, "
                "avg(tempo_execucao_ms) AS tempo_medio_ms, "
                f"avg({_TOKENS}) AS tokens_medio "
                f"FROM tb_auditoria_agente WHERE {_JANELA} "
                "GROUP BY 1 ORDER BY 1"
            ),
            self._params(inicio, fim),
        ).mappings()
        return [dict(row) for row in rows]

    def get_latest(self, inicio: date, fim: date, limite: int) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            text(
                "SELECT id, data_hora, pergunta_original AS pergunta, perfil, "
                "selo_confianca AS selo, tempo_execucao_ms AS tempo_ms, "
                f"{_TOKENS} AS tokens, feedback_usuario AS avaliacao "
                f"FROM tb_auditoria_agente WHERE {_JANELA} "
                "ORDER BY data_hora DESC LIMIT :limite"
            ),
            {**self._params(inicio, fim), "limite": limite},
        ).mappings()
        return [dict(row) for row in rows]
