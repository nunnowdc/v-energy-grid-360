"""
Testes para o novo validador padrão do grafo e o uso de sql_normalizado.
Cobre os requisitos do Passo 5.
"""
from __future__ import annotations

import pytest
from src.grafo.construtor_grafo import _validador_padrao
from security.validador_sqlglot import ValidadorSQLGlotPostgres
from src.nos.no_valida_sql import no_valida_sql


def test_validador_padrao_retorna_instancia_correta():
    """Confere se _validador_padrao() devolve ValidadorSQLGlotPostgres."""
    validador = _validador_padrao()
    assert isinstance(validador, ValidadorSQLGlotPostgres)


def test_validador_bloqueia_coluna_pessoal_com_join():
    """
    Com o SQL do trace (nome_titular, cpf_cnpj_mascarado com JOIN):
    aprovado=False e codigo="COLUMN_NOT_ALLOWED" (ou equivalente na validação).
    """
    validador = _validador_padrao()
    sql = (
        "SELECT DISTINCT d.nome_titular, d.cpf_cnpj_mascarado "
        "FROM dim_unidade_consumidora d "
        "JOIN fact_faturamento f ON d.id_uc = f.id_uc"
    )
    resultado = validador.validar(sql)
    assert not resultado.aprovado
    # O código de erro para colunas não permitidas / pessoais
    assert resultado.codigo == "COLUMN_NOT_ALLOWED"


def test_validador_permite_funcao_unaccent_e_contagem():
    """
    SELECT COUNT(DISTINCT id_uc) FROM fact_faturamento WHERE unaccent(lower(status)) = unaccent(lower('EM_ABERTO'))
    Deve retornar aprovado=True.
    """
    validador = _validador_padrao()
    sql = (
        "SELECT COUNT(DISTINCT id_uc) FROM fact_faturamento "
        "WHERE unaccent(lower(status)) = unaccent(lower('EM_ABERTO'))"
    )
    resultado = validador.validar(sql)
    assert resultado.aprovado


def test_validador_rejeita_tabela_fora_da_lista():
    """
    SELECT titulo FROM tb_auditoria_agente: aprovado=False (tabela fora da lista Gold).
    """
    validador = _validador_padrao()
    sql = "SELECT titulo FROM tb_auditoria_agente"
    resultado = validador.validar(sql)
    assert not resultado.aprovado


def test_no_valida_sql_atualiza_sql_normalizado_no_estado():
    """
    no_valida_sql com o validador oficial e um SQL aprovado:
    o SQL do estado passa a ser o normalizado (contém LIMIT).
    """
    validador = _validador_padrao()
    sql_original = "SELECT id_uc FROM dim_unidade_consumidora"
    state = {
        "sql_gerado": sql_original,
        "tentativas_sql": 0,
        "motivo_recusa": None,
    }

    resultado_no = no_valida_sql(state, validador)

    # O nó agora retorna o SQL normalizado no dicionário resultante, que é atualizado no estado pelo grafo.
    # Verificamos no resultado_no (e atualizamos o state caso o teste simule o comportamento do grafo).
    if "sql_gerado" in resultado_no:
        state["sql_gerado"] = resultado_no["sql_gerado"]

    assert "sql_gerado" in state
    assert "LIMIT" in state["sql_gerado"].upper()
    assert resultado_no["erro_validacao_ou_execucao"] is None
