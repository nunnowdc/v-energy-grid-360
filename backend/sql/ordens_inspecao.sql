-- Estrutura operacional das ordens de inspeção. Execução manual e controlada.
-- Não executar no banco Gold sem autorização; não há criação automática pela API.
BEGIN;

CREATE TABLE ordens_inspecao (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_uc TEXT NOT NULL CHECK (id_uc ~ '^UC[0-9]{6}$'),
    status TEXT NOT NULL CHECK (status IN ('ABERTA', 'EM_CAMPO', 'CONCLUIDA', 'CANCELADA')),
    resultado TEXT,
    criada_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizada_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    concluida_em TIMESTAMPTZ,
    CONSTRAINT ordem_conclusao_coerente CHECK (
        (status = 'CONCLUIDA'
         AND resultado IS NOT NULL
         AND resultado IN ('IRREGULARIDADE_CONFIRMADA', 'SEM_IRREGULARIDADE')
         AND concluida_em IS NOT NULL)
        OR
        (status <> 'CONCLUIDA' AND resultado IS NULL AND concluida_em IS NULL)
    )
);

CREATE UNIQUE INDEX ordens_inspecao_uc_ativa_uidx
    ON ordens_inspecao (id_uc)
    WHERE status IN ('ABERTA', 'EM_CAMPO');

COMMIT;
