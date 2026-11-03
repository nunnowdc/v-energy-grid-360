"""
Nó 10: Abstenção Honesta — resposta clara de "não sei / fora de escopo / bloqueado".
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from ..contratos.estado_agente import EstadoAgente
from .no_valida_sql import MARCADOR_SQL_INDISPONIVEL

logger = logging.getLogger("venergy.no_recusa_honesta")

MENSAGENS_RECUSA = {
    "fora_escopo": (
        "Meu escopo é restrito aos dados operacionais e regulatórios da V-Energy "
        "na concessão da Região Metropolitana do Recife (14 municípios). "
        "Não consigo responder esta pergunta com os dados disponíveis."
    ),
    "bloqueio_seguranca": (
        "Esta solicitação foi bloqueada por segurança. "
        "O agente opera exclusivamente em modo de leitura e não executa operações de modificação de dados."
    ),
    "sem_dados": (
        "Não há dados disponíveis para responder a esta pergunta nas tabelas disponíveis. "
        "Prefiro ser honesto a apresentar dados incorretos."
    ),
    "max_tentativas": (
        "Após múltiplas tentativas, não consegui gerar uma consulta válida para esta pergunta. "
        "Por favor, tente reformular ou entre em contato com o time de dados."
    ),
    "llm_indisponivel": (
        "O serviço de IA está temporariamente indisponível. Tente novamente em instantes."
    ),
    "recusa": (
        "Não consigo responder a esta pergunta. Ela está fora do escopo dos dados da V-Energy "
        "ou não foi possível determinar uma interpretação segura e precisa."
    ),
}


def no_recusa_honesta(state: EstadoAgente) -> Dict[str, Any]:
    """
    Define o texto de recusa apropriado com base na rota e contexto do estado.
    """
    rota = state.get("rota", "recusa")
    malicioso = state.get("malicioso", False)
    erro = state.get("erro_validacao_ou_execucao")
    tentativas = state.get("tentativas_sql", 0)
    motivo_escopo = state.get("motivo_fora_escopo")
    motivo_recusa_estado = state.get("motivo_recusa")

    # Prioridade de classificação
    if malicioso:
        tipo = "bloqueio_seguranca"
        texto = MENSAGENS_RECUSA["bloqueio_seguranca"]
    elif motivo_recusa_estado == "llm_indisponivel":
        tipo = "llm_indisponivel"
        texto = MENSAGENS_RECUSA["llm_indisponivel"]
    elif rota in ("fora_escopo", "bloqueio_seguranca"):
        tipo = rota
        texto = MENSAGENS_RECUSA[rota]
        if motivo_escopo:
            texto += f" (Motivo: {motivo_escopo})"
    elif erro and MARCADOR_SQL_INDISPONIVEL in erro:
        tipo = "sem_dados"
        texto = MENSAGENS_RECUSA["sem_dados"]
    elif tentativas >= 2:
        tipo = "max_tentativas"
        texto = MENSAGENS_RECUSA["max_tentativas"]
    elif motivo_recusa_estado in MENSAGENS_RECUSA:
        tipo = motivo_recusa_estado
        texto = MENSAGENS_RECUSA[tipo]
    else:
        tipo = "recusa"
        texto = MENSAGENS_RECUSA["recusa"]

    logger.info("Nó 10 — Recusa honesta emitida. Tipo: %s", tipo)

    return {
        "texto_resposta": texto,
        "motivo_recusa": tipo,
        "selo_confianca": "recusa_honesta" if not malicioso else "erro_bloqueado",
        "passos_executados": [f"Nó 10 — Recusa emitida: {tipo}."],
    }
