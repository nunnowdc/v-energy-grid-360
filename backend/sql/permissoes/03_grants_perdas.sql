-- Perfil Perdas: Fila de inspeção, ordens e Visão 360 (com nome e endereço, sem CPF).
-- A Visão 360 vale para qualquer UC pesquisada pelo ID, não só as da fila (matriz da seção 7.1
-- do planejamento-backend.md). As colunas abaixo são as que o repositories/uc.py lê.
-- Rodar de novo depois de cada carga da Gold: o DROP ... CASCADE da carga apaga os GRANTs.

-- Começa do zero, para uma regra removida daqui também sair do banco
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM perfil_perdas;

-- Fila: só as colunas que a tela usa
GRANT SELECT (prioridade, id_uc, score, motivo_suspeita, kwh_recuperavel_estimado_ano,
              municipio, bairro, classe, data_referencia)
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
GRANT INSERT (id_uc, status) ON ordens_inspecao TO perfil_perdas;
GRANT UPDATE (status, resultado, atualizada_em, concluida_em) ON ordens_inspecao TO perfil_perdas;
