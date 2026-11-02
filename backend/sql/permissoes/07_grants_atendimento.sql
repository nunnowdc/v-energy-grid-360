-- Perfil Atendimento: Visão 360 (com nome e endereço, sem CPF).
-- A Visão 360 vale para qualquer UC pesquisada pelo ID (matriz da seção 7.1 do
-- planejamento-backend.md). As colunas abaixo são as que o repositories/uc.py lê.
-- Não tem fila, ordens de inspeção nem receita. Só leitura: nenhum INSERT, UPDATE ou DELETE.
-- Rodar de novo depois de cada carga da Gold: o DROP ... CASCADE da carga apaga os GRANTs.

-- Começa do zero, para uma regra removida daqui também sair do banco
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM perfil_atendimento;

-- Calendário dos 12 meses de consumo
GRANT SELECT ON dim_competencia TO perfil_atendimento;

-- Cadastro da Visão 360. Sem CPF, CEP, latitude e longitude (o uc.py não lê)
GRANT SELECT (id_uc, nome_titular, logradouro, numero, bairro, municipio, uf, classe,
              id_medidor_atual, tipo_medidor_atual, modelo_medidor_atual,
              data_instalacao_medidor_atual,
              possui_gd, data_conexao_gd, potencia_gd_kwp, modalidade_gd)
   ON dim_unidade_consumidora TO perfil_atendimento;

-- Visão 360: consumo, faturas, ocorrências e chamados
GRANT SELECT ON fact_leituras, fact_faturamento, fact_ocorrencias, fact_atendimentos TO perfil_atendimento;
