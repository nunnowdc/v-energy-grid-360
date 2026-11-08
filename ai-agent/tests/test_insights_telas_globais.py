"""Contrato dos insights globais, sem banco ou chamadas ao modelo real."""
from copy import deepcopy
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import sqlglot
from sqlglot import exp

from src.insights.conferente_numerico import conferir, numeros_nao_encontrados
from src.insights.extrator_metricas_fixas import QUERIES, extrair_metricas, fontes_da_tela
from src.insights.narrador_insights import SEM_DADOS, gerar_texto_modelo, narrar_insight
from src.insights.service import InsightsService


FATOS = {
    "receita": [
        {"grupo": "todas as UCs", "periodo_base": "jul/2022 a jun/2023", "periodo_comparado": "jul/2025 a jun/2026",
         "ucs": 45000, "receita_base_milhoes": 157.1, "receita_comparada_milhoes": 169.7,
         "variacao_receita_pct": 8.0, "variacao_consumo_medido_pct": -4.0,
         "efeito_volume_milhoes": -6.8, "efeito_preco_milhoes": 19.3},
        {"grupo": "com geração própria", "ucs": 3503, "efeito_volume_milhoes": -8.1,
         "efeito_preco_mil": 778.4, "efeito_preco_milhoes": None, "variacao_consumo_medido_pct": -60.9},
        {"grupo": "sem geração própria", "ucs": 41497, "variacao_consumo_medido_pct": 1.0},
    ],
    "indicadores": [
        {"comparacao": "últimos 12 meses contra os 12 anteriores", "inicio": "07/2025", "fim": "06/2026",
         "receita_milhoes": 169.7, "consumo_gwh": 217.9, "faturas_atrasadas_pct": 7.7,
         "faturas_atrasadas_anterior_pct": 8.0, "variacao_receita_pct": -1.2, "variacao_consumo_pct": -0.9},
        {"classe": "industrial", "receita_ultimos_12m_milhoes": 59.7,
         "variacao_receita_milhoes": -5.6, "variacao_receita_pct": -8.6},
    ],
    "continuidade": [
        {"destaque": "maior DEC entre todos", "alimentador": "ALM-JAB-016",
         "municipio": "Jaboatão dos Guararapes", "total_ucs": 20,
         "inicio": "07/2025", "fim": "06/2026", "dec_horas": 43.9, "fec_vezes": 19.7},
        {"destaque": "maior DEC com 100 UCs ou mais", "alimentador": "ALM-SAO-004",
         "municipio": "São Lourenço da Mata", "total_ucs": 1091,
         "inicio": "07/2025", "fim": "06/2026", "dec_horas": 15.6,
         "dec_sem_dias_criticos_horas": 0.5, "fec_vezes": 3.4},
        {"destaque": "maior DEC com 100 UCs ou mais, sem os dias críticos", "alimentador": "ALM-REC-006",
         "municipio": "Recife", "total_ucs": 104, "inicio": "07/2025", "fim": "06/2026",
         "dec_horas": 8.3, "dec_sem_dias_criticos_horas": 6.0},
        {"abrangencia": "toda a rede", "causa": "climática", "pct_das_ucs_interrompidas": 41.0, "pct_das_horas": 62.1},
        {"abrangencia": "toda a rede", "dias_criticos": 31, "inicio_dias_criticos": "07/2025",
         "fim_dias_criticos": "07/2025", "pct_das_horas_em_dias_criticos": 56.3},
    ],
    "fila_inspecao": [
        {"fila_de": "06/2026", "ucs_na_fila": 11586, "gwh_recuperavel_ano": 3.0,
         "criterio_bairro_critico_irregularidade_minima_pct": 50,
         "bairros_criticos": 4, "ucs_em_bairros_criticos": 2200, "pct_da_energia_em_bairros_criticos": 84.8},
        {"bairro": "Iputinga", "municipio": "Recife", "irregularidade_confirmada_no_bairro_pct": 91.0},
        {"bairro": "Jardim Jordão", "municipio": "Jaboatão", "irregularidade_confirmada_no_bairro_pct": 89.6},
        {"bairro": "Prazeres", "municipio": "Jaboatão", "irregularidade_confirmada_no_bairro_pct": 89.9},
        {"bairro": "Macaxeira", "municipio": "Recife", "irregularidade_confirmada_no_bairro_pct": 88.7},
    ],
}

TEXTOS = {
    "receita": "Entre jul/2022 a jun/2023 e jul/2025 a jun/2026, a receita subiu 8,0%, com efeito preço de R$ 19,3 milhões e efeito volume de -R$ 6,8 milhões. A perda de volume veio das 3.503 UCs com geração própria, cujo consumo medido caiu 60,9% (efeito volume de -R$ 8,1 milhões e efeito preço de R$ 778,4 mil); nas 41.497 demais, o consumo subiu 1,0%.",
    "indicadores": "De 07/2025 a 06/2026, a receita foi de R$ 169,7 milhões (queda de 1,2%) e o consumo de 217,9 GWh (queda de 0,9%) frente aos 12 meses anteriores; a classe industrial perdeu R$ 5,6 milhões (queda de 8,6%), e as faturas atrasadas caíram de 8,0% para 7,7%.",
    "continuidade": "De 07/2025 a 06/2026, 56,3% das horas sem energia da rede caíram nos 31 dias críticos de 07/2025. O maior DEC entre os alimentadores com 100 UCs ou mais foi o do ALM-SAO-004, com 15,6 horas, mas sem os dias críticos ele teria só 0,5 hora; fora deles, o pior é o ALM-REC-006, com 6,0 horas. Na rede toda, a causa climática respondeu por 41,0% das UCs interrompidas e 62,1% das horas.",
    "fila_inspecao": "A fila de 06/2026 tem 11.586 UCs e 3,0 GWh/ano de energia recuperável estimada; 84,8% dessa energia está em 2.200 UCs de 4 bairros com irregularidade confirmada em pelo menos 50% das inspeções: Iputinga (91,0%), Jardim Jordão (89,6%), Prazeres (89,9%) e Macaxeira (88,7%).",
}


@pytest.mark.parametrize("tela", FATOS)
def test_textos_do_documento_passam_no_conferente(tela):
    assert conferir(FATOS[tela], TEXTOS[tela])
    assert numeros_nao_encontrados(FATOS[tela], TEXTOS[tela]) == []


@pytest.mark.parametrize("tela", FATOS)
def test_texto_modelo_seleciona_resumo_mesmo_fora_da_primeira_linha(tela):
    fatos = FATOS[tela]
    texto = gerar_texto_modelo(tela, fatos[1:] + fatos[:1])
    assert texto != SEM_DADOS
    assert conferir(fatos, texto)
    assert "_" not in texto
    assert "None" not in texto
    assert "Dados recentes da tela" not in texto
    if tela == "receita":
        assert "157,1 milhões" in texto and "-6,8 milhões" in texto
    elif tela == "indicadores":
        assert "217,9 GWh" in texto
    elif tela == "continuidade":
        assert "ALM-SAO-004" in texto and "15,6 horas" in texto
    else:
        assert "11.586 UCs" in texto and "3,0 GWh/ano" in texto


@pytest.mark.parametrize("tela", FATOS)
def test_fallback_sem_dados_nao_inventa_zero(tela):
    assert gerar_texto_modelo(tela, []) == SEM_DADOS
    assert gerar_texto_modelo(tela, [{}]) == SEM_DADOS


def test_fallback_decimal_zero_e_causa_legivel():
    fatos = deepcopy(FATOS["receita"])
    fatos[0]["efeito_volume_milhoes"] = Decimal("0.0")
    assert "efeito volume de R$ 0,0 milhões" in gerar_texto_modelo("receita", fatos)
    fatos[0]["receita_base_milhoes"] = None
    assert gerar_texto_modelo("receita", fatos) == SEM_DADOS
    fatos = deepcopy(FATOS["continuidade"])
    fatos[3]["causa"] = "FALHA_EQUIPAMENTO"
    assert "causa falha equipamento" in gerar_texto_modelo("continuidade", fatos)


@pytest.mark.parametrize("texto,aceito", [
    ("R$ 157,1 milhões; o volume tirou R$ 6,8 milhões.", True),
    ("R$ 12,6 milhões", False),
])
def test_milhoes_ja_convertidos_no_sql(texto, aceito):
    fatos = [{"receita_base_milhoes": 157.1, "efeito_volume_milhoes": -6.8}]
    assert conferir(fatos, texto) is aceito
    assert bool(numeros_nao_encontrados(fatos, texto)) is not aceito


@pytest.mark.parametrize("preco,volume", [(Decimal("778.4"), Decimal("-100.0")), (0, 0)])
def test_fallback_receita_com_efeitos_em_mil(preco, volume):
    fatos = deepcopy(FATOS["receita"])
    fatos[0].update(efeito_preco_milhoes=None, efeito_volume_milhoes=None,
                    efeito_preco_mil=preco, efeito_volume_mil=volume)
    texto = gerar_texto_modelo("receita", fatos)
    assert texto != SEM_DADOS
    assert "efeito preço de R$" in texto and "efeito volume de R$" in texto
    assert conferir(fatos, texto)
    if preco:
        assert "778,4 mil" in texto and "-100,0 mil" in texto
    else:
        assert texto.count("R$ 0,0 mil") == 2


def test_fallback_nao_inventa_efeitos_ausentes():
    fatos = deepcopy(FATOS["receita"])
    fatos[0].update(efeito_preco_milhoes=None, efeito_volume_milhoes=None)
    texto = gerar_texto_modelo("receita", fatos)
    assert "157,1 milhões" in texto
    assert "efeito" not in texto


def test_continuidade_separa_causa_da_rede_e_explica_dias_criticos():
    texto = gerar_texto_modelo("continuidade", FATOS["continuidade"])
    assert "excluindo os dias críticos, seu DEC foi de 0,5 horas" in texto
    assert "Na rede toda, 56,3%" in texto
    assert "Na rede toda, a causa climática" in texto
    fatos = deepcopy(FATOS["continuidade"])
    fatos[3]["abrangencia"] = "um alimentador"
    assert "causa" not in gerar_texto_modelo("continuidade", fatos)


def test_sql_preserva_protecao_de_divisao_por_zero():
    for consultas in QUERIES.values():
        for sql in ([consultas] if isinstance(consultas, str) else consultas):
            arvore = sqlglot.parse_one(sql.format(id_uc="UC123"), read="postgres")
            for divisao in arvore.find_all(exp.Div):
                denominador = divisao.expression
                assert isinstance(denominador, (exp.Literal, exp.Nullif)), sql


def test_consultas_trazem_criterios_e_abrangencias_explicitos():
    assert "variacao_consumo_medido_pct" in QUERIES["receita"]
    assert "efeito_preco_mil" in QUERIES["receita"]
    assert "AS comparacao" in QUERIES["indicadores"][0]
    assert "ORDER BY ABS(atual - anterior) DESC NULLS LAST" in QUERIES["indicadores"][1]
    assert len(QUERIES["continuidade"]) == 3
    assert "SUM(c.dec_sem_dia_critico)" in QUERIES["continuidade"][0]
    assert "'toda a rede' AS abrangencia" in QUERIES["continuidade"][1]
    assert "AS inicio_dias_criticos" in QUERIES["continuidade"][2]
    assert "AS fim_dias_criticos" in QUERIES["continuidade"][2]
    assert "50 AS criterio_bairro_critico_irregularidade_minima_pct" in QUERIES["fila_inspecao"][0]
    assert "taxa_irregularidade_bairro >= 0.5" in QUERIES["fila_inspecao"][0]
    assert fontes_da_tela("fila_inspecao") == ["fila_inspecao"]


@pytest.mark.parametrize("tela", QUERIES)
def test_consultas_postgres_e_fontes_do_contrato(tela):
    queries = QUERIES[tela]
    queries = [queries] if isinstance(queries, str) else queries
    tabelas = set()
    for sql in queries:
        arvore = sqlglot.parse_one(sql.format(id_uc="UC12345"), read="postgres")
        ctes = {cte.alias for cte in arvore.find_all(exp.CTE)}
        tabelas.update(t.name for t in arvore.find_all(exp.Table) if t.name not in ctes)
        assert not {"nome_titular", "cpf", "logradouro"} & {c.name for c in arvore.find_all(exp.Column)}
    assert tabelas == set(fontes_da_tela(tela))


def test_receita_usa_periodos_gold_e_indicadores_janelas_dinamicas():
    assert set(QUERIES) == {"visao_360_uc", *FATOS}
    assert "GROUPING SETS" in QUERIES["receita"]
    assert "SPLIT_PART(periodo_p0" in QUERIES["receita"]
    assert "SPLIT_PART(periodo_p1" in QUERIES["receita"]
    for sql in QUERIES["indicadores"]:
        assert "MAX(competencia)" in sql
        assert "INTERVAL '24 months'" in sql
        assert "INTERVAL '12 months'" in sql
        assert "2025" not in sql and "2026" not in sql


@pytest.mark.parametrize("tela", ["indicadores", "continuidade", "fila_inspecao"])
def test_extrator_junta_consultas_sem_recalcular(tela):
    executor = Mock()
    respostas = [
        SimpleNamespace(sucesso=True, linhas=FATOS[tela][:1]),
        SimpleNamespace(sucesso=True, linhas=FATOS[tela][1:]),
    ]
    if tela == "continuidade":
        respostas[1].linhas = FATOS[tela][1:-1]
        respostas.append(SimpleNamespace(sucesso=True, linhas=FATOS[tela][-1:]))
    executor.executar.side_effect = respostas
    assert extrair_metricas(tela, "global", executor) == FATOS[tela]
    assert executor.executar.call_count == (3 if tela == "continuidade" else 2)


def test_extrator_rejeita_falha_parcial_e_entrada_invalida():
    executor = Mock()
    executor.executar.side_effect = [
        SimpleNamespace(sucesso=True, linhas=[{"janela": "últimos 12 meses"}]),
        SimpleNamespace(sucesso=False, erro="consulta indisponível"),
    ]
    with pytest.raises(RuntimeError, match="consulta indisponível"):
        extrair_metricas("indicadores", "global", executor)
    executor.reset_mock()
    for tela, entidade in [("desconhecida", "global"), ("diagnostico_receita", "global"), ("visao_360_uc", "UC'; DROP TABLE x")]:
        with pytest.raises(ValueError):
            extrair_metricas(tela, entidade, executor)
    executor.executar.assert_not_called()


def test_visao_360_preserva_fatos_e_filtro_uc():
    fatos = [{"competencia": "jun/2026", "consumo_kwh": 618.0, "receita_faturada": 563.85}]
    executor = Mock()
    executor.executar.return_value = SimpleNamespace(sucesso=True, linhas=fatos)
    assert extrair_metricas("visao_360_uc", "UC12345", executor) == fatos
    assert "WHERE f.id_uc = 'UC12345'" in executor.executar.call_args.args[0]
    assert gerar_texto_modelo("visao_360_uc", fatos) == "Em jun/2026 a UC consumiu 618 kWh e a conta foi de R$ 563,85."


@pytest.mark.parametrize("tela", FATOS)
def test_narrador_recebe_contexto_e_preserva_proibicao_de_calculos(tela):
    llm = Mock()
    llm.invoke.return_value = SimpleNamespace(texto=TEXTOS[tela])
    assert narrar_insight(tela, FATOS[tela], llm) == TEXTOS[tela]
    argumentos = llm.invoke.call_args.kwargs
    limite = "três" if tela == "continuidade" else "duas"
    assert f"no máximo {limite} frases" in argumentos["prompt"]
    assert "Foco da síntese:" in argumentos["prompt"]
    assert "Não faça cálculos" in argumentos["system_prompt"]


@pytest.mark.parametrize("tela", FATOS)
def test_servico_tenta_tres_vezes_e_nao_grava_fallback(tela, monkeypatch):
    monkeypatch.setattr("src.insights.service.extrair_metricas", lambda *args: FATOS[tela])
    llm = Mock()
    llm.invoke.return_value = SimpleNamespace(texto="Valor inventado: 999999999999.")
    servico = InsightsService(executor=Mock(), llm=llm)
    servico._ler_cache = Mock(return_value=None)
    servico._gravar_cache = Mock()
    resultado = servico.obter(tela, "global")
    assert llm.invoke.call_count == 3
    assert resultado["selo"] == "template_fallback"
    assert resultado["insight_texto"] == gerar_texto_modelo(tela, FATOS[tela])
    assert resultado["fontes"] == fontes_da_tela(tela)
    servico._gravar_cache.assert_not_called()


def test_servico_grava_aprovado_e_retorna_cache_sem_modelo(monkeypatch):
    monkeypatch.setattr("src.insights.service.extrair_metricas", lambda *args: FATOS["receita"])
    llm = Mock()
    llm.invoke.return_value = SimpleNamespace(texto=TEXTOS["receita"])
    servico = InsightsService(executor=Mock(), llm=llm)
    servico._ler_cache = Mock(return_value=None)
    servico._gravar_cache = Mock()
    resultado = servico.obter("receita", "global")
    assert resultado["selo"] == "auditado_llm"
    servico._gravar_cache.assert_called_once_with(resultado, FATOS["receita"])
    llm.invoke.assert_called_once()
    servico._ler_cache.return_value = resultado
    assert servico.obter("receita", "global") == resultado
    llm.invoke.assert_called_once()


@pytest.mark.parametrize("tela", ["visao_360_uc", *FATOS])
def test_servico_sem_fatos_tem_mensagem_adequada(tela, monkeypatch):
    monkeypatch.setattr("src.insights.service.extrair_metricas", lambda *args: [])
    llm = Mock()
    servico = InsightsService(executor=Mock(), llm=llm)
    resultado = servico.obter(tela, "global")
    esperado = "Não há dados disponíveis para esta unidade consumidora." if tela == "visao_360_uc" else SEM_DADOS
    assert resultado["insight_texto"] == esperado
    llm.invoke.assert_not_called()
