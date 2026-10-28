"""
Buscador Vetorial — Busca semântica na base de conhecimento usando PostgreSQL + pgvector.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from pydantic import ValidationError

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
ORDER BY embedding <=> %(embedding)s::vector
LIMIT %(top_k)s;
"""


def _obter_limiar_padrao() -> float:
    env_limiar = os.getenv("RAG_LIMIAR_SIMILARIDADE")
    if env_limiar is not None and env_limiar.strip() != "":
        try:
            return float(env_limiar)
        except ValueError:
            logger.warning(
                "Valor inválido para RAG_LIMIAR_SIMILARIDADE ('%s'). Usando fallback %.2f.",
                env_limiar,
                LIMIAR_SIMILARIDADE,
            )
            return LIMIAR_SIMILARIDADE
    return LIMIAR_SIMILARIDADE


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
        limiar: Optional[float] = None,
    ):
        self.db_url = db_url or os.getenv("DATABASE_URL")
        self.modelo_embedding = modelo_embedding
        self.top_k = top_k
        self.limiar = _obter_limiar_padrao() if limiar is None else limiar
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

        params: Dict[str, Any] = {
            "embedding": f"[{','.join(str(v) for v in embedding)}]",
            "top_k": self.top_k,
        }

        filtro_categoria = ""
        if categorias:
            filtro_categoria = "AND categoria = ANY(%(categorias)s)"
            params["categorias"] = list(categorias)

        sql = SQL_BUSCA_VETORIAL.format(filtro_categoria=filtro_categoria)

        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor, Json
            import json

            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Desativa o scan de índice para forçar busca exata por knn (ideal para base pequena).
                    # Deve ser removido se a tabela crescer significativamente ou ao adotar índices HNSW / IVFFLAT calibrados.
                    cur.execute("SET enable_indexscan = off;")
                    cur.execute(sql, params)
                    rows = cur.fetchall()

        except Exception as e:
            logger.error("Erro na busca vetorial pgvector: %s", e)
            return ResultadoBuscaRAG(chunks=[], top_score=0.0, houve_corte_limiar=False)

        if not rows:
            return ResultadoBuscaRAG(chunks=[], top_score=0.0, houve_corte_limiar=False)

        top_score = float(rows[0]["similaridade"]) if rows else 0.0
        validos = [r for r in rows if float(r["similaridade"]) >= self.limiar]
        if not validos:
            logger.info(
                "RAG: melhor chunk '%s' (%s) com score %.3f, abaixo do limiar %.2f",
                rows[0]["titulo"], rows[0]["categoria"], top_score, self.limiar,
            )
            return ResultadoBuscaRAG(chunks=[], top_score=top_score, houve_corte_limiar=True)
        rows = validos

        chunks = []
        for row in rows:
            try:
                chunks.append(ChunkConhecimento(
                    id=str(row["id"]),
                    categoria=row["categoria"],
                    titulo=row["titulo"],
                    conteudo=row["conteudo"],
                    fonte=row["fonte"] or "",
                    metadados=row.get("metadados") or {},
                ))
            except ValidationError as e:
                logger.warning("RAG: chunk %s ignorado: %s", row["id"], e.errors()[0]["msg"])

        logger.info("RAG: %d chunk(s) recuperados. Top score: %.3f", len(chunks), top_score)

        return ResultadoBuscaRAG(
            chunks=chunks,
            top_score=top_score,
            houve_corte_limiar=False,
        )
