-- Testes das permissões: simula cada perfil com SET ROLE e tenta o permitido e o proibido.
-- Rodar SEM parar no primeiro erro (sem ON_ERROR_STOP): os "permission denied" são esperados.
--   psql -h localhost -p 5433 -U postgres -d v_energy -f backend/sql/permissoes/99_testes.sql
-- UC132549 está na fila de inspeção; UC100005 não está.

\echo '========== OPERACAO =========='
SET ROLE perfil_operacao;

\echo '[ok] continuidade'
SELECT count(*) FROM agg_continuidade_alimentador;
\echo '[ok] filtros: municípios de todas as UCs (45000 linhas, sem filtro do RLS)'
SELECT count(municipio) FROM dim_unidade_consumidora;
\echo '[negado] nome do titular'
SELECT nome_titular FROM dim_unidade_consumidora LIMIT 1;
\echo '[negado] fila de inspeção'
SELECT count(*) FROM fila_inspecao;
\echo '[negado] leituras'
SELECT count(*) FROM fact_leituras;

RESET ROLE;

\echo '========== PERDAS =========='
SET ROLE perfil_perdas;

\echo '[ok] fila: 11586 UCs'
SELECT count(*) FROM fila_inspecao;
\echo '[ok] cadastro: só as 11586 UCs da fila, não as 45000 (RLS)'
SELECT count(*) FROM dim_unidade_consumidora;
\echo '[ok] Visão 360 de uma UC da fila: 1 linha'
SELECT id_uc, nome_titular, bairro FROM dim_unidade_consumidora WHERE id_uc = 'UC132549';
\echo '[ok, mas vazio] Visão 360 de uma UC fora da fila: 0 linhas, como se ela não existisse'
SELECT id_uc, nome_titular, bairro FROM dim_unidade_consumidora WHERE id_uc = 'UC100005';
\echo '[ok, mas 0] leituras de uma UC fora da fila'
SELECT count(*) FROM fact_leituras WHERE id_uc = 'UC100005';
\echo '[negado] CPF'
SELECT cpf_cnpj_mascarado FROM dim_unidade_consumidora LIMIT 1;
\echo '[negado] receita'
SELECT count(*) FROM agg_receita_mensal;

\echo '[ok] criar uma ordem (desfeita no ROLLBACK)'
BEGIN;
INSERT INTO ordens_inspecao (id_uc, status) VALUES ('UC132549', 'ABERTA') RETURNING id, id_uc, status;
ROLLBACK;
\echo '[negado] trocar a UC de uma ordem'
UPDATE ordens_inspecao SET id_uc = 'UC100005' WHERE false;
\echo '[negado] apagar ordem'
DELETE FROM ordens_inspecao WHERE false;

RESET ROLE;
