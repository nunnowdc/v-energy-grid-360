-- Diagnóstico da receita · 06. Hipóteses descartadas e parâmetros das recomendações

-- Inadimplência por período: parte da receita faturada que está atrasada
SELECT CASE WHEN mes_referencia <= '2023-06' THEN 'P0' ELSE 'P1' END AS periodo,
       ROUND((SUM(receita_faturada) FILTER (WHERE status_pagamento = 'ATRASADA'))::numeric / 1e6, 2) AS atrasada_mi,
       ROUND((100 * SUM(receita_faturada) FILTER (WHERE status_pagamento = 'ATRASADA') / SUM(receita_faturada))::numeric, 1) AS atrasada_pct
FROM fact_faturamento
WHERE mes_referencia BETWEEN '2022-07' AND '2023-06'
   OR mes_referencia BETWEEN '2025-07' AND '2026-06'
GROUP BY 1
ORDER BY 1;

-- Estoque de faturas atrasadas em toda a base
SELECT ROUND(SUM(receita_faturada)::numeric / 1e6, 2) AS atrasada_mi,
       COUNT(*) AS faturas_atrasadas,
       COUNT(DISTINCT id_uc) AS ucs
FROM fact_faturamento
WHERE status_pagamento = 'ATRASADA';

-- Inspeções de campo (ago a dez/2025): quantidade, taxa de irregularidade e kWh recuperado por irregularidade
SELECT COUNT(*) AS inspecoes,
       COUNT(*) FILTER (WHERE resultado ILIKE '%confirmada%') AS irregulares,
       ROUND((100.0 * COUNT(*) FILTER (WHERE resultado ILIKE '%confirmada%') / COUNT(*))::numeric, 1) AS taxa_irregularidade_pct,
       ROUND((AVG(kwh_recuperado::numeric) FILTER (WHERE resultado ILIKE '%confirmada%')), 0) AS kwh_recuperado_medio
FROM fact_inspecoes;

-- Fila de inspeção: UCs e energia estimada a recuperar por ano, nos bairros com irregularidade alta e no resto
WITH bairros_irregulares AS (
    SELECT u.municipio, u.bairro
    FROM fact_inspecoes AS i
    JOIN dim_unidade_consumidora AS u USING (id_uc)
    GROUP BY u.municipio, u.bairro
    HAVING COUNT(*) >= 50
       AND COUNT(*) FILTER (WHERE i.resultado ILIKE '%confirmada%') >= 0.5 * COUNT(*)
)
SELECT CASE WHEN b.bairro IS NULL THEN 'resto da base' ELSE 'bairros com irregularidade alta' END AS grupo,
       COUNT(*) AS ucs_na_fila,
       ROUND(SUM(f.kwh_recuperavel_estimado_ano)::numeric / 1e6, 2) AS kwh_recuperavel_ano_mi
FROM fila_inspecao AS f
LEFT JOIN bairros_irregulares AS b USING (municipio, bairro)
GROUP BY 1
ORDER BY 1;

-- Inspeções por grupo de bairro: quantidade e taxa de irregularidade
WITH bairros_irregulares AS (
    SELECT u.municipio, u.bairro
    FROM fact_inspecoes AS i
    JOIN dim_unidade_consumidora AS u USING (id_uc)
    GROUP BY u.municipio, u.bairro
    HAVING COUNT(*) >= 50
       AND COUNT(*) FILTER (WHERE i.resultado ILIKE '%confirmada%') >= 0.5 * COUNT(*)
)
SELECT CASE WHEN b.bairro IS NULL THEN 'resto da base' ELSE 'bairros com irregularidade alta' END AS grupo,
       COUNT(*) AS inspecoes,
       ROUND((100.0 * COUNT(*) FILTER (WHERE i.resultado ILIKE '%confirmada%') / COUNT(*))::numeric, 1) AS irregularidade_pct
FROM fact_inspecoes AS i
JOIN dim_unidade_consumidora AS u USING (id_uc)
LEFT JOIN bairros_irregulares AS b ON b.municipio = u.municipio AND b.bairro = u.bairro
GROUP BY 1
ORDER BY 1;

-- UCs com irregularidade confirmada: o consumo voltou depois da inspeção?
-- Consumo médio mensal nos 3 meses antes e nos meses 1 a 6 depois, ao lado do mesmo mês do ano anterior
WITH irregulares AS (
    SELECT id_uc, date_trunc('month', data_inspecao::date)::date AS mes_inspecao
    FROM fact_inspecoes
    WHERE resultado ILIKE '%confirmada%' AND data_inspecao IS NOT NULL
), leituras AS (
    SELECT (EXTRACT(YEAR FROM age(l.competencia::date, i.mes_inspecao)) * 12
            + EXTRACT(MONTH FROM age(l.competencia::date, i.mes_inspecao)))::int AS mes_relativo,
           l.consumo_kwh, l.consumo_ano_anterior_kwh
    FROM fact_leituras AS l
    JOIN irregulares AS i USING (id_uc)
)
SELECT CASE WHEN mes_relativo < 0 THEN '1. antes (3 meses)' ELSE '2. depois (meses 1 a 6)' END AS momento,
       ROUND(AVG(consumo_kwh)::numeric, 0) AS kwh_medio,
       ROUND(AVG(consumo_ano_anterior_kwh)::numeric, 0) AS kwh_medio_ano_anterior
FROM leituras
WHERE mes_relativo BETWEEN -3 AND -1 OR mes_relativo BETWEEN 1 AND 6
GROUP BY 1
ORDER BY 1;

-- UCs com irregularidade confirmada: consumo médio mensal no período base e nos últimos 3 meses da base
SELECT COUNT(DISTINCT l.id_uc) AS ucs,
       ROUND((AVG(l.consumo_kwh) FILTER (WHERE l.mes_referencia BETWEEN '2022-07' AND '2023-06'))::numeric, 0) AS kwh_mes_p0,
       ROUND((AVG(l.consumo_kwh) FILTER (WHERE l.mes_referencia BETWEEN '2026-04' AND '2026-06'))::numeric, 0) AS kwh_mes_abr_jun_2026
FROM fact_leituras AS l
WHERE l.id_uc IN (SELECT id_uc FROM fact_inspecoes WHERE resultado ILIKE '%confirmada%');
