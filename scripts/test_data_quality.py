#!/usr/bin/env python3
"""
scripts/test_data_quality.py
V-Energy Grid 360 · CLI de Testes de Qualidade Automatizados (Gate 2)

Executa a validação do Contrato de Dados da Gold contra o banco local
(PostgreSQL ou SQLite), gerando relatório detalhado de conformidade.

Uso:
    python scripts/test_data_quality.py            # Valida PostgreSQL local
    python scripts/test_data_quality.py --sqlite   # Valida SQLite (data/v_energy_gold.db)
"""

import os
import sys
import argparse
import sqlite3

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from scripts.validador_qualidade import validar_banco_sqlite, validar_banco_postgres, ResultadoValidacao


def testar_sqlite(caminho_db: str) -> bool:
    if not os.path.exists(caminho_db):
        print(f"❌ Banco SQLite não encontrado em: {caminho_db}")
        return False

    print(f"\n🔍 Executando Data Quality Gate no SQLite ({caminho_db})...")
    conn = sqlite3.connect(caminho_db)
    res = validar_banco_sqlite(conn)
    conn.close()
    return _exibir_resultado(res)


def testar_postgres(args) -> bool:
    import psycopg

    print(f"\n🔍 Executando Data Quality Gate no PostgreSQL ({args.dbname} @ {args.host}:{args.port})...")
    try:
        if args.url:
            conn = psycopg.connect(args.url)
        else:
            conn = psycopg.connect(
                host=args.host,
                port=args.port,
                dbname=args.dbname,
                user=args.user,
                password=args.password,
            )
        cursor = conn.cursor()
        res = validar_banco_postgres(cursor)
        conn.close()
        return _exibir_resultado(res)
    except Exception as e:
        print(f"❌ Falha de conexão com PostgreSQL: {e}")
        return False


def _exibir_resultado(res: ResultadoValidacao) -> bool:
    print(f"-> Total de verificações executadas: {res.total_verificacoes}")
    if res.avisos:
        print("\n⚠️ AVISOS ENCONTRADOS:")
        for aviso in res.avisos:
            print(f"   • {aviso}")

    if res.sucesso:
        print("\n✅ TODAS AS REGRAS DO CONTRATO DE DADOS PASSARAM COM SUCESSO!")
        print("   O banco local está íntegro e liberado para consumo pelo Portal Web e Agente de IA.")
        return True
    else:
        print("\n❌ FALHAS CRÍTICAS ENCONTRADAS NO CONTRATO DE DADOS:")
        for erro in res.erros:
            print(f"   ❌ {erro}")
        print("\n⛔ CARGA/EXECUÇÃO REJEITADA: Corrija os problemas acima antes de liberar o banco.")
        return False


def main():
    parser = argparse.ArgumentParser(description="Testes de Qualidade Automatizados da Camada Gold")
    parser.add_argument("--sqlite", action="store_true", help="Valida banco local SQLite")
    parser.add_argument("--db-path", type=str, default=os.path.join(ROOT_DIR, "data", "v_energy_gold.db"), help="Caminho do SQLite")
    parser.add_argument("--url", type=str, default=None, help="Database URL para PostgreSQL")
    parser.add_argument("--host", type=str, default=os.getenv("PGHOST", "localhost"))
    parser.add_argument("--port", type=int, default=int(os.getenv("PGPORT", 5432)))
    parser.add_argument("--dbname", type=str, default=os.getenv("PGDATABASE", "v_energy"))
    parser.add_argument("--user", type=str, default=os.getenv("PGUSER", "postgres"))
    parser.add_argument("--password", type=str, default=os.getenv("PGPASSWORD", "postgres"))

    args = parser.parse_args()

    print("=" * 70)
    print("  V-ENERGY GRID 360 · TESTES DE QUALIDADE AUTOMATIZADOS (CAMADA GOLD)")
    print("=" * 70)

    sucesso = testar_sqlite(args.db_path) if args.sqlite else testar_postgres(args)
    sys.exit(0 if sucesso else 1)


if __name__ == "__main__":
    main()
