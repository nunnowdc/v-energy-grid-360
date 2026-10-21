"""
Nó 10: Abstenção Honesta — resposta clara de "não sei / fora de escopo / bloqueado".
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from ai_agent.src.contratos.estado_agente import EstadoAgente

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
        "Não encontrei informações suficientes nas tabelas disponíveis para responder "
        "a esta pergunta com precisão. Prefiro ser honesto a apresentar dados incorretos."
    ),
    "max_tentativas": (
        "Após múltiplas tentativas, não consegui gerar uma consulta válida para esta pergunta. "
        "Por favor, tente reformular ou entre em contato com o time de dados."
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
    malicioso = state.get("eh_malicioso", False)
    erro = state.get("erro_validacao_ou_execucao")
    tentativas = state.get("tentativas_sql", 0)
    motivo_escopo = state.get("motivo_fora_escopo")

    # Prioridade de classificação
    if malicioso:
        tipo = "bloqueio_seguranca"
        texto = MENSAGENS_RECUSA["bloqueio_seguranca"]
    elif rota in ("fora_escopo", "bloqueio_seguranca"):
        tipo = rota
        texto = MENSAGENS_RECUSA[rota]
        if motivo_escopo:
            texto += f" (Motivo: {motivo_escopo})"
    elif erro and "SQL_INDISPONIVEL" in (erro or ""):
        tipo = "sem_dados"
        texto = MENSAGENS_RECUSA["sem_dados"]
    elif tentativas >= 2:
        tipo = "max_tentativas"
        texto = MENSAGENS_RECUSA["max_tentativas"]
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
