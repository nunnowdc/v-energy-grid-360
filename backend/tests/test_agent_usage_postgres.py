"""Consultas do uso do agente em PostgreSQL descartável, com o fuso de Recife."""

from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.repositories.agent_usage import AgentUsageRepository

pytest_plugins = ("test_inspection_orders_postgres",)

# (instante em UTC, selo, tempo_ms, tokens_prompt, tokens_resposta, feedback, perfil)
PERGUNTAS = [
    # 30/10 às 09:00 de Recife: antes da janela de 31/10 a 01/11
    ("2026-10-30 12:00:00+00", "certificada", 100.0, 10, 5, None, "ADMIN_TI"),
    # 31/10 às 23:30 de Recife, já 01/11 em UTC: conta no dia 31/10
    ("2026-11-01 02:30:00+00", "gerada_confiavel", 1000.0, 600, 400, 1, "DIRETORIA"),
    ("2026-10-31 15:00:00+00", "recusa_honesta", 3000.0, None, None, -1, None),
    # 01/11 às 00:10 de Recife
    ("2026-11-01 03:10:00+00", "documental_rag", 2000.0, 300, 100, None, "ATENDIMENTO"),
    ("2026-11-01 14:00:00+00", "erro_bloqueado", 4000.0, 50, 0, None, "ADMIN_TI"),
    ("2026-11-01 16:00:00+00", "certificada", 500.0, 0, 0, 1, "ADMIN_TI"),
]
INICIO = date(2026, 10, 31)
FIM = date(2026, 11, 1)


@pytest.fixture(scope="module")
def usage_engine(orders_engine: Engine) -> Engine:
    """Só as colunas da auditoria que a tela lê, com os tipos do ai-agent."""
    with orders_engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE tb_auditoria_agente ("
            "id UUID PRIMARY KEY, "
            "data_hora TIMESTAMPTZ NOT NULL, "
            "pergunta_original TEXT NOT NULL, "
            "selo_confianca VARCHAR(50) NOT NULL, "
            "tempo_execucao_ms FLOAT NOT NULL DEFAULT 0, "
            "tokens_prompt INTEGER DEFAULT 0, "
            "tokens_resposta INTEGER DEFAULT 0, "
            "feedback_usuario SMALLINT, "
            "perfil VARCHAR(50))"
        )
        connection.execute(
            text(
                "INSERT INTO tb_auditoria_agente (id, data_hora, pergunta_original, "
                "selo_confianca, tempo_execucao_ms, tokens_prompt, tokens_resposta, "
                "feedback_usuario, perfil) VALUES (:id, CAST(:data_hora AS timestamptz), "
                ":pergunta, :selo, :tempo, :prompt, :resposta, :feedback, :perfil)"
            ),
            [
                {
                    "id": uuid4(),
                    "data_hora": data_hora,
                    "pergunta": f"Pergunta {indice}",
                    "selo": selo,
                    "tempo": tempo,
                    "prompt": prompt,
                    "resposta": resposta,
                    "feedback": feedback,
                    "perfil": perfil,
                }
                for indice, (
                    data_hora,
                    selo,
                    tempo,
                    prompt,
                    resposta,
                    feedback,
                    perfil,
                ) in enumerate(PERGUNTAS)
            ],
        )
    return orders_engine


def test_summary_counts_only_the_window_by_seal(usage_engine: Engine) -> None:
    with usage_engine.connect() as connection:
        summary = AgentUsageRepository(connection).get_summary(INICIO, FIM)

    assert summary["perguntas"] == 5
    assert summary["respondidas_com_dados"] == 2
    assert summary["respondidas_com_documentos"] == 1
    assert summary["recusas"] == 1
    assert summary["erros"] == 1
    assert float(summary["tempo_medio_ms"]) == 2100.0
    # 95% de 5 tempos (500, 1000, 2000, 3000, 4000), interpolado
    assert float(summary["tempo_p95_ms"]) == pytest.approx(3800.0)
    # Tokens nulos contam como zero: (1000 + 0 + 400 + 50 + 0) / 5
    assert float(summary["tokens_medio"]) == 290.0
    assert summary["tokens_total"] == 1450
    assert summary["avaliacoes_uteis"] == 2
    assert summary["avaliacoes_inuteis"] == 1


def test_days_follow_recife_time_not_utc(usage_engine: Engine) -> None:
    with usage_engine.connect() as connection:
        daily = AgentUsageRepository(connection).get_daily(INICIO, FIM)

    assert [(row["dia"], row["perguntas"]) for row in daily] == [
        (date(2026, 10, 31), 2),
        (date(2026, 11, 1), 3),
    ]
    dia_31, dia_1 = daily
    assert (dia_31["respondidas"], dia_31["recusas"], dia_31["erros"]) == (1, 1, 0)
    assert (dia_1["respondidas"], dia_1["recusas"], dia_1["erros"]) == (2, 0, 1)
    assert float(dia_31["tempo_medio_ms"]) == 2000.0
    assert float(dia_1["tokens_medio"]) == pytest.approx(150.0)


def test_latest_questions_come_newest_first_and_respect_the_limit(
    usage_engine: Engine,
) -> None:
    with usage_engine.connect() as connection:
        latest = AgentUsageRepository(connection).get_latest(INICIO, FIM, 3)

    assert [row["selo"] for row in latest] == [
        "certificada",
        "erro_bloqueado",
        "documental_rag",
    ]
    assert latest[0]["tokens"] == 0
    assert latest[0]["avaliacao"] == 1
    assert latest[2]["perfil"] == "ATENDIMENTO"


def test_question_without_tokens_has_zero_tokens(usage_engine: Engine) -> None:
    with usage_engine.connect() as connection:
        latest = AgentUsageRepository(connection).get_latest(INICIO, INICIO, 10)

    recusa = next(row for row in latest if row["selo"] == "recusa_honesta")
    assert recusa["tokens"] == 0
    assert recusa["perfil"] is None
    assert recusa["avaliacao"] == -1


def test_today_is_a_date_in_recife(usage_engine: Engine) -> None:
    with usage_engine.connect() as connection:
        assert isinstance(AgentUsageRepository(connection).get_today(), date)
