-- Tabela operacional de usuários. Aplicação controlada pelo setup local.
-- Não executar automaticamente na API nem pelo bootstrap.
BEGIN;

CREATE TABLE usuarios (
    id UUID PRIMARY KEY,
    nome VARCHAR(150) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    senha_hash VARCHAR(255) NOT NULL,
    perfil VARCHAR(30) NOT NULL
        CHECK (perfil IN ('DIRETORIA', 'ATENDIMENTO', 'PERDAS', 'OPERACAO', 'ADMIN_TI')),
    criado_em TIMESTAMP NOT NULL
);

COMMIT;
