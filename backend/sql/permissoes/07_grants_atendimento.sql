-- Perfil Atendimento: Visão 360 (com nome e endereço, sem CPF).
-- A Visão 360 vale para qualquer UC pesquisada pelo ID (matriz da seção 7.1 do
-- planejamento-backend.md). As colunas abaixo são as que o repositories/uc.py lê.
-- Não tem fila, ordens de inspeção nem receita. Só leitura: nenhum INSERT, UPDATE ou DELETE.
-- Todas as telas chamam GET /api/filters/options (o SeloBase do cabeçalho e o painel do agente),
-- então o Atendimento também lê o que esse endpoint lê: dim_competencia, dim_alimentador,
-- as colunas de filtro do cadastro e as causas de fact_ocorrencias.
-- Rodar de novo depois de cada carga da Gold: o DROP ... CASCADE da carga apaga os GRANTs.

-- Começa do zero, para uma regra removida daqui também sair do banco
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM perfil_atendimento;

-- Calendário dos 12 meses de consumo e filtros (GET /api/filters/options)
GRANT SELECT ON dim_competencia, dim_alimentador TO perfil_atendimento;

-- Cadastro: Visão 360 e filtros (alimentador). Sem CPF, CEP, latitude e longitude (nenhum repository lê)
GRANT SELECT (id_uc, nome_titular, logradouro, numero, bairro, municipio, uf, classe, alimentador,
              id_medidor_atual, tipo_medidor_atual, modelo_medidor_atual,
              data_instalacao_medidor_atual,
              possui_gd, data_conexao_gd, potencia_gd_kwp, modalidade_gd)
   ON dim_unidade_consumidora TO perfil_atendimento;

-- Visão 360: consumo, faturas, ocorrências (também as causas dos filtros) e chamados
GRANT SELECT ON fact_leituras, fact_faturamento, fact_ocorrencias, fact_atendimentos TO perfil_atendimento;
