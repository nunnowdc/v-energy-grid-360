"""Consultas analíticas fixas usadas pelo pipeline de insights."""
from __future__ import annotations

import re
from typing import Any, Dict

from ..services.sql_executor import SQLExecutor

RECEITA = """
SELECT CASE WHEN GROUPING(possui_gd) = 1 THEN 'todas as UCs'
            WHEN possui_gd THEN 'com geração própria' ELSE 'sem geração própria' END AS grupo,
       MAX(periodo_p0) AS periodo_base,
       MAX(periodo_p1) AS periodo_comparado,
       SUM(ucs_p1)::int AS ucs,
       ROUND(SUM(receita_p0)::numeric / 1e6, 1) AS receita_base_milhoes,
       ROUND(SUM(receita_p1)::numeric / 1e6, 1) AS receita_comparada_milhoes,
       ROUND((100 * (SUM(receita_p1) / NULLIF(SUM(receita_p0), 0) - 1))::numeric, 1) AS variacao_receita_pct,
       ROUND((100 * (SUM(kwh_p1) / NULLIF(SUM(kwh_p0), 0) - 1))::numeric, 1) AS variacao_consumo_pct,
       ROUND(SUM(efeito_volume)::numeric / 1e6, 1) AS efeito_volume_milhoes,
       ROUND(SUM(efeito_preco)::numeric / 1e6, 1) AS efeito_preco_milhoes
FROM agg_receita_preco_volume
GROUP BY GROUPING SETS ((possui_gd), ())
ORDER BY GROUPING(possui_gd) DESC, possui_gd DESC
"""

INDICADORES_JANELAS = """
WITH lim AS (SELECT MAX(competencia) AS fim FROM agg_receita_mensal)
SELECT CASE WHEN r.competencia > l.fim - INTERVAL '12 months' THEN 'últimos 12 meses' ELSE '12 meses anteriores' END AS janela,
       TO_CHAR(MIN(r.competencia), 'MM/YYYY') AS inicio,
       TO_CHAR(MAX(r.competencia), 'MM/YYYY') AS fim,
       ROUND(SUM(r.receita_faturada)::numeric / 1e6, 1) AS receita_milhoes,
       ROUND(SUM(r.consumo_kwh)::numeric / 1e6, 1) AS consumo_gwh,
       ROUND((100.0 * SUM(r.faturas_atrasadas) / NULLIF(SUM(r.faturas), 0))::numeric, 1) AS faturas_atrasadas_pct
FROM agg_receita_mensal r, lim l
WHERE r.competencia > l.fim - INTERVAL '24 months'
GROUP BY 1
ORDER BY MIN(r.competencia) DESC
"""

INDICADORES_CLASSES = """
WITH lim AS (SELECT MAX(competencia) AS fim FROM agg_receita_mensal)
SELECT r.classe,
       ROUND(SUM(r.receita_faturada) FILTER (WHERE r.competencia > l.fim - INTERVAL '12 months')::numeric / 1e6, 1) AS receita_ultimos_12m_milhoes,
       ROUND((100 * (SUM(r.receita_faturada) FILTER (WHERE r.competencia > l.fim - INTERVAL '12 months')
             / NULLIF(SUM(r.receita_faturada) FILTER (WHERE r.competencia <= l.fim - INTERVAL '12 months'), 0) - 1))::numeric, 1) AS variacao_receita_pct
FROM agg_receita_mensal r, lim l
WHERE r.competencia > l.fim - INTERVAL '24 months'
GROUP BY r.classe
ORDER BY 2 DESC
"""

CONTINUIDADE_ALIMENTADORES = """
WITH lim AS (SELECT MAX(competencia) AS fim FROM agg_continuidade_alimentador),
a AS (
  SELECT c.alimentador, MAX(c.municipio_principal) AS municipio, MAX(c.total_ucs) AS total_ucs,
         TO_CHAR(MIN(c.competencia), 'MM/YYYY') AS inicio, TO_CHAR(MAX(c.competencia), 'MM/YYYY') AS fim,
         ROUND(SUM(c.dec)::numeric, 1) AS dec_horas, ROUND(SUM(c.fec)::numeric, 1) AS fec_vezes
  FROM agg_continuidade_alimentador c, lim l
  WHERE c.competencia > l.fim - INTERVAL '12 months'
  GROUP BY c.alimentador)
(SELECT 'maior DEC entre todos' AS destaque, * FROM a ORDER BY dec_horas DESC LIMIT 1)
UNION ALL
(SELECT 'maior DEC com 100 UCs ou mais', * FROM a WHERE total_ucs >= 100 ORDER BY dec_horas DESC LIMIT 1)
"""

CONTINUIDADE_CAUSAS = """
WITH lim AS (SELECT MAX(competencia) AS fim FROM fact_ocorrencias)
SELECT o.causa,
       COUNT(*) AS ocorrencias,
       ROUND((100.0 * COUNT(*) / NULLIF(SUM(COUNT(*)) OVER (), 0))::numeric, 1) AS pct_das_ocorrencias,
       ROUND((100.0 * SUM(o.duracao_h) / NULLIF(SUM(SUM(o.duracao_h)) OVER (), 0))::numeric, 1) AS pct_das_horas
FROM fact_ocorrencias o, lim l
WHERE o.competencia > l.fim - INTERVAL '12 months'
GROUP BY o.causa
ORDER BY ocorrencias DESC
LIMIT 3
"""

FILA_RESUMO = """
WITH criticos AS (
  SELECT COUNT(DISTINCT (municipio, bairro)) AS bairros, COUNT(*) AS ucs, SUM(kwh_recuperavel_estimado_ano) AS kwh
  FROM fila_inspecao WHERE taxa_irregularidade_bairro >= 0.5),
fila AS (
  SELECT COUNT(*) AS ucs, SUM(kwh_recuperavel_estimado_ano) AS kwh, MAX(data_referencia) AS ref
  FROM fila_inspecao),
insp AS (
  SELECT COUNT(*) AS feitas, COUNT(*) FILTER (WHERE resultado = 'IRREGULARIDADE_CONFIRMADA') AS confirmadas
  FROM fact_inspecoes)
SELECT TO_CHAR(f.ref, 'MM/YYYY') AS fila_de,
       f.ucs AS ucs_na_fila,
       ROUND(f.kwh::numeric / 1e3, 1) AS mwh_recuperavel_ano,
       i.feitas AS inspecoes_realizadas,
       ROUND((100.0 * i.confirmadas / NULLIF(i.feitas, 0))::numeric, 1) AS irregularidade_confirmada_pct,
       c.bairros AS bairros_criticos,
       c.ucs AS ucs_em_bairros_criticos,
       ROUND((100.0 * c.kwh / NULLIF(f.kwh, 0))::numeric, 1) AS pct_da_energia_em_bairros_criticos
FROM fila f, insp i, criticos c
"""

FILA_BAIRROS = """
SELECT municipio, bairro,
       COUNT(*) AS ucs_na_fila,
       ROUND(SUM(kwh_recuperavel_estimado_ano)::numeric / 1e3, 1) AS mwh_recuperavel_ano,
       ROUND(MAX(taxa_irregularidade_bairro)::numeric * 100, 1) AS irregularidade_confirmada_pct
FROM fila_inspecao
WHERE taxa_irregularidade_bairro >= 0.5
GROUP BY municipio, bairro
ORDER BY ucs_na_fila DESC
"""

QUERIES: dict[str, str | list[str]] = {
    "visao_360_uc": (
        "SELECT f.competencia, f.consumo_kwh, f.receita_faturada, "
        "f.status_pagamento FROM fact_faturamento f "
        "WHERE f.id_uc = '{id_uc}' ORDER BY f.competencia DESC LIMIT 2"
    ),
    "receita": RECEITA,
    "indicadores": [INDICADORES_JANELAS, INDICADORES_CLASSES],
    "continuidade": [CONTINUIDADE_ALIMENTADORES, CONTINUIDADE_CAUSAS],
    "fila_inspecao": [FILA_RESUMO, FILA_BAIRROS],
}

FONTES_POR_TELA = {
    "visao_360_uc": ["fact_faturamento"],
    "receita": ["agg_receita_preco_volume"],
    "indicadores": ["agg_receita_mensal"],
    "continuidade": ["agg_continuidade_alimentador", "fact_ocorrencias"],
    "fila_inspecao": ["fila_inspecao", "fact_inspecoes"],
}


def fontes_da_tela(tela: str) -> list[str]:
    """Devolve a lista de fontes fixas para a tela. Levanta ValueError se tela desconhecida."""
    try:
        return FONTES_POR_TELA[tela]
    except KeyError:
        raise ValueError(f"Tela de insight não suportada: {tela}")


def extrair_metricas(
    tela: str,
    id_uc: str,
    executor: SQLExecutor,
) -> list[Dict[str, Any]]:
    """Executa as consultas homologadas e reúne resumo e ranking nos fatos."""
    templates = QUERIES.get(tela)
    if templates is None:
        raise ValueError(f"Tela de insight não suportada: {tela}")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", id_uc):
        raise ValueError("Identificador de entidade inválido.")
    if isinstance(templates, str):
        templates = [templates]
    linhas: list[Dict[str, Any]] = []
    for template in templates:
        sql = template.format(id_uc=id_uc) if tela == "visao_360_uc" else template
        resultado = executor.executar(sql)
        if not resultado.sucesso:
            raise RuntimeError(f"Falha ao extrair métricas: {resultado.erro}")
        linhas.extend(resultado.linhas)
    return linhas
