"""Consultas analíticas fixas usadas pelo pipeline de insights."""
from __future__ import annotations

import re
from typing import Any, Dict

from ..services.sql_executor import SQLExecutor

QUERIES = {
    "visao_360_uc": (
        "SELECT f.competencia, f.consumo_kwh, f.receita_faturada, "
        "f.status_pagamento FROM fact_faturamento f "
        "WHERE f.id_uc = '{id_uc}' ORDER BY f.competencia DESC LIMIT 2"
    ),
    "diagnostico_receita": (
        "SELECT r.ano, SUM(r.receita_faturada) AS receita_total, "
        "SUM(r.consumo_kwh) AS volume_total "
        "FROM agg_receita_mensal r GROUP BY r.ano ORDER BY r.ano DESC LIMIT 2"
    ),
}


def extrair_metricas(
    tela: str,
    id_uc: str,
    executor: SQLExecutor,
) -> list[Dict[str, Any]]:
    """Executa somente a consulta previamente homologada para a tela."""
    template = QUERIES.get(tela)
    if template is None:
        raise ValueError(f"Tela de insight não suportada: {tela}")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", id_uc):
        raise ValueError("Identificador de entidade inválido.")
    resultado = executor.executar(template.format(id_uc=id_uc))
    if not resultado.sucesso:
        raise RuntimeError(f"Falha ao extrair métricas: {resultado.erro}")
    linhas = resultado.linhas
    # Adiciona variação percentual apenas para a tela diagnostico_receita
    if tela == "diagnostico_receita":
        adicionar_variacao_percentual_diagnostico_receita(linhas)
    return linhas


def adicionar_variacao_percentual_diagnostico_receita(linhas: list[Dict[str, Any]]) -> None:
    """Calcula variação percentual de receita e volume entre dois anos.

    A consulta retorna duas linhas ordenadas por ano DESC: linha 0 = ano mais recente,
    linha 1 = ano anterior. Espera-se as chaves ``receita_total`` e ``volume_total``.
    Se houver dados suficientes, adiciona nas chaves ``variacao_receita_pct`` e
    ``variacao_volume_pct`` na linha mais recente, arredondados para duas casas decimais.
    Caso contrário, os campos são deixados ausentes ou definidos como ``None``.
    """
    if len(linhas) < 2:
        return
    atual = linhas[0]
    anterior = linhas[1]
    # valores podem ser None ou 0
    receita_atual = atual.get("receita_total")
    receita_ant = anterior.get("receita_total")
    volume_atual = atual.get("volume_total")
    volume_ant = anterior.get("volume_total")

    def _calc(atual_val, ant_val):
        try:
            if ant_val in (None, 0):
                return None
            return round(((float(atual_val) - float(ant_val)) / float(ant_val)) * 100, 2)
        except Exception:
            return None

    atual["variacao_receita_pct"] = _calc(receita_atual, receita_ant)
    atual["variacao_volume_pct"] = _calc(volume_atual, volume_ant)
