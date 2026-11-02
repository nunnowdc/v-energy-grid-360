-- Testes das permissões: simula cada perfil com SET ROLE e tenta o permitido e o proibido.
-- Rodar SEM parar no primeiro erro (sem ON_ERROR_STOP): os "permission denied" são esperados.
-- Só no banco local de desenvolvimento: os testes de ordens escrevem (desfeito no ROLLBACK).
--   psql -h localhost -p 5433 -U postgres -d v_energy -f backend/sql/permissoes/99_testes.sql
-- UC132549 está na fila de inspeção; UC100005 não está.

\echo '========== OPERACAO =========='
SET ROLE perfil_operacao;

\echo '[ok] continuidade'
SELECT count(*) FROM agg_continuidade_alimentador;
\echo '[ok] filtros: municípios de todas as UCs (45000 linhas)'
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

\echo '[ok] fila: 11586 UCs, com as colunas da tela'
SELECT count(*), max(data_referencia) FROM fila_inspecao;
SELECT prioridade, id_uc, score, motivo_suspeita, municipio, bairro, classe
  FROM fila_inspecao ORDER BY prioridade LIMIT 1;
\echo '[negado] nome na fila'
SELECT nome_titular FROM fila_inspecao LIMIT 1;
\echo '[ok] filtros: municípios de todas as UCs (45000 linhas)'
SELECT count(municipio) FROM dim_unidade_consumidora;
\echo '[negado] CPF'
SELECT cpf_cnpj_mascarado FROM dim_unidade_consumidora LIMIT 1;
\echo '[ok] Visão 360: cadastro com nome e endereço'
SELECT id_uc, nome_titular, logradouro, numero, bairro, municipio, tipo_medidor_atual, possui_gd
  FROM dim_unidade_consumidora WHERE id_uc = 'UC132549';
\echo '[ok] Visão 360: leituras, faturas, ocorrências e chamados da UC'
SELECT (SELECT count(*) FROM fact_leituras     WHERE id_uc = 'UC132549') AS leituras,
       (SELECT count(*) FROM fact_faturamento  WHERE id_uc = 'UC132549') AS faturas,
       (SELECT count(*) FROM fact_ocorrencias  WHERE id_uc = 'UC132549') AS ocorrencias,
       (SELECT count(*) FROM fact_atendimentos WHERE id_uc = 'UC132549') AS chamados;
\echo '[ok] Visão 360 de uma UC fora da fila'
SELECT id_uc, nome_titular, logradouro FROM dim_unidade_consumidora WHERE id_uc = 'UC100005';
SELECT count(*) FROM fact_leituras WHERE id_uc = 'UC100005';
\echo '[negado] histórico de inspeções'
SELECT count(*) FROM fact_inspecoes;
\echo '[negado] receita'
SELECT count(*) FROM agg_receita_mensal;

\echo '[ok] criar e cancelar uma ordem (desfeito no ROLLBACK)'
BEGIN;
INSERT INTO ordens_inspecao (id_uc, status) VALUES ('UC132549', 'ABERTA') RETURNING id, id_uc, status;
UPDATE ordens_inspecao SET status = 'CANCELADA', atualizada_em = now() WHERE id_uc = 'UC132549';
ROLLBACK;
\echo '[negado pelo trigger] ordem para UC fora da fila (dentro de ROLLBACK)'
BEGIN;
INSERT INTO ordens_inspecao (id_uc, status) VALUES ('UC100005', 'ABERTA');
ROLLBACK;
\echo '[negado] trocar a UC de uma ordem'
UPDATE ordens_inspecao SET id_uc = 'UC100005' WHERE false;
\echo '[negado] apagar ordem'
DELETE FROM ordens_inspecao WHERE false;

RESET ROLE;

\echo '========== ADMIN_TI =========='
SET ROLE perfil_admin_ti;

\echo '[ok] receita'
SELECT count(*) FROM agg_receita_preco_volume;
\echo '[ok] cadastro: as 45000 UCs'
SELECT count(*) FROM dim_unidade_consumidora;
\echo '[ok] CPF'
SELECT cpf_cnpj_mascarado FROM dim_unidade_consumidora LIMIT 1;
\echo '[ok] leituras de uma UC fora da fila'
SELECT count(*) FROM fact_leituras WHERE id_uc = 'UC100005';
\echo '[ok] tabelas sem tela (só o agente)'
SELECT count(*) FROM fact_inspecoes;

\echo '[ok] criar uma ordem (desfeita no ROLLBACK)'
BEGIN;
INSERT INTO ordens_inspecao (id_uc, status) VALUES ('UC132549', 'ABERTA') RETURNING id, id_uc, status;
ROLLBACK;
\echo '[negado] apagar ordem'
DELETE FROM ordens_inspecao WHERE false;
\echo '[negado] escrever na Gold'
UPDATE fila_inspecao SET score = 0 WHERE false;

RESET ROLE;

\echo '========== DIRETORIA =========='
SET ROLE perfil_diretoria;

\echo '[ok] receita'
SELECT count(*) FROM agg_receita_mensal;
SELECT count(*) FROM agg_receita_preco_volume;
\echo '[ok] continuidade'
SELECT count(*) FROM agg_continuidade_alimentador;
SELECT count(*) FROM agg_continuidade_alimentador_anual;
\echo '[ok] filtros: municípios, bairros, classes e alimentadores (45000 linhas)'
SELECT count(municipio), count(bairro), count(classe), count(alimentador) FROM dim_unidade_consumidora;
\echo '[ok] filtros: as consultas do GET /api/filters/options (filters.py)'
SELECT count(DISTINCT (competencia, mes_referencia)) FROM dim_competencia WHERE mes_referencia IS NOT NULL;
SELECT count(*) FROM (SELECT DISTINCT municipio, bairro FROM dim_unidade_consumidora WHERE municipio IS NOT NULL) f;
SELECT count(*) FROM (SELECT DISTINCT classe FROM dim_unidade_consumidora WHERE classe IS NOT NULL) f;
SELECT count(*) FROM (SELECT DISTINCT alimentador FROM dim_alimentador WHERE alimentador IS NOT NULL) f;
SELECT count(*) FROM (SELECT DISTINCT alimentador, municipio FROM dim_unidade_consumidora
                       WHERE alimentador IS NOT NULL AND municipio IS NOT NULL) f;
SELECT count(*) FROM (SELECT DISTINCT causa FROM fact_ocorrencias WHERE causa IS NOT NULL) f;
\echo '[negado] nome do titular'
SELECT nome_titular FROM dim_unidade_consumidora LIMIT 1;
\echo '[negado] CPF'
SELECT cpf_cnpj_mascarado FROM dim_unidade_consumidora LIMIT 1;
\echo '[negado] fila de inspeção'
SELECT count(*) FROM fila_inspecao;
\echo '[negado] leituras'
SELECT count(*) FROM fact_leituras;
\echo '[negado] chamados'
SELECT count(*) FROM fact_atendimentos;
\echo '[negado] ordens de inspeção'
SELECT count(*) FROM ordens_inspecao;
\echo '[negado] escrever na Gold'
UPDATE agg_receita_mensal SET receita_faturada = 0 WHERE false;

RESET ROLE;

\echo '========== ATENDIMENTO =========='
SET ROLE perfil_atendimento;

\echo '[ok] Visão 360: cadastro com nome e endereço'
SELECT id_uc, nome_titular, logradouro, numero, bairro, municipio, tipo_medidor_atual, possui_gd
  FROM dim_unidade_consumidora WHERE id_uc = 'UC132549';
\echo '[ok] Visão 360: calendário, leituras, faturas, ocorrências e chamados da UC'
SELECT count(*) FROM dim_competencia;
SELECT (SELECT count(*) FROM fact_leituras     WHERE id_uc = 'UC132549') AS leituras,
       (SELECT count(*) FROM fact_faturamento  WHERE id_uc = 'UC132549') AS faturas,
       (SELECT count(*) FROM fact_ocorrencias  WHERE id_uc = 'UC132549') AS ocorrencias,
       (SELECT count(*) FROM fact_atendimentos WHERE id_uc = 'UC132549') AS chamados;
\echo '[ok] Visão 360 de uma UC fora da fila'
SELECT id_uc, nome_titular, logradouro FROM dim_unidade_consumidora WHERE id_uc = 'UC100005';
SELECT count(*) FROM fact_leituras WHERE id_uc = 'UC100005';
\echo '[ok] filtros: as consultas do GET /api/filters/options (filters.py)'
SELECT count(DISTINCT (competencia, mes_referencia)) FROM dim_competencia WHERE mes_referencia IS NOT NULL;
SELECT count(*) FROM (SELECT DISTINCT municipio, bairro FROM dim_unidade_consumidora WHERE municipio IS NOT NULL) f;
SELECT count(*) FROM (SELECT DISTINCT classe FROM dim_unidade_consumidora WHERE classe IS NOT NULL) f;
SELECT count(*) FROM (SELECT DISTINCT alimentador FROM dim_alimentador WHERE alimentador IS NOT NULL) f;
SELECT count(*) FROM (SELECT DISTINCT alimentador, municipio FROM dim_unidade_consumidora
                       WHERE alimentador IS NOT NULL AND municipio IS NOT NULL) f;
SELECT count(*) FROM (SELECT DISTINCT causa FROM fact_ocorrencias WHERE causa IS NOT NULL) f;
\echo '[negado] CPF'
SELECT cpf_cnpj_mascarado FROM dim_unidade_consumidora LIMIT 1;
\echo '[negado] CEP'
SELECT cep FROM dim_unidade_consumidora LIMIT 1;
\echo '[negado] fila de inspeção'
SELECT count(*) FROM fila_inspecao;
\echo '[negado] histórico de inspeções'
SELECT count(*) FROM fact_inspecoes;
\echo '[negado] receita'
SELECT count(*) FROM agg_receita_mensal;
\echo '[negado] continuidade'
SELECT count(*) FROM agg_continuidade_alimentador;
\echo '[negado] ver ordens de inspeção'
SELECT count(*) FROM ordens_inspecao;
\echo '[negado] criar ordem (dentro de ROLLBACK)'
BEGIN;
INSERT INTO ordens_inspecao (id_uc, status) VALUES ('UC132549', 'ABERTA');
ROLLBACK;
\echo '[negado] escrever na Gold'
UPDATE fact_atendimentos SET status_chamado = 'X' WHERE false;

RESET ROLE;
