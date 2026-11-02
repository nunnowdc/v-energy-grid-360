"""
Avaliação do agente contra o golden set (REQ-AI-08).

Usa as mesmas métricas e metas de tests/test_avaliacao_golden_set.py, mas com o
modelo e o banco de verdade, para acompanhar a qualidade entre uma execução e outra.
Diferença: na consulta, "certificada" também conta como executada (com o banco real,
as perguntas do cache certificado rodam a consulta pronta; com o LLM falso, nunca).
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError

from ..contratos.resposta_agente import RespostaAgente

CAMINHO_GOLDEN_SET = (
    Path(__file__).resolve().parents[2]
    / "tests"
    / "golden_dataset"
    / "golden_dataset.json"
)

# Metas do REQ-AI-08, as mesmas do teste do golden set
META_EXECUCAO = 90.0
META_COMPONENT_MATCH = 85.0
META_ABSTENCAO = 100.0
META_TOKENS = 1800.0

SELOS_COM_CONSULTA = ("certificada", "gerada_confiavel")
SELOS_DE_RECUSA = ("recusa_honesta", "erro_bloqueado")


def carregar_casos(caminho: Path = CAMINHO_GOLDEN_SET) -> list[dict[str, Any]]:
    with open(caminho, "r", encoding="utf-8") as arquivo:
        return json.load(arquivo)


def tabelas_do_sql(sql: str | None) -> set[str]:
    """Tabelas citadas na consulta, lidas pela árvore do sqlglot (vazio se não ler)."""
    if not sql:
        return set()
    try:
        arvore = sqlglot.parse_one(sql, read="postgres")
        return {t.name.lower() for t in arvore.find_all(exp.Table) if t.name}
    except SqlglotError:
        return set()


def avaliar_caso(caso: dict[str, Any], resposta: RespostaAgente) -> dict[str, Any]:
    """Se a resposta do agente atende ao caso, com o motivo em uma frase."""
    selo = resposta.selo_confianca
    tipo = caso["rota_esperada"]
    executou = tabelas_certas = None

    if caso["deve_recusar"]:
        passou = selo in SELOS_DE_RECUSA
        motivo = (
            "Recusou, como esperado"
            if passou
            else f"Respondeu quando devia recusar (selo {selo})"
        )
    elif tipo == "sql":
        executou = resposta.dados_tabela is not None and selo in SELOS_COM_CONSULTA
        obrigatorias = {t.lower() for t in caso["tabelas_obrigatorias"]}
        faltando = sorted(obrigatorias - tabelas_do_sql(resposta.sql_gerado))
        tabelas_certas = bool(resposta.sql_gerado) and not faltando
        passou = executou and tabelas_certas
        if not executou:
            motivo = f"A consulta não rodou (selo {selo})"
        elif faltando:
            motivo = f"Rodou, mas sem a tabela esperada: {', '.join(faltando)}"
        else:
            motivo = "Rodou a consulta com as tabelas esperadas"
    else:
        passou = selo == "documental_rag"
        motivo = (
            "Respondeu com os documentos"
            if passou
            else f"Não respondeu com os documentos (selo {selo})"
        )

    return {
        "caso_id": caso["id"],
        "tipo": tipo,
        "pergunta": caso["pergunta"],
        "selo": selo,
        "passou": passou,
        "motivo": motivo,
        # Só nos casos de consulta; nulos nos outros
        "executou": executou,
        "tabelas_certas": tabelas_certas,
        "sql_gerado": resposta.sql_gerado,
        "tokens": resposta.tokens_totais,
        "tempo_ms": resposta.tempo_execucao_ms,
    }


def _percentual(parte: int, total: int) -> float | None:
    return parte / total * 100 if total else None


def resumir(resultados: list[dict[str, Any]]) -> dict[str, Any]:
    """As 4 métricas do REQ-AI-08; nula quando não há caso daquele tipo."""
    consultas = [r for r in resultados if r["executou"] is not None]
    recusas = [r for r in resultados if r["tipo"] == "recusa"]
    tokens = [r["tokens"] for r in resultados]
    return {
        "total_casos": len(resultados),
        "casos_aprovados": sum(r["passou"] for r in resultados),
        "taxa_execucao": _percentual(
            sum(r["executou"] for r in consultas), len(consultas)
        ),
        "taxa_component_match": _percentual(
            sum(r["tabelas_certas"] for r in consultas), len(consultas)
        ),
        "taxa_abstencao": _percentual(sum(r["passou"] for r in recusas), len(recusas)),
        "tokens_medio": sum(tokens) / len(tokens) if tokens else None,
    }


def executar_avaliacao(
    casos: list[dict[str, Any]],
    executar: Callable[..., RespostaAgente],
    ao_terminar_caso: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Faz cada pergunta ao agente, sem gravar na auditoria (não entra no uso do portal)."""
    inicio = time.perf_counter()
    resultados = []
    for caso in casos:
        resposta = executar(
            pergunta=caso["pergunta"],
            sessao_id=f"golden-{caso['id']}",
            persistir_auditoria=False,
        )
        resultado = avaliar_caso(caso, resposta)
        resultados.append(resultado)
        if ao_terminar_caso:
            ao_terminar_caso(resultado)
    return {
        **resumir(resultados),
        "duracao_ms": (time.perf_counter() - inicio) * 1000,
        "casos": resultados,
    }
