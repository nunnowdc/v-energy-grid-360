from __future__ import annotations

from unittest.mock import Mock

import pytest

from ai_agent.src.provedores.cliente_llm import ClienteLLM, RespostaLLM
from ai_agent.src.services.sql_executor import ResultadoExecucaoSQL
from ai_agent.tests.real_llm_eval_support import (
    ClienteOpenRouterLimitado,
    ErroAvaliacaoLLM,
    ExecutorGoldAgregado,
    ValidadorSQLAgregadoGold,
)


def test_cliente_estrito_exige_chave_openrouter(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("LLM_MOCK_MODE", "false")

    with pytest.raises(ErroAvaliacaoLLM, match="OPENROUTER_API_KEY"):
        ClienteOpenRouterLimitado()


def test_cliente_estrito_recusa_modo_mock(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MOCK_MODE", "true")

    with pytest.raises(ErroAvaliacaoLLM, match="LLM_MOCK_MODE"):
        ClienteOpenRouterLimitado()


def test_cliente_estrito_recusa_fallback_e_limita_chamadas(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("NINEROUTER_API_KEY", "fallback-key")
    monkeypatch.setenv("LLM_MOCK_MODE", "false")
    chamada_api = Mock(
        return_value=RespostaLLM(
            texto="resposta",
            tokens_prompt=4,
            tokens_resposta=2,
            provedor_utilizado="mock",
        )
    )
    monkeypatch.setattr(ClienteLLM, "_chamar_api", chamada_api)
    cliente = ClienteOpenRouterLimitado(limite_chamadas=1)

    resposta = cliente.invoke("pergunta")
    assert resposta.provedor_utilizado == "openrouter"
    assert cliente.chamadas_openrouter == 1
    assert cliente.tokens_prompt == 4
    assert cliente.tokens_resposta == 2
    assert cliente.ninerouter_key == ""

    with pytest.raises(ErroAvaliacaoLLM, match="Limite de 1"):
        cliente.invoke("segunda pergunta", resposta_mock="nao usar")
    assert chamada_api.call_count == 1


def test_cliente_estrito_falha_se_openrouter_indisponivel(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("NINEROUTER_API_KEY", "fallback-key")
    monkeypatch.setenv("LLM_MOCK_MODE", "false")
    chamada_api = Mock(side_effect=RuntimeError("rede indisponível"))
    monkeypatch.setattr(ClienteLLM, "_chamar_api", chamada_api)
    cliente = ClienteOpenRouterLimitado()

    with pytest.raises(ErroAvaliacaoLLM, match="A chamada ao OpenRouter falhou"):
        cliente.invoke("pergunta", resposta_mock="nao usar")
    chamada_api.assert_called_once()
    assert chamada_api.call_args.kwargs["url"] == cliente.openrouter_url


def test_validador_aprova_consulta_agregada_com_tamanho_amostral():
    sql = """
        SELECT u.classe, SUM(f.receita_faturada) AS receita_total,
               COUNT(DISTINCT f.id_uc) AS sample_size
        FROM fact_faturamento f
        JOIN dim_unidade_consumidora u ON f.id_uc = u.id_uc
        WHERE u.municipio = 'Olinda' AND f.ano = 2023
        GROUP BY u.classe
    """

    resultado = ValidadorSQLAgregadoGold().validar(sql)

    assert resultado.aprovado is True
    assert resultado.tabelas_detectadas == [
        "fact_faturamento",
        "dim_unidade_consumidora",
    ]


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT id_uc, COUNT(*) AS sample_size FROM fact_faturamento GROUP BY id_uc",
        "SELECT nome_titular, COUNT(*) AS sample_size FROM dim_unidade_consumidora GROUP BY nome_titular",
        (
            "SELECT classe, COUNT(*) AS sample_size "
            "FROM dim_unidade_consumidora "
            "WHERE cpf_cnpj_mascarado = '***' GROUP BY classe"
        ),
        "SELECT classe, SUM(receita_faturada) AS receita FROM fact_faturamento GROUP BY classe",
    ],
)
def test_validador_rejeita_saida_identificavel_ou_sem_prova_amostral(sql):
    resultado = ValidadorSQLAgregadoGold().validar(sql)

    assert resultado.aprovado is False


def test_validador_registra_violacao_de_identificador():
    validador = ValidadorSQLAgregadoGold()

    resultado = validador.validar(
        "SELECT id_uc, COUNT(*) AS sample_size "
        "FROM fact_faturamento GROUP BY id_uc"
    )

    assert resultado.malicioso is True
    assert validador.violacoes_sql_inseguro


def test_executor_suprime_grupos_com_menos_de_dez_registros():
    executor = Mock()
    executor.executar.return_value = ResultadoExecucaoSQL(
        sucesso=True,
        linhas=[
            {"classe": "COMERCIAL", "valor": 100.0, "sample_size": 10},
            {"classe": "RURAL", "valor": 20.0, "sample_size": 9},
        ],
        total_linhas=2,
    )
    validador = ValidadorSQLAgregadoGold()

    resultado = ExecutorGoldAgregado(executor, validador).executar(
        "SELECT classe, SUM(receita_faturada) AS receita, "
        "COUNT(*) AS sample_size FROM fact_faturamento GROUP BY classe"
    )

    assert resultado.sucesso is True
    assert resultado.linhas == [
        {"classe": "COMERCIAL", "valor": 100.0, "sample_size": 10}
    ]
    assert resultado.total_linhas == 1


def test_executor_revalida_sql_antes_de_qualquer_consulta():
    executor = Mock()
    validador = ValidadorSQLAgregadoGold()

    resultado = ExecutorGoldAgregado(executor, validador).executar(
        "SELECT id_uc, COUNT(*) AS sample_size "
        "FROM fact_faturamento GROUP BY id_uc"
    )

    assert resultado.sucesso is False
    executor.executar.assert_not_called()
    assert validador.violacoes_sql_inseguro


@pytest.mark.parametrize(
    "linhas",
    [
        [{"valor": 1.0}],
        [{"sample_size": "invalido"}],
    ],
)
def test_executor_nao_compartilha_resultados_sem_tamanho_amostral(linhas):
    executor = Mock()
    executor.executar.return_value = ResultadoExecucaoSQL(
        sucesso=True,
        linhas=linhas,
        total_linhas=len(linhas),
    )
    validador = ValidadorSQLAgregadoGold()

    resultado = ExecutorGoldAgregado(executor, validador).executar(
        "SELECT classe, SUM(receita_faturada) AS receita, "
        "COUNT(*) AS sample_size FROM fact_faturamento GROUP BY classe"
    )

    assert resultado.sucesso is False
    assert resultado.linhas == []
