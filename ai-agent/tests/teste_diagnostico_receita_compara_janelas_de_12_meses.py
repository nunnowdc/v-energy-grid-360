"""Testa diagnostico_receita comparando duas janelas de 12 meses."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.insights.extrator_metricas_fixas import QUERIES


def test_diagnostico_receita_janela_12_meses():
    """Verifica se a consulta usa duas janelas de 12 meses (jul/2025-jun/2026 vs jul/2024-jun/2025) e não GROUP BY r.ano."""
    sql = QUERIES["diagnostico_receita"]
    
    # Deve conter a lógica de janelas de 12 meses
    assert "DATE '2025-07-01'" in sql
    assert "DATE '2024-07-01'" in sql
    assert "DATE '2026-07-01'" in sql
    assert "periodo" in sql
    
    # NÃO deve ter GROUP BY r.ano
    assert "GROUP BY r.ano" not in sql
    assert "GROUP BY ano" not in sql
    
    # Deve ter GROUP BY periodo (ou GROUP BY 1)
    assert "GROUP BY 1" in sql or "GROUP BY periodo" in sql
    
    # Deve ter ORDER BY MIN(r.competencia) DESC
    assert "ORDER BY MIN(r.competencia) DESC" in sql or "ORDER BY periodo DESC" in sql
    
    print(f"SQL da diagnostico_receita:\n{sql}")


if __name__ == "__main__":
    test_diagnostico_receita_janela_12_meses()
    print("Teste de diagnostico_receita com janelas de 12 meses passou!")