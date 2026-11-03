-- Perfil Perdas: Fila de inspeção, ordens e Visão 360 (com nome e endereço, sem CPF).
-- A Visão 360 vale para qualquer UC pesquisada pelo ID, não só as da fila (matriz da seção 7.1
-- do planejamento-backend.md). As colunas abaixo são as que o repositories/uc.py lê.
-- Rodar de novo depois de cada carga da Gold: o DROP ... CASCADE da carga apaga os GRANTs.
-- Pré-requisito: usuarios.sql e ordens_inspecao_autoria.sql já aplicados (os GRANTs abaixo citam
-- a tabela usuarios e as colunas criada_por e atualizada_por).

-- Começa do zero, para uma regra removida daqui também sair do banco
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM perfil_perdas;

-- Fila: só as colunas que a tela e a exportação usam (a exportação leva endereço e coordenadas
-- para o campo; o nome do titular continua de fora)
GRANT SELECT (prioridade, id_uc, score, motivo_suspeita, kwh_recuperavel_estimado_ano,
              municipio, bairro, classe, data_referencia,
              logradouro, numero, latitude, longitude)
   ON fila_inspecao TO perfil_perdas;

-- Filtros (GET /api/filters/options carrega todos de uma vez) e o JOIN das ordens
GRANT SELECT ON dim_competencia, dim_alimentador TO perfil_perdas;

-- Cadastro: filtros, ordens e Visão 360. Sem CPF
GRANT SELECT (id_uc, nome_titular, logradouro, numero, municipio, bairro, uf, classe, alimentador,
              id_medidor_atual, tipo_medidor_atual, modelo_medidor_atual,
              data_instalacao_medidor_atual,
              possui_gd, data_conexao_gd, potencia_gd_kwp, modalidade_gd)
   ON dim_unidade_consumidora TO perfil_perdas;

-- Visão 360: consumo, faturas, ocorrências e chamados
GRANT SELECT ON fact_leituras, fact_faturamento, fact_ocorrencias, fact_atendimentos TO perfil_perdas;

-- Ordens de inspeção: criar e mudar o status, sem trocar a UC nem apagar (cancelar é UPDATE).
-- A ordens_inspecao não é recriada pela carga, então estes GRANTs sobrevivem a ela
GRANT SELECT ON ordens_inspecao TO perfil_perdas;
-- criada_por e atualizada_por guardam quem fez (ordens_inspecao_autoria.sql)
GRANT INSERT (id_uc, status, criada_por, atualizada_por) ON ordens_inspecao TO perfil_perdas;
GRANT UPDATE (status, resultado, atualizada_em, concluida_em, atualizada_por)
   ON ordens_inspecao TO perfil_perdas;

-- A listagem das ordens mostra o nome de quem criou e de quem mudou por último (LEFT JOIN usuarios).
-- Só id e nome: e-mail e senha_hash continuam negados
GRANT SELECT (id, nome) ON usuarios TO perfil_perdas;

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
           ON tb_auditoria_agente TO perfil_perdas;
        -- Feedback: o UPDATE filtra pela resposta e pela conta (WHERE id e user_id), daí o SELECT nas duas
        GRANT UPDATE (feedback_usuario), SELECT (id, user_id) ON tb_auditoria_agente TO perfil_perdas;
    END IF;
    IF to_regclass('public.tb_cache_perguntas_certificadas') IS NOT NULL THEN
        -- Cache de perguntas certificadas: só leitura (no_cache_parametrizado.py)
        GRANT SELECT (esqueleto, sql_template, ativo) ON tb_cache_perguntas_certificadas TO perfil_perdas;
    END IF;
    IF to_regclass('public.tb_conhecimento_vetorial') IS NOT NULL THEN
        -- Base do RAG que o chat consulta (buscador_vetorial.py): documentos, sem dado de cliente
        GRANT SELECT ON tb_conhecimento_vetorial TO perfil_perdas;
    END IF;
    IF to_regclass('public.tb_insights_tela') IS NOT NULL THEN
        -- Cache dos insights da Visão 360 (insights/service.py, GET /api/ai/insights): lê o cache e
        -- grava com INSERT ... ON CONFLICT (tela, entidade_id) DO UPDATE, que também lê as colunas
        GRANT SELECT (tela, entidade_id, fatos_calculados_json, texto_insight, selo_validacao),
              INSERT (tela, entidade_id, fatos_calculados_json, texto_insight, selo_validacao),
              UPDATE (fatos_calculados_json, texto_insight, selo_validacao, gerado_em)
           ON tb_insights_tela TO perfil_perdas;
    END IF;
END
$$;
