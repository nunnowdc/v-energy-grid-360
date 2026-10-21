"""Validador de SQL do agente Text-to-SQL (V-Energy Grid 360).

Etapa 1 (base): parse real com SQLGlot, uma única instrução, raiz SELECT,
nenhuma construção de escrita e LIMIT forçado. As regras de tabelas,
funções e colunas entram na etapa 2.

Camada de aplicação da defesa em profundidade (bloco "Confere o SQL" do
diagrama, requisito 5.3). Não substitui o usuário de banco somente-leitura
nem o statement_timeout.

O agente deve executar `result.sql` (versão normalizada, sem comentários e
com LIMIT), nunca o texto original do LLM.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError


def _node_types(*names: str) -> tuple[type, ...]:
    """Resolve classes do SQLGlot por nome (tolera diferenças de versão)."""
    return tuple(t for n in names if (t := getattr(exp, n, None)) is not None)


# Nós que nunca podem aparecer em nenhum ponto da árvore (inclusive em CTE).
_FORBIDDEN_NODES = _node_types(
    "Insert", "Update", "Delete", "Merge", "Drop", "Create", "Alter",
    "AlterTable", "TruncateTable", "Command", "Copy", "Set", "Use", "Into",
    "Lock", "Grant", "Revoke", "Transaction", "Commit", "Rollback",
    "Pragma", "Attach", "Detach", "LoadData", "Analyze", "Describe",
    "Show", "Kill", "Declare",
)

_ALLOWED_ROOTS = _node_types("Select", "Union", "Intersect", "Except")


@dataclass(frozen=True)
class ValidationResult:
    allowed: bool
    code: str  # "OK" ou o motivo do bloqueio
    reason: str  # texto legível para log/auditoria
    sql: str | None = None  # SQL normalizado (só quando allowed=True)

    def to_dict(self) -> dict:
        return asdict(self)


def _block(code: str, reason: str) -> ValidationResult:
    return ValidationResult(allowed=False, code=code, reason=reason)


class SQLValidator:
    def __init__(
        self,
        dialect: str = "postgres",
        max_rows: int = 1000,
        max_length: int = 4000,
    ) -> None:
        self.dialect = dialect
        self.max_rows = max_rows
        self.max_length = max_length

    def validate(self, sql: str) -> ValidationResult:
        if not isinstance(sql, str) or not sql.strip():
            return _block("EMPTY", "Consulta vazia.")
        if len(sql) > self.max_length:
            return _block("TOO_LONG", f"Consulta maior que {self.max_length} caracteres.")
        if "\x00" in sql:
            return _block("INVALID_CHARS", "Caractere nulo na consulta.")

        # 1) Parse real. Erro de sintaxe/tokenização = bloqueio.
        try:
            statements = [s for s in sqlglot.parse(sql, read=self.dialect) if s is not None]
        except SqlglotError as exc:
            return _block("PARSE_ERROR", f"SQL inválido: {str(exc).splitlines()[0][:150]}")

        if not statements:
            return _block("EMPTY", "Nenhuma instrução SQL encontrada.")
        if len(statements) > 1:
            return _block("MULTIPLE_STATEMENTS", "Apenas uma instrução SQL é permitida.")

        root = statements[0]
        while isinstance(root, exp.Subquery):  # "(SELECT ...)" -> SELECT
            root = root.this

        # 2) A raiz precisa ser SELECT (ou UNION/INTERSECT/EXCEPT de SELECTs).
        if not isinstance(root, _ALLOWED_ROOTS):
            return _block("NOT_SELECT", f"Só SELECT é permitido (recebido: {type(root).__name__}).")

        # 3) Nenhum nó de escrita/administração em qualquer ponto da árvore.
        for node in root.find_all(exp.Expression):
            if isinstance(node, _FORBIDDEN_NODES):
                return _block(
                    "FORBIDDEN_NODE",
                    f"Construção não permitida dentro da consulta: {type(node).__name__}.",
                )

        # 4) Força LIMIT (inexistente, maior que o teto ou não numérico).
        self._enforce_limit(root)

        return ValidationResult(
            allowed=True,
            code="OK",
            reason="Consulta aprovada.",
            sql=root.sql(dialect=self.dialect, comments=False),
        )

    def _enforce_limit(self, root: exp.Expression) -> None:
        limit = root.args.get("limit")
        if limit is None:
            root.limit(self.max_rows, copy=False)
            return
        try:
            value = int(limit.expression.name)
        except (ValueError, AttributeError):
            value = None
        if value is None or value > self.max_rows:
            root.limit(self.max_rows, copy=False)


_DEFAULT = SQLValidator()


def validate_sql(sql: str) -> ValidationResult:
    """Atalho com a configuração padrão."""
    return _DEFAULT.validate(sql)
