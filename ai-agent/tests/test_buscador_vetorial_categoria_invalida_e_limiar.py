"""
Testes unitários para o BuscadorVetorial:
- Tratamento de categorias inválidas (resiliência contra ValidationError).
- Suporte à nova categoria 'perfis_dados'.
- Aplicação de limiar em Python com log do melhor chunk.
- Filtro parametrizado de categoria (sem interpolação direta no SQL).
- Configuração de limiar via variável de ambiente RAG_LIMIAR_SIMILARIDADE.
"""
from __future__ import annotations

import logging
from unittest.mock import MagicMock
import pytest

from src.rag.buscador_vetorial import BuscadorVetorial, LIMIAR_SIMILARIDADE


@pytest.fixture(autouse=True)
def mock_embedding(monkeypatch):
    """Evita carregar o modelo de sentence-transformers nos testes."""
    monkeypatch.setattr(
        BuscadorVetorial,
        "_gerar_embedding",
        lambda self, texto: [0.01] * 384,
    )


@pytest.fixture
def mock_db(monkeypatch):
    """Cria um mock para psycopg2.connect retornando o cursor configurado."""
    def _criar_mock(rows):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = rows

        mock_conn = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        monkeypatch.setattr("psycopg2.connect", lambda *args, **kwargs: mock_conn)
        return mock_cursor

    return _criar_mock


def test_categoria_invalida_ignorada_e_validas_retornam(mock_db, caplog):
    """Linha com categoria desconhecida/inválida é ignorada via ValidationError sem derrubar a busca."""
    rows = [
        {
            "id": "11111111-1111-1111-1111-111111111111",
            "categoria": "categoria_desconhecida_xyz",
            "titulo": "Chunk Invalido",
            "conteudo": "Conteudo invalido",
            "fonte": "Fonte X",
            "metadados": {},
            "similaridade": 0.90,
        },
        {
            "id": "22222222-2222-2222-2222-222222222222",
            "categoria": "glossario",
            "titulo": "Conta de Luz",
            "conteudo": "Fatura mensal",
            "fonte": "Glossario",
            "metadados": {},
            "similaridade": 0.85,
        },
    ]
    mock_db(rows)
    buscador = BuscadorVetorial(db_url="postgresql://mock:5432/db")

    with caplog.at_level(logging.WARNING):
        resultado = buscador.buscar(query="conta de luz")

    assert len(resultado.chunks) == 1
    assert resultado.chunks[0].id == "22222222-2222-2222-2222-222222222222"
    assert resultado.chunks[0].categoria == "glossario"
    assert resultado.top_score == 0.90
    assert resultado.houve_corte_limiar is False
    assert "11111111-1111-1111-1111-111111111111 ignorado" in caplog.text


def test_categoria_perfis_dados_aceita(mock_db):
    """Linha com a categoria 'perfis_dados' é aceita com sucesso pelo modelo Pydantic."""
    rows = [
        {
            "id": "33333333-3333-3333-3333-333333333333",
            "categoria": "perfis_dados",
            "titulo": "Perfil Faturas: Inconsistência de Datas",
            "conteudo": "Datas futuras identificadas e tratadas na silver.",
            "fonte": "Perfil de Dados - faturas",
            "metadados": {"tabela": "fact_faturamento"},
            "similaridade": 0.82,
        }
    ]
    mock_db(rows)
    buscador = BuscadorVetorial(db_url="postgresql://mock:5432/db")

    resultado = buscador.buscar(query="problemas em faturas")

    assert len(resultado.chunks) == 1
    assert resultado.chunks[0].categoria == "perfis_dados"
    assert resultado.chunks[0].titulo == "Perfil Faturas: Inconsistência de Datas"
    assert resultado.top_score == 0.82
    assert resultado.houve_corte_limiar is False


def test_melhor_score_abaixo_do_limiar(mock_db, caplog):
    """Quando o melhor chunk fica abaixo do limiar, retorna vazio com houve_corte_limiar=True e loga o título."""
    rows = [
        {
            "id": "44444444-4444-4444-4444-444444444444",
            "categoria": "prodist",
            "titulo": "Indicador DEC Regulatório",
            "conteudo": "Definição do DEC",
            "fonte": "PRODIST",
            "metadados": {},
            "similaridade": 0.65,  # Abaixo do limiar 0.70
        },
        {
            "id": "55555555-5555-5555-5555-555555555555",
            "categoria": "prodist",
            "titulo": "Indicador FEC",
            "conteudo": "Definição do FEC",
            "fonte": "PRODIST",
            "metadados": {},
            "similaridade": 0.60,
        },
    ]
    mock_db(rows)
    buscador = BuscadorVetorial(db_url="postgresql://mock:5432/db", limiar=0.70)

    with caplog.at_level(logging.INFO):
        resultado = buscador.buscar(query="O que é DEC e FEC?")

    assert resultado.chunks == []
    assert resultado.top_score == 0.65
    assert resultado.houve_corte_limiar is True
    assert "melhor chunk 'Indicador DEC Regulatório'" in caplog.text
    assert "score 0.650, abaixo do limiar 0.70" in caplog.text


def test_melhor_score_acima_do_limiar_filtra_somente_validos(mock_db):
    """Devolve apenas os chunks que atendem ao limiar, preservando o top_score da busca."""
    rows = [
        {
            "id": "1",
            "categoria": "glossario",
            "titulo": "Chunk A",
            "conteudo": "Texto A",
            "fonte": "",
            "metadados": {},
            "similaridade": 0.85,
        },
        {
            "id": "2",
            "categoria": "glossario",
            "titulo": "Chunk B",
            "conteudo": "Texto B",
            "fonte": "",
            "metadados": {},
            "similaridade": 0.71,
        },
        {
            "id": "3",
            "categoria": "glossario",
            "titulo": "Chunk C",
            "conteudo": "Texto C",
            "fonte": "",
            "metadados": {},
            "similaridade": 0.68,  # Abaixo de 0.70
        },
    ]
    mock_db(rows)
    buscador = BuscadorVetorial(db_url="postgresql://mock:5432/db", limiar=0.70)

    resultado = buscador.buscar(query="teste")

    assert len(resultado.chunks) == 2
    assert [c.id for c in resultado.chunks] == ["1", "2"]
    assert resultado.top_score == 0.85
    assert resultado.houve_corte_limiar is False


def test_tabela_vazia_retorna_vazio_sem_corte_limiar(mock_db):
    """Quando o banco retorna 0 linhas, retorna top_score=0.0 e houve_corte_limiar=False."""
    mock_db([])
    buscador = BuscadorVetorial(db_url="postgresql://mock:5432/db")

    resultado = buscador.buscar(query="algo inexistente")

    assert resultado.chunks == []
    assert resultado.top_score == 0.0
    assert resultado.houve_corte_limiar is False


def test_filtro_categorias_por_parametro_sem_colar_sql(mock_db):
    """O filtro de categoria é passado por parâmetro (ANY) sem interpolação direta no SQL."""
    cur = mock_db([])
    buscador = BuscadorVetorial(db_url="postgresql://mock:5432/db")

    buscador.buscar(query="teste", categorias=["glossario", "prodist"])

    sql_executado, params_executados = cur.execute.call_args[0]

    # Verifica que o SQL usa o parâmetro ANY
    assert "categoria = ANY(%(categorias)s)" in sql_executado
    # Garante que os nomes das categorias NÃO foram colados diretamente como string literal no SQL
    assert "'glossario'" not in sql_executado
    assert "'prodist'" not in sql_executado
    # Verifica que a lista foi passada no dicionário de parâmetros
    assert params_executados["categorias"] == ["glossario", "prodist"]
    # Verifica que o limiar NÃO está mais no SQL nem nos parâmetros
    assert "%(limiar)s" not in sql_executado
    assert "limiar" not in params_executados


def test_busca_sem_categorias_nao_injeta_filtro_nem_parametro(mock_db):
    """Quando categorias é None ou vazio, não inclui filtro nem parâmetro de categorias."""
    cur = mock_db([])
    buscador = BuscadorVetorial(db_url="postgresql://mock:5432/db")

    buscador.buscar(query="teste", categorias=None)

    sql_executado, params_executados = cur.execute.call_args[0]
    assert "categoria = ANY" not in sql_executado
    assert "categorias" not in params_executados


def test_limiar_configuravel_por_variavel_ambiente(monkeypatch):
    """RAG_LIMIAR_SIMILARIDADE no ambiente ajusta o limiar padrão do BuscadorVetorial."""
    monkeypatch.setenv("RAG_LIMIAR_SIMILARIDADE", "0.55")
    buscador = BuscadorVetorial(db_url="postgresql://mock:5432/db")

    assert buscador.limiar == 0.55


def test_limiar_variavel_ambiente_invalida_cai_no_fallback_com_warning(monkeypatch, caplog):
    """Valor não numérico na variável de ambiente gera warning e usa o fallback 0.70."""
    monkeypatch.setenv("RAG_LIMIAR_SIMILARIDADE", "abc")

    with caplog.at_level(logging.WARNING):
        buscador = BuscadorVetorial(db_url="postgresql://mock:5432/db")

    assert buscador.limiar == LIMIAR_SIMILARIDADE
    assert buscador.limiar == 0.70
    assert "Valor inválido para RAG_LIMIAR_SIMILARIDADE ('abc')" in caplog.text
