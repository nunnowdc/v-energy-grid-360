"""O agente grava quem perguntou a partir da sessão, nunca de um id enviado no corpo."""

from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.security.dependencies import get_current_user

USUARIO = {
    "id": UUID("6f1c2b8e-1d2a-4c3b-9e8f-0a1b2c3d4e5f"),
    "nome": "Pessoa da sessão",
    "email": "sessao@example.invalid",
    "perfil": "ATENDIMENTO",
}
OUTRA_PESSOA = "11111111-2222-3333-4444-555555555555"


@pytest.fixture
def client():
    app.dependency_overrides[get_current_user] = lambda: USUARIO
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def _resposta_falsa():
    return SimpleNamespace(
        resposta_texto="Resposta fictícia",
        sql_gerado=None,
        audit_id="a0000000-0000-0000-0000-000000000001",
        selo_confianca="gerada_confiavel",
        fontes_citadas=[],
        tempo_execucao_ms=1.0,
        dashboard=None,
    )


def test_ask_grava_usuario_e_perfil_da_sessao_e_ignora_o_corpo(client, monkeypatch):
    from src.api import ai_router

    chamadas = []
    monkeypatch.setattr(
        ai_router,
        "executar_agente",
        lambda **kwargs: chamadas.append(kwargs) or _resposta_falsa(),
    )

    response = client.post(
        "/api/ai/ask",
        json={"user_id": OUTRA_PESSOA, "session_id": "s1", "message": "Pergunta"},
    )

    assert response.status_code == 200
    assert chamadas[0]["user_id"] == str(USUARIO["id"])
    assert chamadas[0]["perfil"] == "ATENDIMENTO"
    assert OUTRA_PESSOA not in chamadas[0].values()


class ConexaoFalsa:
    """psycopg2 falso: guarda o UPDATE e responde quantas linhas ele mudou."""

    def __init__(self, linhas: int) -> None:
        self.linhas = linhas
        self.comandos: list[tuple[str, tuple]] = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def cursor(self):
        conexao = self

        class Cursor:
            rowcount = 0

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def execute(self, sql, params):
                conexao.comandos.append((sql, params))
                self.rowcount = conexao.linhas

        return Cursor()

    def commit(self):
        pass


@pytest.mark.parametrize("linhas,status", [(1, 200), (0, 404)])
def test_feedback_so_vale_para_as_respostas_da_propria_conta(
    client, monkeypatch, linhas, status
):
    import psycopg2

    conexao = ConexaoFalsa(linhas)
    monkeypatch.setenv("DATABASE_URL", "postgresql://teste@localhost/inexistente")
    monkeypatch.setattr(psycopg2, "connect", lambda *_a, **_k: conexao)

    response = client.post(
        "/api/ai/feedback",
        json={"audit_id": "a0000000-0000-0000-0000-000000000001", "feedback": 1},
    )

    assert response.status_code == status
    sql, params = conexao.comandos[0]
    assert "AND user_id = %s" in sql
    assert params == (1, "a0000000-0000-0000-0000-000000000001", str(USUARIO["id"]))


def test_rota_do_agente_sem_conta_na_requisicao_responde_401():
    from src.api.ai_router import usuario_logado

    sem_conta = SimpleNamespace(state=SimpleNamespace())
    with pytest.raises(HTTPException) as erro:
        usuario_logado(sem_conta)
    assert erro.value.status_code == 401
