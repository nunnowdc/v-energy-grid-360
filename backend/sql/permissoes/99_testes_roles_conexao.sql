-- Testes do 06: tabelas auxiliares e roles de conexão. Rodar SEM ON_ERROR_STOP:
-- os "permission denied" marcados [negado] são o resultado esperado.
-- Cada escrita roda em BEGIN/ROLLBACK, sem sobrar dado.
--
--   psql -h localhost -p 5433 -U postgres -d v_energy_grid -f 99_testes_roles_conexao.sql

\echo '========== PORTAL_APP sem perfil =========='
SET ROLE portal_app;
\echo '[negado] portal_app sozinho não lê nada'
SELECT count(*) FROM fila_inspecao;
\echo '[negado] portal_app sozinho não lê receita'
SELECT count(*) FROM fact_faturamento;
RESET ROLE;

\echo '========== PORTAL_AUTH =========='
SET ROLE portal_auth;
\echo '[ok] login: lê usuarios'
SELECT count(*) FROM usuarios;
\echo '[negado] não lê a Gold'
SELECT count(*) FROM fact_faturamento;
\echo '[negado] não muda o perfil de ninguém'
BEGIN; UPDATE usuarios SET perfil = 'ADMIN_TI' WHERE false; ROLLBACK;
\echo '[ok] troca de senha (UPDATE só em senha_hash)'
BEGIN; UPDATE usuarios SET senha_hash = senha_hash WHERE false; ROLLBACK;
RESET ROLE;

\echo '========== PERDAS: tabelas auxiliares =========='
SET ROLE perfil_perdas;
\echo '[ok] grava auditoria'
BEGIN;
INSERT INTO tb_auditoria_agente (sessao_id, pergunta_original, rota_escolhida, selo_confianca)
VALUES ('teste', 'teste', 'teste', 'teste');
ROLLBACK;
\echo '[ok] feedback: UPDATE de feedback_usuario filtrando por id e user_id'
BEGIN; UPDATE tb_auditoria_agente SET feedback_usuario = 1 WHERE id = gen_random_uuid() AND user_id = gen_random_uuid(); ROLLBACK;
\echo '[negado] não lê a auditoria inteira'
SELECT sql_gerado FROM tb_auditoria_agente LIMIT 1;
\echo '[ok] lê o cache de perguntas certificadas e o RAG'
SELECT count(*) FROM tb_cache_perguntas_certificadas;
SELECT count(*) FROM tb_conhecimento_vetorial;
\echo '[ok] insights (Perdas usa a Visão 360)'
BEGIN;
INSERT INTO tb_insights_tela (tela, entidade_id, fatos_calculados_json, texto_insight, selo_validacao)
VALUES ('teste', 'teste', '{}', 'teste', 'teste')
ON CONFLICT (tela, entidade_id) DO UPDATE SET texto_insight = EXCLUDED.texto_insight;
ROLLBACK;
\echo '[negado] não cria usuários'
BEGIN; INSERT INTO usuarios (id, nome, email, senha_hash, perfil, criado_em)
VALUES (gen_random_uuid(), 'x', 'x@x', 'x', 'PERDAS', now()); ROLLBACK;
RESET ROLE;

\echo '========== OPERACAO: sem insights =========='
SET ROLE perfil_operacao;
\echo '[ok] grava auditoria'
BEGIN;
INSERT INTO tb_auditoria_agente (sessao_id, pergunta_original, rota_escolhida, selo_confianca)
VALUES ('teste', 'teste', 'teste', 'teste');
ROLLBACK;
\echo '[negado] insights é só ATENDIMENTO, PERDAS e ADMIN_TI'
SELECT count(*) FROM tb_insights_tela;
RESET ROLE;

\echo '========== ADMIN_TI =========='
SET ROLE perfil_admin_ti;
\echo '[ok] auditoria inteira (gaveta Como a IA chegou nisso)'
SELECT * FROM tb_auditoria_agente LIMIT 1;
\echo '[ok] cria usuário (RETURNING id, nome)'
BEGIN;
INSERT INTO usuarios (id, nome, email, senha_hash, perfil, criado_em)
VALUES (gen_random_uuid(), 'x', 'x@x', 'x', 'PERDAS', now()) RETURNING id, nome;
ROLLBACK;
RESET ROLE;

\echo '========== VAZAMENTO CONHECIDO: PERDAS lê receita agregada =========='
\echo 'Hoje isto RETORNA valor (fact_faturamento inteira está liberada ao Perdas).'
\echo 'Resolver no agente (allowlist por perfil ou role próprio do chat); não some só ligando a flag.'
SET ROLE perfil_perdas;
SELECT sum(receita_faturada) FROM fact_faturamento;
RESET ROLE;

-- Teste de verdade do portal_app (precisa de login real, não de SET ROLE a partir do postgres):
--   docker exec postgres-venergy psql -U portal_app -d v_energy_grid -c "SELECT count(*) FROM fila_inspecao;"
--       -> deve dar permission denied
--   docker exec postgres-venergy psql -U portal_app -d v_energy_grid -c "BEGIN; SET LOCAL ROLE perfil_perdas; SELECT count(*) FROM fila_inspecao; ROLLBACK;"
--       -> deve funcionar (11586 linhas)
--   docker exec postgres-venergy psql -U portal_app -d v_energy_grid -c "BEGIN; SET LOCAL ROLE perfil_perdas; RESET ROLE; SELECT count(*) FROM fila_inspecao; ROLLBACK;"
--       -> deve dar permission denied (portal_app não herda nada, mesmo se a IA tentar RESET ROLE)
