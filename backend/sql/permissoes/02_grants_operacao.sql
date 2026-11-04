-- Perfil Operação: tela de Continuidade e filtros globais.
-- Rodar de novo depois de cada carga da Gold: o DROP ... CASCADE da carga apaga os GRANTs.

GRANT SELECT ON agg_continuidade_alimentador, agg_continuidade_alimentador_anual,
                dim_alimentador, dim_competencia, fact_ocorrencias
   TO perfil_operacao;

-- Filtros (municípios, bairros, classes e alimentadores): só as colunas sem dado pessoal
GRANT SELECT (municipio, bairro, classe, alimentador) ON dim_unidade_consumidora TO perfil_operacao;

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
           ON tb_auditoria_agente TO perfil_operacao;
        -- Feedback: o UPDATE filtra pela resposta e pela conta (WHERE id e user_id), daí o SELECT nas duas
        GRANT UPDATE (feedback_usuario), SELECT (id, user_id) ON tb_auditoria_agente TO perfil_operacao;
    END IF;
    IF to_regclass('public.tb_cache_perguntas_certificadas') IS NOT NULL THEN
        -- Cache de perguntas certificadas: só leitura (no_cache_parametrizado.py)
        GRANT SELECT (esqueleto, sql_template, ativo) ON tb_cache_perguntas_certificadas TO perfil_operacao;
    END IF;
    IF to_regclass('public.tb_conhecimento_vetorial') IS NOT NULL THEN
        -- Base do RAG que o chat consulta (buscador_vetorial.py): documentos, sem dado de cliente
        GRANT SELECT ON tb_conhecimento_vetorial TO perfil_operacao;
    END IF;
END
$$;
