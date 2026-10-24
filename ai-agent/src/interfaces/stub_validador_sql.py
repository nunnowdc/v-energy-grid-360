"""
Implementação provisória (Stub) do validador SQL.
Permite o funcionamento imediato do agente enquanto a frente de Segurança finaliza o validador SQLGlot oficial.
"""
from __future__ import annotations

import re
from typing import List, Set
from .validador_sql_interface import (
    ResultadoValidacaoSQL,
    ValidadorSQLInterface,
)

TABELAS_PERMITIDAS: Set[str] = {
    "dim_unidade_consumidora",
    "fact_leituras",
    "fact_faturamento",
    "fact_ocorrencias",
    "fact_atendimentos",
    "dim_alimentadores",
    "tb_insights_tela",
    "tb_auditoria_agente",
    "tb_cache_perguntas_certificadas",
}

PALAVRAS_DESTRUTIVAS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|ATTACH|DETACH|PRAGMA|REPLACE|GRANT|REVOKE|EXEC|EXECUTE)\b",
    re.IGNORECASE,
)


class StubValidadorSQL:
    """Validador sintático provisório com regras de segurança em regex e análise de palavras-chave."""

    def __init__(self, tabelas_autorizadas: Set[str] | None = None):
        self.tabelas_autorizadas = {t.lower() for t in (tabelas_autorizadas or TABELAS_PERMITIDAS)}

    def validar(self, sql: str) -> ResultadoValidacaoSQL:
        if not sql or not sql.strip():
            return ResultadoValidacaoSQL(
                aprovado=False,
                motivo_rejeicao="Consulta SQL vazia ou inválida.",
                malicioso=False,
            )

        limpo = sql.strip().rstrip(";").strip()

        # 1. Checagem de injeção destrutiva / modificações
        if PALAVRAS_DESTRUTIVAS.search(limpo):
            return ResultadoValidacaoSQL(
                aprovado=False,
                motivo_rejeicao="Bloqueado por segurança: apenas consultas SELECT de leitura são permitidas.",
                malicioso=True,
            )

        # 2. Deve iniciar exclusivamente com SELECT ou WITH (para CTEs)
        if not re.match(r"^\s*(SELECT|WITH)\b", limpo, re.IGNORECASE):
            return ResultadoValidacaoSQL(
                aprovado=False,
                motivo_rejeicao="A consulta deve iniciar estritamente com SELECT ou WITH.",
                malicioso=False,
            )

        # 3. Defesa contra múltiplos comandos empilhados
        # Checa se há ponto e vírgula seguido de novo comando
        if ";" in limpo:
            partes = [p.strip() for p in limpo.split(";") if p.strip()]
            if len(partes) > 1:
                return ResultadoValidacaoSQL(
                    aprovado=False,
                    motivo_rejeicao="Bloqueado: execução de múltiplos comandos SQL em uma única requisição é proibida.",
                    malicioso=True,
                )

        # 4. Checagem simples de tabelas referenciadas (FROM / JOIN)
        matches = re.findall(r"\b(?:FROM|JOIN)\s+([a-zA-Z0-9_]+)", limpo, re.IGNORECASE)
        tabelas_encontradas = [m.lower() for m in matches]

        for tabela in tabelas_encontradas:
            if tabela.startswith("vw_gold_"):
                continue  # views autorizadas
            if tabela not in self.tabelas_autorizadas:
                return ResultadoValidacaoSQL(
                    aprovado=False,
                    motivo_rejeicao=f"Acesso negado à tabela ou view não autorizada: '{tabela}'.",
                    malicioso=False,
                    tabelas_detectadas=tabelas_encontradas,
                )

        return ResultadoValidacaoSQL(
            aprovado=True,
            motivo_rejeicao=None,
            malicioso=False,
            tabelas_detectadas=tabelas_encontradas,
        )
