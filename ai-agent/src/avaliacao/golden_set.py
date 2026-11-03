"""
Avaliação do agente contra o golden set (REQ-AI-08).

Usa as mesmas métricas e metas de tests/test_avaliacao_golden_set.py, mas com o
modelo e o banco de verdade, para acompanhar a qualidade entre uma execução e outra.
Diferença: na consulta, "certificada" também conta como executada (com o banco real,
as perguntas do cache certificado rodam a consulta pronta; com o LLM falso, nunca).
"""

from __future__ import annotations

import json
import math
import time
import unicodedata
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
META_RESULTADO_CERTO = 85.0
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


def _numeros(linhas: list[dict[str, Any]] | None) -> list[float]:
    """Todos os valores numéricos do resultado, sem olhar o nome da coluna."""
    numeros = []
    for linha in linhas or []:
        for valor in linha.values():
            if valor is None or isinstance(valor, bool):
                continue
            try:
                numeros.append(float(valor))
            except (TypeError, ValueError):
                continue
    return numeros


def _textos(linhas: list[dict[str, Any]] | None) -> set[str]:
    """Valores de texto não numéricos, sem acento e em minúsculas ('Jaboatão' = 'jaboatao')."""
    textos = set()
    for linha in linhas or []:
        for valor in linha.values():
            if not isinstance(valor, str) or not valor.strip():
                continue
            try:
                float(valor)
                continue
            except ValueError:
                pass
            sem_acento = unicodedata.normalize("NFKD", valor).encode("ascii", "ignore").decode()
            textos.add(sem_acento.strip().lower())
    return textos


def comparar_resultado(
    esperado: list[dict[str, Any]] | None,
    obtido: list[dict[str, Any]] | None,
    tolerancia: float = 0.005,
) -> list[Any] | None:
    """O que do resultado esperado não aparece no do agente: vazio = bate, None = nada a conferir.

    Confere os números: ignora nome e ordem das colunas e aceita colunas a mais no agente.
    A tolerância relativa de 0,5% cobre o ROUND(..., 2) que o agente costuma aplicar; a
    absoluta é mínima, para não aceitar 0,8065 no lugar de 0,7978 (preço do kWh).
    Só quando o esperado não tem número nenhum, confere os textos (ex.: nome do bairro).
    Não confere a linha de cada número: é uma conferência de valores, não uma comparação exata.
    """
    numeros_esperados = _numeros(esperado)
    if numeros_esperados:
        do_agente = _numeros(obtido)
        return [
            numero
            for numero in numeros_esperados
            if not any(
                math.isclose(numero, outro, rel_tol=tolerancia, abs_tol=1e-4) for outro in do_agente
            )
        ]
    textos_esperados = _textos(esperado)
    if textos_esperados:
        return sorted(textos_esperados - _textos(obtido))
    # Resultado esperado vazio: aprovar seria aprovar sem conferir
    return None


def avaliar_caso(
    caso: dict[str, Any],
    resposta: RespostaAgente,
    resultado_esperado: list[dict[str, Any]] | None = None,
    erro_esperado: str | None = None,
) -> dict[str, Any]:
    """Se a resposta do agente atende ao caso, com o motivo em uma frase.

    Sem o resultado esperado (testes com LLM falso) o critério é o das tabelas. Se o
    sql_esperado falhou (erro_esperado) ou veio vazio, o caso fica "não conferido"
    (resultado_certo nulo) e o motivo avisa: nunca conta como resultado certo.
    """
    selo = resposta.selo_confianca
    tipo = caso["rota_esperada"]
    executou = tabelas_certas = resultado_certo = None

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
        nao_conferido = None
        if executou and erro_esperado:
            nao_conferido = f"o sql_esperado falhou ({erro_esperado[:120]})"
        elif executou and resultado_esperado is not None:
            diferencas = comparar_resultado(resultado_esperado, resposta.dados_tabela)
            if diferencas is None:
                nao_conferido = "o sql_esperado não devolveu nada"
            else:
                resultado_certo = not diferencas
        passou = executou and (resultado_certo if resultado_certo is not None else tabelas_certas)
        if not executou:
            motivo = f"A consulta não rodou (selo {selo})"
        elif resultado_certo is False:
            motivo = f"Rodou, mas o resultado não bate com o esperado: {diferencas[:3]}"
        elif resultado_certo:
            motivo = "Rodou e o resultado bate com o esperado"
        elif faltando:
            motivo = f"Rodou, mas sem a tabela esperada: {', '.join(faltando)}"
        else:
            motivo = "Rodou a consulta com as tabelas esperadas"
        if nao_conferido:
            motivo += f"; resultado NÃO conferido: {nao_conferido}"
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
        "resultado_certo": resultado_certo,
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
    conferidos = [r for r in consultas if r.get("resultado_certo") is not None]
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
        # Nula quando a execução não conferiu resultados (sem banco para rodar o sql_esperado)
        "taxa_resultado_certo": _percentual(
            sum(r["resultado_certo"] for r in conferidos), len(conferidos)
        ),
        "tokens_medio": sum(tokens) / len(tokens) if tokens else None,
    }


def executar_avaliacao(
    casos: list[dict[str, Any]],
    executar: Callable[..., RespostaAgente],
    ao_terminar_caso: Callable[[dict[str, Any]], None] | None = None,
    executar_esperado: Callable[[str], list[dict[str, Any]]] | None = None,
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
        esperado = erro_esperado = None
        if executar_esperado and caso.get("sql_esperado"):
            # Um sql_esperado quebrado não derruba a rodada: o caso fica "não conferido"
            try:
                esperado = executar_esperado(caso["sql_esperado"])
            except Exception as erro:
                erro_esperado = str(erro) or type(erro).__name__
        resultado = avaliar_caso(caso, resposta, esperado, erro_esperado)
        resultados.append(resultado)
        if ao_terminar_caso:
            ao_terminar_caso(resultado)
    return {
        **resumir(resultados),
        "duracao_ms": (time.perf_counter() - inicio) * 1000,
        "casos": resultados,
    }
