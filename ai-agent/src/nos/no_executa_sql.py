"""
Nó 9: Execução de SQL no PostgreSQL com limite de linhas, timeout e safeguard de leitura.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from ai_agent.src.contratos.estado_agente import EstadoAgente
from ai_agent.src.services.sql_executor import SQLExecutor

logger = logging.getLogger("venergy.no_executa_sql")

MAX_TENTATIVAS = 2


def no_executa_sql(
    state: EstadoAgente,
    executor: SQLExecutor,
) -> Dict[str, Any]:
    """
    Executa a query SQL aprovada no banco e armazena os dados no estado.
    """
    sql = state.get("sql_gerado", "")
    tentativas = state.get("tentativas_sql", 0)
    hit_cache = state.get("hit_cache", False)

    resultado = executor.executar(sql)

    if resultado.sucesso:
        logger.info(
            "Nó 9 — SQL executado com sucesso. Linhas retornadas: %d | %.1fms",
            resultado.total_linhas,
            resultado.tempo_execucao_ms,
        )
        return {
            "dados_sql": resultado.linhas,
            "total_linhas_retornadas": resultado.total_linhas,
            "tempo_execucao_sql_ms": resultado.tempo_execucao_ms,
            "erro_validacao_ou_execucao": None,
            "passos_executados": [
                f"Nó 9 — Execução SQL OK. {resultado.total_linhas} linha(s) em {resultado.tempo_execucao_ms:.0f}ms."
            ],
        }

    # Falha na execução
    logger.warning("Nó 9 — Erro na execução SQL: %s", resultado.erro)
    return {
        "dados_sql": None,
        "total_linhas_retornadas": 0,
        "tempo_execucao_sql_ms": resultado.tempo_execucao_ms,
        "erro_validacao_ou_execucao": resultado.erro,
        "passos_executados": [
            f"Nó 9 — Erro na execução (tentativa {tentativas}): {resultado.erro}"
        ],
    }


def rota_pos_execucao(state: EstadoAgente) -> str:
    """
    Roteamento condicional após Nó 9.
    """
    erro = state.get("erro_validacao_ou_execucao")
    tentativas = state.get("tentativas_sql", 0)

    if not erro:
        return "sintetiza"

    if tentativas >= MAX_TENTATIVAS:
        return "recusa"

    return "retry_sql"
