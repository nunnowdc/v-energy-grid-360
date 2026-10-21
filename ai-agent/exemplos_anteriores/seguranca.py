from __future__ import annotations

import logging 
import re
import sqlite3
import sys
import time
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

import sqlglot
from sqlglot import exp

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from schemas.structureds_outputs import QueryExecutionResult

logger = logging.getLogger("cinedata.sql_executor") #o parÂmetro que passamos para o getLogger é o nome do logger, que vai aparecer no log, e que podemos usar para filtrar logs de diferentes partes do sistema

DEAULT_ROW_LIMIT = 20
QUERY_TIMEOUT_SECONDS = 35.0

_FORBIDDEN_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|ATTACH|DETACH|" #SERVE PARA BLOQUEAR PALAVRAS CHAVE QUE PODEM ALTERAR O BANCO DE DADOS, COMO INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, ATTACH, DETACH, PRAGMA, REPLACE, VACUUM E REINDEX
    r"PRAGMA|REPLACE|VACUUM|REINDEX)\b",
    re.IGNORECASE,
)

class SQLSecurityError(Exception):
    """A query gerada não passou numa das checagens de segurança."""

def validate_readonly_sql(sql: str) -> exp.Expression: 
    if not sql or not sql.strip(): # se a query for vazia ou só tiver espaços em branco, levanta uma exceção
        raise SQLSecurityError("A query gerada veio vazia.")
    stripped = sql.strip().rstrip(";").strip() 

    if _FORBIDDEN_KEYWORDS.search(stripped): # se encontrar alguma gracinha de palavra-chave que não seja SELECT, levanta uma exceção
        raise SQLSecurityError(
            "Bloqueado: apenas consultas de leitura (SELECT) são permitidas — "
            "detectada palavra-chave de escrita/DDL na query gerada."
        )
    try:
        statements = [s for s in sqlglot.parse(stripped, read="sqlite") if s is not None] #parseia a query e devolve uma lista de statements
    except Exception as exc:
        raise SQLSecurityError(f"A SQL gerada não pôde ser interpretada: {exc}") from exc

    if len(statements) != 1: # Defesa contra sql injection se a lista de statements tiver mais de 1 elemento, levanta uma exceção
        raise SQLSecurityError(
            f"Bloqueado: esperava exatamente 1 instrução, encontrei {len(statements)} "
            "(instruções encadeadas com ';' não são permitidas)."
        )

    tree = statements[0]
    if not isinstance(tree, (exp.Select, exp.Union, exp.With)): # se o statement não for SELECT, UNION ou WITH, levanta uma exceção
        raise SQLSecurityError(
            f"Bloqueado: esperava SELECT/UNION/WITH, encontrei {type(tree).__name__}."
        )
    return tree

def _with_row_limit(tree, max_rows):
    existing = tree.args.get("limit")
    if existing is not None:
        try:
            current = int(existing.expression.name)
            max_rows = min(current, max_rows)
        except (ValueError, AttributeError):
            pass
    return tree.limit(max_rows).sql(dialect="sqlite")



@contextmanager
def _readonly_connection(db_path: str, timeout: float) -> Generator[sqlite3.Connection, None, None]:
    """Cria uma conexão read-only com o SQLite, que recusa qualquer tentativa de escrita."""
    resolved = Path(db_path).resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"Arquivo de banco de dados não encontrado: {resolved}")

    uri = f"file:{resolved}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)

    deadline = time.monotonic() + timeout

    def _abort_if_timeout() -> int:
        return 1 if time.monotonic() > deadline else 0
    connection.set_progress_handler(_abort_if_timeout, 1000)

    try:
        yield connection
    finally:
        connection.close()


def execute_read_only_query(sql: str, db_path: str, max_rows: int = DEAULT_ROW_LIMIT, time_seconds: float = QUERY_TIMEOUT_SECONDS) -> QueryExecutionResult:
    """Executa uma query SELECT/UNION/WITH no SQLite, com segurança e timeout."""
    tree = validate_readonly_sql(sql)
    final_sql= _with_row_limit(tree, max_rows)
    logger.info(f"Executando query no SQLite: {final_sql}" )

    with _readonly_connection(db_path, time_seconds) as connection:
        cursor = connection.cursor()
        try:
            cursor.execute(final_sql)
            columns = [desc[0] for desc in cursor.description]
            rows = [list(row) for row in cursor.fetchall()]
        except sqlite3.OperationalError as exc:
            raise RuntimeError(f"{exc} | SQL: {final_sql}") from exc

    return QueryExecutionResult(columns=columns, rows=rows, row_count=len(rows))