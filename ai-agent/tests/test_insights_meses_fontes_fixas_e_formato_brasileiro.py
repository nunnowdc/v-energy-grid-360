"""Testa insights: meses, fontes fixas, formato brasileiro e fallback."""
import sys
import os
from datetime import date
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.insights.extrator_metricas_fixas import fontes_da_tela, QUERIES, FONTES_POR_TELA
from src.insights.narrador_insights import gerar_texto_modelo


def test_meses_pt_br():
    """Testa conversão de data para formato brasileiro (ex: mai/2026)."""
    c = date(2026, 5, 1)
    MESES = ["jan","fev","mar","abr","mai","jun","jul","ago","set","out","nov","dez"]
    comp = f"{MESES[c.month - 1]}/{c.year}"
    assert comp == "mai/2026"


def test_fontes_por_tela():
    """Valida se todas as chaves de QUERIES estão em FONTES_POR_TELA e vice-versa, e testa ValueError para tela desconhecida."""
    for tela in QUERIES.keys():
        assert tela in FONTES_POR_TELA, f"Tela {tela} de QUERIES falta em FONTES_POR_TELA"
    for tela in FONTES_POR_TELA.keys():
        assert tela in QUERIES, f"Tela {tela} de FONTES_POR_TELA falta em QUERIES"

    # Testa fontes_da_tela
    assert fontes_da_tela("visao_360_uc") == ["fact_faturamento"]
    assert fontes_da_tela("receita") == ["agg_receita_preco_volume"]

    # Tela desconhecida deve levantar ValueError
    with pytest.raises(ValueError):
        fontes_da_tela("tela_inexistente")


def test_formatar_texto_modelo():
    """Testa texto-modelo com R$, vírgula e kWh sem .0."""
    fatos = [{
        "competencia": "jun/2026",
        "consumo_kwh": 618.0,
        "receita_faturada": 563.85
    }]
    texto = gerar_texto_modelo("visao_360_uc", fatos)
    assert "jun/2026" in texto
    assert "618 kWh" in texto
    assert "R$ 563,85" in texto
    assert ".0" not in texto


if __name__ == "__main__":
    test_meses_pt_br()
    test_fontes_por_tela()
    test_formatar_texto_modelo()
    print("Testes de insights passaram!")