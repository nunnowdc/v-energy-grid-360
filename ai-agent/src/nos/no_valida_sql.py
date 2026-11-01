"""
Nó 8: Validação de SQL via interface desacoplada.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from ..contratos.estado_agente import EstadoAgente
from ..interfaces.validador_sql_interface import ValidadorSQLInterface

logger = logging.getLogger("venergy.no_valida_sql")

MAX_TENTATIVAS = 2
MARCADOR_SQL_INDISPONIVEL = "SQL_INDISPONIVEL"


def no_valida_sql(
    state: EstadoAgente,
    validador: ValidadorSQLInterface,
) -> Dict[str, Any]:
    """
    Valida a query SQL usando a interface do validador (Stub ou SQLGlot definitivo).
    Determina se o laço de retry deve continuar ou se deve haver recusa honesta.
    """
    if state.get("motivo_recusa") == "llm_indisponivel":
        logger.info("Nó 8 — Ignorado: LLM indisponível no Nó 7.")
        return {
            "motivo_recusa": "llm_indisponivel",
            "passos_executados": [
                "Nó 8 — Validação ignorada devido a LLM indisponível."
            ],
        }

    sql = state.get("sql_gerado", "")
    tentativas = state.get("tentativas_sql", 0)

    # Caso especial: o LLM reconheceu que não tem dados para responder
    if sql.strip().upper().startswith(MARCADOR_SQL_INDISPONIVEL):
        logger.info("Nó 8 — SQL_INDISPONIVEL declarado pelo LLM.")
        return {
            "erro_validacao_ou_execucao": (
                f"{MARCADOR_SQL_INDISPONIVEL}: O agente não encontrou dados suficientes "
                "nas tabelas disponíveis para responder a esta pergunta."
            ),
            "malicioso": False,
            "passos_executados": [
                "Nó 8 — Validação: LLM declarou SQL_INDISPONIVEL (sem dados mapeáveis)."
            ],
        }

    resultado = validador.validar(sql)

    if resultado.aprovado:
        # Se o validador oficial devolve sql_normalizado, retornamos no dicionário de resposta
        # para que o LangGraph propague ao próximo nó corretamente.
        sql_norm = getattr(resultado, "sql_normalizado", None)
        resposta = {
            "erro_validacao_ou_execucao": None,
            "malicioso": False,
            "passos_executados": [
                f"Nó 8 — Validação aprovada. Tabelas identificadas: {resultado.tabelas_detectadas}"
            ],
        }
        if sql_norm:
            resposta["sql_gerado"] = sql_norm
        return resposta

    # SQL reprovado
    logger.warning("Nó 8 — SQL reprovado: %s (malicioso=%s)", resultado.motivo_rejeicao, resultado.malicioso)
    return {
        "erro_validacao_ou_execucao": resultado.motivo_rejeicao,
        "malicioso": resultado.malicioso,
        "passos_executados": [
            f"Nó 8 — Validação reprovada (tentativa {tentativas}): {resultado.motivo_rejeicao}"
        ],
    }


def rota_pos_validacao(state: EstadoAgente) -> str:
    """
    Função de roteamento condicional após o Nó 8.
    Decide entre: retry, recusa honesta ou execução.
    """
    if state.get("motivo_recusa") == "llm_indisponivel":
        return "recusa"

    erro = state.get("erro_validacao_ou_execucao")
    malicioso = state.get("malicioso", False)
    tentativas = state.get("tentativas_sql", 0)

    if not erro:
        return "executa"

    if MARCADOR_SQL_INDISPONIVEL in erro:
        return "recusa"

    if malicioso or tentativas >= MAX_TENTATIVAS:
        return "recusa"

    return "retry_sql"
