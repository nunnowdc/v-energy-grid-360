"""Testes da etapa 1: estrutura da consulta, escrita e LIMIT."""

import pytest

from security.sql_validator import SQLValidator, validate_sql


# ---------------- entradas inválidas ----------------

@pytest.mark.parametrize("entrada", ["", "   \n  ", None, 123, [], b"SELECT 1"])
def test_entrada_vazia_ou_que_nao_e_string(entrada):
    r = validate_sql(entrada)
    assert not r.allowed and r.code == "EMPTY"


def test_consulta_acima_do_tamanho_maximo():
    r = validate_sql("SELECT " + ", ".join(["1"] * 3000) + " FROM fact_leituras")
    assert not r.allowed and r.code == "TOO_LONG"


def test_caractere_nulo():
    r = validate_sql("SELECT 1\x00; DROP TABLE fact_leituras")
    assert not r.allowed and r.code == "INVALID_CHARS"


def test_sql_com_aspas_abertas():
    r = validate_sql("SELECT * FROM fact_leituras WHERE bairro = 'abc")
    assert not r.allowed and r.code == "PARSE_ERROR"


# ---------------- uma única instrução ----------------

@pytest.mark.parametrize(
    "sql",
    [
        "SELECT 1; DROP TABLE fact_faturamento",
        "SELECT COUNT(*) FROM fact_leituras; DELETE FROM fact_leituras",
        "SELECT 1 /* inocente */; DROP TABLE fact_leituras -- fim",
    ],
)
def test_multiplas_instrucoes(sql):
    r = validate_sql(sql)
    assert not r.allowed and r.code == "MULTIPLE_STATEMENTS"


def test_ponto_e_virgula_final_e_aceito():
    assert validate_sql("SELECT COUNT(*) FROM fact_leituras;").allowed


def test_texto_dentro_de_string_nao_e_tratado_como_comando():
    r = validate_sql("SELECT COUNT(*) FROM dim_unidade_consumidora WHERE bairro = 'x''; DROP TABLE y; --'")
    assert r.allowed
    assert "DROP TABLE y" in r.sql  # continua sendo apenas texto do filtro


def test_ponto_e_virgula_dentro_de_string():
    assert validate_sql("SELECT COUNT(*) FROM dim_unidade_consumidora WHERE bairro = 'Boa; Viagem'").allowed


# ---------------- só leitura ----------------

@pytest.mark.parametrize(
    "sql",
    [
        "DROP TABLE fact_faturamento",
        "DELETE FROM fact_leituras WHERE 1=1",
        "UPDATE fact_faturamento SET valor_fatura = 0",
        "INSERT INTO fact_ocorrencias (id_uc) VALUES (1)",
        "TRUNCATE TABLE fact_leituras",
        "ALTER TABLE dim_unidade_consumidora ADD COLUMN x int",
        "CREATE TABLE copia AS SELECT * FROM fact_faturamento",
        "SET ROLE postgres",
    ],
)
def test_raiz_que_nao_e_select(sql):
    r = validate_sql(sql)
    assert not r.allowed and r.code == "NOT_SELECT"
    assert r.sql is None


@pytest.mark.parametrize(
    "sql",
    [
        "WITH d AS (DELETE FROM fact_leituras RETURNING *) SELECT * FROM d",
        "SELECT * INTO copia FROM fact_faturamento",
        "SELECT * FROM fact_leituras FOR UPDATE",
    ],
)
def test_escrita_escondida_dentro_de_select(sql):
    r = validate_sql(sql)
    assert not r.allowed and r.code in {"FORBIDDEN_NODE", "PARSE_ERROR"}


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT COUNT(*) FROM fact_ocorrencias",
        "WITH mensal AS (SELECT id_uc FROM fact_leituras) SELECT * FROM mensal",
        "SELECT id_uc FROM fact_leituras UNION SELECT id_uc FROM fact_faturamento",
        "(SELECT 1) UNION (SELECT 2)",
    ],
)
def test_consultas_de_leitura_passam(sql):
    assert validate_sql(sql).allowed


# ---------------- SQL normalizado e LIMIT ----------------

def test_adiciona_limit_quando_ausente():
    r = validate_sql("SELECT * FROM fact_leituras")
    assert r.allowed and r.sql.upper().endswith("LIMIT 1000")


def test_reduz_limit_acima_do_teto():
    r = validate_sql("SELECT * FROM fact_leituras LIMIT 99999999")
    assert r.allowed and r.sql.upper().endswith("LIMIT 1000")


def test_limit_all_vira_limit_com_teto():
    r = validate_sql("SELECT * FROM fact_leituras LIMIT ALL")
    assert r.allowed and r.sql.upper().endswith("LIMIT 1000")


def test_mantem_limit_menor_que_o_teto():
    r = validate_sql("SELECT * FROM fact_leituras LIMIT 5")
    assert r.allowed and r.sql.upper().endswith("LIMIT 5")


def test_teto_de_linhas_customizado():
    v = SQLValidator(max_rows=50)
    assert v.validate("SELECT * FROM fact_leituras").sql.upper().endswith("LIMIT 50")


def test_remove_comentarios_do_sql_normalizado():
    r = validate_sql("SELECT 1 /* oculto */ FROM fact_leituras -- fim")
    assert r.allowed and "oculto" not in r.sql and "--" not in r.sql


def test_resultado_serializavel_para_auditoria():
    d = validate_sql("DROP TABLE fact_leituras").to_dict()
    assert d["allowed"] is False and d["code"] == "NOT_SELECT" and d["reason"]


def test_dialeto_sqlite():
    v = SQLValidator(dialect="sqlite")
    assert v.validate("SELECT COUNT(*) FROM fact_leituras").allowed
    assert not v.validate("DROP TABLE fact_leituras").allowed
