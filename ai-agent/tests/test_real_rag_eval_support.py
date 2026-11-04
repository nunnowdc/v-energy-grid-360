from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import psycopg2
import pytest

from ai_agent.tests.real_rag_eval_support import (
    RAG_PENDING_REASON,
    ErroAvaliacaoRAG,
    medir_resultado_rag,
    prevalidar_banco_rag,
    prevalidar_recuperacao,
    separar_casos_rag,
    validar_bases_separadas,
    validar_modelo_configurado,
    validacao_rag_real_habilitada,
)


def _caso(caso_id: str, *, rota: str = "rag") -> dict:
    return {
        "id": caso_id,
        "pergunta": f"Pergunta de teste para {caso_id}",
        "rota_esperada": rota,
        "termos_obrigatorios_resposta": ["DEC", "interrupção"],
    }


def test_avaliacao_rag_exige_opt_in(monkeypatch):
    monkeypatch.delenv("AI_AGENT_RUN_REAL_RAG", raising=False)
    assert validacao_rag_real_habilitada() is False

    monkeypatch.setenv("AI_AGENT_RUN_REAL_RAG", "1")
    assert validacao_rag_real_habilitada() is True


def test_separar_casos_roda_dois_e_mantem_tc009_pendente():
    executar, pendentes = separar_casos_rag(
        [_caso("TC-007"), _caso("TC-008"), _caso("TC-009")]
    )

    assert [caso["id"] for caso in executar] == ["TC-007", "TC-008"]
    assert [caso["id"] for caso in pendentes] == ["TC-009"]
    assert "pendente" in RAG_PENDING_REASON


def test_separar_casos_falha_se_golden_dataset_mudar_rota():
    with pytest.raises(ErroAvaliacaoRAG, match="TC-008"):
        separar_casos_rag(
            [_caso("TC-007"), _caso("TC-008", rota="sql"), _caso("TC-009")]
        )


def test_preflight_banco_exige_url_postgresql():
    with pytest.raises(ErroAvaliacaoRAG, match="deve apontar para PostgreSQL"):
        prevalidar_banco_rag("sqlite:///rag.db")


def test_avaliacao_rag_rejeita_mesmo_banco_configurado_para_gold():
    url = "postgresql://readonly:secret@localhost:5433/v_energy"

    with pytest.raises(ErroAvaliacaoRAG, match="banco RAG separado"):
        validar_bases_separadas(url, url)


def test_avaliacao_rag_aceita_bancos_separados():
    validar_bases_separadas(
        "postgresql://readonly@localhost:5433/v_energy_rag",
        "postgresql://readonly@localhost:5433/v_energy",
    )


def test_avaliacao_rag_exige_modelo_explicitamente_configurado():
    with pytest.raises(ErroAvaliacaoRAG, match="MODELO_LLM_PRIMARIO"):
        validar_modelo_configurado(None)

    assert validar_modelo_configurado(" provider/model ") == "provider/model"


def test_preflight_recuperacao_exige_chunks_para_todos_casos(monkeypatch):
    from ai_agent.src.rag.buscador_vetorial import BuscadorVetorial

    buscador_mock = Mock()
    buscador_mock.buscar.side_effect = [
        SimpleNamespace(chunks=[object(), object()]),
        SimpleNamespace(chunks=[object()]),
    ]
    monkeypatch.setattr(
        BuscadorVetorial,
        "__new__",
        Mock(return_value=buscador_mock),
    )

    quantidades = prevalidar_recuperacao(
        [_caso("TC-007"), _caso("TC-008")],
        "postgresql://readonly@localhost/v_energy_rag",
    )

    assert quantidades == {"TC-007": 2, "TC-008": 1}
    assert buscador_mock.buscar.call_count == 2


def test_preflight_recuperacao_falha_se_caso_nao_recupera_chunks(monkeypatch):
    from ai_agent.src.rag.buscador_vetorial import BuscadorVetorial

    buscador_mock = Mock()
    buscador_mock.buscar.return_value = SimpleNamespace(chunks=[])
    monkeypatch.setattr(
        BuscadorVetorial,
        "__new__",
        Mock(return_value=buscador_mock),
    )

    with pytest.raises(ErroAvaliacaoRAG, match="TC-007"):
        prevalidar_recuperacao(
            [_caso("TC-007")],
            "postgresql://readonly@localhost/v_energy_rag",
        )


def test_preflight_banco_usa_sessao_read_only_e_valida_pgvector(monkeypatch):
    cursor = Mock()
    cursor.fetchone.side_effect = [(True,), (25, 25, 384)]
    cursor_context = Mock()
    cursor_context.__enter__ = Mock(return_value=cursor)
    cursor_context.__exit__ = Mock(return_value=False)
    connection = Mock()
    connection.cursor.return_value = cursor_context
    connection_context = Mock()
    connection_context.__enter__ = Mock(return_value=connection)
    connection_context.__exit__ = Mock(return_value=False)
    connect = Mock(return_value=connection_context)
    monkeypatch.setattr(psycopg2, "connect", connect)

    import sys
    import types

    monkeypatch.setitem(
        sys.modules,
        "sentence_transformers",
        types.ModuleType("sentence_transformers"),
    )
    estado = prevalidar_banco_rag("postgresql://readonly@localhost/v_energy_rag")

    assert estado.documentos == 25
    assert estado.documentos_com_embedding == 25
    assert estado.dimensao_embedding == 384
    connection.set_session.assert_called_once_with(readonly=True)
    assert connect.call_args.kwargs["connect_timeout"] == 5


@pytest.mark.parametrize(
    ("fetch_results", "mensagem"),
    [
        ([(False,)], "pgvector não está ativada"),
        ([(True,), (0, 0, None)], "está vazia"),
        ([(True,), (25, 24, 384)], "sem embedding"),
        ([(True,), (25, 25, 768)], "Dimensão dos embeddings incompatível"),
    ],
)
def test_preflight_banco_rejeita_schema_vetorial_incompleto(
    monkeypatch, fetch_results, mensagem
):
    cursor = Mock()
    cursor.fetchone.side_effect = fetch_results
    cursor_context = Mock()
    cursor_context.__enter__ = Mock(return_value=cursor)
    cursor_context.__exit__ = Mock(return_value=False)
    connection = Mock()
    connection.cursor.return_value = cursor_context
    connection_context = Mock()
    connection_context.__enter__ = Mock(return_value=connection)
    connection_context.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(
        psycopg2,
        "connect",
        Mock(return_value=connection_context),
    )

    import sys
    import types

    monkeypatch.setitem(
        sys.modules,
        "sentence_transformers",
        types.ModuleType("sentence_transformers"),
    )

    with pytest.raises(ErroAvaliacaoRAG, match=mensagem):
        prevalidar_banco_rag("postgresql://readonly@localhost/v_energy_rag")


def test_preflight_banco_falha_com_mensagem_segura_se_conexao_falhar(monkeypatch):
    monkeypatch.setattr(
        psycopg2,
        "connect",
        Mock(side_effect=RuntimeError("postgresql://secret-password")),
    )

    with pytest.raises(ErroAvaliacaoRAG, match="Não foi possível validar") as erro:
        prevalidar_banco_rag("postgresql://readonly@localhost/v_energy_rag")

    assert "secret-password" not in str(erro.value)


def test_preflight_banco_exige_sentence_transformers(monkeypatch):
    cursor = Mock()
    cursor.fetchone.side_effect = [(True,), (25, 25, 384)]
    cursor_context = Mock()
    cursor_context.__enter__ = Mock(return_value=cursor)
    cursor_context.__exit__ = Mock(return_value=False)
    connection = Mock()
    connection.cursor.return_value = cursor_context
    connection_context = Mock()
    connection_context.__enter__ = Mock(return_value=connection)
    connection_context.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(
        psycopg2,
        "connect",
        Mock(return_value=connection_context),
    )

    import sys

    monkeypatch.setitem(sys.modules, "sentence_transformers", None)
    with pytest.raises(ErroAvaliacaoRAG, match="sentence-transformers"):
        prevalidar_banco_rag("postgresql://readonly@localhost/v_energy_rag")


def test_medicao_exige_contexto_fontes_e_chamada_openrouter():
    resultado = SimpleNamespace(
        selo_confianca="documental_rag",
        passos_executados=["Nó 5 — RAG: 2 chunk(s) recuperados."],
        fontes_citadas=["PRODIST Módulo 8"],
        resposta_texto="O DEC considera a duração de interrupção. Fonte: PRODIST Módulo 8.",
    )

    medicao = medir_resultado_rag(_caso("TC-007"), resultado, 2)

    assert medicao["avaliacao_tecnica_ok"] is True
    assert medicao["chunks_recuperados"] == 2
    assert medicao["fontes_recuperadas"] == 1
    assert medicao["fonte_no_texto"] is True
    assert medicao["termos_encontrados"] == 2


@pytest.mark.parametrize(
    ("selo", "passos", "fontes", "chamadas"),
    [
        ("recusa_honesta", ["Nó 5 — RAG: 0 chunks recuperados."], [], 0),
        ("documental_rag", ["Nó 5 — RAG: 0 chunks recuperados."], ["PRODIST"], 2),
        ("documental_rag", ["Nó 5 — RAG: 1 chunk(s) recuperados."], [], 2),
        ("documental_rag", ["Nó 5 — RAG: 1 chunk(s) recuperados."], ["PRODIST"], 0),
    ],
)
def test_medicao_reprova_resposta_sem_recuperacao_tecnica(
    selo, passos, fontes, chamadas
):
    resultado = SimpleNamespace(
        selo_confianca=selo,
        passos_executados=passos,
        fontes_citadas=fontes,
        resposta_texto="Resposta de avaliação",
    )

    medicao = medir_resultado_rag(_caso("TC-007"), resultado, chamadas)

    assert medicao["avaliacao_tecnica_ok"] is False


def test_medicao_nao_inclui_texto_da_resposta_ou_contexto():
    texto_privado = "conteúdo confidencial do chunk"
    resultado = SimpleNamespace(
        selo_confianca="documental_rag",
        passos_executados=["Nó 5 — RAG: 1 chunk(s) recuperados."],
        fontes_citadas=["Fonte interna"],
        resposta_texto=texto_privado,
    )

    medicao = medir_resultado_rag(_caso("TC-007"), resultado, 1)

    assert texto_privado not in repr(medicao)
