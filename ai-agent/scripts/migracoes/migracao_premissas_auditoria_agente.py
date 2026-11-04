#!/usr/bin/env python
"""
Migração: Adiciona coluna premissas em tb_auditoria_agente (idempotente).

Rastreia premissas de negócio inferidas ou fixadas na geração de SQL.

Execute:
  python -m scripts.migracoes.migracao_premissas_auditoria_agente
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parents[3]
load_dotenv(RAIZ / "backend" / ".env.local")
load_dotenv(RAIZ / ".env")


def main() -> int:
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("[ERRO] DATABASE_URL não definida")
        return 1

    try:
        import psycopg2
    except ImportError:
        print("[ERRO] psycopg2 não disponível")
        return 1

    print("[MIGRACAO] Aplicando migração: coluna premissas em tb_auditoria_agente...")

    try:
        with psycopg2.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "ALTER TABLE tb_auditoria_agente "
                    "ADD COLUMN IF NOT EXISTS premissas JSONB DEFAULT '[]'::jsonb;"
                )
            conn.commit()
        print("[SUCESSO] Migração concluída com sucesso: coluna 'premissas' adicionada.")
        return 0
    except Exception as exc:
        print(f"[ERRO] Erro ao aplicar migração: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
