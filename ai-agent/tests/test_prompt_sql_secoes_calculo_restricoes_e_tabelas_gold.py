"""Testa estrutura e regras do SYSTEM_PROMPT_SQL."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ai_agent.src.nos.no_escreve_sql import SYSTEM_PROMPT_SQL


def test_15_create_table_public():
    """Deve ter exatamente 15 'CREATE TABLE public.' correspondentes à allowlist."""
    count = SYSTEM_PROMPT_SQL.count("CREATE TABLE public.")
    assert count == 15, f"Encontrados {count} CREATE TABLE, esperado 15"


def test_contexto_rag_appears_once():
    """{contexto_rag} deve aparecer exatamente uma vez, no final."""
    count = SYSTEM_PROMPT_SQL.count("{contexto_rag}")
    assert count == 1, f"{{contexto_rag}} aparece {count} vezes, esperado 1"
    # Verifica que está no final
    assert SYSTEM_PROMPT_SQL.rstrip().endswith("{contexto_rag}")


def test_no_invented_views_in_ddl():
    """Não deve haver views inventadas no DDL (apenas tabelas reais)."""
    # Verifica que não há 'CREATE VIEW' no prompt
    assert "CREATE VIEW" not in SYSTEM_PROMPT_SQL
    assert "vw_gold_" not in SYSTEM_PROMPT_SQL  # views gold não devem estar no DDL


def test_comentario_agg_receita_preco_volume():
    """Deve ter comentário antes do DDL de agg_receita_preco_volume."""
    assert "-- Grão: município × bairro × classe × possui_gd; P0 e P1 fixos em periodo_p0/periodo_p1." in SYSTEM_PROMPT_SQL


def test_r3_periodo_atual_anterior():
    """Regra R3 deve citar periodo_atual e periodo_anterior no SELECT final."""
    assert "'jul/2025-jun/2026' AS periodo_atual" in SYSTEM_PROMPT_SQL
    assert "'jul/2024-jun/2025' AS periodo_anterior" in SYSTEM_PROMPT_SQL


def test_python_comment_r3_fixed_dates():
    """Comentário Python FORA da string avisando que datas de R3 são fixas."""
    # Verifica no próprio arquivo
    with open(os.path.join(os.path.dirname(__file__), "..", "src", "nos", "no_escreve_sql.py"), encoding="utf-8") as f:
        content = f.read()
    assert "ATENÇÃO: As datas da regra R3" in content
    assert "são fixas e exigem revisão quando a base for atualizada" in content


if __name__ == "__main__":
    test_15_create_table_public()
    test_contexto_rag_appears_once()
    test_no_invented_views_in_ddl()
    test_comentario_agg_receita_preco_volume()
    test_r3_periodo_atual_anterior()
    test_python_comment_r3_fixed_dates()
    print("Todos os testes do prompt SQL passaram!")