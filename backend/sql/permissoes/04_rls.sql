-- RLS: regras por linha nas tabelas da Visão 360.
--
-- Ligar o RLS numa tabela faz todo role SEM política enxergar zero linhas. Só o dono da
-- tabela e os superusuários (como o postgres) passam direto. Por isso, todo perfil que
-- lê estas tabelas precisa de uma política aqui, inclusive os perfis de outras pessoas.
--
-- Rodar de novo depois de cada carga da Gold: o DROP ... CASCADE apaga o RLS e as políticas.

ALTER TABLE dim_unidade_consumidora ENABLE ROW LEVEL SECURITY;
ALTER TABLE fact_leituras           ENABLE ROW LEVEL SECURITY;
ALTER TABLE fact_faturamento        ENABLE ROW LEVEL SECURITY;
ALTER TABLE fact_atendimentos       ENABLE ROW LEVEL SECURITY;
ALTER TABLE fact_ocorrencias        ENABLE ROW LEVEL SECURITY;

-- Perdas: só as UCs da fila de inspeção
DROP POLICY IF EXISTS perdas_so_fila ON dim_unidade_consumidora;
CREATE POLICY perdas_so_fila ON dim_unidade_consumidora FOR SELECT TO perfil_perdas
    USING (id_uc IN (SELECT id_uc FROM fila_inspecao));

DROP POLICY IF EXISTS perdas_so_fila ON fact_leituras;
CREATE POLICY perdas_so_fila ON fact_leituras FOR SELECT TO perfil_perdas
    USING (id_uc IN (SELECT id_uc FROM fila_inspecao));

DROP POLICY IF EXISTS perdas_so_fila ON fact_faturamento;
CREATE POLICY perdas_so_fila ON fact_faturamento FOR SELECT TO perfil_perdas
    USING (id_uc IN (SELECT id_uc FROM fila_inspecao));

DROP POLICY IF EXISTS perdas_so_fila ON fact_atendimentos;
CREATE POLICY perdas_so_fila ON fact_atendimentos FOR SELECT TO perfil_perdas
    USING (id_uc IN (SELECT id_uc FROM fila_inspecao));

DROP POLICY IF EXISTS perdas_so_fila ON fact_ocorrencias;
CREATE POLICY perdas_so_fila ON fact_ocorrencias FOR SELECT TO perfil_perdas
    USING (id_uc IN (SELECT id_uc FROM fila_inspecao));

-- Operação: todas as linhas. As colunas já estão limitadas pelo GRANT (02_grants_operacao.sql)
DROP POLICY IF EXISTS operacao_todas ON dim_unidade_consumidora;
CREATE POLICY operacao_todas ON dim_unidade_consumidora FOR SELECT TO perfil_operacao
    USING (true);

DROP POLICY IF EXISTS operacao_todas ON fact_ocorrencias;
CREATE POLICY operacao_todas ON fact_ocorrencias FOR SELECT TO perfil_operacao
    USING (true);
