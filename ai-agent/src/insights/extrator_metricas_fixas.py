"""Consultas analíticas fixas usadas pelo pipeline de insights."""
from __future__ import annotations

import re
from typing import Any, Dict

from ..services.sql_executor import SQLExecutor

RECEITA = """
WITH p AS (
  SELECT possui_gd, receita_p0, receita_p1, kwh_p0, kwh_p1, ucs_p1, efeito_volume, efeito_preco,
         TO_DATE(SPLIT_PART(periodo_p0, ' a ', 1), 'YYYY-MM') AS p0_ini,
         TO_DATE(SPLIT_PART(periodo_p0, ' a ', 2), 'YYYY-MM') AS p0_fim,
         TO_DATE(SPLIT_PART(periodo_p1, ' a ', 1), 'YYYY-MM') AS p1_ini,
         TO_DATE(SPLIT_PART(periodo_p1, ' a ', 2), 'YYYY-MM') AS p1_fim
  FROM agg_receita_preco_volume),
m AS (SELECT ARRAY['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez'] AS nome)
SELECT CASE WHEN GROUPING(p.possui_gd) = 1 THEN 'todas as UCs'
            WHEN p.possui_gd THEN 'com geração própria' ELSE 'sem geração própria' END AS grupo,
       MAX(m.nome[EXTRACT(MONTH FROM p.p0_ini)::int] || '/' || EXTRACT(YEAR FROM p.p0_ini) || ' a '
           || m.nome[EXTRACT(MONTH FROM p.p0_fim)::int] || '/' || EXTRACT(YEAR FROM p.p0_fim)) AS periodo_base,
       MAX(m.nome[EXTRACT(MONTH FROM p.p1_ini)::int] || '/' || EXTRACT(YEAR FROM p.p1_ini) || ' a '
           || m.nome[EXTRACT(MONTH FROM p.p1_fim)::int] || '/' || EXTRACT(YEAR FROM p.p1_fim)) AS periodo_comparado,
       SUM(p.ucs_p1)::int AS ucs,
       CASE WHEN GROUPING(p.possui_gd) = 1 THEN ROUND(SUM(p.receita_p0)::numeric / 1e6, 1) END AS receita_base_milhoes,
       CASE WHEN GROUPING(p.possui_gd) = 1 THEN ROUND(SUM(p.receita_p1)::numeric / 1e6, 1) END AS receita_comparada_milhoes,
       CASE WHEN GROUPING(p.possui_gd) = 1
            THEN ROUND((100 * (SUM(p.receita_p1) / NULLIF(SUM(p.receita_p0), 0) - 1))::numeric, 1) END AS variacao_receita_pct,
       ROUND((100 * (SUM(p.kwh_p1) / NULLIF(SUM(p.kwh_p0), 0) - 1))::numeric, 1) AS variacao_consumo_medido_pct,
       CASE WHEN ABS(SUM(p.efeito_volume)) >= 1e6 THEN ROUND(SUM(p.efeito_volume)::numeric / 1e6, 1) END AS efeito_volume_milhoes,
       CASE WHEN ABS(SUM(p.efeito_volume)) < 1e6 THEN ROUND(SUM(p.efeito_volume)::numeric / 1e3, 1) END AS efeito_volume_mil,
       CASE WHEN ABS(SUM(p.efeito_preco)) >= 1e6 THEN ROUND(SUM(p.efeito_preco)::numeric / 1e6, 1) END AS efeito_preco_milhoes,
       CASE WHEN ABS(SUM(p.efeito_preco)) < 1e6 THEN ROUND(SUM(p.efeito_preco)::numeric / 1e3, 1) END AS efeito_preco_mil
FROM p, m
GROUP BY GROUPING SETS ((p.possui_gd), ())
ORDER BY GROUPING(p.possui_gd) DESC, p.possui_gd DESC
"""

INDICADORES_JANELAS = """
WITH lim AS (SELECT MAX(competencia) AS fim FROM agg_receita_mensal),
j AS (
  SELECT SUM(r.receita_faturada) FILTER (WHERE r.competencia > l.fim - INTERVAL '12 months') AS receita_atual,
         SUM(r.receita_faturada) FILTER (WHERE r.competencia <= l.fim - INTERVAL '12 months') AS receita_anterior,
         SUM(r.consumo_kwh) FILTER (WHERE r.competencia > l.fim - INTERVAL '12 months') AS kwh_atual,
         SUM(r.consumo_kwh) FILTER (WHERE r.competencia <= l.fim - INTERVAL '12 months') AS kwh_anterior,
         SUM(r.faturas_atrasadas) FILTER (WHERE r.competencia > l.fim - INTERVAL '12 months') AS atrasadas_atual,
         SUM(r.faturas) FILTER (WHERE r.competencia > l.fim - INTERVAL '12 months') AS faturas_atual,
         SUM(r.faturas_atrasadas) FILTER (WHERE r.competencia <= l.fim - INTERVAL '12 months') AS atrasadas_anterior,
         SUM(r.faturas) FILTER (WHERE r.competencia <= l.fim - INTERVAL '12 months') AS faturas_anterior,
         TO_CHAR(MIN(r.competencia) FILTER (WHERE r.competencia > l.fim - INTERVAL '12 months'), 'MM/YYYY') AS inicio,
         TO_CHAR(MAX(r.competencia), 'MM/YYYY') AS fim
  FROM agg_receita_mensal r, lim l
  WHERE r.competencia > l.fim - INTERVAL '24 months')
SELECT 'últimos 12 meses contra os 12 anteriores' AS comparacao, inicio, fim,
       ROUND(receita_atual::numeric / 1e6, 1) AS receita_milhoes,
       ROUND((100 * (receita_atual / NULLIF(receita_anterior, 0) - 1))::numeric, 1) AS variacao_receita_pct,
       ROUND(kwh_atual::numeric / 1e6, 1) AS consumo_gwh,
       ROUND((100 * (kwh_atual / NULLIF(kwh_anterior, 0) - 1))::numeric, 1) AS variacao_consumo_pct,
       ROUND((100.0 * atrasadas_atual / NULLIF(faturas_atual, 0))::numeric, 1) AS faturas_atrasadas_pct,
       ROUND((100.0 * atrasadas_anterior / NULLIF(faturas_anterior, 0))::numeric, 1) AS faturas_atrasadas_anterior_pct
FROM j
"""

INDICADORES_CLASSES = """
WITH lim AS (SELECT MAX(competencia) AS fim FROM agg_receita_mensal),
c AS (
  SELECT r.classe,
         SUM(r.receita_faturada) FILTER (WHERE r.competencia > l.fim - INTERVAL '12 months') AS atual,
         SUM(r.receita_faturada) FILTER (WHERE r.competencia <= l.fim - INTERVAL '12 months') AS anterior
  FROM agg_receita_mensal r, lim l
  WHERE r.competencia > l.fim - INTERVAL '24 months'
  GROUP BY r.classe)
SELECT CASE classe WHEN 'PODER_PUBLICO' THEN 'poder público' ELSE LOWER(REPLACE(classe, '_', ' ')) END AS classe,
       ROUND(atual::numeric / 1e6, 1) AS receita_ultimos_12m_milhoes,
       ROUND((atual - anterior)::numeric / 1e6, 1) AS variacao_receita_milhoes,
       ROUND((100 * (atual / NULLIF(anterior, 0) - 1))::numeric, 1) AS variacao_receita_pct
FROM c
ORDER BY ABS(atual - anterior) DESC NULLS LAST, classe
LIMIT 3
"""

CONTINUIDADE_ALIMENTADORES = """
WITH lim AS (SELECT MAX(competencia) AS fim FROM agg_continuidade_alimentador),
a AS (
  SELECT c.alimentador, MAX(c.municipio_principal) AS municipio, MAX(c.total_ucs) AS total_ucs,
         TO_CHAR(MIN(c.competencia), 'MM/YYYY') AS inicio, TO_CHAR(MAX(c.competencia), 'MM/YYYY') AS fim,
         ROUND(SUM(c.dec)::numeric, 1) AS dec_horas,
         ROUND(SUM(c.dec_sem_dia_critico)::numeric, 1) AS dec_sem_dias_criticos_horas,
         ROUND(SUM(c.fec)::numeric, 1) AS fec_vezes
  FROM agg_continuidade_alimentador c, lim l
  WHERE c.competencia > l.fim - INTERVAL '12 months'
  GROUP BY c.alimentador)
(SELECT 'maior DEC entre todos' AS destaque, * FROM a ORDER BY dec_horas DESC LIMIT 1)
UNION ALL
(SELECT 'maior DEC com 100 UCs ou mais', * FROM a WHERE total_ucs >= 100 ORDER BY dec_horas DESC LIMIT 1)
UNION ALL
(SELECT 'maior DEC com 100 UCs ou mais, sem os dias críticos', * FROM a
  WHERE total_ucs >= 100 ORDER BY dec_sem_dias_criticos_horas DESC LIMIT 1)
"""

CONTINUIDADE_CAUSAS = """
WITH lim AS (SELECT MAX(competencia) AS fim FROM fact_ocorrencias),
o AS (SELECT o.* FROM fact_ocorrencias o, lim l WHERE o.competencia > l.fim - INTERVAL '12 months')
SELECT 'toda a rede' AS abrangencia,
       CASE REPLACE(o.causa, '_', ' ') WHEN 'CLIMATICA' THEN 'climática' WHEN 'VEGETACAO' THEN 'vegetação'
                    WHEN 'NAO IDENTIFICADA' THEN 'não identificada' WHEN 'NAO INFORMADA' THEN 'não informada'
                    ELSE LOWER(REPLACE(o.causa, '_', ' ')) END AS causa,
       ROUND((100.0 * COUNT(*) / NULLIF(SUM(COUNT(*)) OVER (), 0))::numeric, 1) AS pct_das_ucs_interrompidas,
       ROUND((100.0 * SUM(o.duracao_h) / NULLIF(SUM(SUM(o.duracao_h)) OVER (), 0))::numeric, 1) AS pct_das_horas
FROM o
GROUP BY o.causa
ORDER BY COUNT(*) DESC
LIMIT 3
"""

CONTINUIDADE_DIAS_CRITICOS = """
WITH lim AS (SELECT MAX(competencia) AS fim FROM fact_ocorrencias),
o AS (SELECT o.* FROM fact_ocorrencias o, lim l WHERE o.competencia > l.fim - INTERVAL '12 months')
SELECT 'toda a rede' AS abrangencia,
       COUNT(DISTINCT o.data_abertura::date) FILTER (WHERE o.dia_critico) AS dias_criticos,
       TO_CHAR(MIN(o.data_abertura) FILTER (WHERE o.dia_critico), 'MM/YYYY') AS inicio_dias_criticos,
       TO_CHAR(MAX(o.data_abertura) FILTER (WHERE o.dia_critico), 'MM/YYYY') AS fim_dias_criticos,
       ROUND((100.0 * SUM(o.duracao_h) FILTER (WHERE o.dia_critico) / NULLIF(SUM(o.duracao_h), 0))::numeric, 1)
         AS pct_das_horas_em_dias_criticos
FROM o
"""

FILA_RESUMO = """
WITH criticos AS (
  SELECT COUNT(DISTINCT (municipio, bairro)) AS bairros, COUNT(*) AS ucs, SUM(kwh_recuperavel_estimado_ano) AS kwh
  FROM fila_inspecao WHERE taxa_irregularidade_bairro >= 0.5),
fila AS (
  SELECT COUNT(*) AS ucs, SUM(kwh_recuperavel_estimado_ano) AS kwh, MAX(data_referencia) AS ref
  FROM fila_inspecao)
SELECT TO_CHAR(f.ref, 'MM/YYYY') AS fila_de,
       f.ucs AS ucs_na_fila,
       ROUND(f.kwh::numeric / 1e6, 1) AS gwh_recuperavel_ano,
       c.bairros AS bairros_criticos,
       50 AS criterio_bairro_critico_irregularidade_minima_pct,
       c.ucs AS ucs_em_bairros_criticos,
       ROUND((100.0 * c.kwh / NULLIF(f.kwh, 0))::numeric, 1) AS pct_da_energia_em_bairros_criticos
FROM fila f, criticos c
"""

FILA_BAIRROS = """
SELECT municipio, bairro,
       COUNT(*) AS ucs_na_fila,
       ROUND(SUM(kwh_recuperavel_estimado_ano)::numeric / 1e3, 1) AS mwh_recuperavel_ano,
       ROUND(MAX(taxa_irregularidade_bairro)::numeric * 100, 1) AS irregularidade_confirmada_no_bairro_pct
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
    "continuidade": [CONTINUIDADE_ALIMENTADORES, CONTINUIDADE_CAUSAS, CONTINUIDADE_DIAS_CRITICOS],
    "fila_inspecao": [FILA_RESUMO, FILA_BAIRROS],
}

FONTES_POR_TELA = {
    "visao_360_uc": ["fact_faturamento"],
    "receita": ["agg_receita_preco_volume"],
    "indicadores": ["agg_receita_mensal"],
    "continuidade": ["agg_continuidade_alimentador", "fact_ocorrencias"],
    "fila_inspecao": ["fila_inspecao"],
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
