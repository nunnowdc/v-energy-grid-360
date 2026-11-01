"""Opt-in real LLM evaluation for the RAG Golden Dataset cases."""
from __future__ import annotations

import os

import pytest

from ai_agent.src.grafo.executor_agente import executar_agente
from ai_agent.tests.real_llm_eval_support import (
    ErroAvaliacaoLLM,
    ClienteOpenRouterLimitado,
)
from ai_agent.tests.real_rag_eval_support import (
    MAX_OPENROUTER_CALLS,
    RAG_PENDING_REASON,
    ErroAvaliacaoRAG,
    medir_resultado_rag,
    mensagem_falha_openrouter,
    prevalidar_banco_rag,
    prevalidar_recuperacao,
    separar_casos_rag,
    validar_bases_separadas,
    validar_modelo_configurado,
    validacao_rag_real_habilitada,
)
from ai_agent.tests.test_avaliacao_golden_set import carregar_golden_dataset


def test_avaliacao_real_casos_rag_openrouter(monkeypatch: pytest.MonkeyPatch) -> None:
    if not validacao_rag_real_habilitada():
        pytest.skip(
            "Defina AI_AGENT_RUN_REAL_RAG=1 para habilitar chamadas reais "
            "ao OpenRouter nos casos RAG."
        )

    rag_url = os.getenv("AI_AGENT_RAG_DATABASE_URL", "").strip()
    if not rag_url:
        pytest.fail("Defina AI_AGENT_RAG_DATABASE_URL para o banco vetorial.")

    try:
        validar_bases_separadas(
            rag_url,
            os.getenv("AI_AGENT_GOLD_DATABASE_URL"),
        )
        casos, pendentes = separar_casos_rag(carregar_golden_dataset())
        estado_banco = prevalidar_banco_rag(rag_url)
        chunks_preflight = prevalidar_recuperacao(casos, rag_url)
        cliente = ClienteOpenRouterLimitado(
            limite_chamadas=MAX_OPENROUTER_CALLS,
        )
        validar_modelo_configurado(cliente.modelo_primario)
    except (ErroAvaliacaoLLM, ErroAvaliacaoRAG) as exc:
        pytest.fail(str(exc))

    # The existing graph reads DATABASE_URL for its vector search. Keep this
    # override scoped to this test; the Gold connection is not used by RAG.
    monkeypatch.setenv("DATABASE_URL", rag_url)

    resultados = []
    falhas_tecnicas = []
    print("\n[AVALIAÇÃO REAL RAG DO GOLDEN DATASET]")
    print("Banco: PostgreSQL/pgvector configurado (URL não exibida)")
    print(f"LLM: OpenRouter / modelo {cliente.modelo_primario}")
    print(f"Documentos indexados com embedding: {estado_banco.documentos_com_embedding}")
    print(f"Casos RAG avaliados: {len(casos)}")

    for caso in casos:
        chamadas_antes = cliente.chamadas_openrouter
        resultado = executar_agente(
            pergunta=caso["pergunta"],
            llm=cliente,
            db_url=rag_url,
            persistir_auditoria=False,
            sessao_id=f"live-rag-eval-{caso['id']}",
        )
        if cliente.erro_fatal:
            pytest.fail(
                f"Falha OpenRouter no caso {caso['id']}: "
                f"{mensagem_falha_openrouter(cliente)}"
            )

        medicao = medir_resultado_rag(
            caso,
            resultado,
            cliente.chamadas_openrouter - chamadas_antes,
        )
        if not medicao["avaliacao_tecnica_ok"]:
            falhas_tecnicas.append(caso["id"])
        resultados.append(medicao)
        print(
            f"{caso['id']}: selo={medicao['selo']}, "
            f"chunks={medicao['chunks_recuperados']} "
            f"(preflight={chunks_preflight[caso['id']]}), "
            f"fontes_recuperadas={medicao['fontes_recuperadas']}, "
            f"fonte_no_texto={medicao['fonte_no_texto']}, "
            f"termos={medicao['termos_encontrados']}/{medicao['termos_total']}"
        )

    termos_encontrados = sum(item["termos_encontrados"] for item in resultados)
    termos_totais = sum(item["termos_total"] for item in resultados)
    cobertura_termos = (
        100.0 * termos_encontrados / termos_totais if termos_totais else 0.0
    )
    print("-" * 72)
    print(f"Cobertura de termos esperados: {cobertura_termos:.1f}% (informativa)")
    print(f"Chamadas OpenRouter: {cliente.chamadas_openrouter}/{MAX_OPENROUTER_CALLS}")
    print(f"Tokens reportados pelo provedor: {cliente.tokens_prompt + cliente.tokens_resposta}")
    print(
        f"Casos RAG pendentes: {len(pendentes)} — "
        f"{RAG_PENDING_REASON}"
    )

    if falhas_tecnicas:
        pytest.fail(
            "Os casos não recuperaram contexto RAG utilizável ou não produziram "
            "resposta documental com fonte após chamada real ao OpenRouter: "
            + ", ".join(falhas_tecnicas)
        )
