"""Support for the opt-in RAG evaluation against a real OpenRouter model."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Sequence
from urllib.parse import unquote, urlparse

from ai_agent.tests.real_llm_eval_support import MAX_OPENROUTER_CALLS

RAG_CASES_TO_RUN = frozenset({"TC-007", "TC-008"})
RAG_CASES_PENDING = frozenset({"TC-009"})
RAG_PENDING_REASON = (
    "TC-009 continua pendente: o corpus atual não contém fonte sobre os critérios "
    "de compensação financeira por violação de continuidade."
)
RAG_DATABASE_TABLE = "tb_conhecimento_vetorial"
RAG_EMBEDDING_DIMENSION = 384


class ErroAvaliacaoRAG(RuntimeError):
    """Configuration or readiness failure for the live RAG evaluation."""


@dataclass(frozen=True)
class EstadoBancoRAG:
    documentos: int
    documentos_com_embedding: int
    dimensao_embedding: int | None


def validacao_rag_real_habilitada() -> bool:
    return os.getenv("AI_AGENT_RUN_REAL_RAG", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def validar_modelo_configurado(modelo: str | None) -> str:
    if not modelo or not modelo.strip():
        raise ErroAvaliacaoRAG(
            "Defina MODELO_LLM_PRIMARIO com o identificador do modelo OpenRouter."
        )
    return modelo.strip()


def separar_casos_rag(
    casos: Sequence[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    por_id = {caso["id"]: caso for caso in casos}
    ausentes = (RAG_CASES_TO_RUN | RAG_CASES_PENDING) - por_id.keys()
    if ausentes:
        raise ErroAvaliacaoRAG(
            "Golden Dataset sem casos RAG esperados: "
            + ", ".join(sorted(ausentes))
        )

    for caso_id in RAG_CASES_TO_RUN | RAG_CASES_PENDING:
        if por_id[caso_id].get("rota_esperada") != "rag":
            raise ErroAvaliacaoRAG(
                f"O caso {caso_id} deveria estar configurado com rota RAG."
            )

    para_executar = [
        por_id[caso_id] for caso_id in sorted(RAG_CASES_TO_RUN)
    ]
    pendentes = [
        por_id[caso_id] for caso_id in sorted(RAG_CASES_PENDING)
    ]
    return para_executar, pendentes


def prevalidar_banco_rag(db_url: str) -> EstadoBancoRAG:
    if not db_url.strip().lower().startswith(("postgres://", "postgresql://")):
        raise ErroAvaliacaoRAG(
            "AI_AGENT_RAG_DATABASE_URL deve apontar para PostgreSQL."
        )

    try:
        import psycopg2
    except ImportError as exc:
        raise ErroAvaliacaoRAG(
            "psycopg2 não está instalado no ambiente Python ativo."
        ) from exc

    try:
        with psycopg2.connect(db_url, connect_timeout=5) as conn:
            conn.set_session(readonly=True)
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT EXISTS ("
                    "SELECT 1 FROM pg_extension WHERE extname = 'vector'"
                    ")"
                )
                if not cursor.fetchone()[0]:
                    raise ErroAvaliacaoRAG(
                        "A extensão pgvector não está ativada no banco RAG."
                    )

                cursor.execute(
                    "SELECT COUNT(*), COUNT(embedding), "
                    "MAX(vector_dims(embedding)) "
                    f"FROM {RAG_DATABASE_TABLE}"
                )
                documentos, com_embedding, dimensao = cursor.fetchone()
    except ErroAvaliacaoRAG:
        raise
    except Exception as exc:
        codigo = getattr(exc, "pgcode", None)
        detalhe = f" (SQLSTATE {codigo})" if codigo else ""
        raise ErroAvaliacaoRAG(
            "Não foi possível validar a tabela vetorial no banco RAG. "
            "Confira a URL, a tabela, o schema de busca e as permissões "
            f"somente leitura{detalhe}."
        ) from exc

    if documentos == 0:
        raise ErroAvaliacaoRAG(
            f"A tabela {RAG_DATABASE_TABLE} está vazia; indexe o conteúdo RAG."
        )
    if com_embedding != documentos:
        raise ErroAvaliacaoRAG(
            f"Há documentos sem embedding em {RAG_DATABASE_TABLE}."
        )
    if dimensao != RAG_EMBEDDING_DIMENSION:
        raise ErroAvaliacaoRAG(
            "Dimensão dos embeddings incompatível: esperada "
            f"{RAG_EMBEDDING_DIMENSION}, encontrada {dimensao}."
        )

    try:
        import sentence_transformers  # noqa: F401
    except ImportError as exc:
        raise ErroAvaliacaoRAG(
            "sentence-transformers não está instalado no ambiente Python ativo. "
            "Instale a dependência antes da avaliação."
        ) from exc

    return EstadoBancoRAG(
        documentos=documentos,
        documentos_com_embedding=com_embedding,
        dimensao_embedding=dimensao,
    )


def validar_bases_separadas(rag_url: str, gold_url: str | None) -> None:
    if not gold_url:
        return
    rag = urlparse(rag_url)
    gold = urlparse(gold_url)
    destino_rag = (
        (rag.hostname or "").lower(),
        rag.port or 5432,
        unquote(rag.path.lstrip("/")),
    )
    destino_gold = (
        (gold.hostname or "").lower(),
        gold.port or 5432,
        unquote(gold.path.lstrip("/")),
    )
    if destino_rag == destino_gold:
        raise ErroAvaliacaoRAG(
            "AI_AGENT_RAG_DATABASE_URL aponta para o mesmo banco configurado "
            "em AI_AGENT_GOLD_DATABASE_URL. Use o banco RAG separado."
        )


def prevalidar_recuperacao(
    casos: Sequence[dict[str, Any]],
    db_url: str,
) -> dict[str, int]:
    from ai_agent.src.nos.no_recupera_contexto import _CATEGORIAS_POR_ROTA
    from ai_agent.src.rag.buscador_vetorial import BuscadorVetorial

    buscador = BuscadorVetorial(db_url=db_url)
    quantidades: dict[str, int] = {}
    for caso in casos:
        resultado = buscador.buscar(
            query=caso["pergunta"],
            categorias=_CATEGORIAS_POR_ROTA["rag"],
        )
        total = len(resultado.chunks)
        if total == 0:
            raise ErroAvaliacaoRAG(
                f"Preflight sem contexto para {caso['id']}. Confira se o corpus "
                "contém o assunto, se a indexação terminou e se o limiar de "
                "similaridade permite recuperar os documentos."
            )
        quantidades[caso["id"]] = total
    return quantidades


def medir_resultado_rag(
    caso: dict[str, Any],
    resultado: Any,
    chamadas_openrouter: int,
) -> dict[str, Any]:
    contagens = [
        int(match.group(1))
        for passo in resultado.passos_executados
        if (
            match := re.search(
                r"Nó 5 — RAG:\s*(\d+)\s+chunk(?:\(s\)|s)?\s+recuperad",
                passo,
            )
        )
    ]
    chunks_recuperados = max(contagens, default=0)
    fontes_recuperadas = list(resultado.fontes_citadas or [])
    texto = (resultado.resposta_texto or "").casefold()
    termos = caso.get("termos_obrigatorios_resposta", [])
    fontes_no_texto = any(fonte.casefold() in texto for fonte in fontes_recuperadas)

    return {
        "id": caso["id"],
        "selo": resultado.selo_confianca,
        "chunks_recuperados": chunks_recuperados,
        "fontes_recuperadas": len(fontes_recuperadas),
        "fonte_no_texto": fontes_no_texto,
        "chamadas_openrouter": chamadas_openrouter,
        "termos_encontrados": sum(termo.casefold() in texto for termo in termos),
        "termos_total": len(termos),
        "avaliacao_tecnica_ok": (
            resultado.selo_confianca == "documental_rag"
            and chunks_recuperados > 0
            and bool(fontes_recuperadas)
            and chamadas_openrouter > 0
        ),
    }


def mensagem_falha_openrouter(cliente: Any) -> str:
    """Return a provider failure without exposing exception or request contents."""
    return cliente.erro_fatal or "Falha na chamada OpenRouter durante a avaliação RAG."


__all__ = [
    "MAX_OPENROUTER_CALLS",
    "RAG_CASES_PENDING",
    "RAG_CASES_TO_RUN",
    "RAG_PENDING_REASON",
    "ErroAvaliacaoRAG",
    "EstadoBancoRAG",
    "medir_resultado_rag",
    "mensagem_falha_openrouter",
    "prevalidar_banco_rag",
    "prevalidar_recuperacao",
    "separar_casos_rag",
    "validar_bases_separadas",
    "validar_modelo_configurado",
    "validacao_rag_real_habilitada",
]
