-- 06: roles de conexão (portal_app, portal_auth) e grants das tabelas auxiliares
-- (usuários, auditoria, insights, cache de perguntas e RAG) para USE_DB_ROLES=true.
--
-- Rodar como dono (postgres), DEPOIS dos grants de perfil (03, 05 e os demais): o 03 faz
-- REVOKE ALL e apagaria estes grants se rodasse depois. Repetir depois de cada carga da Gold.
-- Só no banco local de desenvolvimento, de preferência numa cópia.
--
--   psql -h localhost -p 5433 -U postgres -d v_energy_grid \
--        -v app_pass='TROQUE_1' -v auth_pass='TROQUE_2' -f 06_roles_conexao_e_tabelas_auxiliares.sql
--
-- Pré-requisito: os roles perfil_diretoria, perfil_atendimento, perfil_perdas, perfil_operacao
-- e perfil_admin_ti já existem (são os que o 99_testes.sql usa).

-- 1. Roles com login. NOINHERIT: sozinhos não enxergam nada; o acesso vem do SET LOCAL ROLE.
SELECT format('CREATE ROLE portal_app LOGIN NOINHERIT PASSWORD %L', :'app_pass')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'portal_app') \gexec

SELECT format('CREATE ROLE portal_auth LOGIN NOINHERIT PASSWORD %L', :'auth_pass')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'portal_auth') \gexec

ALTER ROLE portal_app NOINHERIT;
ALTER ROLE portal_auth NOINHERIT;

-- 2. portal_app pode assumir os 5 perfis (SET ROLE), mas não herda os privilégios deles.
--    O REVOKE antes do GRANT refaz a participação já com NOINHERIT (no PG 16+ a opção de herança
--    é gravada no momento do GRANT).
REVOKE perfil_diretoria, perfil_atendimento, perfil_perdas, perfil_operacao, perfil_admin_ti
   FROM portal_app;
GRANT perfil_diretoria, perfil_atendimento, perfil_perdas, perfil_operacao, perfil_admin_ti
   TO portal_app;

-- 3. Os dois começam sem nenhuma permissão em tabelas.
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM portal_app, portal_auth;

-- 4. portal_auth: só login, conta atual e troca de senha (perfil ainda desconhecido).
--    O repository lê a linha inteira (select da tabela) e faz SELECT ... FOR UPDATE na troca.
GRANT SELECT (id, nome, email, senha_hash, perfil, criado_em) ON usuarios TO portal_auth;
GRANT UPDATE (senha_hash) ON usuarios TO portal_auth;

-- 5. Criar conta (POST /api/auth/users, só ADMIN_TI). O RETURNING lê id e nome, que já estão liberados.
GRANT INSERT (id, nome, email, senha_hash, perfil, criado_em) ON usuarios TO perfil_admin_ti;

-- 6. Tabelas do agente de IA. Cada bloco é pulado se a tabela ainda não existir.
DO $$
BEGIN
    -- Auditoria: todo perfil grava a própria execução; o feedback (UPDATE) filtra por id e user_id.
    IF to_regclass('public.tb_auditoria_agente') IS NOT NULL THEN
        GRANT INSERT ON tb_auditoria_agente
           TO perfil_diretoria, perfil_atendimento, perfil_perdas, perfil_operacao, perfil_admin_ti;
        GRANT SELECT (id, user_id) ON tb_auditoria_agente
           TO perfil_diretoria, perfil_atendimento, perfil_perdas, perfil_operacao, perfil_admin_ti;
        GRANT UPDATE (feedback_usuario) ON tb_auditoria_agente
           TO perfil_diretoria, perfil_atendimento, perfil_perdas, perfil_operacao, perfil_admin_ti;
        -- GET /api/ai/audit/{id} faz SELECT * (só ADMIN_TI): precisa de todas as colunas
        GRANT SELECT ON tb_auditoria_agente TO perfil_admin_ti;
    END IF;

    -- Insights da Visão 360 (rota liberada a ATENDIMENTO, PERDAS e ADMIN_TI): lê e grava o cache
    IF to_regclass('public.tb_insights_tela') IS NOT NULL THEN
        GRANT SELECT, INSERT, UPDATE ON tb_insights_tela
           TO perfil_atendimento, perfil_perdas, perfil_admin_ti;
    END IF;

    -- Cache de perguntas certificadas e base de conhecimento (RAG): só leitura, todos os perfis
    IF to_regclass('public.tb_cache_perguntas_certificadas') IS NOT NULL THEN
        GRANT SELECT ON tb_cache_perguntas_certificadas
           TO perfil_diretoria, perfil_atendimento, perfil_perdas, perfil_operacao, perfil_admin_ti;
    END IF;
    IF to_regclass('public.tb_conhecimento_vetorial') IS NOT NULL THEN
        GRANT SELECT ON tb_conhecimento_vetorial
           TO perfil_diretoria, perfil_atendimento, perfil_perdas, perfil_operacao, perfil_admin_ti;
    END IF;
END
$$;

-- 7. Conferência rápida
\echo '--- participação de portal_app (role_herda e inherit_option devem ser f; a coluna pg16 fica vazia em versões antigas)'
SELECT r.rolname AS perfil, u.rolinherit AS role_herda, to_jsonb(m) ->> 'inherit_option' AS inherit_option_pg16
FROM pg_auth_members m
JOIN pg_roles r ON r.oid = m.roleid
JOIN pg_roles u ON u.oid = m.member
WHERE u.rolname = 'portal_app'
ORDER BY 1;
