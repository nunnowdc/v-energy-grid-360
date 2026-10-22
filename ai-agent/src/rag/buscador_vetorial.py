"""
Buscador Vetorial — Busca semântica na base de conhecimento usando PostgreSQL + pgvector.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from ..contratos.modelos_rag import ChunkConhecimento, ResultadoBuscaRAG

logger = logging.getLogger("venergy.buscador_vetorial")

TOP_K = 4
LIMIAR_SIMILARIDADE = 0.70

SQL_BUSCA_VETORIAL = """
SELECT
    id::text,
    categoria,
    titulo,
    conteudo,
    fonte,
    metadados,
    1 - (embedding <=> %(embedding)s::vector) AS similaridade
FROM tb_conhecimento_vetorial
WHERE 1 = 1
  {filtro_categoria}
  AND 1 - (embedding <=> %(embedding)s::vector) >= %(limiar)s
ORDER BY embedding <=> %(embedding)s::vector
LIMIT %(top_k)s;
"""


class BuscadorVetorial:
    """
    Realiza buscas semânticas na tabela tb_conhecimento_vetorial usando pgvector.
    O modelo de embedding é carregado uma vez e reutilizado (lazy load).
    """

    def __init__(
        self,
        db_url: Optional[str] = None,
        modelo_embedding: str = "paraphrase-multilingual-MiniLM-L12-v2",
        top_k: int = TOP_K,
        limiar: float = LIMIAR_SIMILARIDADE,
    ):
        self.db_url = db_url or os.getenv("DATABASE_URL")
        self.modelo_embedding = modelo_embedding
        self.top_k = top_k
        self.limiar = limiar
        self._modelo = None  # lazy load

    def _carregar_modelo(self):
        """Carrega o modelo de embedding apenas na primeira chamada."""
        if self._modelo is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info("Carregando modelo de embedding: %s", self.modelo_embedding)
                self._modelo = SentenceTransformer(self.modelo_embedding)
            except ImportError:
                raise RuntimeError(
                    "sentence-transformers não instalado. "
                    "Execute: pip install sentence-transformers"
                )
        return self._modelo

    def _gerar_embedding(self, texto: str) -> List[float]:
        modelo = self._carregar_modelo()
        vetor = modelo.encode(texto, normalize_embeddings=True)
        return vetor.tolist()

    def buscar(
        self,
        query: str,
        categorias: Optional[List[str]] = None,
    ) -> ResultadoBuscaRAG:
        """
        Busca os chunks mais relevantes para a query com filtro opcional por categoria.
        Retorna lista vazia se nenhum chunk atingir o limiar de similaridade.
        """
        if not self.db_url:
            logger.warning("DATABASE_URL não configurada. Retornando RAG vazio.")
            return ResultadoBuscaRAG(chunks=[], top_score=0.0, houve_corte_limiar=False)

        try:
            embedding = self._gerar_embedding(query)
        except Exception as e:
            logger.error("Erro ao gerar embedding: %s", e)
            return ResultadoBuscaRAG(chunks=[], top_score=0.0, houve_corte_limiar=False)

        filtro_categoria = ""
        if categorias:
            placeholders = ", ".join(f"'{c}'" for c in categorias)
            filtro_categoria = f"AND categoria IN ({placeholders})"

        sql = SQL_BUSCA_VETORIAL.format(filtro_categoria=filtro_categoria)

        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor, Json
            import json

            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(sql, {
                        "embedding": f"[{','.join(str(v) for v in embedding)}]",
                        "limiar": self.limiar,
                        "top_k": self.top_k,
                    })
                    rows = cur.fetchall()

        except Exception as e:
            logger.error("Erro na busca vetorial pgvector: %s", e)
            return ResultadoBuscaRAG(chunks=[], top_score=0.0, houve_corte_limiar=False)

        if not rows:
            logger.info("RAG: nenhum chunk acima do limiar %.2f para query: %s", self.limiar, query[:60])
            return ResultadoBuscaRAG(chunks=[], top_score=0.0, houve_corte_limiar=True)

        chunks = [
            ChunkConhecimento(
                id=str(row["id"]),
                categoria=row["categoria"],
                titulo=row["titulo"],
                conteudo=row["conteudo"],
                fonte=row["fonte"] or "",
                metadados=row.get("metadados") or {},
            )
            for row in rows
        ]

        top_score = float(rows[0]["similaridade"]) if rows else 0.0
        logger.info("RAG: %d chunk(s) recuperados. Top score: %.3f", len(chunks), top_score)

        return ResultadoBuscaRAG(
            chunks=chunks,
            top_score=top_score,
            houve_corte_limiar=False,
        )
