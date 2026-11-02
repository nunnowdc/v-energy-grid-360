"""Leitura das avaliações do golden set, gravadas por ai-agent/scripts/avaliar_golden_set.py."""

from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection


class AgentEvaluationsRepository:
    def __init__(self, connection: Connection) -> None:
        self.connection = connection

    def has_tables(self) -> bool:
        """As tabelas só existem depois da primeira execução do script."""
        return self.connection.execute(
            text(
                "SELECT to_regclass('public.tb_avaliacoes_agente') IS NOT NULL "
                "AND to_regclass('public.tb_avaliacoes_agente_casos') IS NOT NULL"
            )
        ).scalar_one()

    def get_runs(self, limite: int) -> list[dict[str, Any]]:
        """As execuções mais recentes, da mais antiga para a mais nova."""
        rows = self.connection.execute(
            text(
                "SELECT * FROM ("
                "SELECT id, executada_em, modelo, total_casos, casos_aprovados, "
                "taxa_execucao, taxa_component_match, taxa_abstencao, tokens_medio, "
                "duracao_ms FROM tb_avaliacoes_agente "
                "ORDER BY executada_em DESC LIMIT :limite"
                ") AS recentes ORDER BY executada_em"
            ),
            {"limite": limite},
        ).mappings()
        return [dict(row) for row in rows]

    def get_cases(self, avaliacao_id: Any) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            text(
                "SELECT caso_id, tipo, pergunta, selo, passou, motivo, sql_gerado, "
                "tokens, tempo_ms FROM tb_avaliacoes_agente_casos "
                "WHERE avaliacao_id = :avaliacao_id ORDER BY caso_id"
            ),
            {"avaliacao_id": avaliacao_id},
        ).mappings()
        return [dict(row) for row in rows]
