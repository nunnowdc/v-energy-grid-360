"""Testes da etapa 2: tabelas, schemas, funções, colunas e complexidade.

Nomes de tabelas: guia_seguranca_agente.md. Colunas pessoais:
perfil_unidades_consumidoras.md. Tabelas de IA: scripts/criar_tabelas_ia.py.
"""

import pytest

from security.sql_validator import SQLValidator, validate_sql


def _bloqueado(sql, *codigos):
    r = validate_sql(sql)
    assert not r.allowed, f"deveria bloquear e passou: {r.sql}"
    assert r.code in codigos, f"código {r.code}, esperado {codigos}"
    assert r.sql is None


# ---------------- tabelas ----------------

@pytest.mark.parametrize(
    "tabela",
    [
        "dim_unidade_consumidora", "fact_leituras", "fact_faturamento",
        "fact_ocorrencias", "fact_atendimentos", "fact_gd", "fact_inspecoes",
        "fact_perdas", "dim_alimentadores",
    ],
)
def test_tabelas_do_guia_passam(tabela):
    assert validate_sql(f"SELECT COUNT(*) FROM {tabela}").allowed


def test_view_com_prefixo_vw_gold_passa():
    r = validate_sql("SELECT * FROM vw_gold_receita_mensal")
    assert r.allowed and r.tables == ("vw_gold_receita_mensal",)


def test_prefixo_parecido_nao_passa():
    _bloqueado("SELECT * FROM vw_silver_receita", "TABLE_NOT_ALLOWED")
    _bloqueado("SELECT * FROM xvw_gold_receita", "TABLE_NOT_ALLOWED")


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM tb_auditoria_agente",
        "SELECT * FROM tb_cache_perguntas_certificadas",
        "SELECT * FROM tb_insights_tela",
        "SELECT * FROM tb_conhecimento_vetorial",
        'SELECT * FROM "TB_Auditoria_Agente"',
        "SELECT id_uc FROM fact_leituras UNION SELECT user_id FROM tb_auditoria_agente",
        "SELECT * FROM fact_leituras WHERE id_uc IN (SELECT id_uc FROM tb_auditoria_agente)",
        "SELECT * FROM pg_shadow",
        "SELECT * FROM fact_leituras a JOIN tb_auditoria_agente b ON true",
        "SELECT id_uc FROM fact_leituras EXCEPT SELECT id_uc FROM tb_auditoria_agente",
        "SELECT * FROM public.tb_auditoria_agente",
        "SELECT * FROM medidores",
    ],
)
def test_tabela_fora_da_allowlist(sql):
    _bloqueado(sql, "TABLE_NOT_ALLOWED")


@pytest.mark.parametrize(
    "sql",
    ["SELECT * FROM pg_catalog.pg_tables", "SELECT * FROM information_schema.columns"],
)
def test_schema_de_sistema(sql):
    _bloqueado(sql, "SCHEMA_NOT_ALLOWED")


def test_schema_public_e_aceito_para_tabela_permitida():
    assert validate_sql("SELECT COUNT(*) FROM public.fact_leituras").allowed


def test_funcao_na_clausula_from():
    _bloqueado("SELECT * FROM generate_series(1, 100000000)", "TABLE_FUNCTION", "FUNCTION_NOT_ALLOWED")


def test_allowlist_customizada():
    v = SQLValidator(allowed_tables=frozenset({"outra_tabela"}), allowed_table_prefixes=())
    assert v.validate("SELECT * FROM outra_tabela").allowed
    assert v.validate("SELECT * FROM fact_leituras").code == "TABLE_NOT_ALLOWED"


# ---------------- CTE não pode esconder tabela proibida ----------------

def test_cte_legitima_passa():
    r = validate_sql("WITH tmp AS (SELECT id_uc FROM fact_leituras) SELECT * FROM tmp")
    assert r.allowed and r.tables == ("fact_leituras",)


def test_cte_que_le_tabela_proibida():
    _bloqueado("WITH tmp AS (SELECT * FROM tb_auditoria_agente) SELECT * FROM tmp", "TABLE_NOT_ALLOWED")


@pytest.mark.parametrize(
    "sql",
    [
        # CTE com o mesmo nome da tabela proibida lendo a própria tabela real
        "WITH tb_auditoria_agente AS (SELECT * FROM tb_auditoria_agente) SELECT * FROM tb_auditoria_agente",
        # CTE definida depois não enxerga a de baixo: a primeira lê a tabela real
        "WITH a AS (SELECT * FROM tb_auditoria_agente), tb_auditoria_agente AS (SELECT 1) SELECT * FROM a",
    ],
)
def test_cte_com_nome_de_tabela_proibida_nao_esconde_a_tabela_real(sql):
    _bloqueado(sql, "TABLE_NOT_ALLOWED")


# ---------------- tabelas detectadas ----------------

def test_tabelas_detectadas_em_join():
    r = validate_sql(
        "SELECT u.bairro, SUM(f.valor_fatura) FROM fact_faturamento f "
        "JOIN dim_unidade_consumidora u ON u.id_uc = f.id_uc GROUP BY u.bairro"
    )
    assert r.allowed and set(r.tables) == {"fact_faturamento", "dim_unidade_consumidora"}


def test_tabelas_detectadas_mesmo_quando_bloqueado_por_tabela():
    r = validate_sql("SELECT * FROM fact_leituras a JOIN tb_auditoria_agente b ON true")
    assert not r.allowed and "tb_auditoria_agente" in r.tables


# ---------------- funções ----------------

@pytest.mark.parametrize(
    "sql",
    [
        "SELECT pg_sleep(30)",
        "SELECT pg_catalog.pg_sleep(1)",
        "SELECT * FROM fact_leituras ORDER BY pg_sleep(1)",
        "SELECT pg_read_file('/etc/passwd')",
        "SELECT lo_import('/etc/passwd')",
        "SELECT current_setting('is_superuser')",
        "SELECT set_config('a', 'b', false)",
        "SELECT dblink('host=evil.com', 'SELECT 1')",
        "SELECT load_extension('/tmp/evil.so')",
        "SELECT version()",
        "SELECT current_user",
    ],
)
def test_funcao_perigosa(sql):
    _bloqueado(sql, "FUNCTION_NOT_ALLOWED")


def test_funcao_desconhecida_tem_codigo_proprio():
    _bloqueado("SELECT txid_current()", "FUNCTION_UNKNOWN")


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT u.bairro, SUM(f.valor_fatura) FROM fact_faturamento f JOIN dim_unidade_consumidora u ON u.id_uc = f.id_uc GROUP BY u.bairro",
        "SELECT DATE_TRUNC('month', data_competencia), ROUND(AVG(consumo_kwh), 2) FROM fact_leituras GROUP BY 1",
        "SELECT id_uc, LAG(consumo_kwh) OVER (PARTITION BY id_uc ORDER BY data_competencia) FROM fact_leituras",
        "SELECT CASE WHEN consumo_kwh > 300 THEN 'alto' ELSE 'normal' END, COUNT(*) FROM fact_leituras GROUP BY 1",
        "SELECT EXTRACT(YEAR FROM data_competencia), COALESCE(SUM(consumo_kwh), 0) FROM fact_leituras GROUP BY 1",
    ],
)
def test_funcoes_analiticas_comuns_passam(sql):
    assert validate_sql(sql).allowed


def test_funcao_extra_pode_ser_liberada():
    sql = "SELECT txid_current()"
    assert validate_sql(sql).code == "FUNCTION_UNKNOWN"
    assert SQLValidator(allowed_extra_functions=frozenset({"txid_current"})).validate(sql).allowed


# ---------------- colunas ----------------

@pytest.mark.parametrize(
    "coluna",
    ["cpf_cnpj", "nome_titular", "logradouro", "numero", "cep", "latitude", "longitude"],
)
def test_colunas_pessoais_reais_da_dim_unidade_consumidora(coluna):
    _bloqueado(f"SELECT {coluna} FROM dim_unidade_consumidora", "COLUMN_NOT_ALLOWED")


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT u.Cpf_Cnpj FROM dim_unidade_consumidora u",
        'SELECT u."NOME_TITULAR" FROM dim_unidade_consumidora u',
        "SELECT id_uc FROM dim_unidade_consumidora WHERE cpf_cnpj = '123'",
        "SELECT COUNT(*) FROM dim_unidade_consumidora GROUP BY cep",
        "SELECT user",
    ],
)
def test_coluna_bloqueada_em_qualquer_posicao(sql):
    _bloqueado(sql, "COLUMN_NOT_ALLOWED")


def test_colunas_de_negocio_continuam_livres():
    sql = ("SELECT bairro, municipio, classe, subgrupo_tarifario, COUNT(*) "
           "FROM dim_unidade_consumidora GROUP BY 1, 2, 3, 4")
    assert validate_sql(sql).allowed


# ---------------- tipos de raiz ----------------

def test_nao_select_so_para_comandos_de_escrita_ou_administracao():
    _bloqueado("DROP TABLE fact_leituras", "NOT_SELECT")
    _bloqueado("SHOW TABLES", "NOT_SELECT")


@pytest.mark.parametrize("sql", ["SQL_INDISPONIVEL", "VALUES (1), (2)", "1 + 1"])
def test_texto_que_nao_e_instrucao_nao_e_tratado_como_ataque(sql):
    _bloqueado(sql, "UNSUPPORTED", "PARSE_ERROR")


@pytest.mark.parametrize(
    "sql",
    [
        "Aqui está o SQL: SELECT 1 FROM fact_leituras",
        "```sql\nSELECT 1 FROM fact_leituras\n```",
        "me mostre as faturas",
    ],
)
def test_prosa_ou_markdown_do_llm_e_erro_de_sintaxe(sql):
    _bloqueado(sql, "PARSE_ERROR")


# ---------------- complexidade ----------------

def test_excesso_de_joins():
    joins = " ".join(f"CROSS JOIN fact_leituras t{i}" for i in range(10))
    _bloqueado(f"SELECT * FROM fact_leituras a {joins}", "TOO_COMPLEX")


def test_joins_dentro_do_limite():
    joins = " ".join(f"CROSS JOIN fact_leituras t{i}" for i in range(3))
    assert validate_sql(f"SELECT COUNT(*) FROM fact_leituras a {joins}").allowed
