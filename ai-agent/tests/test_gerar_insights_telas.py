"""Geração antecipada: escopo do DELETE, falhas e confirmação do cache."""
from unittest.mock import MagicMock, Mock

import pytest

from ai_agent.scripts import gerar_insights_telas as script


@pytest.fixture
def conexao(monkeypatch):
    connect = MagicMock()
    monkeypatch.setattr(script.psycopg2, "connect", connect)
    return connect


def criar_servico(selo="auditado_llm"):
    servico = Mock()
    servico.db_url = "postgresql://usuario:segredo@host/base"
    servico.obter.return_value = {"selo": selo, "insight_texto": "Texto de teste."}
    servico._ler_cache.return_value = servico.obter.return_value
    return servico


def test_renova_apenas_quatro_pares_globais(conexao, capsys):
    servico = criar_servico()
    assert script.renovar_insights(servico)
    cursor = conexao.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
    assert cursor.execute.call_count == 4
    for chamada, tela in zip(cursor.execute.call_args_list, script.TELAS_GLOBAIS):
        assert chamada.args == (
            "DELETE FROM tb_insights_tela WHERE tela = %s AND entidade_id = %s", (tela, "global")
        )
        servico.obter.assert_any_call(tela, "global")
        servico._ler_cache.assert_any_call(tela, "global")
    saida = capsys.readouterr().out
    assert saida.count("auditado_llm") == 4
    assert "segredo" not in saida and "postgresql" not in saida


@pytest.mark.parametrize("selo,cache", [("template_fallback", None), ("auditado_llm", None)])
def test_nao_declara_sucesso_sem_cache_auditado(conexao, selo, cache):
    servico = criar_servico(selo)
    servico._ler_cache.return_value = cache
    assert not script.renovar_insights(servico)


def test_falha_em_uma_tela_continua_sem_expor_url(conexao, capsys):
    servico = criar_servico()
    servico.obter.side_effect = [RuntimeError(servico.db_url)] + [servico.obter.return_value] * 3
    assert not script.renovar_insights(servico)
    assert servico.obter.call_count == 4
    saida = capsys.readouterr().out
    assert "receita: falha" in saida
    assert "segredo" not in saida and "postgresql" not in saida


def test_main_nao_apaga_cache_em_modo_mock(monkeypatch, conexao):
    monkeypatch.setattr(script, "load_dotenv", Mock())
    monkeypatch.setenv("DATABASE_URL", "postgresql://host/base")
    monkeypatch.setattr(script, "ClienteLLM", Mock(return_value=Mock(forcar_mock=True)))
    assert script.main([]) == 1
    conexao.assert_not_called()
