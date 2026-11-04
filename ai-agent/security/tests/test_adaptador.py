"""Testes do adaptador: contrato com a frente de Agentes.

Rodar a partir de ai-agent/ (precisa enxergar `src` e `security`):
    python -m pytest security/tests -q
"""

import pytest

from security.validador_sqlglot import (
    CODIGOS_MALICIOSOS,
    ResultadoValidacaoSQLSeguro,
    ValidadorSQLGlotPostgres,
)
from src.interfaces.validador_sql_interface import ResultadoValidacaoSQL

v = ValidadorSQLGlotPostgres()


# ---------------- contrato ----------------

def test_interface_do_agente_tem_os_campos_que_o_adaptador_preenche():
    # Se a frente de Agentes renomear um campo, o pydantic IGNORA em silêncio o
    # nome antigo e o resultado passa a dizer "malicioso=False" para todo ataque.
    # Este teste falha antes disso.
    campos = set(ResultadoValidacaoSQL.model_fields)
    assert {"aprovado", "motivo_rejeicao", "malicioso", "tabelas_detectadas"} <= campos


def test_o_campo_malicioso_chega_ao_resultado_da_interface():
    r = v.validar("DROP TABLE fact_leituras")
    assert r.model_dump()["malicioso"] is True


def test_resultado_e_compativel_com_a_interface_do_agente():
    r = v.validar("SELECT COUNT(*) FROM fact_leituras")
    assert isinstance(r, ResultadoValidacaoSQL)
    assert isinstance(r, ResultadoValidacaoSQLSeguro)


def test_consulta_aprovada():
    r = v.validar("SELECT bairro, COUNT(*) FROM dim_unidade_consumidora GROUP BY bairro")
    assert r.aprovado is True
    assert r.motivo_rejeicao is None
    assert r.malicioso is False
    assert r.tabelas_detectadas == ["dim_unidade_consumidora"]
    assert r.codigo == "OK"
    assert r.sql_normalizado.upper().endswith("LIMIT 1000")


def test_tabelas_detectadas_em_join():
    r = v.validar(
        "SELECT u.municipio, SUM(f.receita_faturada) FROM fact_faturamento f JOIN dim_unidade_consumidora u ON u.id_uc = f.id_uc GROUP BY u.municipio"
    )
    assert r.aprovado and set(r.tabelas_detectadas) == {"fact_faturamento", "dim_unidade_consumidora"}


# ---------------- ataques: malicioso = True ----------------

@pytest.mark.parametrize(
    "sql",
    [
        "DROP TABLE fact_faturamento",
        "DELETE FROM fact_leituras",
        "UPDATE fact_faturamento SET valor_fatura = 0",
        "INSERT INTO fact_ocorrencias (id_uc) VALUES (1)",
        "CREATE TABLE x AS SELECT * FROM fact_leituras",
        "SELECT 1; DROP TABLE fact_leituras",
        "SELECT COUNT(*) FROM fact_leituras; DELETE FROM fact_leituras",
        "WITH d AS (DELETE FROM fact_leituras RETURNING *) SELECT * FROM d",
        "SELECT * INTO copia FROM fact_faturamento",
        "SELECT pg_sleep(30)",
        "SELECT pg_read_file('/etc/passwd')",
        "SELECT version()",
        "SELECT * FROM pg_catalog.pg_tables",
        "SELECT * FROM information_schema.columns",
        "SELECT 1\x00; DROP TABLE fact_leituras",
    ],
)
def test_ataque_flagrante_e_malicioso(sql):
    r = v.validar(sql)
    assert r.aprovado is False
    assert r.malicioso is True, f"{r.codigo}: {r.motivo_rejeicao}"
    assert r.motivo_rejeicao
    assert r.sql_normalizado is None


# ---------------- erro provável do LLM: malicioso = False ----------------

@pytest.mark.parametrize(
    "sql,codigo",
    [
        ("", "EMPTY"),
        ("SELEC 1 FROM fact_leituras", "PARSE_ERROR"),
        ("SELECT * FROM fact_leituras WHERE bairro = 'abc", "PARSE_ERROR"),
        ("Aqui está o SQL: SELECT 1 FROM fact_leituras", "PARSE_ERROR"),
        ("```sql\nSELECT 1 FROM fact_leituras\n```", "PARSE_ERROR"),
        ("SQL_INDISPONIVEL", "UNSUPPORTED"),
        ("SELECT * FROM tabela_que_nao_existe", "TABLE_NOT_ALLOWED"),
        ("SELECT * FROM tb_auditoria_agente", "TABLE_NOT_ALLOWED"),
        ("SELECT cpf_cnpj FROM dim_unidade_consumidora", "COLUMN_NOT_ALLOWED"),
        ("SELECT txid_current()", "FUNCTION_UNKNOWN"),
        ("SELECT * FROM generate_series(1, 10)", "TABLE_FUNCTION"),
        ("SELECT * FROM dim_unidade_consumidora", "STAR_NOT_ALLOWED"),
        ("SELECT * FROM fact_gd", "TABLE_NOT_ALLOWED"),
    ],
)
def test_erro_do_llm_nao_e_malicioso(sql, codigo):
    r = v.validar(sql)
    assert r.aprovado is False
    assert r.malicioso is False
    assert r.codigo == codigo


def test_tabelas_detectadas_acompanham_o_bloqueio_por_tabela():
    r = v.validar("SELECT * FROM fact_leituras a JOIN tb_auditoria_agente b ON true")
    assert not r.aprovado and "tb_auditoria_agente" in r.tabelas_detectadas


def test_todo_codigo_malicioso_existe_no_validador():
    # Evita que um código renomeado no validador deixe o adaptador desatualizado.
    import inspect
    import security.sql_validator as mod

    fonte = inspect.getsource(mod)
    for codigo in CODIGOS_MALICIOSOS:
        assert f'"{codigo}"' in fonte, f"código {codigo} não existe mais no validador"


# ---------------- integração com o nó 8 do agente ----------------

def test_no_valida_sql_aprova_e_segue_para_execucao():
    from src.nos.no_valida_sql import no_valida_sql, rota_pos_validacao

    state = {"sql_gerado": "SELECT COUNT(*) FROM fact_leituras", "tentativas_sql": 1}
    state.update(no_valida_sql(state, validador=v))
    assert rota_pos_validacao(state) == "executa"


def test_no_valida_sql_ataque_cancela_retry_e_recusa():
    from src.nos.no_valida_sql import no_valida_sql, rota_pos_validacao

    state = {"sql_gerado": "SELECT 1; DROP TABLE fact_leituras", "tentativas_sql": 1}
    state.update(no_valida_sql(state, validador=v))
    assert state["malicioso"] is True
    assert rota_pos_validacao(state) == "recusa"


def test_no_valida_sql_erro_do_llm_tenta_de_novo():
    from src.nos.no_valida_sql import no_valida_sql, rota_pos_validacao

    state = {"sql_gerado": "SELECT * FROM tabela_que_nao_existe", "tentativas_sql": 1}
    state.update(no_valida_sql(state, validador=v))
    assert state["malicioso"] is False
    assert rota_pos_validacao(state) == "retry_sql"
