"""
Testes específicos para o conferente numérico e novas regras exigidas.
- '45.000' aceito quando a soma está nos fatos
- '38,3 mil' aceito com _ESCALAS
- '85%' rejeitado quando não há percentual calculado
"""
import pytest
from src.insights.conferente_numerico import conferir, numeros_nao_encontrados


def test_conferir_soma_nos_fatos():
    fatos = [{"total": 45000}]
    texto = "O total consolidado atingiu 45.000 unidades."
    assert conferir(fatos, texto) is True
    assert numeros_nao_encontrados(fatos, texto) == []


def test_conferir_escala_mil():
    fatos = [{"consumo": 38300}]
    texto = "Registrou-se um consumo de 38,3 mil kWh na região."
    assert conferir(fatos, texto) is True
    assert numeros_nao_encontrados(fatos, texto) == []


def test_conferir_percentual_rejeitado_sem_calculo():
    fatos = [{"valor": 100}]
    texto = "A participação foi de 85% do total."
    # Como 85 não está nos fatos e nenhum percentual foi calculado ou fornecido, deve rejeitar
    assert conferir(fatos, texto) is False
    faltantes = numeros_nao_encontrados(fatos, texto)
    assert "85" in faltantes or "85%" in faltantes


def test_conferir_percentual_aceito_com_calculo():
    fatos = [{"valor": 100}, {"_percentual_calculado": 85.0}]
    texto = "A participação foi de 85% do total."
    assert conferir(fatos, texto) is True
    assert numeros_nao_encontrados(fatos, texto) == []
