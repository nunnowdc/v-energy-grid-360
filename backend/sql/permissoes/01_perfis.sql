CREATE ROLE perfil_operacao NOLOGIN;
CREATE ROLE perfil_perdas NOLOGIN;
-- BYPASSRLS: hoje nenhuma tabela tem RLS; se alguma ganhar, o admin continua vendo todas as linhas
CREATE ROLE perfil_admin NOLOGIN BYPASSRLS;
