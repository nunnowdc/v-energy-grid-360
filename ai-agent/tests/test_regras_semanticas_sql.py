"""Regras de negócio no SQL: o que é válido mas dá número errado precisa voltar ao LLM."""
import pytest

from src.services.regras_semanticas_sql import problemas_semanticos

ERRADOS = {
    # O bug da Iputinga: somou o percentual das linhas com e sem GD
    "soma de percentual": (
        "SELECT municipio, bairro, SUM(variacao_volume_pct) AS v FROM agg_receita_preco_volume "
        "WHERE classe = 'RESIDENCIAL' GROUP BY municipio, bairro ORDER BY v LIMIT 1"
    ),
    # TC-006: dividiu pela soma das UCs de cada mês (média mensal, não por cliente)
    "contagem mensal somada no denominador": (
        "SELECT SUM(receita_faturada) / NULLIF(SUM(ucs_faturadas), 0) AS r "
        "FROM agg_receita_mensal WHERE ano = 2023"
    ),
    # TC-017: soma das contagens mensais no lugar de UCs distintas (539.305 em vez de 44.986)
    "contagem mensal somada no ano": "SELECT SUM(ucs_faturadas) AS ucs FROM agg_receita_mensal WHERE ano = 2025",
    "media de preco medio": "SELECT municipio, AVG(preco_medio_kwh) FROM agg_receita_mensal GROUP BY municipio",
    "bairro sem municipio": "SELECT bairro, SUM(consumo_kwh) FROM agg_receita_mensal GROUP BY bairro",
    # TC-013 em 4 de 5 rodadas: a linha crua de um bairro é só a parte sem GD (−15,72% no lugar de −22,2%)
    "linha crua da agg_receita_preco_volume": (
        "SELECT municipio, bairro, kwh_p0, kwh_p1, (kwh_p1 - kwh_p0) AS variacao_volume_kwh, variacao_volume_pct "
        "FROM agg_receita_preco_volume WHERE classe = 'RESIDENCIAL' AND (kwh_p1 - kwh_p0) < 0 "
        "ORDER BY (kwh_p1 - kwh_p0) ASC LIMIT 1"
    ),
}

CERTOS = {
    "variacao recalculada": (
        "SELECT municipio, bairro, 100.0 * (SUM(kwh_p1) - SUM(kwh_p0)) / NULLIF(SUM(kwh_p0), 0) AS variacao_volume_pct "
        "FROM agg_receita_preco_volume GROUP BY municipio, bairro"
    ),
    "inadimplencia": (
        "SELECT municipio, 100.0 * (SUM(receita_faturada) - SUM(receita_recebida)) / NULLIF(SUM(receita_faturada), 0) "
        "AS inadimplencia_pct FROM agg_receita_mensal WHERE ano = 2025 GROUP BY municipio"
    ),
    "receita por cliente": (
        "SELECT SUM(f.receita_faturada) / COUNT(DISTINCT f.id_uc) FROM fact_faturamento f "
        "JOIN dim_unidade_consumidora u ON f.id_uc = u.id_uc WHERE u.classe = 'RESIDENCIAL' AND f.ano = 2023"
    ),
    "DEC do ano somando os meses": (
        "SELECT alimentador, SUM(dec) AS dec_ano FROM agg_continuidade_alimentador WHERE ano = 2025 GROUP BY alimentador"
    ),
    "DEC recalculado no mes": (
        "SELECT competencia, SUM(horas_x_uc) / NULLIF(SUM(total_ucs), 0) AS dec "
        "FROM agg_continuidade_alimentador GROUP BY competencia"
    ),
    "UCs faturadas mes a mes": "SELECT competencia, SUM(ucs_faturadas) FROM agg_receita_mensal GROUP BY competencia",
    "UCs faturadas de um mes": (
        "SELECT SUM(ucs_faturadas) FROM agg_receita_mensal WHERE competencia = DATE '2026-06-01'"
    ),
    # Linha crua com possui_gd à mostra (ou filtrado) é uma escolha explícita
    "linha da agg_receita_preco_volume com possui_gd": (
        "SELECT municipio, bairro, possui_gd, kwh_p0, kwh_p1 FROM agg_receita_preco_volume WHERE classe = 'RESIDENCIAL'"
    ),
    "agg_receita_preco_volume filtrada por GD": (
        "SELECT municipio, bairro, kwh_p0, kwh_p1 FROM agg_receita_preco_volume WHERE possui_gd = true"
    ),
    # Com o município fixo no filtro, agrupar só por bairro é o certo
    "bairro de um municipio": (
        "SELECT bairro, SUM(consumo_kwh) FROM agg_receita_mensal "
        "WHERE unaccent(lower(municipio)) = unaccent(lower('Recife')) GROUP BY bairro"
    ),
}


@pytest.mark.parametrize("sql", ERRADOS.values(), ids=ERRADOS.keys())
def test_sql_valido_com_conta_errada_e_apontado(sql):
    assert problemas_semanticos(sql)


@pytest.mark.parametrize("sql", CERTOS.values(), ids=CERTOS.keys())
def test_sql_certo_passa(sql):
    assert problemas_semanticos(sql) == []


def test_templates_certificados_passam():
    import re

    from src.nos.no_cache_parametrizado import _TEMPLATES_REGISTROS

    for registro in _TEMPLATES_REGISTROS:
        sql = re.sub(r"\{(\w+)\}", lambda m: "2023" if m.group(1) == "ano" else "x", registro["sql"])
        assert problemas_semanticos(sql) == [], registro["esqueleto"]


def test_sql_esperado_do_golden_set_passa():
    from src.avaliacao.golden_set import carregar_casos

    for caso in carregar_casos():
        if caso.get("sql_esperado"):
            assert problemas_semanticos(caso["sql_esperado"]) == [], caso["id"]
