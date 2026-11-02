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

-- Telas de uso e de avaliação do agente (GET /api/ai/usage e /api/ai/evaluations, só Admin TI).
-- Só as colunas que as consultas leem. As tabelas vêm do ai-agent (criar_tabelas_ia.py e a avaliação
-- do golden set) e podem não existir ainda: sem elas, o GRANT é pulado em vez de derrubar o script.
DO $$
BEGIN
    IF to_regclass('public.tb_auditoria_agente') IS NOT NULL THEN
        GRANT SELECT (id, data_hora, pergunta_original, perfil, selo_confianca, tempo_execucao_ms,
                      tokens_prompt, tokens_resposta, feedback_usuario)
           ON tb_auditoria_agente TO perfil_admin_ti;
    END IF;
    IF to_regclass('public.tb_avaliacoes_agente') IS NOT NULL
       AND to_regclass('public.tb_avaliacoes_agente_casos') IS NOT NULL THEN
        GRANT SELECT ON tb_avaliacoes_agente, tb_avaliacoes_agente_casos TO perfil_admin_ti;
    END IF;
END
$$;
