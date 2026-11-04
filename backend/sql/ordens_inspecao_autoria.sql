-- Quem gerou e quem mudou por último cada ordem de inspeção. Execução manual e controlada,
-- depois de ordens_inspecao.sql e usuarios.sql. Rodar de novo não muda nada.
-- Ordens de antes destas colunas ficam sem autor (NULL). A chave não apaga nem esvazia
-- em cascata: o histórico não pode perder o autor, então uma conta com ordens não pode
-- ser apagada (o portal não apaga contas).
BEGIN;

ALTER TABLE ordens_inspecao
    ADD COLUMN IF NOT EXISTS criada_por UUID REFERENCES usuarios (id),
    ADD COLUMN IF NOT EXISTS atualizada_por UUID REFERENCES usuarios (id);

COMMIT;
