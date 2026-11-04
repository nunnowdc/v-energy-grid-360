"""Execução opt-in do agente contra a camada Gold já carregada no PostgreSQL local."""
from __future__ import annotations

import os

import pytest

from ai_agent.src.grafo.executor_agente import executar_agente
from ai_agent.src.services.sql_executor import SQLExecutor
from ai_agent.tests.conftest import FakeClienteLLM


@pytest.fixture(scope="module")
def gold_postgres_executor() -> SQLExecutor:
    db_url = os.getenv("AI_AGENT_GOLD_DATABASE_URL")
    if not db_url:
        pytest.skip("Configure AI_AGENT_GOLD_DATABASE_URL para testar a Gold local.")
    if not db_url.lower().startswith(("postgres://", "postgresql://")):
        pytest.fail("AI_AGENT_GOLD_DATABASE_URL deve apontar para PostgreSQL.")

    schema = os.getenv("AI_AGENT_GOLD_SCHEMA", "public")
    executor = SQLExecutor(db_url=db_url, schema=schema)
    verificacao = executor.executar(
        "SELECT COUNT(*) AS total FROM agg_receita_mensal"
    )
    if not verificacao.sucesso:
        pytest.fail(
            "Não foi possível ler agg_receita_mensal no schema Gold configurado: "
            f"{verificacao.erro}"
        )
    if not verificacao.linhas or verificacao.linhas[0]["total"] == 0:
        pytest.fail("A tabela agg_receita_mensal não contém dados.")

    return executor


def test_agente_executa_sql_na_gold_postgres_local(
    gold_postgres_executor: SQLExecutor,
) -> None:
    sql_gold = (
        "SELECT ano, SUM(receita_faturada) AS receita_total "
        "FROM agg_receita_mensal "
        "GROUP BY ano "
        "ORDER BY ano DESC "
        "LIMIT 1"
    )
    llm = FakeClienteLLM(
        mapa_respostas={
            "roteador": (
                '{"rota": "sql", "confianca": 0.96, '
                '"motivo": "Consulta agregada de receita"}'
            ),
            "ESPECIALISTA EM SQL": sql_gold,
            "transformar dados tabulares": "Consulta agregada executada na Gold local.",
        }
    )

    resultado = executar_agente(
        pergunta="Qual foi a receita agregada mais recente disponível?",
        executor=gold_postgres_executor,
        llm=llm,
        sessao_id="teste-gold-postgres-local",
    )

    assert resultado.selo_confianca == "gerada_confiavel"
    assert resultado.sql_gerado is not None
    assert "agg_receita_mensal" in resultado.sql_gerado
    assert resultado.dados_tabela
    assert resultado.dados_tabela[0]["ano"] is not None
    assert resultado.dados_tabela[0]["receita_total"] is not None
    assert resultado.chamadas_llm > 0
