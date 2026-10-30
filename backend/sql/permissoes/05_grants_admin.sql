-- Perfil Admin TI: todas as telas, mas sem escrever na Gold, apagar ou mudar a estrutura.
-- As tabelas vão uma a uma: tudo está no public, e ON ALL TABLES daria também as tb_* do agente.
-- Rodar de novo depois de cada carga da Gold: o DROP ... CASCADE da carga apaga os GRANTs.

GRANT SELECT ON agg_continuidade_alimentador, agg_continuidade_alimentador_anual,
                agg_receita_mensal, agg_receita_preco_volume,
                dim_alimentador, dim_competencia, dim_geracao_distribuida, dim_medidor,
                dim_unidade_consumidora,
                fact_atendimentos, fact_faturamento, fact_inspecoes, fact_leituras, fact_ocorrencias,
                fila_inspecao
   TO perfil_admin;

-- Ordens de inspeção: as mesmas ações do Perdas (criar e mudar o status, sem apagar)
GRANT SELECT ON ordens_inspecao TO perfil_admin;
GRANT INSERT (id_uc, status) ON ordens_inspecao TO perfil_admin;
GRANT UPDATE (status, resultado, atualizada_em, concluida_em) ON ordens_inspecao TO perfil_admin;
GRANT SELECT ON vw_ordens_campo TO perfil_admin;

-- Pendente: tb_auditoria_agente (pergunta 7 do plano) e a tabela de usuários, quando existir
