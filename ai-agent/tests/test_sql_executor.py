"""
Testes unitários do SQLExecutor (camada de infraestrutura de dados).
Valida execução em SQLite sintético, injeção de LIMIT, cálculo de tempo e tratamento de erros.
"""
from __future__ import annotations

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
