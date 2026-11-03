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
        "SELECT CASE WHEN r.competencia >= DATE '2025-07-01' "
        "THEN 'jul/2025-jun/2026' ELSE 'jul/2024-jun/2025' END AS periodo, "
        "SUM(r.receita_faturada) AS receita_total, "
        "SUM(r.consumo_kwh) AS volume_total "
        "FROM agg_receita_mensal r "
        "WHERE r.competencia >= DATE '2024-07-01' AND r.competencia < DATE '2026-07-01' "
        "GROUP BY 1 "
        "ORDER BY MIN(r.competencia) DESC"
    ),
}

FONTES_POR_TELA = {
    "visao_360_uc": ["fact_faturamento"],
    "diagnostico_receita": ["agg_receita_mensal"],
}


def fontes_da_tela(tela: str) -> list[str]:
    """Devolve a lista de fontes fixas para a tela. Levanta ValueError se tela desconhecida."""
    try:
        return FONTES_POR_TELA[tela]
    except KeyError:
        raise ValueError(f"Tela de insight não suportada: {tela}")


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
    """Calcula variação percentual de receita e volume entre dois períodos de 12 meses.

    A consulta retorna duas linhas ordenadas por período mais recente primeiro:
    linha 0 = 'jul/2025-jun/2026' (período mais recente),
    linha 1 = 'jul/2024-jun/2025' (período anterior).
    Espera-se as chaves ``receita_total``, ``volume_total`` e ``periodo``.
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
