-- Perfil Operação: tela de Continuidade e filtros globais.
-- Rodar de novo depois de cada carga da Gold: o DROP ... CASCADE da carga apaga os GRANTs.

GRANT SELECT ON agg_continuidade_alimentador, agg_continuidade_alimentador_anual,
                dim_alimentador, dim_competencia, fact_ocorrencias
   TO perfil_operacao;

-- Filtros (municípios, bairros, classes e alimentadores): só as colunas sem dado pessoal
GRANT SELECT (municipio, bairro, classe, alimentador) ON dim_unidade_consumidora TO perfil_operacao;
