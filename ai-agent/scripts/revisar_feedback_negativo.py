#!/usr/bin/env python
"""
Revisão de feedbacks negativos do agente (REQ-AI-08 / B6).

Consulta a tabela tb_auditoria_agente para listar execuções que receberam
avaliação negativa (feedback_usuario = -1), permitindo transformá-las em
casos de teste do golden dataset ou novos templates certificados.

Execute:
  python ai-agent/scripts/revisar_feedback_negativo.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parents[2]
load_dotenv(RAIZ / "backend" / ".env.local")
load_dotenv(RAIZ / ".env")


def main() -> int:
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("[ERRO] DATABASE_URL não definida no ambiente (.env ou backend/.env.local).")
        return 1

    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
    except ImportError:
        print("[ERRO] psycopg2 não disponível.")
        return 1

    print("=" * 80)
    print("REVISAO DE FEEDBACK NEGATIVO (feedback_usuario = -1)")
    print("=" * 80)

    try:
        with psycopg2.connect(db_url) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        id,
                        data_hora,
                        pergunta_original,
                        rota_escolhida,
                        sql_gerado,
                        selo_confianca,
                        amostra_resultado_json,
                        erro_mensagem,
                        COALESCE(premissas::text, '[]') AS premissas_txt
                    FROM tb_auditoria_agente
                    WHERE feedback_usuario = -1
                    ORDER BY data_hora DESC;
                    """
                )
                registros = cur.fetchall()

        if not registros:
            print("\nNenhum feedback negativo registrado até o momento.")
            print("Quando usuários marcarem feedback negativo no portal, as perguntas aparecerão aqui.\n")
            return 0

        print(f"\nEncontradas {len(registros)} pergunta(s) com avaliação negativa:\n")
        for i, reg in enumerate(registros, start=1):
            print(f"--- Caso #{i} | ID: {reg['id']} | Data: {reg['data_hora']} ---")
            print(f"Pergunta:   {reg['pergunta_original']}")
            print(f"Rota:       {reg['rota_escolhida']} (Selo: {reg['selo_confianca']})")
            print(f"SQL:        {reg['sql_gerado'] or '(nenhum SQL)'}")

            try:
                premissas = json.loads(reg['premissas_txt'])
                if premissas:
                    print(f"Premissas:  {premissas}")
            except Exception:
                pass

            if reg.get("erro_mensagem"):
                print(f"Erro:       {reg['erro_mensagem']}")

            print(f"Resultado:  {str(reg['amostra_resultado_json'])[:200]}...")
            print()

        print("=" * 80)
        print("Proximos passos:")
        print("1. Se o SQL gerado estiver incorreto, monte o sql_esperado e adicione a tests/golden_dataset/golden_dataset.json")
        print("2. Se a pergunta for frequente e previsivel, adicione um template em no_cache_parametrizado.py")
        print("=" * 80)
        return 0

    except Exception as exc:
        print(f"[ERRO] Falha ao consultar auditoria: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
