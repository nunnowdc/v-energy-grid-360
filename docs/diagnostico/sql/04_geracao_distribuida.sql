-- Diagnóstico da receita · 04. Geração própria (painel solar): quando e quanto
-- A data de ligação do painel vem de dim_unidade_consumidora.data_conexao_gd.

-- Ligações por semestre
SELECT EXTRACT(YEAR FROM data_conexao_gd::date)::int AS ano,
       CASE WHEN EXTRACT(MONTH FROM data_conexao_gd::date) <= 6 THEN '1º semestre' ELSE '2º semestre' END AS semestre,
       COUNT(*) AS ucs_ligadas
FROM dim_unidade_consumidora
WHERE possui_gd
GROUP BY 1, 2
ORDER BY 1, 2;

-- Consumo das UCs com painel nos meses em torno da ligação (mês 0 = mês da ligação).
-- "razao" compara com o mesmo mês do ano anterior das mesmas UCs, o que tira a sazonalidade:
-- 1,00 = consumo igual ao do ano anterior.
WITH ligacao AS (
    SELECT id_uc, date_trunc('month', data_conexao_gd::date)::date AS mes_ligacao
    FROM dim_unidade_consumidora
    WHERE possui_gd AND data_conexao_gd IS NOT NULL
), leituras AS (
    SELECT (EXTRACT(YEAR FROM age(l.competencia::date, g.mes_ligacao)) * 12
            + EXTRACT(MONTH FROM age(l.competencia::date, g.mes_ligacao)))::int AS mes_relativo,
           l.consumo_kwh, l.consumo_ano_anterior_kwh
    FROM fact_leituras AS l
    JOIN ligacao AS g USING (id_uc)
)
SELECT mes_relativo,
       COUNT(*) AS leituras,
       ROUND(AVG(consumo_kwh)::numeric, 0) AS kwh_medio,
       ROUND(AVG(consumo_ano_anterior_kwh)::numeric, 0) AS kwh_medio_ano_anterior,
       ROUND((SUM(consumo_kwh) FILTER (WHERE consumo_ano_anterior_kwh IS NOT NULL)
              / NULLIF(SUM(consumo_ano_anterior_kwh), 0))::numeric, 2) AS razao
FROM leituras
WHERE mes_relativo BETWEEN -6 AND 11
GROUP BY mes_relativo
ORDER BY mes_relativo;

-- Consumo médio mensal por UC: 6 meses antes da ligação × meses 1 a 11 depois
WITH ligacao AS (
    SELECT id_uc, date_trunc('month', data_conexao_gd::date)::date AS mes_ligacao
    FROM dim_unidade_consumidora
    WHERE possui_gd AND data_conexao_gd IS NOT NULL
), leituras AS (
    SELECT (EXTRACT(YEAR FROM age(l.competencia::date, g.mes_ligacao)) * 12
            + EXTRACT(MONTH FROM age(l.competencia::date, g.mes_ligacao)))::int AS mes_relativo,
           l.consumo_kwh
    FROM fact_leituras AS l
    JOIN ligacao AS g USING (id_uc)
)
SELECT ROUND((AVG(consumo_kwh) FILTER (WHERE mes_relativo BETWEEN -6 AND -1))::numeric, 0) AS kwh_mes_antes,
       ROUND((AVG(consumo_kwh) FILTER (WHERE mes_relativo BETWEEN 1 AND 11))::numeric, 0) AS kwh_mes_depois
FROM leituras;

-- UCs que ligaram o painel dentro de P1 (jul/2025 a jun/2026) e quantos meses de P1 elas ainda
-- consumiram sem painel. Essa parte da queda ainda não apareceu na receita e vai aparecer nos próximos 12 meses.
SELECT COUNT(*) AS ucs_ligadas_em_p1,
       SUM((EXTRACT(YEAR FROM age(date_trunc('month', data_conexao_gd::date), DATE '2025-07-01')) * 12
            + EXTRACT(MONTH FROM age(date_trunc('month', data_conexao_gd::date), DATE '2025-07-01')))::int) AS meses_de_p1_sem_painel
FROM dim_unidade_consumidora
WHERE possui_gd AND data_conexao_gd::date >= DATE '2025-07-01';
