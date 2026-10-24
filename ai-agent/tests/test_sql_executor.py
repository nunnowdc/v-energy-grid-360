"""
Testes unitários do SQLExecutor (camada de infraestrutura de dados).
Valida execução em SQLite sintético, injeção de LIMIT, cálculo de tempo e tratamento de erros.
"""
from __future__ import annotations

import decimal
import sys
import types
from unittest.mock import MagicMock, patch

import pytest
from ai_agent.src.services.sql_executor import SQLExecutor, ResultadoExecucaoSQL


def test_execucao_consulta_valida(sql_executor_teste: SQLExecutor):
    """Garante que consultas SELECT simples retornam dados estruturados e métricas de execução."""
    resultado: ResultadoExecucaoSQL = sql_executor_teste.executar(
        "SELECT COUNT(*) AS total_ucs FROM dim_unidade_consumidora"
    )

    assert resultado.sucesso is True
    assert resultado.erro is None
    assert resultado.total_linhas == 1
    assert resultado.linhas[0]["total_ucs"] == 6
    assert resultado.tempo_execucao_ms >= 0.0


def test_filtro_e_agrupamento(sql_executor_teste: SQLExecutor):
    """Valida agregações por classe com GROUP BY e ORDER BY."""
    sql = """
    SELECT classe, COUNT(*) AS qtd
    FROM dim_unidade_consumidora
    GROUP BY classe
    ORDER BY classe
    """
    resultado = sql_executor_teste.executar(sql)

    assert resultado.sucesso is True
    assert resultado.total_linhas == 4  # Comercial, Industrial, Poder Público, Residencial
    dados = {linha["classe"]: linha["qtd"] for linha in resultado.linhas}
    assert dados["Comercial"] == 2
    assert dados["Residencial"] == 2
    assert dados["Industrial"] == 1
    assert dados["Poder Público"] == 1


def test_injecao_automatica_de_limit(sql_executor_teste: SQLExecutor):
    """Garante que queries sem LIMIT explícito recebem LIMIT seguro automaticamente."""
    resultado = sql_executor_teste.executar(
        "SELECT * FROM fact_faturamento",
        limite_linhas=5,
    )

    assert resultado.sucesso is True
    assert len(resultado.linhas) == 5
    assert resultado.total_linhas == 5


def test_respeita_limit_menor_ja_existente(sql_executor_teste: SQLExecutor):
    """Se a query já possui LIMIT 2, o executor não deve inflar para o teto padrão."""
    resultado = sql_executor_teste.executar(
        "SELECT * FROM dim_unidade_consumidora LIMIT 2",
        limite_linhas=50,
    )

    assert resultado.sucesso is True
    assert len(resultado.linhas) == 2


def test_join_dimensao_e_fato_faturamento(sql_executor_teste: SQLExecutor):
    """Valida consulta analítica clássica cruzando tabela fato com dimensão."""
    sql = """
    SELECT u.classe, SUM(f.receita_faturada) AS total_receita
    FROM fact_faturamento f
    JOIN dim_unidade_consumidora u ON f.uc_id = u.uc_id
    WHERE u.municipio = 'Olinda' AND f.ano = 2023
    GROUP BY u.classe
    """
    resultado = sql_executor_teste.executar(sql)

    assert resultado.sucesso is True
    assert len(resultado.linhas) >= 1
    linha_comercial = next(r for r in resultado.linhas if r["classe"] == "Comercial")
    # Restaurante Beta (uc_id=2): faturas 1 (765.0) + 2 (810.0) = 1575.0
    assert linha_comercial["total_receita"] == 1575.0


def test_cruzamento_ocorrencias_interrupcoes(sql_executor_teste: SQLExecutor):
    """Valida cálculo de duração de interrupções na tabela fato de ocorrências."""
    sql = """
    SELECT tipo_interrupcao, SUM(duracao_minutos) AS total_minutos
    FROM fact_ocorrencias
    WHERE ano = 2023
    GROUP BY tipo_interrupcao
    """
    resultado = sql_executor_teste.executar(sql)

    assert resultado.sucesso is True
    totais = {r["tipo_interrupcao"]: r["total_minutos"] for r in resultado.linhas}
    assert totais["Acidental"] == 135.0  # 45 + 90
    assert totais["Programada"] == 120.0


def test_erro_sintaxe_sql_capturado_graciosamente(sql_executor_teste: SQLExecutor):
    """Queries com erro de sintaxe ou tabelas inexistentes devem retornar sucesso=False sem estourar exceção."""
    resultado = sql_executor_teste.executar("SELECT coluna_inexistente FROM tabela_fantasma")

    assert resultado.sucesso is False
    assert resultado.erro is not None
    assert "tabela_fantasma" in resultado.erro.lower() or "no such table" in resultado.erro.lower()
    assert resultado.linhas == []
    assert resultado.total_linhas == 0


def test_sql_com_ponto_e_virgula_e_espacos(sql_executor_teste: SQLExecutor):
    """Garante que ponto e vírgula e quebras de linha são devidamente sanitizados antes do LIMIT."""
    sql = "  SELECT uc_id, codigo_uc FROM dim_unidade_consumidora ;  \n "
    resultado = sql_executor_teste.executar(sql, limite_linhas=2)

    assert resultado.sucesso is True
    assert len(resultado.linhas) == 2


def test_executor_postgres_configura_timeout_readonly_e_search_path():
    cursor = MagicMock()
    cursor.__enter__.return_value = cursor
    cursor.fetchall.return_value = [{"total": decimal.Decimal("12.50")}]
    conn = MagicMock()
    conn.cursor.return_value = cursor

    psycopg2 = types.ModuleType("psycopg2")
    psycopg2.connect = MagicMock(return_value=conn)
    extras = types.ModuleType("psycopg2.extras")
    extras.RealDictCursor = object()

    with patch.dict(sys.modules, {"psycopg2": psycopg2, "psycopg2.extras": extras}):
        executor = SQLExecutor(
            db_url="postgresql://localhost/v_energy_test_db",
            schema="VEnergy_Test_Gold",
        )
        resultado = executor.executar("SELECT SUM(valor) AS total FROM fatos")

    psycopg2.connect.assert_called_once_with(
        "postgresql://localhost/v_energy_test_db",
        connect_timeout=30,
        options="-c statement_timeout=30000",
    )
    conn.set_session.assert_called_once_with(readonly=True, autocommit=True)
    cursor.execute.assert_any_call('SET search_path TO "VEnergy_Test_Gold", public')
    cursor.execute.assert_any_call("SELECT SUM(valor) AS total FROM fatos LIMIT 50")
    assert resultado.sucesso is True
    assert resultado.linhas == [{"total": 12.5}]


def test_executor_rejeita_schema_postgres_com_identificador_invalido():
    with pytest.raises(ValueError, match="schema"):
        SQLExecutor(
            db_url="postgresql://localhost/v_energy_test_db",
            schema="venergy_test; DROP SCHEMA public",
        )


def test_sqlite_explicito_ignora_database_url_generica(monkeypatch, tmp_path):
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/production_db")

    executor = SQLExecutor(sqlite_path=str(tmp_path / "test.db"))

    assert executor.is_postgres is False
