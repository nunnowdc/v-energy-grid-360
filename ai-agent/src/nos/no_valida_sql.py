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


def no_valida_sql(
    state: EstadoAgente,
    validador: ValidadorSQLInterface,
) -> Dict[str, Any]:
    """
    Valida a query SQL usando a interface do validador (Stub ou SQLGlot definitivo).
    Determina se o laço de retry deve continuar ou se deve haver recusa honesta.
    """
    sql = state.get("sql_gerado", "")
    tentativas = state.get("tentativas_sql", 0)

    # Caso especial: o LLM reconheceu que não tem dados para responder
    if sql.strip().upper().startswith("SQL_INDISPONIVEL"):
        logger.info("Nó 8 — SQL_INDISPONIVEL declarado pelo LLM.")
        return {
            "erro_validacao_ou_execucao": "O agente não encontrou dados suficientes nas tabelas disponíveis para responder a esta pergunta.",
            "eh_malicioso": False,
            "passos_executados": [
                "Nó 8 — Validação: LLM declarou SQL_INDISPONIVEL (sem dados mapeáveis)."
            ],
        }

    resultado = validador.validar(sql)

    if resultado.aprovado:
        logger.info("Nó 8 — SQL aprovado pela validação.")
        return {
            "erro_validacao_ou_execucao": None,
            "eh_malicioso": False,
            "passos_executados": [
                f"Nó 8 — Validação aprovada. Tabelas identificadas: {resultado.tabelas_detectadas}"
            ],
        }

    # SQL reprovado
    logger.warning("Nó 8 — SQL reprovado: %s (malicioso=%s)", resultado.motivo_rejeicao, resultado.eh_malicioso)
    return {
        "erro_validacao_ou_execucao": resultado.motivo_rejeicao,
        "eh_malicioso": resultado.eh_malicioso,
        "passos_executados": [
            f"Nó 8 — Validação reprovada (tentativa {tentativas}): {resultado.motivo_rejeicao}"
        ],
    }


def rota_pos_validacao(state: EstadoAgente) -> str:
    """
    Função de roteamento condicional após o Nó 8.
    Decide entre: retry, recusa honesta ou execução.
    """
    erro = state.get("erro_validacao_ou_execucao")
    malicioso = state.get("eh_malicioso", False)
    tentativas = state.get("tentativas_sql", 0)

    if not erro:
        return "executa"

    if malicioso or tentativas >= MAX_TENTATIVAS:
        return "recusa"

    return "retry_sql"
