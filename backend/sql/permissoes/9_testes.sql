SET ROLE perfil_operacao;
SELECT count(*) FROM agg_continuidade_alimentador;          -- da certo
SELECT nome_titular FROM dim_unidade_consumidora LIMIT 1;   -- permissao negada
SELECT count(*) FROM fila_inspecao;                         --permissao negada
RESET ROLE;
