"""
Nó 5: Recuperação de Contexto (RAG) — busca semântica no PostgreSQL + pgvector.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from ..contratos.estado_agente import EstadoAgente
from ..rag.buscador_vetorial import BuscadorVetorial

logger = logging.getLogger("venergy.no_recupera_contexto")

# Mapeamento de rota para categorias de busca prioritárias
_CATEGORIAS_POR_ROTA = {
    "sql": [
        "glossario", "esquema", "templates",
        "dicionario_gold", "decisoes_negocio", "perfis_dados"
    ],
    "rag": [
        "glossario", "prodist", "regras_setoriais",
        "decisoes_negocio", "lgpd", "outros_relatorios"
    ],
    "ambos": [
        "glossario", "esquema", "prodist", "templates",
        "dicionario_gold", "decisoes_negocio", "lgpd",
        "perfis_dados", "outros_relatorios"
    ],
}

_LIMIAR_POR_ROTA = {
    "sql": 0.70,
    "rag": 0.45,
    "ambos": 0.55,
}


def no_recupera_contexto(
    state: EstadoAgente,
    buscador: Optional[BuscadorVetorial] = None,
) -> Dict[str, Any]:
    """
    Recupera chunks de conhecimento relevantes para a pergunta.
    Filtra as categorias e ajusta o limiar de similaridade com base na rota decidida pelo Nó 4.
    """
    pergunta = state.get("pergunta_autonoma") or state.get("pergunta_original", "")
    rota = state.get("rota", "sql")

    # Se RAG_LIMIAR_SIMILARIDADE estiver definido no ambiente, ele prevalece (passar limiar=None)
    env_limiar = os.getenv("RAG_LIMIAR_SIMILARIDADE")
    if env_limiar is not None and env_limiar.strip() != "":
        limiar_calculado = None
    else:
        limiar_calculado = _LIMIAR_POR_ROTA.get(rota, 0.70)

    _buscador = buscador or BuscadorVetorial(
        db_url=os.getenv("DATABASE_URL"),
        limiar=limiar_calculado,
    )

    categorias = _CATEGORIAS_POR_ROTA.get(rota, ["glossario", "esquema"])

    resultado = _buscador.buscar(query=pergunta, categorias=categorias)

    # Converte chunks para dicionários simples para o estado TypedDict
    contexto_rag: List[Dict[str, Any]] = [
        {
            "id": chunk.id,
            "categoria": chunk.categoria,
            "titulo": chunk.titulo,
            "conteudo": chunk.conteudo,
            "fonte": chunk.fonte,
        }
        for chunk in resultado.chunks
    ]

    if resultado.houve_corte_limiar and not contexto_rag:
        logger.info(
            "Nó 5 — RAG: nenhum chunk acima do limiar para rota '%s'. Prosseguindo sem contexto.",
            rota,
        )
        return {
            "contexto_rag": [],
            "passos_executados": [
                f"Nó 5 — RAG: 0 chunks recuperados (abaixo do limiar). Rota: {rota}."
            ],
        }

    fontes_unicas = list({c["fonte"] for c in contexto_rag if c.get("fonte")})
    logger.info(
        "Nó 5 — RAG: %d chunk(s) recuperados para rota '%s'. Fontes: %s",
        len(contexto_rag), rota, fontes_unicas,
    )

    return {
        "contexto_rag": contexto_rag,
        "passos_executados": [
            f"Nó 5 — RAG: {len(contexto_rag)} chunk(s) recuperados. "
            f"Categorias: {categorias}. Fontes: {fontes_unicas}."
        ],
    }
