-- Perfil Perdas: Fila de inspeção e ordens. Sem Visão 360.
-- Nome e endereço só das UCs com ordem ativa (ABERTA ou EM_CAMPO), pela vw_ordens_campo.
-- Rodar de novo depois de cada carga da Gold: o DROP ... CASCADE da carga apaga os GRANTs e a view.

-- Começa do zero, para uma regra removida daqui também sair do banco
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM perfil_perdas;

-- Fila: só o que identifica e prioriza a UC, sem nome nem endereço
GRANT SELECT (prioridade, id_uc, score, motivo_suspeita, kwh_recuperavel_estimado_ano,
              municipio, bairro, classe, data_referencia)
   ON fila_inspecao TO perfil_perdas;

-- Filtros (GET /api/filters/options carrega todos de uma vez) e o JOIN das ordens
GRANT SELECT ON dim_competencia, dim_alimentador TO perfil_perdas;
GRANT SELECT (id_uc, municipio, bairro, classe, alimentador) ON dim_unidade_consumidora TO perfil_perdas;
GRANT SELECT (causa) ON fact_ocorrencias TO perfil_perdas;

-- Ordens de inspeção: criar e mudar o status, sem trocar a UC nem apagar (cancelar é UPDATE).
-- A ordens_inspecao não é recriada pela carga, então estes GRANTs sobrevivem a ela
GRANT SELECT ON ordens_inspecao TO perfil_perdas;
GRANT INSERT (id_uc, status) ON ordens_inspecao TO perfil_perdas;
GRANT UPDATE (status, resultado, atualizada_em, concluida_em) ON ordens_inspecao TO perfil_perdas;

-- Nome e endereço para ir a campo. A view roda com as permissões do dono, então o Perdas
-- lê estas colunas sem ter acesso a elas na dim_unidade_consumidora.
-- Concluída ou cancelada, a ordem sai da view e o endereço deixa de aparecer
CREATE OR REPLACE VIEW vw_ordens_campo AS
SELECT o.id, o.id_uc, o.status, o.criada_em,
       uc.nome_titular, uc.logradouro, uc.numero, uc.bairro, uc.municipio, uc.uf, uc.cep,
       uc.latitude, uc.longitude
  FROM ordens_inspecao AS o
  JOIN dim_unidade_consumidora AS uc USING (id_uc)
 WHERE o.status IN ('ABERTA', 'EM_CAMPO');

GRANT SELECT ON vw_ordens_campo TO perfil_perdas;
