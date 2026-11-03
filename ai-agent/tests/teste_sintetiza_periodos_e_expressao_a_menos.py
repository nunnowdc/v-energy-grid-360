"""Testa síntese com períodos e expressão 'a menos' / 'a mais'."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.nos.no_sintetiza_resposta import _formatar_valor
from src.insights.conferente_numerico import conferir


def test_formatar_valor_variacao_kwh():
    """Testa se colunas de variação de kwh aplicam 'a menos'/'a mais' sem tocar em consumo_atual_kwh."""
    # Variação negativa
    assert _formatar_valor("variacao_kwh", -498545) == "498.545 kWh a menos"
    # Variação positiva
    assert _formatar_valor("variacao_kwh", 100000) == "100.000 kWh a mais"
    # Coluna de consumo normal não deve receber "a menos"/"a mais"
    assert _formatar_valor("consumo_atual_kwh", 1743770) == "1.743.770 kWh"


def test_conferir_caso_iputinga():
    """Caso Iputinga: kwh_p0 2.242.315, kwh_p1 1.743.770, variação -498.545, pct -22,2."""
    fatos = [{
        "periodo_p0": "jul/2022-jun/2023",
        "periodo_p1": "jul/2025-jun/2026",
        "consumo_p0_kwh": 2242315,
        "consumo_p1_kwh": 1743770,
        "variacao_kwh": -498545,
        "variacao_pct": -22.2
    }]
    texto = (
        "Conforme a base de dados, de jul/2022-jun/2023 para jul/2025-jun/2026 o consumo variou com "
        "498.545 kWh a menos (queda de 22,2%), indo de 2.242.315 kWh para 1.743.770 kWh."
    )
    resultado = conferir(fatos, texto)
    assert resultado, f"Deveria passar na conferência numérica: {texto}"


if __name__ == "__main__":
    test_formatar_valor_variacao_kwh()
    test_conferir_caso_iputinga()
    print("Testes do Nó 11 (períodos e a menos) passaram!")