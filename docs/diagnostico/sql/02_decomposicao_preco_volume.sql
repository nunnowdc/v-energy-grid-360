-- Diagnóstico da receita · 02. Decomposição preço × volume
-- Fórmula da Gold (a mesma da tela de Receita), por segmento município × bairro × classe × GD:
--   efeito-volume = (kWh P1 − kWh P0) × preço P0
--   efeito-preço  = (preço P1 − preço P0) × kWh P1
--   efeito-volume + efeito-preço = receita P1 − receita P0 (exato)

-- Total
SELECT ROUND(SUM(receita_p1 - receita_p0)::numeric / 1e6, 2) AS variacao_receita_mi,
       ROUND(SUM(efeito_volume)::numeric / 1e6, 2) AS efeito_volume_mi,
       ROUND(SUM(efeito_preco)::numeric / 1e6, 2) AS efeito_preco_mi
FROM agg_receita_preco_volume;

-- Com e sem geração própria (painel solar)
SELECT possui_gd,
       SUM(ucs_p1) AS ucs_p1,
       ROUND(SUM(kwh_p0)::numeric / 1e6, 2) AS kwh_p0_mi,
       ROUND(SUM(kwh_p1)::numeric / 1e6, 2) AS kwh_p1_mi,
       ROUND((100 * (SUM(kwh_p1) / SUM(kwh_p0) - 1))::numeric, 1) AS variacao_volume_pct,
       ROUND(SUM(efeito_volume)::numeric / 1e6, 2) AS efeito_volume_mi,
       ROUND(SUM(efeito_preco)::numeric / 1e6, 2) AS efeito_preco_mi
FROM agg_receita_preco_volume
GROUP BY possui_gd
ORDER BY possui_gd;

-- Classe × geração própria
SELECT classe, possui_gd,
       SUM(ucs_p1) AS ucs_p1,
       ROUND((100 * (SUM(kwh_p1) / NULLIF(SUM(kwh_p0), 0) - 1))::numeric, 1) AS variacao_volume_pct,
       ROUND(SUM(efeito_volume)::numeric / 1e6, 2) AS efeito_volume_mi,
       ROUND(SUM(efeito_preco)::numeric / 1e6, 2) AS efeito_preco_mi
FROM agg_receita_preco_volume
GROUP BY classe, possui_gd
ORDER BY classe, possui_gd;

-- Preço médio efetivo por classe (R$/kWh, com tributos e bandeiras)
SELECT classe,
       ROUND((SUM(receita_p0) / SUM(kwh_p0))::numeric, 3) AS preco_p0,
       ROUND((SUM(receita_p1) / SUM(kwh_p1))::numeric, 3) AS preco_p1,
       ROUND((100 * ((SUM(receita_p1) / SUM(kwh_p1)) / (SUM(receita_p0) / SUM(kwh_p0)) - 1))::numeric, 1) AS variacao_preco_pct
FROM agg_receita_preco_volume
GROUP BY classe
ORDER BY SUM(receita_p1) DESC;
