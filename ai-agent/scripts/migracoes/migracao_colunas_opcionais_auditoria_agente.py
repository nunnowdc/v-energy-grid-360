#!/usr/bin/env python
"""
Migração: Colunas opcionais na auditoria do agente (idempotente).

Adiciona colunas para rastrear tentativas_sql, chamadas_llm, malicioso,
motivo_recusa, ids_chunks_rag, user_id e perfil em tb_auditoria_agente.

Execute:
  python -m scripts.migracoes.migracao_colunas_opcionais_auditoria_agente
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

    print("🔧  Aplicando migração: colunas opcionais na auditoria...")

    try:
        with psycopg2.connect(db_url) as conn:
            with conn.cursor() as cur:
                # Colunas a adicionar (IF NOT EXISTS = idempotente)
                colunas = [
                    ("tentativas_sql", "INTEGER DEFAULT 0"),
                    ("chamadas_llm", "INTEGER DEFAULT 0"),
                    ("malicioso", "BOOLEAN DEFAULT FALSE"),
                    ("motivo_recusa", "TEXT"),
                    ("ids_chunks_rag", "TEXT"),
                    ("user_id", "VARCHAR(100)"),
                    ("perfil", "VARCHAR(50)"),
                ]

                for coluna, tipo in colunas:
                    print(f"   Adicionando coluna {coluna} ({tipo})...")
                    cur.execute(
                        f"ALTER TABLE tb_auditoria_agente ADD COLUMN IF NOT EXISTS {coluna} {tipo};"
                    )

            conn.commit()

        print("✅  Migração concluída com sucesso.")
        return 0

    except Exception as e:
        print(f"❌  Erro ao aplicar migração: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())