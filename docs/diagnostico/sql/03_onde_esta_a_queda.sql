-- Diagnóstico da receita · 03. Onde está a queda de volume
-- Efeito-volume por município e por bairro, separando as UCs com e sem geração própria.

-- Municípios, do maior efeito-volume negativo para o menor
SELECT municipio,
       ROUND(SUM(efeito_volume)::numeric / 1e6, 2) AS efeito_volume_mi,
       ROUND((SUM(efeito_volume) FILTER (WHERE possui_gd))::numeric / 1e6, 2) AS efeito_volume_com_gd_mi,
       ROUND((SUM(efeito_volume) FILTER (WHERE NOT possui_gd))::numeric / 1e6, 2) AS efeito_volume_sem_gd_mi,
       SUM(ucs_p1) FILTER (WHERE possui_gd) AS ucs_com_gd
FROM agg_receita_preco_volume
GROUP BY municipio
ORDER BY 2;

-- Os 10 bairros com maior efeito-volume negativo
SELECT municipio, bairro,
       ROUND(SUM(efeito_volume)::numeric / 1e6, 2) AS efeito_volume_mi,
       ROUND((SUM(efeito_volume) FILTER (WHERE possui_gd))::numeric / 1e6, 2) AS efeito_volume_com_gd_mi,
       SUM(ucs_p1) FILTER (WHERE possui_gd) AS ucs_com_gd
FROM agg_receita_preco_volume
GROUP BY municipio, bairro
ORDER BY 3
LIMIT 10;

-- Bairros com irregularidade alta nas inspeções de campo (pelo menos 50 inspeções e 50% de irregularidade)
SELECT u.municipio, u.bairro,
       COUNT(*) AS inspecoes,
       ROUND((100.0 * COUNT(*) FILTER (WHERE i.resultado ILIKE '%confirmada%') / COUNT(*))::numeric, 1) AS irregularidade_pct
FROM fact_inspecoes AS i
JOIN dim_unidade_consumidora AS u USING (id_uc)
GROUP BY u.municipio, u.bairro
HAVING COUNT(*) >= 50
   AND COUNT(*) FILTER (WHERE i.resultado ILIKE '%confirmada%') >= 0.5 * COUNT(*)
ORDER BY irregularidade_pct DESC;

-- UCs sem geração própria: bairros com irregularidade alta × resto da base
WITH bairros_irregulares AS (
    SELECT u.municipio, u.bairro
    FROM fact_inspecoes AS i
    JOIN dim_unidade_consumidora AS u USING (id_uc)
    GROUP BY u.municipio, u.bairro
    HAVING COUNT(*) >= 50
       AND COUNT(*) FILTER (WHERE i.resultado ILIKE '%confirmada%') >= 0.5 * COUNT(*)
)
SELECT CASE WHEN b.bairro IS NULL THEN 'resto da base' ELSE 'bairros com irregularidade alta' END AS grupo,
       SUM(a.ucs_p1) AS ucs_p1,
       ROUND((100 * (SUM(a.kwh_p1) / SUM(a.kwh_p0) - 1))::numeric, 1) AS variacao_volume_pct,
       ROUND(SUM(a.efeito_volume)::numeric / 1e6, 2) AS efeito_volume_mi
FROM agg_receita_preco_volume AS a
LEFT JOIN bairros_irregulares AS b USING (municipio, bairro)
WHERE NOT a.possui_gd
GROUP BY 1
ORDER BY 1;

-- Bairros com irregularidade alta, UCs sem geração própria, por classe: consumo médio por UC no ano
WITH bairros_irregulares AS (
    SELECT u.municipio, u.bairro
    FROM fact_inspecoes AS i
    JOIN dim_unidade_consumidora AS u USING (id_uc)
    GROUP BY u.municipio, u.bairro
    HAVING COUNT(*) >= 50
       AND COUNT(*) FILTER (WHERE i.resultado ILIKE '%confirmada%') >= 0.5 * COUNT(*)
)
SELECT a.classe,
       SUM(a.ucs_p1) AS ucs_p1,
       ROUND((SUM(a.kwh_p0) / SUM(a.ucs_p0))::numeric, 0) AS kwh_por_uc_p0,
       ROUND((SUM(a.kwh_p1) / SUM(a.ucs_p1))::numeric, 0) AS kwh_por_uc_p1,
       ROUND((100 * (SUM(a.kwh_p1) / SUM(a.kwh_p0) - 1))::numeric, 1) AS variacao_volume_pct,
       ROUND(SUM(a.efeito_volume)::numeric / 1e6, 2) AS efeito_volume_mi
FROM agg_receita_preco_volume AS a
JOIN bairros_irregulares AS b USING (municipio, bairro)
WHERE NOT a.possui_gd
GROUP BY a.classe
ORDER BY efeito_volume_mi;

-- Quando a queda começou: consumo mensal desses bairros (sem geração própria) ÷ mesmo mês do ano anterior
WITH bairros_irregulares AS (
    SELECT u.municipio, u.bairro
    FROM fact_inspecoes AS i
    JOIN dim_unidade_consumidora AS u USING (id_uc)
    GROUP BY u.municipio, u.bairro
    HAVING COUNT(*) >= 50
       AND COUNT(*) FILTER (WHERE i.resultado ILIKE '%confirmada%') >= 0.5 * COUNT(*)
)
SELECT l.mes_referencia,
       ROUND((SUM(l.consumo_kwh) / NULLIF(SUM(l.consumo_ano_anterior_kwh), 0))::numeric, 2) AS razao_ano_anterior
FROM fact_leituras AS l
JOIN dim_unidade_consumidora AS u USING (id_uc)
JOIN bairros_irregulares AS b ON b.municipio = u.municipio AND b.bairro = u.bairro
WHERE NOT u.possui_gd AND l.mes_referencia >= '2024-07'
GROUP BY l.mes_referencia
ORDER BY l.mes_referencia;

-- Concentração: bairros com efeito-volume negativo e quanto os 20 piores somam
WITH bairros AS (
    SELECT municipio, bairro, SUM(efeito_volume) AS efeito_volume
    FROM agg_receita_preco_volume
    GROUP BY municipio, bairro
)
SELECT COUNT(*) AS bairros,
       COUNT(*) FILTER (WHERE efeito_volume < 0) AS bairros_com_queda,
       ROUND((SUM(efeito_volume) FILTER (WHERE efeito_volume < 0))::numeric / 1e6, 2) AS queda_total_mi,
       ROUND((SELECT SUM(efeito_volume) FROM (SELECT efeito_volume FROM bairros ORDER BY efeito_volume LIMIT 20) AS piores)::numeric / 1e6, 2) AS queda_20_piores_mi
FROM bairros;
