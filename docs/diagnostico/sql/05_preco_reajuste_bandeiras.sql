-- Diagnóstico da receita · 05. Preço: reajuste tarifário e bandeiras
-- O acréscimo da bandeira está embutido no valor da energia da fatura (dicionário da Gold),
-- então o preço médio efetivo já inclui as bandeiras.

-- Preço médio mês a mês das UCs residenciais sem geração própria (o grupo do reajuste de 10,5% do case)
SELECT mes_referencia, bandeira_tarifaria,
       ROUND((SUM(receita_faturada) / SUM(consumo_kwh))::numeric, 4) AS preco_kwh
FROM agg_receita_mensal
WHERE classe = 'RESIDENCIAL' AND NOT possui_gd
GROUP BY mes_referencia, bandeira_tarifaria
ORDER BY mes_referencia;

-- Meses de cada bandeira nos dois períodos
SELECT CASE WHEN mes_referencia <= '2023-06' THEN 'P0' ELSE 'P1' END AS periodo,
       bandeira_tarifaria,
       COUNT(DISTINCT mes_referencia) AS meses
FROM agg_receita_mensal
WHERE mes_referencia BETWEEN '2022-07' AND '2023-06'
   OR mes_referencia BETWEEN '2025-07' AND '2026-06'
GROUP BY 1, 2
ORDER BY 1, 2;

-- Quanto as bandeiras somaram à receita de P1 (estimativa).
-- Cada mês não verde de P1 é recalculado com o preço médio dos meses verdes de P1 da mesma classe
-- e do mesmo grupo de geração própria. P0 teve só bandeira verde.
WITH p1 AS (
    SELECT * FROM agg_receita_mensal WHERE mes_referencia BETWEEN '2025-07' AND '2026-06'
), preco_verde AS (
    SELECT classe, possui_gd, SUM(receita_faturada) / SUM(consumo_kwh) AS preco
    FROM p1
    WHERE bandeira_tarifaria = 'VERDE'
    GROUP BY classe, possui_gd
)
SELECT ROUND(SUM(p1.receita_faturada)::numeric / 1e6, 2) AS receita_p1_mi,
       ROUND(SUM(CASE WHEN p1.bandeira_tarifaria = 'VERDE' THEN p1.receita_faturada
                      ELSE p1.consumo_kwh * v.preco END)::numeric / 1e6, 2) AS receita_p1_sem_bandeira_mi,
       ROUND(SUM(CASE WHEN p1.bandeira_tarifaria = 'VERDE' THEN 0
                      ELSE p1.receita_faturada - p1.consumo_kwh * v.preco END)::numeric / 1e6, 2) AS receita_das_bandeiras_mi
FROM p1
JOIN preco_verde AS v USING (classe, possui_gd);
