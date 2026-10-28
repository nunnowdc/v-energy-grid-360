"""
Modelos de dados para o subsistema de RAG (Busca Vetorial e Conhecimento Regulatório).
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

CategoriaRAG = Literal[
    "glossario",
    "esquema",
    "prodist",
    "templates",
    "perfis_dados",
    "dicionario_gold",
    "decisoes_negocio",
    "regras_setoriais",
    "lgpd",
    "outros_relatorios",
]


class ChunkConhecimento(BaseModel):
    """Um fragmento de conhecimento indexado na base vetorial."""
    id: str
    categoria: CategoriaRAG
    titulo: str
    conteudo: str
    fonte: str
    metadados: Dict[str, Any] = Field(default_factory=dict)
    embedding: Optional[List[float]] = None


class ResultadoBuscaRAG(BaseModel):
    """Resultado retornado pelo motor de busca vetorial."""
    chunks: List[ChunkConhecimento] = Field(default_factory=list)
    top_score: float = 0.0
    houve_corte_limiar: bool = False
