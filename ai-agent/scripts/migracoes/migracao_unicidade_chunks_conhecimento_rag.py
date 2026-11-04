#!/usr/bin/env python
"""
Migração: Unicidade de chunks no RAG (idempotente).

Cria índice único composto em (categoria, titulo, md5(conteudo)) na tabela
tb_conhecimento_vetorial, permitindo ON CONFLICT nos indexadores.

Execute:
  python -m scripts.migracoes.migracao_unicidade_chunks_conhecimento_rag
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Carrega .env da raiz do projeto
RAIZ = Path(__file__).resolve().parents[3]
load_dotenv(RAIZ / ".env")


def main() -> int:
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌  DATABASE_URL não definida no .env")
        return 1

    try:
        import psycopg2
    except ImportError:
        print("❌  psycopg2-binary não instalado. Execute: pip install psycopg2-binary")
        return 1

    print("🔧  Aplicando migração: unicidade de chunks de conhecimento...")

    try:
        with psycopg2.connect(db_url) as conn:
            with conn.cursor() as cur:
                # 1. Remove duplicatas EXATAS (mantém uma por categoria, titulo, md5(conteudo))
                print("   Removendo duplicatas exatas...")
                cur.execute("""
                    DELETE FROM tb_conhecimento_vetorial
                    WHERE ctid NOT IN (
                        SELECT min(ctid)
                        FROM tb_conhecimento_vetorial
                        GROUP BY categoria, titulo, md5(conteudo)
                    );
                """)
                removidos = cur.rowcount
                print(f"   {removidos} duplicata(s) removida(s).")

                # 2. Cria índice único composto (IF NOT EXISTS = idempotente)
                print("   Criando índice único idx_conhecimento_unico_conteudo...")
                cur.execute("""
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_conhecimento_unico_conteudo
                    ON tb_conhecimento_vetorial (categoria, titulo, md5(conteudo));
                """)

            conn.commit()

        print("✅  Migração concluída com sucesso.")
        return 0

    except Exception as e:
        print(f"❌  Erro ao aplicar migração: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())