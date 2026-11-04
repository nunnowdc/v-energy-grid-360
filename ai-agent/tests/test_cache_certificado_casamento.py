"""Cache certificado: só casa a pergunta que o template responde de fato.

Errar para o lado do hit entrega resposta errada com selo "certificada", o selo mais forte;
errar para o lado do miss só custa uma chamada ao LLM.
"""
import pytest

from src.nos.no_cache_parametrizado import _encontrar_template, no_cache_parametrizado

# Perguntas reais da auditoria e variações que o template responde
CASAM = {
    "Qual a receita média faturada por cliente residencial em Recife em 2023?": (
        "receita_media_por_cliente", "Recife", 2023,
    ),
    "Qual o faturamento em Recife no ano de 2024?": ("faturamento_por_municipio_ano", "Recife", 2024),
    "Qual o faturamento de Recife em 2024?": ("faturamento_por_municipio_ano", "Recife", 2024),
    "Qual o faturamento em Olinda no ano de 2023?": ("faturamento_por_municipio_ano", "Olinda", 2023),
    "Qual a receita faturada em Recife em 2023?": ("faturamento_por_municipio_ano", "Recife", 2023),
    "Qual o faturamento de Jaboatão em 2025?": ("faturamento_por_municipio_ano", "Jaboatão dos Guararapes", 2025),
    "Qual o faturamento do Cabo de Santo Agostinho em 2024?": (
        "faturamento_por_municipio_ano", "Cabo de Santo Agostinho", 2024,
    ),
    "Qual o faturamento da classe residencial em Recife em 2023?": (
        "faturamento_classe_municipio_ano", "Recife", 2023,
    ),
    # Variações com outros municípios e classes
    "Qual a receita média por cliente comercial em Olinda em 2025?": (
        "receita_media_por_cliente", "Olinda", 2025,
    ),
    "Qual o faturamento da classe comercial em Jaboatão em 2024?": (
        "faturamento_classe_municipio_ano", "Jaboatão dos Guararapes", 2024,
    ),
    "Qual o faturamento industrial do Cabo de Santo Agostinho em 2025?": (
        "faturamento_classe_municipio_ano", "Cabo de Santo Agostinho", 2025,
    ),
    "Qual o faturamento de Paulista em 2025?": ("faturamento_por_municipio_ano", "Paulista", 2025),
    "Qual a receita de Camaragibe em 2023?": ("faturamento_por_municipio_ano", "Camaragibe", 2023),
}

# Perguntas diferentes que antes recebiam a receita faturada total com selo "certificada"
NAO_CASAM = [
    "Qual o ticket médio por fatura residencial em Recife em 2023?",
    "Qual a receita recebida em Recife em 2023?",
    "Qual a receita média por cliente em Recife em 2023?",
    "Qual a receita de Recife em 2023 comparada com 2022?",
    "Qual a receita perdida por fraude em Recife em 2023?",
    "Qual a receita do bairro Boa Viagem em Recife em 2023?",
    "Qual a receita mensal de Recife em jan/2025?",
    "Qual o FEC do alimentador AL-001 em 2025 comparado com 2024?",
    "Qual a nota média do call center em 2025?",
    "O agente acertou quantas perguntas?",
]


@pytest.mark.parametrize("pergunta", CASAM, ids=CASAM)
def test_pergunta_do_template_casa_com_o_nome_do_municipio_do_banco(pergunta):
    esqueleto, municipio, ano = CASAM[pergunta]
    achado = _encontrar_template(pergunta)
    assert achado is not None
    assert achado["registro"]["esqueleto"] == esqueleto
    assert achado["slots"]["municipio"] == municipio
    assert achado["slots"]["ano"] == ano


@pytest.mark.parametrize("pergunta", NAO_CASAM)
def test_pergunta_diferente_vai_para_o_text_to_sql(pergunta):
    assert _encontrar_template(pergunta) is None


def test_call_center_filtra_o_ano_pedido():
    # competencia é data: comparar com o número do ano dava erro no banco
    resultado = no_cache_parametrizado({"pergunta_original": "Qual o desempenho do call center em 2025?"}, db_url="")

    assert resultado["hit_cache"] is True
    assert "competencia >= make_date(2025, 1, 1)" in resultado["sql_gerado"]
    assert "competencia < make_date(2025 + 1, 1, 1)" in resultado["sql_gerado"]
    # Sem o subassunto, os grupos cabem nas 50 linhas que o executor devolve
    assert "GROUP BY assunto, canal " in resultado["sql_gerado"]


def test_filtro_de_classe_ignora_maiusculas_do_banco():
    # O banco guarda 'RESIDENCIAL'; comparar com 'residencial' devolvia zero linhas
    resultado = no_cache_parametrizado(
        {"pergunta_original": "Qual o faturamento da classe residencial em Recife em 2023?"}, db_url=""
    )
    assert resultado["hit_cache"] is True
    assert "unaccent(lower(u.classe)) = unaccent(lower('residencial'))" in resultado["sql_gerado"]
