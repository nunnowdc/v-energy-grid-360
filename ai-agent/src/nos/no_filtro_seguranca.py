"""
Nó 1: Filtro de Segurança — Detecção de Prompt Injection e Jailbreak.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict

from ..contratos.estado_agente import EstadoAgente

logger = logging.getLogger("venergy.no_filtro_seguranca")

# Padrões de ataque clássicos de prompt injection e jailbreak
_PADROES_ATAQUE = re.compile(
    r"""
    ignore\s+(all\s+)?previous\s+instructions? |
    disregard\s+.{0,30}instructions? |
    ignore\s+.{0,30}rules? |
    you\s+are\s+now\s+.{0,30}(DAN|EVIL|JAILBREAK) |
    \\n\\nHuman: |
    \\n\\nAssistant: |
    <\s*/?system\s*> |
    <\s*/?instructions\s*> |
    IGNORE\s+ALL |
    # SQL direto no prompt
    (DROP|ALTER|TRUNCATE)\s+(TABLE|DATABASE)\s+\w+ |
    (DELETE\s+FROM|INSERT\s+INTO|UPDATE)\s+\w+ |
    # Tentativa de sair do escopo via instrução
    act\s+as\s+(a\s+)?(different|other|new)\s+(AI|model|assistant) |
    pretend\s+(you\s+are|to\s+be) |
    esqueça\s+(todas\s+as\s+|as\s+)?(suas\s+)?instruções(\s+anteriores)? |
    ignore\s+(todas\s+as\s+|as\s+)?(suas\s+)?instruções(\s+anteriores)? |
    você\s+agora\s+é |
    finja\s+que\s+(você\s+é|é) |
    ignore\s+(todas\s+as\s+|as\s+)?(suas\s+)?regras
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Comprimento máximo aceito para proteger contra ataques de flooding
MAX_COMPRIMENTO = 1_200


def no_filtro_seguranca(state: EstadoAgente) -> Dict[str, Any]:
    """
    Analisa a pergunta bruta em busca de padrões de ataque.
    Se detectado, define a rota como bloqueio antes de qualquer chamada de LLM.
    """
    pergunta = state.get("pergunta_original", "")

    # 1. Proteção contra flooding de contexto
    if len(pergunta) > MAX_COMPRIMENTO:
        logger.warning("Nó 1 — Bloqueio: pergunta excede %d caracteres (%d).", MAX_COMPRIMENTO, len(pergunta))
        return {
            "rota": "bloqueio_seguranca",
            "motivo_fora_escopo": "Entrada excede o limite de caracteres permitido.",
            "malicioso": True,
            "passos_executados": [
                f"Nó 1 — Bloqueado: pergunta com {len(pergunta)} caracteres (máx. {MAX_COMPRIMENTO})."
            ],
        }

    # 2. Detecção de padrões de injeção / jailbreak
    if _PADROES_ATAQUE.search(pergunta):
        logger.warning("Nó 1 — Bloqueio: padrão de injeção detectado na pergunta.")
        return {
            "rota": "bloqueio_seguranca",
            "motivo_fora_escopo": "Padrão de manipulação de prompt detectado.",
            "malicioso": True,
            "passos_executados": [
                "Nó 1 — Bloqueado: padrão de prompt injection detectado."
            ],
        }

    logger.debug("Nó 1 — Pergunta aprovada no filtro de segurança.")
    return {
        "malicioso": False,
        "passos_executados": ["Nó 1 — Filtro de segurança: aprovado."],
    }


def rota_pos_filtro(state: EstadoAgente) -> str:
    """Roteamento condicional após o filtro de segurança."""
    if state.get("rota") == "bloqueio_seguranca":
        return "bloqueado"
    return "aprovado"
