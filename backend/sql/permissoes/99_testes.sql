-- Testes das permissões: simula cada perfil com SET ROLE e tenta o permitido e o proibido.
-- Rodar SEM parar no primeiro erro (sem ON_ERROR_STOP): os "permission denied" são esperados.
-- Só no banco local de desenvolvimento: os testes de ordens, contas e do agente escrevem
-- (desfeito no ROLLBACK). Os do agente precisam das tabelas tb_* (criar_tabelas_ia.py) e do
-- 08_contas_portal.sql já aplicado.
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

\echo '[ok] chat: registrar a pergunta (tb_auditoria_agente; desfeito no ROLLBACK)'
BEGIN;
INSERT INTO tb_auditoria_agente (sessao_id, pergunta_original, rota_escolhida, selo_confianca, user_id, perfil)
VALUES ('teste-permissoes', 'teste', 'teste', 'teste', NULL, 'OPERACAO');
ROLLBACK;
\echo '[negado] chat: gravar o feedback junto com a pergunta (dentro de ROLLBACK)'
BEGIN;
INSERT INTO tb_auditoria_agente (sessao_id, pergunta_original, rota_escolhida, selo_confianca, feedback_usuario)
VALUES ('teste-permissoes', 'teste', 'teste', 'teste', 1);
ROLLBACK;
\echo '[ok] chat: feedback na própria resposta (UPDATE de feedback_usuario filtrando id e user_id)'
UPDATE tb_auditoria_agente SET feedback_usuario = 1
 WHERE id = '00000000-0000-0000-0000-000000000000' AND user_id = '00000000-0000-0000-0000-000000000000';
\echo '[negado] chat: ler as perguntas da auditoria'
SELECT pergunta_original FROM tb_auditoria_agente LIMIT 1;
\echo '[ok] chat: cache de perguntas certificadas'
SELECT sql_template FROM tb_cache_perguntas_certificadas WHERE esqueleto = 'teste' AND ativo = TRUE LIMIT 1;
\echo '[negado] chat: alterar o cache de perguntas certificadas'
UPDATE tb_cache_perguntas_certificadas SET ativo = FALSE WHERE false;
\echo '[ok] chat: base do RAG'
SELECT count(*) FROM tb_conhecimento_vetorial;
\echo '[negado] insights da Visão 360 (perfil sem a tela)'
SELECT count(*) FROM tb_insights_tela;

RESET ROLE;

\echo '========== PERDAS =========='
SET ROLE perfil_perdas;

\echo '[ok] fila: 11586 UCs, com as colunas da tela'
SELECT count(*), max(data_referencia) FROM fila_inspecao;
SELECT prioridade, id_uc, score, motivo_suspeita, municipio, bairro, classe
  FROM fila_inspecao ORDER BY prioridade LIMIT 1;
\echo '[negado] nome na fila'
SELECT nome_titular FROM fila_inspecao LIMIT 1;
\echo '[ok] exportação da fila: endereço e coordenadas'
SELECT logradouro, numero, latitude, longitude FROM fila_inspecao ORDER BY prioridade LIMIT 1;
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
\echo '[ok] criar ordem com autoria (criada_por e atualizada_por; desfeito no ROLLBACK)'
BEGIN;
INSERT INTO ordens_inspecao (id_uc, status, criada_por, atualizada_por) VALUES ('UC132549', 'ABERTA', NULL, NULL) RETURNING id;
UPDATE ordens_inspecao SET status = 'CANCELADA', atualizada_por = NULL WHERE id_uc = 'UC132549';
ROLLBACK;
\echo '[ok] nome de quem criou a ordem (usuarios: id e nome)'
SELECT id, nome FROM usuarios LIMIT 1;
\echo '[negado] e-mail dos usuários'
SELECT email FROM usuarios LIMIT 1;
\echo '[negado] senha dos usuários'
SELECT senha_hash FROM usuarios LIMIT 1;
\echo '[negado pelo trigger] ordem para UC fora da fila (dentro de ROLLBACK)'
BEGIN;
INSERT INTO ordens_inspecao (id_uc, status) VALUES ('UC100005', 'ABERTA');
ROLLBACK;
\echo '[negado] trocar a UC de uma ordem'
UPDATE ordens_inspecao SET id_uc = 'UC100005' WHERE false;
\echo '[negado] apagar ordem'
DELETE FROM ordens_inspecao WHERE false;

\echo '[ok] chat: registrar a pergunta (tb_auditoria_agente; desfeito no ROLLBACK)'
BEGIN;
INSERT INTO tb_auditoria_agente (sessao_id, pergunta_original, rota_escolhida, selo_confianca, user_id, perfil)
VALUES ('teste-permissoes', 'teste', 'teste', 'teste', NULL, 'PERDAS');
ROLLBACK;
\echo '[negado] chat: gravar o feedback junto com a pergunta (dentro de ROLLBACK)'
BEGIN;
INSERT INTO tb_auditoria_agente (sessao_id, pergunta_original, rota_escolhida, selo_confianca, feedback_usuario)
VALUES ('teste-permissoes', 'teste', 'teste', 'teste', 1);
ROLLBACK;
\echo '[ok] chat: feedback na própria resposta (UPDATE de feedback_usuario filtrando id e user_id)'
UPDATE tb_auditoria_agente SET feedback_usuario = 1
 WHERE id = '00000000-0000-0000-0000-000000000000' AND user_id = '00000000-0000-0000-0000-000000000000';
\echo '[negado] chat: ler as perguntas da auditoria'
SELECT pergunta_original FROM tb_auditoria_agente LIMIT 1;
\echo '[ok] chat: cache de perguntas certificadas'
SELECT sql_template FROM tb_cache_perguntas_certificadas WHERE esqueleto = 'teste' AND ativo = TRUE LIMIT 1;
\echo '[negado] chat: alterar o cache de perguntas certificadas'
UPDATE tb_cache_perguntas_certificadas SET ativo = FALSE WHERE false;
\echo '[ok] chat: base do RAG'
SELECT count(*) FROM tb_conhecimento_vetorial;
\echo '[ok] insights da Visão 360: ler e gravar o cache (desfeito no ROLLBACK)'
SELECT texto_insight FROM tb_insights_tela WHERE tela = 'visao_360' AND entidade_id = 'UC132549';
BEGIN;
INSERT INTO tb_insights_tela (tela, entidade_id, fatos_calculados_json, texto_insight, selo_validacao)
VALUES ('teste_permissoes', 'UC132549', '[]', 'teste', 'teste')
ON CONFLICT (tela, entidade_id) DO UPDATE SET
    fatos_calculados_json = EXCLUDED.fatos_calculados_json, texto_insight = EXCLUDED.texto_insight,
    selo_validacao = EXCLUDED.selo_validacao, gerado_em = CURRENT_TIMESTAMP;
ROLLBACK;
\echo '[negado] insights: apagar do cache'
DELETE FROM tb_insights_tela WHERE false;
\echo '[negado] criar conta (dentro de ROLLBACK)'
BEGIN;
INSERT INTO usuarios (id, nome, email, senha_hash, perfil, criado_em)
VALUES (gen_random_uuid(), 'Teste permissões', 'teste.permissoes@exemplo.local', 'x', 'OPERACAO', now());
ROLLBACK;

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
INSERT INTO ordens_inspecao (id_uc, status, criada_por, atualizada_por) VALUES ('UC132549', 'ABERTA', NULL, NULL) RETURNING id, id_uc, status;
ROLLBACK;
\echo '[ok] nome de quem criou a ordem (usuarios: id e nome)'
SELECT id, nome FROM usuarios LIMIT 1;
\echo '[negado] e-mail dos usuários'
SELECT email FROM usuarios LIMIT 1;
\echo '[ok] uso do agente (tb_auditoria_agente)'
SELECT count(*), max(data_hora) FROM tb_auditoria_agente;
\echo '[negado] apagar ordem'
DELETE FROM ordens_inspecao WHERE false;
\echo '[negado] escrever na Gold'
UPDATE fila_inspecao SET score = 0 WHERE false;

\echo '[ok] chat: registrar a pergunta (tb_auditoria_agente; desfeito no ROLLBACK)'
BEGIN;
INSERT INTO tb_auditoria_agente (sessao_id, pergunta_original, rota_escolhida, selo_confianca, user_id, perfil)
VALUES ('teste-permissoes', 'teste', 'teste', 'teste', NULL, 'ADMIN_TI');
ROLLBACK;
\echo '[negado] chat: gravar o feedback junto com a pergunta (dentro de ROLLBACK)'
BEGIN;
INSERT INTO tb_auditoria_agente (sessao_id, pergunta_original, rota_escolhida, selo_confianca, feedback_usuario)
VALUES ('teste-permissoes', 'teste', 'teste', 'teste', 1);
ROLLBACK;
\echo '[ok] chat: feedback na própria resposta (UPDATE de feedback_usuario filtrando id e user_id)'
UPDATE tb_auditoria_agente SET feedback_usuario = 1
 WHERE id = '00000000-0000-0000-0000-000000000000' AND user_id = '00000000-0000-0000-0000-000000000000';
\echo '[ok] chat: cache de perguntas certificadas'
SELECT sql_template FROM tb_cache_perguntas_certificadas WHERE esqueleto = 'teste' AND ativo = TRUE LIMIT 1;
\echo '[negado] chat: alterar o cache de perguntas certificadas'
UPDATE tb_cache_perguntas_certificadas SET ativo = FALSE WHERE false;
\echo '[ok] chat: base do RAG'
SELECT count(*) FROM tb_conhecimento_vetorial;
\echo '[ok] insights da Visão 360: ler e gravar o cache (desfeito no ROLLBACK)'
SELECT texto_insight FROM tb_insights_tela WHERE tela = 'visao_360' AND entidade_id = 'UC132549';
BEGIN;
INSERT INTO tb_insights_tela (tela, entidade_id, fatos_calculados_json, texto_insight, selo_validacao)
VALUES ('teste_permissoes', 'UC132549', '[]', 'teste', 'teste')
ON CONFLICT (tela, entidade_id) DO UPDATE SET
    fatos_calculados_json = EXCLUDED.fatos_calculados_json, texto_insight = EXCLUDED.texto_insight,
    selo_validacao = EXCLUDED.selo_validacao, gerado_em = CURRENT_TIMESTAMP;
ROLLBACK;
\echo '[negado] insights: apagar do cache'
DELETE FROM tb_insights_tela WHERE false;
\echo '[ok] trilha de auditoria completa (GET /api/ai/audit/{audit_id}, SELECT *)'
SELECT * FROM tb_auditoria_agente LIMIT 1;
\echo '[negado] senha dos usuários'
SELECT senha_hash FROM usuarios LIMIT 1;
\echo '[ok] criar conta: INSERT sem RETURNING (desfeito no ROLLBACK)'
BEGIN;
INSERT INTO usuarios (id, nome, email, senha_hash, perfil, criado_em)
VALUES (gen_random_uuid(), 'Teste permissões', 'teste.permissoes@exemplo.local', 'x', 'OPERACAO', now());
ROLLBACK;
\echo '[ok] criar conta devolvendo só id e nome (desfeito no ROLLBACK)'
BEGIN;
INSERT INTO usuarios (id, nome, email, senha_hash, perfil, criado_em)
VALUES (gen_random_uuid(), 'Teste permissões', 'teste.permissoes@exemplo.local', 'x', 'OPERACAO', now())
RETURNING id, nome;
ROLLBACK;
\echo '[negado] criar conta com RETURNING de todas as colunas, como o UsersRepository.create faz hoje (pendente no backend; dentro de ROLLBACK)'
BEGIN;
INSERT INTO usuarios (id, nome, email, senha_hash, perfil, criado_em)
VALUES (gen_random_uuid(), 'Teste permissões', 'teste.permissoes@exemplo.local', 'x', 'OPERACAO', now())
RETURNING *;
ROLLBACK;
\echo '[negado] mudar o perfil de uma conta'
UPDATE usuarios SET perfil = 'ADMIN_TI' WHERE false;
\echo '[negado] apagar conta'
DELETE FROM usuarios WHERE false;

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

\echo '[ok] chat: registrar a pergunta (tb_auditoria_agente; desfeito no ROLLBACK)'
BEGIN;
INSERT INTO tb_auditoria_agente (sessao_id, pergunta_original, rota_escolhida, selo_confianca, user_id, perfil)
VALUES ('teste-permissoes', 'teste', 'teste', 'teste', NULL, 'DIRETORIA');
ROLLBACK;
\echo '[negado] chat: gravar o feedback junto com a pergunta (dentro de ROLLBACK)'
BEGIN;
INSERT INTO tb_auditoria_agente (sessao_id, pergunta_original, rota_escolhida, selo_confianca, feedback_usuario)
VALUES ('teste-permissoes', 'teste', 'teste', 'teste', 1);
ROLLBACK;
\echo '[ok] chat: feedback na própria resposta (UPDATE de feedback_usuario filtrando id e user_id)'
UPDATE tb_auditoria_agente SET feedback_usuario = 1
 WHERE id = '00000000-0000-0000-0000-000000000000' AND user_id = '00000000-0000-0000-0000-000000000000';
\echo '[negado] chat: ler as perguntas da auditoria'
SELECT pergunta_original FROM tb_auditoria_agente LIMIT 1;
\echo '[ok] chat: cache de perguntas certificadas'
SELECT sql_template FROM tb_cache_perguntas_certificadas WHERE esqueleto = 'teste' AND ativo = TRUE LIMIT 1;
\echo '[negado] chat: alterar o cache de perguntas certificadas'
UPDATE tb_cache_perguntas_certificadas SET ativo = FALSE WHERE false;
\echo '[ok] chat: base do RAG'
SELECT count(*) FROM tb_conhecimento_vetorial;
\echo '[negado] insights da Visão 360 (perfil sem a tela)'
SELECT count(*) FROM tb_insights_tela;

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

\echo '[ok] chat: registrar a pergunta (tb_auditoria_agente; desfeito no ROLLBACK)'
BEGIN;
INSERT INTO tb_auditoria_agente (sessao_id, pergunta_original, rota_escolhida, selo_confianca, user_id, perfil)
VALUES ('teste-permissoes', 'teste', 'teste', 'teste', NULL, 'ATENDIMENTO');
ROLLBACK;
\echo '[negado] chat: gravar o feedback junto com a pergunta (dentro de ROLLBACK)'
BEGIN;
INSERT INTO tb_auditoria_agente (sessao_id, pergunta_original, rota_escolhida, selo_confianca, feedback_usuario)
VALUES ('teste-permissoes', 'teste', 'teste', 'teste', 1);
ROLLBACK;
\echo '[ok] chat: feedback na própria resposta (UPDATE de feedback_usuario filtrando id e user_id)'
UPDATE tb_auditoria_agente SET feedback_usuario = 1
 WHERE id = '00000000-0000-0000-0000-000000000000' AND user_id = '00000000-0000-0000-0000-000000000000';
\echo '[negado] chat: ler as perguntas da auditoria'
SELECT pergunta_original FROM tb_auditoria_agente LIMIT 1;
\echo '[ok] chat: cache de perguntas certificadas'
SELECT sql_template FROM tb_cache_perguntas_certificadas WHERE esqueleto = 'teste' AND ativo = TRUE LIMIT 1;
\echo '[negado] chat: alterar o cache de perguntas certificadas'
UPDATE tb_cache_perguntas_certificadas SET ativo = FALSE WHERE false;
\echo '[ok] chat: base do RAG'
SELECT count(*) FROM tb_conhecimento_vetorial;
\echo '[ok] insights da Visão 360: ler e gravar o cache (desfeito no ROLLBACK)'
SELECT texto_insight FROM tb_insights_tela WHERE tela = 'visao_360' AND entidade_id = 'UC132549';
BEGIN;
INSERT INTO tb_insights_tela (tela, entidade_id, fatos_calculados_json, texto_insight, selo_validacao)
VALUES ('teste_permissoes', 'UC132549', '[]', 'teste', 'teste')
ON CONFLICT (tela, entidade_id) DO UPDATE SET
    fatos_calculados_json = EXCLUDED.fatos_calculados_json, texto_insight = EXCLUDED.texto_insight,
    selo_validacao = EXCLUDED.selo_validacao, gerado_em = CURRENT_TIMESTAMP;
ROLLBACK;
\echo '[negado] insights: apagar do cache'
DELETE FROM tb_insights_tela WHERE false;

RESET ROLE;

\echo '========== CONTAS DO PORTAL (08_contas_portal.sql) =========='

\echo '[ok] portal_app assume os 5 perfis (SET) sem herdar as permissões (esperado: t t t t t f f)'
SELECT pg_has_role('portal_app', 'perfil_operacao', 'SET')    AS operacao,
       pg_has_role('portal_app', 'perfil_perdas', 'SET')      AS perdas,
       pg_has_role('portal_app', 'perfil_admin_ti', 'SET')    AS admin_ti,
       pg_has_role('portal_app', 'perfil_diretoria', 'SET')   AS diretoria,
       pg_has_role('portal_app', 'perfil_atendimento', 'SET') AS atendimento,
       pg_has_role('portal_app', 'perfil_admin_ti', 'USAGE')  AS herda_admin_ti,
       has_table_privilege('portal_app', 'dim_competencia', 'SELECT') AS le_gold;
\echo '[ok] portal_auth não é membro de nenhum perfil (esperado: f)'
SELECT pg_has_role('portal_auth', 'perfil_operacao', 'MEMBER')
    OR pg_has_role('portal_auth', 'perfil_perdas', 'MEMBER')
    OR pg_has_role('portal_auth', 'perfil_admin_ti', 'MEMBER')
    OR pg_has_role('portal_auth', 'perfil_diretoria', 'MEMBER')
    OR pg_has_role('portal_auth', 'perfil_atendimento', 'MEMBER') AS membro_de_perfil;

SET ROLE portal_app;

\echo '[negado] portal_app sem SET ROLE de perfil: Gold'
SELECT count(*) FROM dim_competencia;
\echo '[negado] portal_app sem SET ROLE de perfil: usuarios'
SELECT id FROM usuarios LIMIT 1;

RESET ROLE;

SET ROLE portal_auth;

\echo '[ok] login e validação do cookie: a linha inteira de usuarios'
SELECT id, nome, email, senha_hash, perfil, criado_em FROM usuarios WHERE email = 'teste.permissoes@exemplo.local';
\echo '[ok] troca da própria senha: FOR UPDATE e UPDATE de senha_hash (desfeito no ROLLBACK)'
BEGIN;
SELECT id FROM usuarios WHERE id = '00000000-0000-0000-0000-000000000000' FOR UPDATE;
UPDATE usuarios SET senha_hash = 'x' WHERE id = '00000000-0000-0000-0000-000000000000';
ROLLBACK;
\echo '[negado] criar conta (dentro de ROLLBACK)'
BEGIN;
INSERT INTO usuarios (id, nome, email, senha_hash, perfil, criado_em)
VALUES (gen_random_uuid(), 'Teste permissões', 'teste.permissoes@exemplo.local', 'x', 'OPERACAO', now());
ROLLBACK;
\echo '[negado] mudar o perfil de uma conta'
UPDATE usuarios SET perfil = 'ADMIN_TI' WHERE false;
\echo '[negado] Gold'
SELECT count(*) FROM fila_inspecao;
\echo '[negado] auditoria do agente'
SELECT count(*) FROM tb_auditoria_agente;

RESET ROLE;
