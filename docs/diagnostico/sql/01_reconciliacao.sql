-- Diagnóstico da receita · 01. Reconciliação dos números de partida
-- Períodos (os mesmos da tela de Receita):
--   P0 = jul/2022 a jun/2023 (primeiro ano da base)
--   P1 = jul/2025 a jun/2026 (últimos 12 meses)
-- Receita = receita faturada, com tributos. Volume = consumo medido nas leituras (a fatura não tem kWh).

-- Totais dos dois períodos pela tabela mensal
SELECT CASE WHEN mes_referencia <= '2023-06' THEN 'P0' ELSE 'P1' END AS periodo,
       ROUND(SUM(receita_faturada)::numeric / 1e6, 2) AS receita_mi,
       ROUND(SUM(consumo_kwh)::numeric / 1e6, 2) AS kwh_mi,
       ROUND((SUM(receita_faturada) / SUM(consumo_kwh))::numeric, 4) AS preco_medio_kwh
FROM agg_receita_mensal
WHERE mes_referencia BETWEEN '2022-07' AND '2023-06'
   OR mes_referencia BETWEEN '2025-07' AND '2026-06'
GROUP BY 1
ORDER BY 1;

-- Os mesmos totais pela tabela da decomposição (devem bater com a consulta acima)
SELECT ROUND(SUM(receita_p0)::numeric / 1e6, 2) AS receita_p0_mi,
       ROUND(SUM(receita_p1)::numeric / 1e6, 2) AS receita_p1_mi,
       ROUND((100 * (SUM(receita_p1) / SUM(receita_p0) - 1))::numeric, 1) AS variacao_receita_pct,
       ROUND(SUM(kwh_p0)::numeric / 1e6, 2) AS kwh_p0_mi,
       ROUND(SUM(kwh_p1)::numeric / 1e6, 2) AS kwh_p1_mi,
       ROUND((100 * (SUM(kwh_p1) / SUM(kwh_p0) - 1))::numeric, 1) AS variacao_volume_pct,
       SUM(ucs_p0) AS ucs_p0,
       SUM(ucs_p1) AS ucs_p1
FROM agg_receita_preco_volume;

-- Peso dos tributos na receita faturada, por período
SELECT CASE WHEN mes_referencia <= '2023-06' THEN 'P0' ELSE 'P1' END AS periodo,
       ROUND((100 * SUM(tributos) / SUM(receita_faturada))::numeric, 2) AS tributos_pct
FROM fact_faturamento
WHERE mes_referencia BETWEEN '2022-07' AND '2023-06'
   OR mes_referencia BETWEEN '2025-07' AND '2026-06'
GROUP BY 1
ORDER BY 1;
