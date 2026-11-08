"""permission denied (42501): sem retry, mensagem sem tabela/coluna, motivo gravado."""
from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock

from src.nos.no_executa_sql import no_executa_sql, rota_pos_execucao
from src.nos.no_recusa_honesta import no_recusa_honesta
from src.services.sql_executor import ResultadoExecucaoSQL, SQLExecutor


class _ErroPrivilegio(Exception):
    pgcode = "42501"


def _psycopg2_que_falha(monkeypatch, erro):
    cur = MagicMock()
    cur.execute.side_effect = erro
    cur.__enter__.return_value = cur
    conn = MagicMock()
    conn.cursor.return_value = cur
    mod = types.ModuleType("psycopg2")
    mod.connect = MagicMock(return_value=conn)
    extras = types.ModuleType("psycopg2.extras")
    extras.RealDictCursor = object
    monkeypatch.setitem(sys.modules, "psycopg2", mod)
    monkeypatch.setitem(sys.modules, "psycopg2.extras", extras)


def test_executor_marca_42501(monkeypatch):
    monkeypatch.delenv("USE_DB_ROLES", raising=False)
    _psycopg2_que_falha(monkeypatch, _ErroPrivilegio('permission denied for table fila_inspecao'))
    res = SQLExecutor(db_url="postgresql://x/y").executar("SELECT 1")
    assert not res.sucesso and res.sem_permissao


def test_executor_outro_erro_nao_marca(monkeypatch):
    monkeypatch.delenv("USE_DB_ROLES", raising=False)
    _psycopg2_que_falha(monkeypatch, RuntimeError("boom"))
    res = SQLExecutor(db_url="postgresql://x/y").executar("SELECT 1")
    assert not res.sucesso and not res.sem_permissao


def test_fluxo_sem_retry_mensagem_e_motivo():
    executor = MagicMock()
    executor.executar.return_value = ResultadoExecucaoSQL(
        sucesso=False, erro="permission denied for table fila_inspecao", sem_permissao=True
    )
    state = {"sql_gerado": "SELECT 1", "tentativas_sql": 1, "perfil": "OPERACAO"}
    state.update(no_executa_sql(state, executor))
    assert state["motivo_recusa"] == "sem_permissao"
    assert rota_pos_execucao(state) == "recusa"  # mesmo com tentativas < MAX

    saida = no_recusa_honesta({**state, "tentativas_sql": 2})
    assert saida["texto_resposta"] == (
        "Seu perfil (OPERACAO) não tem permissão para consultar os dados "
        "necessários para essa pergunta."
    )
    assert "fila_inspecao" not in saida["texto_resposta"]
    assert saida["motivo_recusa"] == "sem_permissao"
    assert "permission denied" in state["erro_validacao_ou_execucao"]  # vai para erro_mensagem
