"""Contrato HTTP das avaliações do agente contra o golden set."""

from contextlib import contextmanager, nullcontext
from datetime import UTC, datetime
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError, ProgrammingError

from app.controllers.agent_evaluations import get_agent_evaluations_repository
from app.main import app

PRIMEIRA = UUID("11111111-1111-4111-8111-111111111111")
ULTIMA = UUID("22222222-2222-4222-8222-222222222222")


def execucao(id_, dia, aprovados, taxa_execucao):
    return {
        "id": id_,
        "executada_em": datetime(2026, 11, dia, 22, 0, tzinfo=UTC),
        "modelo": "modelo-x",
        "total_casos": 12,
        "casos_aprovados": aprovados,
        "taxa_execucao": taxa_execucao,
        "taxa_component_match": 50.0,
        "taxa_abstencao": 100.0,
        "tokens_medio": 7500.4,
        "duracao_ms": 180000.0,
    }


class EvaluationsFake:
    def __init__(self, tables=True, runs=None):
        self.tables = tables
        self.runs = (
            [execucao(PRIMEIRA, 1, 7, 83.3), execucao(ULTIMA, 2, 9, 100.0)]
            if runs is None
            else runs
        )
        self.cases_of = []
        self.limit = None

    def has_tables(self):
        return self.tables

    def get_runs(self, limite):
        self.limit = limite
        return self.runs

    def get_cases(self, avaliacao_id):
        self.cases_of.append(avaliacao_id)
        return [
            {
                "caso_id": "TC-001",
                "tipo": "sql",
                "pergunta": "Qual o faturamento de Olinda em 2023?",
                "selo": "gerada_confiavel",
                "passou": False,
                "motivo": "Rodou, mas sem a tabela esperada: fact_faturamento",
                "sql_gerado": "SELECT 1 FROM agg_receita_mensal",
                "tokens": 9000,
                "tempo_ms": 15000.0,
            }
        ]


@pytest.fixture
def client():
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.pop(get_agent_evaluations_repository, None)


def _use(fake) -> None:
    app.dependency_overrides[get_agent_evaluations_repository] = lambda: nullcontext(
        fake
    )


def test_runs_in_date_order_and_the_cases_of_the_last_one(client) -> None:
    fake = EvaluationsFake()
    _use(fake)

    response = client.get("/api/ai/evaluations")

    assert response.status_code == 200
    body = response.json()
    assert fake.limit == 30
    assert fake.cases_of == [ULTIMA]
    assert [run["casos_aprovados"] for run in body["execucoes"]] == [7, 9]
    assert body["execucoes"][1] == {
        "id": str(ULTIMA),
        "executada_em": "2026-11-02T22:00:00Z",
        "modelo": "modelo-x",
        "total_casos": 12,
        "casos_aprovados": 9,
        "taxa_execucao": 100.0,
        "taxa_component_match": 50.0,
        "taxa_abstencao": 100.0,
        "tokens_medio": 7500.4,
        "duracao_ms": 180000.0,
    }
    assert body["casos"][0]["motivo"] == (
        "Rodou, mas sem a tabela esperada: fact_faturamento"
    )


def test_before_the_first_run_the_lists_are_empty(client) -> None:
    fake = EvaluationsFake(tables=False)
    _use(fake)

    response = client.get("/api/ai/evaluations")

    assert response.status_code == 200
    assert response.json() == {"execucoes": [], "casos": []}
    assert fake.limit is None


def test_tables_without_runs_also_come_empty(client) -> None:
    fake = EvaluationsFake(runs=[])
    _use(fake)

    assert client.get("/api/ai/evaluations").json() == {"execucoes": [], "casos": []}
    assert fake.cases_of == []


def test_parameters_are_rejected_before_opening_the_connection(client) -> None:
    opened = []

    @contextmanager
    def tracked():
        opened.append(True)
        yield EvaluationsFake()

    # Como a rota recebe: o objeto que abre a conexão, ainda sem abrir
    app.dependency_overrides[get_agent_evaluations_repository] = lambda: tracked()

    response = client.get("/api/ai/evaluations?limite=5")

    assert response.status_code == 422
    assert opened == []


@pytest.mark.parametrize(
    "error",
    [
        ProgrammingError("SELECT", {}, Exception("column does not exist")),
        OperationalError("SELECT", {}, Exception("connection refused")),
    ],
)
def test_database_failures_are_unavailable(client, error) -> None:
    class Broken(EvaluationsFake):
        def has_tables(self):
            raise error

    _use(Broken())

    response = client.get("/api/ai/evaluations")

    assert response.status_code == 503
    assert response.json() == {"detail": "Avaliações do agente indisponíveis"}


def test_unexpected_failure_does_not_leak_details(client) -> None:
    class Broken(EvaluationsFake):
        def get_runs(self, limite):
            raise ValueError("detalhe interno")

    _use(Broken())

    response = client.get("/api/ai/evaluations")

    assert response.status_code == 500
    assert response.json() == {"detail": "Erro interno"}
