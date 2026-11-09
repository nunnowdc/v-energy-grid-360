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


@pytest.mark.parametrize("campo,valor,texto,aceito", [
    ("efeito_preco_mil", 778.4, "R$ 778,4 mil", True),
    ("efeito_preco_mil", 778.4, "R$ 778,4 milhões", False),
    ("efeito_preco_mil", 778.4, "R$ 778,4 mi", False),
    ("efeito_preco_milhoes", 19.3, "R$ 19,3 milhões", True),
    ("efeito_preco_milhoes", 19.3, "R$ 19,3 mi", True),
    ("efeito_preco_milhoes", 19.3, "R$ 19,3 mil", False),
    ("efeito_preco_milhoes", 19.3, "R$ 19,3 bilhões", False),
    ("efeito_volume_mil", -778.4, "redução de R$ 778,4 mil", True),
    ("receita", 19300000, "R$ 19,3 milhões", True),
    ("receita", 19.3, "R$ 19,3 milhões", False),
    ("receita", 289.6, "R$ 290", True),
])
def test_escala_explicita_respeita_campo_ou_valor_bruto(campo, valor, texto, aceito):
    fatos = [{campo: valor}]
    assert conferir(fatos, texto) is aceito
    assert bool(numeros_nao_encontrados(fatos, texto)) is not aceito


def test_escala_errada_nao_e_liberada_por_numero_sem_escala_igual():
    fatos = [{"efeito_preco_mil": 778.4, "outro_indicador": 778.4, "data": "07/2026"}]
    assert not conferir(fatos, "R$ 778,4 milhões")
