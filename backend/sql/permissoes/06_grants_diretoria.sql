-- Perfil Diretoria: Indicadores, Receita e Continuidade, mais os filtros globais.
-- Sem dado pessoal: do cadastro lê só as colunas de filtro (município, bairro, classe, alimentador).
-- Rodar de novo depois de cada carga da Gold: o DROP ... CASCADE da carga apaga os GRANTs.

-- Começa do zero, para uma regra removida daqui também sair do banco
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM perfil_diretoria;

-- Indicadores e Receita
GRANT SELECT ON agg_receita_mensal, agg_receita_preco_volume TO perfil_diretoria;

-- Continuidade e filtros (competências, alimentadores e causas das ocorrências)
GRANT SELECT ON agg_continuidade_alimentador, agg_continuidade_alimentador_anual,
                dim_alimentador, dim_competencia, fact_ocorrencias
   TO perfil_diretoria;

-- Filtros (municípios, bairros, classes e alimentadores) e a validação dos filtros da Receita:
-- só as colunas sem dado pessoal
GRANT SELECT (municipio, bairro, classe, alimentador) ON dim_unidade_consumidora TO perfil_diretoria;
