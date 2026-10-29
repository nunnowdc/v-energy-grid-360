-- Perfil Perdas: Fila de inspeção, ordens e Visão 360 das UCs da fila.
-- Os GRANTs dizem QUAIS tabelas e colunas; QUAIS linhas fica no RLS (04_rls.sql).
-- Rodar de novo depois de cada carga da Gold: o DROP ... CASCADE da carga apaga os GRANTs.

-- Fila e filtros
GRANT SELECT ON fila_inspecao, dim_competencia, dim_alimentador TO perfil_perdas;

-- Visão 360: o cadastro sem o CPF (a inspeção é do imóvel e do medidor, não da pessoa)
GRANT SELECT (id_uc, nome_titular, tipo_pessoa, logradouro, numero, bairro, municipio, uf, cep,
              latitude, longitude, classe, subgrupo_tarifario, alimentador, data_ligacao, status,
              possui_gd, data_conexao_gd, potencia_gd_kwp, modalidade_gd,
              id_medidor_atual, tipo_medidor_atual, modelo_medidor_atual,
              data_instalacao_medidor_atual, trocou_medidor, data_ultima_troca_medidor,
              tipo_medidor_anterior, cadastro_conflitante, _processado_em)
   ON dim_unidade_consumidora TO perfil_perdas;

GRANT SELECT ON fact_leituras, fact_faturamento, fact_atendimentos, fact_ocorrencias TO perfil_perdas;

-- Ordens de inspeção: criar e mudar o status, sem trocar a UC nem apagar (cancelar é UPDATE).
-- A ordens_inspecao não é recriada pela carga, então estes GRANTs sobrevivem a ela
GRANT SELECT ON ordens_inspecao TO perfil_perdas;
GRANT INSERT (id_uc, status) ON ordens_inspecao TO perfil_perdas;
GRANT UPDATE (status, resultado, atualizada_em, concluida_em) ON ordens_inspecao TO perfil_perdas;
