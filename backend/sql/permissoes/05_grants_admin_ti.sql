-- Perfil Admin TI: todas as telas, mas sem escrever na Gold, apagar ou mudar a estrutura.
-- As tabelas vão uma a uma: tudo está no public, e ON ALL TABLES daria também as tb_* do agente.
-- Rodar de novo depois de cada carga da Gold: o DROP ... CASCADE da carga apaga os GRANTs.
-- Pré-requisito: usuarios.sql e ordens_inspecao_autoria.sql já aplicados.

GRANT SELECT ON agg_continuidade_alimentador, agg_continuidade_alimentador_anual,
                agg_receita_mensal, agg_receita_preco_volume,
                dim_alimentador, dim_competencia, dim_geracao_distribuida, dim_medidor,
                dim_unidade_consumidora,
                fact_atendimentos, fact_faturamento, fact_inspecoes, fact_leituras, fact_ocorrencias,
                fila_inspecao
   TO perfil_admin_ti;

-- Ordens de inspeção: as mesmas ações do Perdas (criar e mudar o status, sem apagar)
GRANT SELECT ON ordens_inspecao TO perfil_admin_ti;
-- criada_por e atualizada_por guardam quem fez (ordens_inspecao_autoria.sql)
GRANT INSERT (id_uc, status, criada_por, atualizada_por) ON ordens_inspecao TO perfil_admin_ti;
GRANT UPDATE (status, resultado, atualizada_em, concluida_em, atualizada_por)
   ON ordens_inspecao TO perfil_admin_ti;

-- Nome de quem criou e de quem mudou a ordem (LEFT JOIN usuarios). Só id e nome
GRANT SELECT (id, nome) ON usuarios TO perfil_admin_ti;

-- Criação de contas (POST /api/auth/users, só Admin TI): só INSERT, sem ler e-mail nem senha_hash.
-- Mudar perfil ou senha de outra conta não entra: nenhum endpoint faz isso.
-- PENDENTE NO BACKEND: o UsersRepository.create faz RETURNING de todas as colunas (inclusive
-- senha_hash). O RETURNING exige SELECT nas colunas devolvidas, então, com SET ROLE perfil_admin_ti,
-- a criação vai dar "permission denied" até o RETURNING ficar só em id e nome (as colunas que este
-- perfil lê) e o resto da resposta sair dos valores enviados.
GRANT INSERT (id, nome, email, senha_hash, perfil, criado_em) ON usuarios TO perfil_admin_ti;

-- Telas de uso e de avaliação do agente (GET /api/ai/usage e /api/ai/evaluations, só Admin TI) e a
-- trilha de auditoria completa (GET /api/ai/audit/{audit_id}, só Admin TI, faz SELECT *).
-- As tabelas vêm do ai-agent (criar_tabelas_ia.py e a avaliação do golden set) e podem não existir
-- ainda: sem elas, o GRANT é pulado em vez de derrubar o script.
DO $$
BEGIN
    IF to_regclass('public.tb_auditoria_agente') IS NOT NULL THEN
        GRANT SELECT ON tb_auditoria_agente TO perfil_admin_ti;
    END IF;
    IF to_regclass('public.tb_avaliacoes_agente') IS NOT NULL
       AND to_regclass('public.tb_avaliacoes_agente_casos') IS NOT NULL THEN
        GRANT SELECT ON tb_avaliacoes_agente, tb_avaliacoes_agente_casos TO perfil_admin_ti;
    END IF;
END
$$;

-- Agente de IA: o chat e o feedback valem para todos os perfis (POST /api/ai/ask e /api/ai/feedback).
-- As tabelas vêm do ai-agent (criar_tabelas_ia.py) e podem não existir ainda: sem elas, o GRANT é
-- pulado. Pré-requisito: as colunas opcionais da tb_auditoria_agente já migradas (tentativas_sql,
-- chamadas_llm, malicioso, motivo_recusa, ids_chunks_rag, user_id e perfil).
DO $$
BEGIN
    IF to_regclass('public.tb_auditoria_agente') IS NOT NULL THEN
        -- Pergunta: as colunas que o no_finaliza_auditoria.py grava. Sem data_hora (default do banco)
        -- e sem feedback_usuario (só pelo UPDATE abaixo). Sem ler a pergunta: a tabela guarda as de todos
        GRANT INSERT (id, sessao_id, pergunta_original, pergunta_autonoma, rota_escolhida, hit_cache,
                      sql_gerado, linhas_retornadas, amostra_resultado_json, selo_confianca,
                      passos_execucao, tempo_execucao_ms, tokens_prompt, tokens_resposta, erro_mensagem,
                      tentativas_sql, chamadas_llm, malicioso, motivo_recusa, ids_chunks_rag,
                      user_id, perfil)
           ON tb_auditoria_agente TO perfil_admin_ti;
        -- Feedback: o UPDATE filtra pela resposta e pela conta (WHERE id e user_id), daí o SELECT nas duas
        GRANT UPDATE (feedback_usuario), SELECT (id, user_id) ON tb_auditoria_agente TO perfil_admin_ti;
    END IF;
    IF to_regclass('public.tb_cache_perguntas_certificadas') IS NOT NULL THEN
        -- Cache de perguntas certificadas: só leitura (no_cache_parametrizado.py)
        GRANT SELECT (esqueleto, sql_template, ativo) ON tb_cache_perguntas_certificadas TO perfil_admin_ti;
    END IF;
    IF to_regclass('public.tb_conhecimento_vetorial') IS NOT NULL THEN
        -- Base do RAG que o chat consulta (buscador_vetorial.py): documentos, sem dado de cliente
        GRANT SELECT ON tb_conhecimento_vetorial TO perfil_admin_ti;
    END IF;
    IF to_regclass('public.tb_insights_tela') IS NOT NULL THEN
        -- Cache dos insights da Visão 360 (insights/service.py, GET /api/ai/insights): lê o cache e
        -- grava com INSERT ... ON CONFLICT (tela, entidade_id) DO UPDATE, que também lê as colunas
        GRANT SELECT (tela, entidade_id, fatos_calculados_json, texto_insight, selo_validacao),
              INSERT (tela, entidade_id, fatos_calculados_json, texto_insight, selo_validacao),
              UPDATE (fatos_calculados_json, texto_insight, selo_validacao, gerado_em)
           ON tb_insights_tela TO perfil_admin_ti;
    END IF;
END
$$;
