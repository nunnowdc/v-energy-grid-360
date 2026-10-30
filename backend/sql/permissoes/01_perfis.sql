-- Nomes seguem os perfis do backend (coluna role de usuarios): perfil_<perfil em minúsculas>.
-- perfil_diretoria e perfil_atendimento ficam com outra pessoa (planejamento, seção 6.3).
CREATE ROLE perfil_operacao NOLOGIN;
CREATE ROLE perfil_perdas NOLOGIN;
CREATE ROLE perfil_admin_ti NOLOGIN;
