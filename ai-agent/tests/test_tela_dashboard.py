"""
Testes da escolha da tela do portal a partir do SQL executado e do resultado.
Valores fictícios; nenhum dado vem da base real.
"""
from __future__ import annotations

from datetime import date

import pytest

from src.services.tela_dashboard import tela_do_dashboard


def _filtros(tela) -> dict:
    return tela.filtros.model_dump(exclude_none=True)


def _periodos(tela) -> dict:
    """Só os períodos, para os testes de tempo."""
    filtros = _filtros(tela)
    return {chave: filtros[chave] for chave in ("periodo_base", "periodo") if chave in filtros}


ANO_2024 = {"periodo": {"de": "2024-01", "ate": "2024-12"}}
ANO_2025 = {"periodo": {"de": "2025-01", "ate": "2025-12"}}


def test_cache_certificado_abre_indicadores_com_o_municipio():
    sql = (
        "SELECT r.municipio, r.ano, SUM(r.receita_faturada) AS receita_total "
        "FROM agg_receita_mensal r "
        "WHERE unaccent(lower(r.municipio)) = unaccent(lower('recife')) AND r.ano = 2024 "
        "GROUP BY r.municipio, r.ano"
    )
    tela = tela_do_dashboard(sql, [{"municipio": "Recife", "ano": 2024, "receita_total": 10.0}])
    assert tela.tela == "indicadores"
    # O WHERE vale mais que a linha do resultado
    assert _filtros(tela) == {"municipio": "recife", **ANO_2024}


def test_variacao_de_receita_abre_receita_com_bairro_e_classe():
    sql = (
        "SELECT SUM(efeito_preco) FROM agg_receita_preco_volume "
        "WHERE unaccent(lower(municipio)) = unaccent(lower('Olinda')) "
        "AND (unaccent(lower(bairro)) = unaccent(lower('Centro')) AND classe IN ('COMERCIAL'))"
    )
    tela = tela_do_dashboard(sql, [{"sum": 1.0}])
    assert tela.tela == "receita"
    assert _filtros(tela) == {"municipio": "olinda", "bairro": "centro", "classe": "comercial"}


def test_maior_dec_pega_o_alimentador_da_linha_unica():
    sql = (
        "SELECT alimentador, municipio_principal, dec FROM agg_continuidade_alimentador_anual "
        "WHERE ano = 2025 ORDER BY dec DESC LIMIT 1"
    )
    tela = tela_do_dashboard(sql, [{"alimentador": "ALM-REC-008", "municipio_principal": "Recife", "dec": 9.1}])
    assert tela.tela == "continuidade"
    assert _filtros(tela) == {"alimentador": "alm-rec-008", "municipio": "recife", **ANO_2025}


def test_ranking_com_varias_linhas_nao_escolhe_um_valor():
    sql = "SELECT alimentador, dec FROM agg_continuidade_alimentador_anual WHERE ano = 2025 ORDER BY dec DESC LIMIT 5"
    dados = [{"alimentador": "ALM-REC-008", "dec": 9.1}, {"alimentador": "ALM-OLI-002", "dec": 8.7}]
    tela = tela_do_dashboard(sql, dados)
    assert tela.tela == "continuidade"
    assert _filtros(tela) == ANO_2025


def test_causa_em_ocorrencias_abre_continuidade():
    sql = (
        "SELECT COUNT(*) FROM fact_ocorrencias o JOIN dim_unidade_consumidora u ON o.id_uc = u.id_uc "
        "WHERE unaccent(lower(o.causa)) = unaccent(lower('climatica'))"
    )
    tela = tela_do_dashboard(sql, [{"count": 3}])
    # Continuidade tem prioridade sobre o cadastro de UCs
    assert tela.tela == "continuidade"
    assert _filtros(tela) == {"causa": "climatica"}


def test_uc_filtrada_abre_a_visao_360():
    sql = "SELECT competencia, receita_faturada FROM fact_faturamento WHERE id_uc = 'UC100000'"
    tela = tela_do_dashboard(sql, [{"competencia": "2025-01-01"}, {"competencia": "2025-02-01"}])
    assert tela.tela == "visao_360"
    assert _filtros(tela) == {"id_uc": "uc100000"}


def test_uc_mais_suspeita_abre_a_visao_360_dela():
    sql = "SELECT id_uc, score FROM fila_inspecao ORDER BY prioridade LIMIT 1"
    tela = tela_do_dashboard(sql, [{"id_uc": "UC100001", "score": 90}])
    assert tela.tela == "visao_360"
    assert _filtros(tela) == {"id_uc": "uc100001"}


def test_lista_de_suspeitas_abre_a_fila():
    sql = (
        "SELECT id_uc, score FROM fila_inspecao "
        "WHERE unaccent(lower(municipio)) = unaccent(lower('olinda')) ORDER BY prioridade LIMIT 10"
    )
    tela = tela_do_dashboard(sql, [{"id_uc": "UC100001"}, {"id_uc": "UC100002"}])
    assert tela.tela == "inspecoes"
    assert _filtros(tela) == {"municipio": "olinda"}


@pytest.mark.parametrize(
    "where",
    [
        "unaccent(lower(municipio)) = 'recife' OR unaccent(lower(municipio)) = 'olinda'",
        "unaccent(lower(municipio)) IN ('recife', 'olinda')",
        "municipio = 'Recife' AND municipio = 'Olinda'",
        "municipio <> 'Recife'",
        "municipio LIKE '%Rec%'",
    ],
)
def test_filtro_com_mais_de_um_valor_ou_sem_igualdade_fica_de_fora(where):
    tela = tela_do_dashboard(f"SELECT SUM(consumo_kwh) FROM agg_receita_mensal WHERE {where}", [])
    assert tela.tela == "indicadores"
    assert _filtros(tela) == {}


def test_mesmo_valor_com_grafia_diferente_conta_como_um():
    sql = (
        "SELECT COUNT(*) FROM dim_unidade_consumidora "
        "WHERE municipio = 'Jaboatão dos Guararapes' AND unaccent(lower(municipio)) = 'jaboatao dos guararapes'"
    )
    assert _filtros(tela_do_dashboard(sql, [])) == {"municipio": "jaboatão dos guararapes"}


def test_filtro_dentro_de_subconsulta_tambem_vale():
    sql = (
        "SELECT AVG(dec) FROM agg_continuidade_alimentador WHERE alimentador IN "
        "(SELECT alimentador FROM dim_unidade_consumidora WHERE unaccent(lower(municipio)) = 'paulista')"
    )
    tela = tela_do_dashboard(sql, [{"avg": 1.0}])
    assert tela.tela == "continuidade"
    assert _filtros(tela) == {"municipio": "paulista"}


def test_case_when_nao_vira_filtro():
    sql = (
        "SELECT SUM(CASE WHEN classe = 'RURAL' THEN consumo_kwh ELSE 0 END) "
        "FROM agg_receita_mensal WHERE ano = 2024"
    )
    assert _filtros(tela_do_dashboard(sql, [{"sum": 1.0}])) == ANO_2024


@pytest.mark.parametrize(
    "where",
    [
        "r.ano = 2024",
        "2024 = r.ano",
        "r.ano::int = 2024",
        "EXTRACT(YEAR FROM r.competencia) = 2024",
        "date_part('year', competencia) = 2024",
        "mes_referencia LIKE '2024-%'",
        "mes_referencia BETWEEN '2024-01' AND '2024-12'",
        "competencia >= '2024-01-01' AND competencia < '2025-01-01'",
        "competencia BETWEEN DATE '2024-01-01' AND DATE '2024-12-31'",
        "ano >= 2024 AND ano <= 2024 AND municipio = 'Recife'",
    ],
)
def test_filtro_de_tempo_vira_o_periodo_consultado(where):
    tela = tela_do_dashboard(f"SELECT SUM(receita_faturada) FROM agg_receita_mensal r WHERE {where}", [{"sum": 1.0}])
    assert _periodos(tela) == ANO_2024


@pytest.mark.parametrize(
    ("where", "periodo"),
    [
        ("ano = 2025 AND mes BETWEEN 1 AND 3", {"de": "2025-01", "ate": "2025-03"}),
        ("ano = 2025 AND mes = 3", {"de": "2025-03", "ate": "2025-03"}),
        ("mes_referencia = '2025-03'", {"de": "2025-03", "ate": "2025-03"}),
        ("competencia > '2024-06-15' AND competencia <= '2024-09-30'", {"de": "2024-07", "ate": "2024-09"}),
        ("mes_referencia >= '2024-07' AND mes_referencia < '2025-07'", {"de": "2024-07", "ate": "2025-06"}),
        ("ano BETWEEN 2023 AND 2024", {"de": "2023-01", "ate": "2024-12"}),
    ],
)
def test_meses_e_intervalos_viram_o_periodo(where, periodo):
    tela = tela_do_dashboard(f"SELECT SUM(consumo_kwh) FROM agg_receita_mensal WHERE {where}", [{"sum": 1.0}])
    assert _periodos(tela) == {"periodo": periodo}


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT ano, SUM(receita_faturada) FROM agg_receita_mensal WHERE ano IN (2023, 2024) GROUP BY ano",
        "SELECT ano, SUM(receita_faturada) FROM agg_receita_mensal WHERE ano = 2023 OR ano = 2024 GROUP BY ano",
        (
            "SELECT SUM(receita_faturada) FILTER (WHERE ano = 2023), SUM(receita_faturada) FILTER (WHERE ano = 2024) "
            "FROM agg_receita_mensal"
        ),
        (
            "SELECT SUM(receita_faturada) FILTER (WHERE ano = 2023), SUM(receita_faturada) FILTER (WHERE ano = 2024) "
            "FROM agg_receita_mensal WHERE ano BETWEEN 2023 AND 2024"
        ),
        (
            "WITH a AS (SELECT SUM(receita_faturada) AS r FROM agg_receita_mensal WHERE ano = 2023), "
            "b AS (SELECT SUM(receita_faturada) AS r FROM agg_receita_mensal WHERE ano = 2024) "
            "SELECT b.r - a.r FROM a, b"
        ),
    ],
)
def test_dois_periodos_do_mesmo_tamanho_viram_base_e_comparado(sql):
    tela = tela_do_dashboard(sql, [{"ano": 2023}, {"ano": 2024}])
    assert _periodos(tela) == {"periodo_base": {"de": "2023-01", "ate": "2023-12"}, **ANO_2024}


@pytest.mark.parametrize(
    "where",
    [
        # Sem fim
        "ano >= 2024",
        # Só o banco sabe qual é o último mês
        "competencia >= (SELECT MAX(competencia) FROM agg_receita_mensal) - INTERVAL '11 months'",
        # O OR deixa passar meses de qualquer ano
        "ano = 2024 OR municipio = 'Recife'",
        # Três anos ou blocos de tamanhos diferentes não são uma comparação
        "ano IN (2022, 2023, 2024)",
        "mes_referencia IN ('2023-01', '2024-01', '2024-03')",
        # Só o mês, de todos os anos
        "mes = 3",
        # Nenhum mês
        "ano = 2024 AND ano = 2025",
    ],
)
def test_filtro_de_tempo_que_nao_da_um_periodo_fica_de_fora(where):
    tela = tela_do_dashboard(f"SELECT SUM(consumo_kwh) FROM agg_receita_mensal WHERE {where}", [{"sum": 1.0}])
    assert tela.tela == "indicadores"
    assert _periodos(tela) == {}


def test_juncao_pela_competencia_nao_atrapalha_o_periodo():
    sql = (
        "SELECT SUM(f.receita_faturada) FROM fact_faturamento f, agg_receita_mensal r "
        "WHERE f.competencia = r.competencia AND r.ano = 2024"
    )
    assert _periodos(tela_do_dashboard(sql, [{"sum": 1.0}])) == ANO_2024


@pytest.mark.parametrize(
    ("linha", "periodo"),
    [
        ({"ano": 2024, "receita": 10.0}, {"de": "2024-01", "ate": "2024-12"}),
        ({"ano": 2025, "mes": 3, "receita": 10.0}, {"de": "2025-03", "ate": "2025-03"}),
        ({"mes_referencia": "2025-03", "receita": 10.0}, {"de": "2025-03", "ate": "2025-03"}),
        ({"competencia": date(2025, 3, 1), "dec": 2.0}, {"de": "2025-03", "ate": "2025-03"}),
    ],
)
def test_sem_tempo_no_where_o_periodo_vem_da_linha_unica(linha, periodo):
    sql = "SELECT ano, SUM(receita_faturada) AS receita FROM agg_receita_mensal GROUP BY ano ORDER BY 2 DESC LIMIT 1"
    assert _periodos(tela_do_dashboard(sql, [linha])) == {"periodo": periodo}


def test_ultimo_mes_relativo_usa_o_mes_da_linha():
    sql = (
        "SELECT competencia, SUM(consumo_kwh) FROM agg_receita_mensal "
        "WHERE competencia = (SELECT MAX(competencia) FROM agg_receita_mensal) GROUP BY competencia"
    )
    tela = tela_do_dashboard(sql, [{"competencia": date(2026, 6, 1), "sum": 1.0}])
    assert _periodos(tela) == {"periodo": {"de": "2026-06", "ate": "2026-06"}}


def test_varias_linhas_sem_tempo_no_where_ficam_sem_periodo():
    sql = "SELECT ano, SUM(receita_faturada) FROM agg_receita_mensal GROUP BY ano"
    assert _periodos(tela_do_dashboard(sql, [{"ano": 2023}, {"ano": 2024}])) == {}


def test_visao_360_nao_leva_periodo():
    sql = "SELECT receita_faturada FROM fact_faturamento WHERE id_uc = 'UC100000' AND ano = 2024"
    assert _filtros(tela_do_dashboard(sql, [{"receita_faturada": 1.0}])) == {"id_uc": "uc100000"}


@pytest.mark.parametrize(
    "sql",
    [
        None,
        "",
        "SQL_INDISPONIVEL",
        "SELECT * FROM",
        "SELECT AVG(tempo_resolucao_h) FROM fact_atendimentos",
    ],
)
def test_sem_consulta_legivel_ou_sem_tela_no_portal_nao_muda_a_tela(sql):
    assert tela_do_dashboard(sql, [{"avg": 1.0}]) is None
