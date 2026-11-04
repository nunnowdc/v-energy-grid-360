#!/usr/bin/env python3
"""
scripts/diagnostico_top_chunks_rag_por_pergunta.py
Diagnóstico de recuperação vetorial do RAG por pergunta.

Executa a consulta vetorial no PostgreSQL + pgvector SEM filtro de limiar e SEM
filtro de categoria, exibindo os 5 chunks mais próximos com seus scores e o limiar
atual configurado para comparação.

Uso:
    python scripts/diagnostico_top_chunks_rag_por_pergunta.py "O que é DEC e FEC e como são calculados?"
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Garante que a pasta ai-agent esteja no sys.path para import de src
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
AI_AGENT_DIR = Path(__file__).resolve().parent.parent

for caminho in [ROOT_DIR, AI_AGENT_DIR]:
    if str(caminho) not in sys.path and caminho.exists():
        sys.path.insert(0, str(caminho))

# Carrega .env procurando na raiz e em ai-agent
if (ROOT_DIR / ".env").exists():
    load_dotenv(ROOT_DIR / ".env")
elif (AI_AGENT_DIR / ".env").exists():
    load_dotenv(AI_AGENT_DIR / ".env")
else:
    load_dotenv()

from src.rag.buscador_vetorial import BuscadorVetorial

SQL_DIAGNOSTICO = """
SELECT
    id::text,
    categoria,
    titulo,
    1 - (embedding <=> %(embedding)s::vector) AS similaridade
FROM tb_conhecimento_vetorial
ORDER BY embedding <=> %(embedding)s::vector
LIMIT 5;
"""


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Diagnóstico RAG: Top 5 chunks vetoriais sem corte de limiar."
    )
    parser.add_argument("pergunta", type=str, help="Pergunta para teste de busca semântica.")
    parser.add_argument(
        "--db-url",
        type=str,
        default=None,
        help="URL de conexão PostgreSQL (padrão: DATABASE_URL do .env).",
    )
    args = parser.parse_args()

    db_url = args.db_url or os.getenv("DATABASE_URL")
    if not db_url:
        print("Erro: DATABASE_URL não configurada no ambiente ou .env.", file=sys.stderr)
        return 1

    pergunta = args.pergunta.strip()
    if not pergunta:
        print("Erro: pergunta vazia fornecida.", file=sys.stderr)
        return 1

    print("=" * 80)
    print("DIAGNÓSTICO RAG — TOP CHUNKS VETORIAIS")
    print("=" * 80)
    print(f"Pergunta: {pergunta}")

    buscador = BuscadorVetorial(db_url=db_url)
    print(f"Limiar atual do buscador: {buscador.limiar:.2f} (fonte: RAG_LIMIAR_SIMILARIDADE ou padrão)")
    print("-" * 80)

    try:
        embedding = buscador._gerar_embedding(pergunta)
    except Exception as e:
        print(f"Erro ao gerar embedding: {e}", file=sys.stderr)
        return 1

    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor

        with psycopg2.connect(db_url) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SET enable_indexscan = off;")
                cur.execute(
                    SQL_DIAGNOSTICO,
                    {"embedding": f"[{','.join(str(v) for v in embedding)}]"},
                )
                rows = cur.fetchall()
    except Exception as e:
        print(f"Erro ao consultar banco vetorial: {e}", file=sys.stderr)
        return 1

    if not rows:
        print("Nenhum chunk retornado da tabela tb_conhecimento_vetorial (tabela vazia).")
        return 0

    print(f"{'Posição':<8} | {'Similaridade':<12} | {'Acima Limiar?':<14} | {'Categoria':<18} | {'Título'}")
    print("-" * 80)

    for i, row in enumerate(rows, start=1):
        similaridade = float(row["similaridade"])
        acima = "SIM" if similaridade >= buscador.limiar else "NÃO"
        categoria = str(row["categoria"])
        titulo = str(row["titulo"])
        print(f"{i:<8} | {similaridade:<12.3f} | {acima:<14} | {categoria:<18} | {titulo}")

    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
