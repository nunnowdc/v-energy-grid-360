"""Testa validador aceita fórmulas do prompt SQL."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from security.sql_validator import SQLValidator
from security.validador_sqlglot import ValidadorSQLGlotPostgres


def test_unaccent_allowed():
    """unaccent deve ser aceito (já incluído no validador padrão)."""
    validador = ValidadorSQLGlotPostgres()  # já vem com allowed_extra_functions={"unaccent"}
    sql = "SELECT unaccent(nome) FROM dim_alimentador WHERE id = '1'"
    resultado = validador.validar(sql)
    assert resultado.aprovado, f"unaccent deveria ser aceito: {resultado.motivo_rejeicao}"


def test_cte_sum_case():
    """CTE com SUM(CASE...) deve passar."""
    validador = ValidadorSQLGlotPostgres()
    sql = """
    WITH cte AS (
        SELECT SUM(CASE WHEN classe = 'Residencial' THEN consumo_kwh ELSE 0 END) AS res_kwh
        FROM fact_faturamento
        WHERE id_uc = '123'
    )
    SELECT res_kwh FROM cte
    """
    resultado = validador.validar(sql)
    assert resultado.aprovado, f"SUM(CASE...) deveria passar: {resultado.motivo_rejeicao}"


def test_round_numeric():
    """ROUND(...::numeric, 2) deve passar."""
    validador = ValidadorSQLGlotPostgres()
    sql = "SELECT ROUND(consumo_kwh::numeric, 2) FROM fact_faturamento"
    resultado = validador.validar(sql)
    assert resultado.aprovado, f"ROUND(::numeric, 2) deveria passar: {resultado.motivo_rejeicao}"


def test_nullif():
    """NULLIF deve passar."""
    validador = ValidadorSQLGlotPostgres()
    sql = "SELECT NULLIF(consumo_kwh, 0) FROM fact_faturamento"
    resultado = validador.validar(sql)
    assert resultado.aprovado, f"NULLIF deveria passar: {resultado.motivo_rejeicao}"


def test_percentile_cont():
    """PERCENTILE_CONT deve passar."""
    validador = ValidadorSQLGlotPostgres()
    sql = "SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY consumo_kwh) FROM fact_faturamento"
    resultado = validador.validar(sql)
    assert resultado.aprovado, f"PERCENTILE_CONT deveria passar: {resultado.motivo_rejeicao}"


def test_stddev_samp():
    """STDDEV_SAMP deve passar."""
    validador = ValidadorSQLGlotPostgres()
    sql = "SELECT STDDEV_SAMP(consumo_kwh) FROM fact_faturamento"
    resultado = validador.validar(sql)
    assert resultado.aprovado, f"STDDEV_SAMP deveria passar: {resultado.motivo_rejeicao}"


def test_sum_over():
    """SUM() OVER () deve passar."""
    validador = ValidadorSQLGlotPostgres()
    sql = "SELECT SUM(consumo_kwh) OVER () FROM fact_faturamento"
    resultado = validador.validar(sql)
    assert resultado.aprovado, f"SUM() OVER () deveria passar: {resultado.motivo_rejeicao}"


def test_count_distinct():
    """COUNT(DISTINCT) deve passar."""
    validador = ValidadorSQLGlotPostgres()
    sql = "SELECT COUNT(DISTINCT id_uc) FROM fact_faturamento"
    resultado = validador.validar(sql)
    assert resultado.aprovado, f"COUNT(DISTINCT) deveria passar: {resultado.motivo_rejeicao}"


def test_coalesce():
    """COALESCE deve passar."""
    validador = ValidadorSQLGlotPostgres()
    sql = "SELECT COALESCE(consumo_kwh, 0) FROM fact_faturamento"
    resultado = validador.validar(sql)
    assert resultado.aprovado, f"COALESCE deveria passar: {resultado.motivo_rejeicao}"


def test_text_literals_periodo():
    """Literais de texto como rótulo de período devem passar."""
    validador = ValidadorSQLGlotPostgres()
    sql = "SELECT 'jul/2025-jun/2026' AS periodo_atual, 'jul/2024-jun/2025' AS periodo_anterior FROM dim_competencia LIMIT 1"
    resultado = validador.validar(sql)
    assert resultado.aprovado, f"Literais de período deveriam passar: {resultado.motivo_rejeicao}"


def test_reprova_select_email():
    """SELECT email FROM usuarios deve ser reprovado."""
    validador = ValidadorSQLGlotPostgres()
    sql = "SELECT email FROM usuarios"
    resultado = validador.validar(sql)
    assert not resultado.aprovado, "SELECT email deveria ser reprovado"


def test_reprova_select_star_dim_unidade():
    """SELECT * FROM dim_unidade_consumidora deve ser reprovado."""
    validador = ValidadorSQLGlotPostgres()
    sql = "SELECT * FROM dim_unidade_consumidora"
    resultado = validador.validar(sql)
    assert not resultado.aprovado, "SELECT * FROM dim_unidade_consumidora deveria ser reprovado"


def test_reprova_nome_titular():
    """SELECT nome_titular FROM dim_unidade_consumidora deve ser reprovado."""
    validador = ValidadorSQLGlotPostgres()
    sql = "SELECT nome_titular FROM dim_unidade_consumidora"
    resultado = validador.validar(sql)
    assert not resultado.aprovado, "SELECT nome_titular deveria ser reprovado"


if __name__ == "__main__":
    test_unaccent_allowed()
    test_cte_sum_case()
    test_round_numeric()
    test_nullif()
    test_percentile_cont()
    test_stddev_samp()
    test_sum_over()
    test_count_distinct()
    test_coalesce()
    test_text_literals_periodo()
    test_reprova_select_email()
    test_reprova_select_star_dim_unidade()
    test_reprova_nome_titular()
    print("Todos os testes do validador passaram!")