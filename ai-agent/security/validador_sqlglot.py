"""Adaptador entre o validador de SQL (SQLGlot) e o contrato da frente de Agentes.

O agente espera um objeto com `validar(sql) -> ResultadoValidacaoSQL`
(ai-agent/src/interfaces/validador_sql_interface.py). Esta classe é a
implementação oficial prevista em guia_seguranca_agente.md
("ValidadorSQLGlotPostgres") e substitui o StubValidadorSQL.

Uso (do diretório ai-agent/):
    from security.validador_sqlglot import ValidadorSQLGlotPostgres
    grafo = construir_grafo(..., validador=ValidadorSQLGlotPostgres())

`malicioso` (guia, seção 3, item 5):
  * True  = tentativa flagrante (escrita, instruções empilhadas, função
            perigosa, schema de sistema). O agente cancela o retry e audita.
  * False = erro provável do LLM (sintaxe, tabela ou coluna que não pode
            usar, função desconhecida). O agente tenta corrigir no retry.
"""

from __future__ import annotations

from typing import Optional

from pydantic import Field

from security.sql_validator import SQLValidator, ValidationResult
from src.interfaces.validador_sql_interface import ResultadoValidacaoSQL

# Códigos do SQLValidator que indicam ataque deliberado, não erro do LLM.
CODIGOS_MALICIOSOS = frozenset(
    {
        "MULTIPLE_STATEMENTS",  # SELECT 1; DROP TABLE ...
        "NOT_SELECT",           # DROP, DELETE, UPDATE, INSERT, CREATE, GRANT, SHOW...
        "FORBIDDEN_NODE",       # escrita escondida: CTE com DELETE, SELECT INTO, FOR UPDATE
        "FUNCTION_NOT_ALLOWED", # pg_sleep, pg_read_file, version()...
        "SCHEMA_NOT_ALLOWED",   # pg_catalog, information_schema
        "INVALID_CHARS",        # caractere nulo
    }
)


class ResultadoValidacaoSQLSeguro(ResultadoValidacaoSQL):
    """ResultadoValidacaoSQL com dois campos extras, opcionais para o agente."""

    codigo: str = Field(default="OK", description="Código do validador (ex.: TABLE_NOT_ALLOWED) para auditoria.")
    sql_normalizado: Optional[str] = Field(
        default=None,
        description="SQL verificado, sem comentários e com LIMIT. É o que deve ser executado.",
    )


class ValidadorSQLGlotPostgres:
    """Implementa ValidadorSQLInterface usando SQLGlot (parse real, default deny)."""

    def __init__(self, validador: SQLValidator | None = None) -> None:
        self._validador = validador or SQLValidator(dialect="postgres")

    def validar(self, sql: str) -> ResultadoValidacaoSQLSeguro:
        r: ValidationResult = self._validador.validate(sql)
        if r.allowed:
            return ResultadoValidacaoSQLSeguro(
                aprovado=True,
                motivo_rejeicao=None,
                malicioso=False,
                tabelas_detectadas=list(r.tables),
                codigo=r.code,
                sql_normalizado=r.sql,
            )
        return ResultadoValidacaoSQLSeguro(
            aprovado=False,
            motivo_rejeicao=r.reason,
            malicioso=r.code in CODIGOS_MALICIOSOS,
            tabelas_detectadas=list(r.tables),
            codigo=r.code,
            sql_normalizado=None,
        )
