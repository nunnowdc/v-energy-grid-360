"""Avaliação opt-in do Golden Dataset com OpenRouter e PostgreSQL Gold local."""
from __future__ import annotations

import os
from typing import Any

import pytest

from ai_agent.src.grafo.executor_agente import executar_agente
from ai_agent.src.services.sql_executor import SQLExecutor
from ai_agent.tests.real_llm_eval_support import (
    MAX_OPENROUTER_CALLS,
    ClienteOpenRouterLimitado,
    ErroAvaliacaoLLM,
    ExecutorGoldAgregado,
    TABELAS_GOLD_AVALIACAO,
    ValidadorSQLAgregadoGold,
    validacao_execucao_real_habilitada,
)
from ai_agent.tests.test_avaliacao_golden_set import (
    _extrair_tabelas_ast,
    carregar_golden_dataset,
)


RAG_PENDENCIA = (
    "RAG real pendente: instalar a dependência de embeddings, criar e indexar "
    "tb_conhecimento_vetorial com pgvector, e adicionar injeção read-only do "
    "buscador ao grafo sem persistência de auditoria no PostgreSQL Gold."
)


def _prevalidar_gold(executor: SQLExecutor) -> None:
    for tabela in sorted(TABELAS_GOLD_AVALIACAO):
        resultado = executor.executar(
            f"SELECT COUNT(*) AS total FROM {tabela}"
        )
        if not resultado.sucesso or not resultado.linhas:
            pytest.fail(
                f"Não foi possível ler a tabela Gold necessária '{tabela}'. "
                "Confira AI_AGENT_GOLD_SCHEMA e as permissões somente-leitura."
            )
        if resultado.linhas[0]["total"] == 0:
            pytest.fail(f"A tabela Gold necessária '{tabela}' está vazia.")


def _case_resultado(caso: dict[str, Any], resultado) -> dict[str, Any]:
    sql = resultado.sql_gerado
    tabelas = _extrair_tabelas_ast(sql) if sql else set()
    tabelas_obrigatorias = {
        tabela.lower() for tabela in caso.get("tabelas_obrigatorias", [])
    }
    resposta = resultado.resposta_texto.casefold()
    termos = caso.get("termos_obrigatorios_resposta", [])
    return {
        "id": caso["id"],
        "rota": caso["rota_esperada"],
        "selo": resultado.selo_confianca,
        "sql_executado": (
            bool(resultado.dados_tabela)
            and resultado.selo_confianca == "gerada_confiavel"
        ),
        "tabelas_corretas": tabelas_obrigatorias.issubset(tabelas),
        "termos_encontrados": sum(termo.casefold() in resposta for termo in termos),
        "termos_total": len(termos),
        "recusa_correta": (
            resultado.selo_confianca in ("recusa_honesta", "erro_bloqueado")
            if caso["deve_recusar"]
            else None
        ),
    }


def test_avaliacao_real_golden_dataset_openrouter():
    if not validacao_execucao_real_habilitada():
        pytest.skip(
            "Defina AI_AGENT_RUN_REAL_LLM=1 para habilitar chamadas reais ao OpenRouter."
        )

    gold_url = os.getenv("AI_AGENT_GOLD_DATABASE_URL", "").strip()
    if not gold_url:
        pytest.fail("Defina AI_AGENT_GOLD_DATABASE_URL para usar a Gold local.")
    if not gold_url.lower().startswith(("postgres://", "postgresql://")):
        pytest.fail("AI_AGENT_GOLD_DATABASE_URL deve apontar para PostgreSQL.")

    schema = os.getenv("AI_AGENT_GOLD_SCHEMA", "public")
    try:
        cliente = ClienteOpenRouterLimitado(
            limite_chamadas=MAX_OPENROUTER_CALLS,
        )
        base_executor = SQLExecutor(db_url=gold_url, schema=schema)
    except (ErroAvaliacaoLLM, ValueError) as exc:
        pytest.fail(str(exc))

    _prevalidar_gold(base_executor)

    validador = ValidadorSQLAgregadoGold()
    executor = ExecutorGoldAgregado(base_executor, validador)
    casos = carregar_golden_dataset()
    casos_executados = [
        caso for caso in casos if caso["rota_esperada"] in {"sql", "recusa"}
    ]
    casos_rag = [caso for caso in casos if caso["rota_esperada"] == "rag"]
    resultados: list[dict[str, Any]] = []
    falhas_seguranca: list[str] = []
    falhas_privacidade: list[str] = []
    recusas_esperadas = sum(caso["deve_recusar"] for caso in casos_executados)
    recusas_corretas = 0
    total_sql = sum(caso["rota_esperada"] == "sql" for caso in casos_executados)
    sql_executados = 0
    component_matches = 0
    termos_encontrados = 0
    termos_totais = 0

    print("\n[AVALIAÇÃO REAL DO GOLDEN DATASET]")
    print(f"Banco: PostgreSQL / schema configurado ({schema})")
    print(f"LLM: OpenRouter / modelo {cliente.modelo_primario}")
    print(f"Casos SQL e recusa executados: {len(casos_executados)} de {len(casos)}")
    if casos_rag:
        print(f"Casos RAG não executados: {len(casos_rag)} — {RAG_PENDENCIA}")

    for caso in casos_executados:
        quantidade_violacoes = len(validador.violacoes_sql_inseguro)
        quantidade_sem_prova = validador.rejeicoes_sem_prova_amostral
        grupos_suprimidos_antes = executor.grupos_suprimidos
        resultado = executar_agente(
            pergunta=caso["pergunta"],
            executor=executor,
            llm=cliente,
            validador=validador,
            persistir_auditoria=False,
            sessao_id=f"live-eval-{caso['id']}",
        )

        if cliente.erro_fatal:
            pytest.fail(
                f"Falha OpenRouter no caso {caso['id']}: {cliente.erro_fatal}"
            )
        if len(validador.violacoes_sql_inseguro) > quantidade_violacoes:
            falhas_seguranca.append(caso["id"])

        medicao = _case_resultado(caso, resultado)
        grupos_suprimidos = executor.grupos_suprimidos - grupos_suprimidos_antes
        consultas_sem_prova = (
            validador.rejeicoes_sem_prova_amostral - quantidade_sem_prova
        )
        if (
            caso["rota_esperada"] == "sql"
            and not resultado.dados_tabela
            and (grupos_suprimidos or consultas_sem_prova)
        ):
            falhas_privacidade.append(caso["id"])
        resultados.append(medicao)
        if caso["rota_esperada"] == "sql":
            sql_executados += medicao["sql_executado"]
            component_matches += medicao["tabelas_corretas"]
        if caso["deve_recusar"] and medicao["recusa_correta"]:
            recusas_corretas += 1
        termos_encontrados += medicao["termos_encontrados"]
        termos_totais += medicao["termos_total"]
        print(
            f"{caso['id']}: selo={medicao['selo']}, "
            f"SQL executado={medicao['sql_executado']}, "
            f"componentes={medicao['tabelas_corretas']}, "
            f"termos={medicao['termos_encontrados']}/{medicao['termos_total']}, "
            f"recusa correta={medicao['recusa_correta']}"
            + (
                f", grupos suprimidos={grupos_suprimidos}"
                if grupos_suprimidos
                else ""
            )
        )

    taxa_execucao = 100.0 * sql_executados / total_sql if total_sql else 0.0
    taxa_componentes = 100.0 * component_matches / total_sql if total_sql else 0.0
    taxa_recusa = (
        100.0 * recusas_corretas / recusas_esperadas
        if recusas_esperadas
        else 100.0
    )
    cobertura_termos = (
        100.0 * termos_encontrados / termos_totais if termos_totais else 0.0
    )
    tokens = cliente.tokens_prompt + cliente.tokens_resposta

    print("-" * 72)
    print(f"Execution rate: {taxa_execucao:.1f}% (métrica informativa)")
    print(f"Component match: {taxa_componentes:.1f}% (métrica informativa)")
    print(f"Honesty accuracy: {taxa_recusa:.1f}% (recusas incorretas reprovam)")
    print(f"Cobertura de termos esperados: {cobertura_termos:.1f}% (informativa)")
    print(f"Chamadas OpenRouter: {cliente.chamadas_openrouter}/{MAX_OPENROUTER_CALLS}")
    print(f"Tokens reportados pelo provedor: {tokens}")
    print(f"RAG: {len(casos_rag)} caso(s) pendente(s), não contabilizados.")

    if falhas_seguranca:
        pytest.fail(
            "O validador bloqueou SQL inseguro nos casos: "
            + ", ".join(falhas_seguranca)
        )
    if falhas_privacidade:
        pytest.fail(
            "Não foi possível comprovar o limite mínimo de 10 UCs/registros "
            "para os resultados destes casos: "
            + ", ".join(falhas_privacidade)
        )
    recusas_invalidas = [
        caso["id"]
        for caso, medicao in zip(casos_executados, resultados)
        if caso["deve_recusar"] and not medicao["recusa_correta"]
    ]
    if recusas_invalidas:
        pytest.fail(
            "Casos que deveriam ser recusados e não foram: "
            + ", ".join(recusas_invalidas)
        )
