"""Testes de USE_DB_ROLES no agente: mock de cursor/conexão, sem Postgres."""
from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock

import pytest

from src.nos.no_cache_parametrizado import _template_do_banco
from src.nos.no_finaliza_auditoria import _gravar_auditoria
from src.services import conexao_banco
from src.services.conexao_banco import (
    ExecutorComPerfil,
    aplicar_perfil,
    url_do_banco,
)
from src.services.sql_executor import SQLExecutor


@pytest.fixture
def desligada(monkeypatch):
    monkeypatch.delenv("USE_DB_ROLES", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://admin@h/db")
    monkeypatch.setenv("PORTAL_APP_DATABASE_URL", "postgresql+psycopg2://app@h/db")


@pytest.fixture
def ligada(monkeypatch):
    monkeypatch.setenv("USE_DB_ROLES", "true")
    monkeypatch.setenv("DATABASE_URL", "postgresql://admin@h/db")
    monkeypatch.setenv("PORTAL_APP_DATABASE_URL", "postgresql+psycopg2://app@h/db")


def test_url_desligada_usa_database_url(desligada):
    assert url_do_banco() == "postgresql://admin@h/db"


def test_url_ligada_usa_portal_app_sem_driver(ligada):
    assert url_do_banco() == "postgresql://app@h/db"


def test_url_ligada_sem_portal_app_falha(ligada, monkeypatch):
    monkeypatch.delenv("PORTAL_APP_DATABASE_URL")
    with pytest.raises(RuntimeError):
        url_do_banco()


def test_aplicar_perfil_desligada_nao_faz_nada(desligada):
    cur = MagicMock()
    aplicar_perfil(cur, "QUALQUER")
    aplicar_perfil(cur, None)
    cur.execute.assert_not_called()


@pytest.mark.parametrize("perfil", list(conexao_banco.PERFIL_PARA_ROLE))
def test_aplicar_perfil_ligada_roda_set_local_role(ligada, perfil):
    cur = MagicMock()
    aplicar_perfil(cur, perfil)
    cur.execute.assert_called_once_with(f'SET LOCAL ROLE "perfil_{perfil.lower()}"')


@pytest.mark.parametrize("perfil", [None, "ROOT", "perfil_diretoria", 'X"; DROP'])
def test_aplicar_perfil_ligada_recusa_invalido(ligada, perfil):
    cur = MagicMock()
    with pytest.raises(ValueError):
        aplicar_perfil(cur, perfil)
    cur.execute.assert_not_called()


def test_executor_com_perfil_repassa_perfil():
    base = MagicMock()
    ExecutorComPerfil(base, "PERDAS").executar("SELECT 1")
    base.executar.assert_called_once_with("SELECT 1", perfil="PERDAS")


def _falso_psycopg2(monkeypatch, linhas):
    cur = MagicMock()
    cur.fetchall.return_value = linhas
    cur.__enter__.return_value = cur
    conn = MagicMock()
    conn.cursor.return_value = cur
    mod = types.ModuleType("psycopg2")
    mod.connect = MagicMock(return_value=conn)
    extras = types.ModuleType("psycopg2.extras")
    extras.RealDictCursor = object
    mod.extras = extras
    monkeypatch.setitem(sys.modules, "psycopg2", mod)
    monkeypatch.setitem(sys.modules, "psycopg2.extras", extras)
    return conn, cur


def test_executor_ligada_readonly_transacao_com_role_e_rollback(ligada, monkeypatch):
    conn, cur = _falso_psycopg2(monkeypatch, [{"a": 1}])
    res = SQLExecutor().executar("SELECT 1", perfil="DIRETORIA")
    assert res.sucesso and res.linhas == [{"a": 1}]
    conn.set_session.assert_called_once_with(readonly=True, autocommit=False)
    comandos = [c.args[0] for c in cur.execute.call_args_list]
    assert comandos[0] == 'SET LOCAL ROLE "perfil_diretoria"'
    assert comandos[1].startswith("SELECT 1")
    conn.rollback.assert_called_once()
    conn.close.assert_called_once()


def test_executor_ligada_sem_perfil_nao_executa_sql(ligada, monkeypatch):
    conn, cur = _falso_psycopg2(monkeypatch, [{"a": 1}])
    res = SQLExecutor().executar("SELECT 1")
    assert not res.sucesso
    cur.execute.assert_not_called()
    conn.rollback.assert_called_once()


def test_executor_desligada_mantem_autocommit_sem_role(desligada, monkeypatch):
    conn, cur = _falso_psycopg2(monkeypatch, [{"a": 1}])
    res = SQLExecutor().executar("SELECT 1", perfil="DIRETORIA")
    assert res.sucesso
    conn.set_session.assert_called_once_with(readonly=True, autocommit=True)
    assert all("ROLE" not in c.args[0] for c in cur.execute.call_args_list)
    conn.rollback.assert_not_called()


def test_template_do_banco_aplica_perfil_antes_da_consulta(ligada, monkeypatch):
    conn, cur = _falso_psycopg2(monkeypatch, None)
    cur.fetchone.return_value = ("SELECT 1",)
    conn.__enter__.return_value = conn
    assert _template_do_banco("postgresql://x", "esq", "ATENDIMENTO") == "SELECT 1"
    assert cur.execute.call_args_list[0].args[0] == 'SET LOCAL ROLE "perfil_atendimento"'


def test_auditoria_aplica_perfil_antes_do_information_schema(ligada, monkeypatch):
    conn, cur = _falso_psycopg2(monkeypatch, None)
    conn.__enter__.return_value = conn
    cur.fetchall.return_value = [("id",)]
    _gravar_auditoria({"id": "1", "perfil": "ADMIN_TI"}, "postgresql://x")
    assert cur.execute.call_args_list[0].args[0] == 'SET LOCAL ROLE "perfil_admin_ti"'
