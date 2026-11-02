"""Avaliações gravadas pelo ai-agent e lidas pelo backend, em PostgreSQL descartável."""

import pytest
from sqlalchemy.engine import Engine

# O gravador de verdade do ai-agent: o conftest importa o app.main, que põe o
# ai-agent no caminho de importação (o mesmo que o test_rbac_http faz com os insights)
from src.avaliacao.armazenamento import gravar_execucao

from app.repositories.agent_evaluations import AgentEvaluationsRepository

pytest_plugins = ("test_inspection_orders_postgres",)


def execucao(aprovados: int, casos: list[tuple[str, bool]]) -> dict:
    return {
        "total_casos": len(casos),
        "casos_aprovados": aprovados,
        "taxa_execucao": 75.0,
        "taxa_component_match": None,
        "taxa_abstencao": 100.0,
        "tokens_medio": 1234.5,
        "duracao_ms": 9000.0,
        "casos": [
            {
                "caso_id": caso_id,
                "tipo": "sql",
                "pergunta": f"Pergunta {caso_id}",
                "selo": "gerada_confiavel",
                "passou": passou,
                "motivo": "Rodou a consulta com as tabelas esperadas",
                "sql_gerado": "SELECT 1",
                "tokens": 1000,
                "tempo_ms": 1500.0,
            }
            for caso_id, passou in casos
        ],
    }


def _gravar(engine: Engine, dados: dict, modelo: str) -> str:
    conexao = engine.raw_connection()
    try:
        return gravar_execucao(conexao, dados, modelo)
    finally:
        conexao.close()


@pytest.fixture(scope="module")
def evaluations_engine(orders_engine: Engine) -> Engine:
    return orders_engine


def test_without_the_script_the_tables_do_not_exist(evaluations_engine) -> None:
    with evaluations_engine.connect() as connection:
        assert AgentEvaluationsRepository(connection).has_tables() is False


def test_backend_reads_what_the_ai_agent_writes(evaluations_engine) -> None:
    primeira = _gravar(
        evaluations_engine, execucao(1, [("TC-002", False), ("TC-001", True)]), "a"
    )
    ultima = _gravar(evaluations_engine, execucao(2, [("TC-001", True)]), "b")

    with evaluations_engine.connect() as connection:
        repository = AgentEvaluationsRepository(connection)
        assert repository.has_tables() is True
        runs = repository.get_runs(30)
        cases = repository.get_cases(runs[0]["id"])

    assert [str(run["id"]) for run in runs] == [primeira, ultima]
    assert [run["modelo"] for run in runs] == ["a", "b"]
    assert runs[0]["taxa_component_match"] is None
    assert runs[0]["executada_em"] <= runs[1]["executada_em"]
    # Na ordem do golden set, não na de gravação
    assert [(case["caso_id"], case["passou"]) for case in cases] == [
        ("TC-001", True),
        ("TC-002", False),
    ]


def test_runs_keep_only_the_most_recent_ones(evaluations_engine) -> None:
    with evaluations_engine.connect() as connection:
        runs = AgentEvaluationsRepository(connection).get_runs(1)

    assert len(runs) == 1
    assert runs[0]["modelo"] == "b"
