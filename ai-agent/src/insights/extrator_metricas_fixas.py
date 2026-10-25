"""Consultas analíticas fixas usadas pelo pipeline de insights."""
from __future__ import annotations

import re
from typing import Any, Dict

from ..services.sql_executor import SQLExecutor

QUERIES = {
    "visao_360_uc": (
        "SELECT f.competencia, f.consumo_kwh, f.receita_faturada, "
        "f.status_pagamento FROM fact_faturamento f "
        "WHERE f.id_uc = '{entidade_id}' ORDER BY f.competencia DESC LIMIT 2"
    ),
    "diagnostico_receita": (
        "SELECT r.ano, SUM(r.receita_faturada) AS receita_total, "
        "SUM(r.consumo_kwh) AS volume_total "
        "FROM agg_receita_mensal r GROUP BY r.ano ORDER BY r.ano DESC LIMIT 2"
    ),
}


def extrair_metricas(
    tela: str,
    entidade_id: str,
    executor: SQLExecutor,
) -> list[Dict[str, Any]]:
    """Executa somente a consulta previamente homologada para a tela."""
    template = QUERIES.get(tela)
    if template is None:
        raise ValueError(f"Tela de insight não suportada: {tela}")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", entidade_id):
        raise ValueError("Identificador de entidade inválido.")
    resultado = executor.executar(template.format(entidade_id=entidade_id))
    if not resultado.sucesso:
        raise RuntimeError(f"Falha ao extrair métricas: {resultado.erro}")
    return resultado.linhas
