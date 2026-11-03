-- Contas com login do portal (seção 4.1 do docs/planejamento_permissoes_banco.md).
-- Rodar uma vez por ambiente, depois de 01_perfis.sql e usuarios.sql. A carga da Gold não mexe
-- na tabela usuarios nem nestes roles, então nada aqui precisa rodar de novo depois dela.
-- Nada no backend usa estas contas ainda: o portal segue com a conexão atual (seção 6.3).
-- Senhas fora do repositório: depois de rodar, definir no psql com
--   \password portal_app
--   \password portal_auth

-- portal_app: a conta com que o backend vai conectar. NOINHERIT e membro dos perfis só com a opção
-- SET: sozinha não lê nada, e a cada requisição o backend faz SET LOCAL ROLE perfil_<perfil>.
-- Se o código esquecer o SET LOCAL ROLE, a consulta falha em vez de enxergar tudo.
CREATE ROLE portal_app LOGIN NOINHERIT;
GRANT perfil_operacao, perfil_perdas, perfil_admin_ti, perfil_diretoria, perfil_atendimento
   TO portal_app WITH INHERIT FALSE, SET TRUE;

-- portal_auth: identidade antes de se saber o perfil. Não é membro de nenhum perfil.
-- Login (get_by_email) e a validação do cookie em toda rota, inclusive GET /api/auth/me (get_by_id),
-- leem a linha inteira de usuarios
CREATE ROLE portal_auth LOGIN;
GRANT SELECT (id, nome, email, senha_hash, perfil, criado_em) ON usuarios TO portal_auth;
-- Troca da própria senha (PATCH /api/auth/password): SELECT ... FOR UPDATE e UPDATE de senha_hash.
-- O FOR UPDATE também exige UPDATE em alguma coluna. Sem INSERT: criar contas é do perfil_admin_ti
GRANT UPDATE (senha_hash) ON usuarios TO portal_auth;
