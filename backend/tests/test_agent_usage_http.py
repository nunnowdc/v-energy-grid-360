"""Contrato HTTP do uso do agente de IA, lido da auditoria de cada pergunta."""

from contextlib import contextmanager, nullcontext
from datetime import UTC, date, datetime
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError, ProgrammingError

from app.controllers.agent_usage import get_agent_usage_repository
from app.main import app

HOJE = date(2026, 11, 1)
ID_PERGUNTA = UUID("9461c996-9b95-4306-af80-773f990942a0")


class AuditFake:
    def __init__(self, empty: bool = False) -> None:
        self.empty = empty
        self.calls: list[tuple] = []

    def get_today(self) -> date:
        return HOJE

    def get_summary(self, inicio: date, fim: date) -> dict[str, object]:
        self.calls.append(("summary", inicio, fim))
        if self.empty:
            return {
                "perguntas": 0,
                "respondidas_com_dados": 0,
                "respondidas_com_documentos": 0,
                "recusas": 0,
                "erros": 0,
                "tempo_medio_ms": None,
                "tempo_p95_ms": None,
                "tokens_medio": None,
                "tokens_total": 0,
                "avaliacoes_uteis": 0,
                "avaliacoes_inuteis": 0,
            }
        return {
            "perguntas": 5,
            "respondidas_com_dados": 3,
            "respondidas_com_documentos": 1,
            "recusas": 1,
            "erros": 0,
            # Como o Postgres devolve avg e sum: Decimal e float
            "tempo_medio_ms": 1500.5,
            "tempo_p95_ms": 4000.0,
            "tokens_medio": 800,
            "tokens_total": 4000,
            "avaliacoes_uteis": 2,
            "avaliacoes_inuteis": 1,
        }

    def get_daily(self, inicio: date, fim: date) -> list[dict[str, object]]:
        self.calls.append(("daily", inicio, fim))
        if self.empty:
            return []
        return [
            {
                "dia": date(2026, 10, 30),
                "perguntas": 2,
                "respondidas": 1,
                "recusas": 1,
                "erros": 0,
                "tempo_medio_ms": 1000,
                "tokens_medio": 700,
            },
            {
                "dia": HOJE,
                "perguntas": 3,
                "respondidas": 3,
                "recusas": 0,
                "erros": 0,
                "tempo_medio_ms": 1834.0,
                "tokens_medio": 866.7,
            },
        ]

    def get_latest(
        self, inicio: date, fim: date, limite: int
    ) -> list[dict[str, object]]:
        self.calls.append(("latest", inicio, fim, limite))
        if self.empty:
            return []
        return [
            {
                "id": ID_PERGUNTA,
                "data_hora": datetime(2026, 11, 1, 15, 30, tzinfo=UTC),
                "pergunta": "Qual o faturamento de Recife em 2024?",
                "perfil": "ADMIN_TI",
                "selo": "certificada",
                "tempo_ms": 1200.0,
                "tokens": 900,
                "avaliacao": 1,
            },
            {
                "id": UUID("00000000-0000-4000-8000-000000000001"),
                "data_hora": datetime(2026, 10, 30, 12, 0, tzinfo=UTC),
                "pergunta": "Quem ganha a copa?",
                "perfil": None,
                "selo": "recusa_honesta",
                "tempo_ms": 300.0,
                "tokens": 0,
                "avaliacao": None,
            },
        ]


@pytest.fixture
def client():
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.pop(get_agent_usage_repository, None)


def _use(fake) -> None:
    app.dependency_overrides[get_agent_usage_repository] = lambda: nullcontext(fake)


def test_default_window_is_the_last_30_days_ending_today(client) -> None:
    fake = AuditFake()
    _use(fake)

    response = client.get("/api/ai/usage")

    assert response.status_code == 200
    body = response.json()
    assert body["inicio"] == "2026-10-03"
    assert body["fim"] == "2026-11-01"
    assert fake.calls == [
        ("summary", date(2026, 10, 3), HOJE),
        ("daily", date(2026, 10, 3), HOJE),
        ("latest", date(2026, 10, 3), HOJE, 20),
    ]
    assert body["resumo"] == {
        "perguntas": 5,
        "respondidas_com_dados": 3,
        "respondidas_com_documentos": 1,
        "recusas": 1,
        "erros": 0,
        "tempo_medio_ms": 1500.5,
        "tempo_p95_ms": 4000.0,
        "tokens_medio": 800.0,
        "tokens_total": 4000,
        "avaliacoes_uteis": 2,
        "avaliacoes_inuteis": 1,
    }


def test_every_day_of_the_window_appears_even_without_questions(client) -> None:
    _use(AuditFake())

    por_dia = client.get("/api/ai/usage").json()["por_dia"]

    assert len(por_dia) == 30
    assert [dia["dia"] for dia in por_dia[:2]] == ["2026-10-03", "2026-10-04"]
    assert por_dia[0] == {
        "dia": "2026-10-03",
        "perguntas": 0,
        "respondidas": 0,
        "recusas": 0,
        "erros": 0,
        "tempo_medio_ms": None,
        "tokens_medio": None,
    }
    assert por_dia[-3]["dia"] == "2026-10-30"
    assert por_dia[-3]["perguntas"] == 2
    assert por_dia[-1] == {
        "dia": "2026-11-01",
        "perguntas": 3,
        "respondidas": 3,
        "recusas": 0,
        "erros": 0,
        "tempo_medio_ms": 1834.0,
        "tokens_medio": 866.7,
    }


def test_latest_questions_keep_the_audit_id_for_the_step_by_step(client) -> None:
    _use(AuditFake())

    ultimas = client.get("/api/ai/usage").json()["ultimas"]

    assert ultimas[0] == {
        "id": str(ID_PERGUNTA),
        "data_hora": "2026-11-01T15:30:00Z",
        "pergunta": "Qual o faturamento de Recife em 2024?",
        "perfil": "ADMIN_TI",
        "selo": "certificada",
        "tempo_ms": 1200.0,
        "tokens": 900,
        "avaliacao": 1,
    }
    assert ultimas[1]["perfil"] is None
    assert ultimas[1]["avaliacao"] is None


@pytest.mark.parametrize("dias,inicio", [("7", "2026-10-26"), ("90", "2026-08-04")])
def test_week_and_quarter_windows(client, dias, inicio) -> None:
    _use(AuditFake())

    body = client.get(f"/api/ai/usage?dias={dias}").json()

    assert body["inicio"] == inicio
    assert len(body["por_dia"]) == int(dias)


def test_period_without_questions_has_empty_averages(client) -> None:
    _use(AuditFake(empty=True))

    body = client.get("/api/ai/usage?dias=7").json()

    assert body["resumo"]["perguntas"] == 0
    assert body["resumo"]["tempo_medio_ms"] is None
    assert body["resumo"]["tokens_total"] == 0
    assert all(dia["perguntas"] == 0 for dia in body["por_dia"])
    assert body["ultimas"] == []


@pytest.mark.parametrize(
    "query",
    ["dias=0", "dias=15", "dias=abc", "dias=-7", "dias=7&dias=30", "inicio=2026-10-01"],
)
def test_invalid_parameters_are_rejected_before_opening_the_connection(
    client, query
) -> None:
    opened = []

    @contextmanager
    def tracked():
        opened.append(True)
        yield AuditFake()

    # Como a rota recebe: o objeto que abre a conexão, ainda sem abrir
    app.dependency_overrides[get_agent_usage_repository] = lambda: tracked()

    response = client.get(f"/api/ai/usage?{query}")

    assert response.status_code == 422
    assert opened == []


@pytest.mark.parametrize(
    "error",
    [
        # Setup sem as tabelas da IA: a tb_auditoria_agente não existe
        ProgrammingError("SELECT", {}, Exception('relation "tb_auditoria_agente"')),
        OperationalError("SELECT", {}, Exception("connection refused")),
    ],
)
def test_missing_audit_table_or_database_is_unavailable(client, error) -> None:
    class Broken(AuditFake):
        def get_today(self) -> date:
            raise error

    _use(Broken())

    response = client.get("/api/ai/usage")

    assert response.status_code == 503
    assert response.json() == {"detail": "Auditoria do agente indisponível"}


def test_unexpected_failure_does_not_leak_details(client) -> None:
    class Broken(AuditFake):
        def get_summary(self, inicio: date, fim: date) -> dict[str, object]:
            raise ValueError("detalhe interno")

    _use(Broken())

    response = client.get("/api/ai/usage")

    assert response.status_code == 500
    assert response.json() == {"detail": "Erro interno"}
