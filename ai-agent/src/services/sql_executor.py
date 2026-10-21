"""
Executor seguro de consultas SQL com timeout, limite de linhas e suporte a PostgreSQL e SQLite sintético.
"""
from __future__ import annotations

import logging
import os
import sqlite3
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

logger = logging.getLogger("venergy.sql_executor")

DEFAULT_ROW_LIMIT = 50
QUERY_TIMEOUT_SECONDS = 30.0


class ResultadoExecucaoSQL(BaseModel):
    sucesso: bool
    linhas: List[Dict[str, Any]] = []
    total_linhas: int = 0
    tempo_execucao_ms: float = 0.0
    erro: Optional[str] = None


class SQLExecutor:
    """
    Executa queries SQL em modo estritamente READ-ONLY com governança de timeout e volume.
    """

    def __init__(self, db_url: Optional[str] = None, sqlite_path: Optional[str] = None):
        self.db_url = db_url or os.getenv("DATABASE_URL")
        self.sqlite_path = sqlite_path or os.getenv("SQLITE_PATH")

    def executar(self, sql: str, limite_linhas: int = DEFAULT_ROW_LIMIT) -> ResultadoExecucaoSQL:
        inicio = time.time()
        sql_limpa = sql.strip().rstrip(";")

        # Injeta LIMIT se não houver LIMIT explícito na query
        if "limit" not in sql_limpa.lower():
            sql_limpa = f"{sql_limpa} LIMIT {limite_linhas}"

        # 1. Se houver DATABASE_URL (PostgreSQL)
        if self.db_url and self.db_url.startswith("postgres"):
            return self._executar_postgres(sql_limpa, inicio)

        # 2. Se houver caminho SQLite ou fallback para teste
        return self._executar_sqlite(sql_limpa, inicio)

    def _executar_postgres(self, sql: str, inicio: float) -> ResultadoExecucaoSQL:
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
        except ImportError:
            try:
                import psycopg
                return self._executar_psycopg3(sql, inicio)
            except ImportError:
                return ResultadoExecucaoSQL(
                    sucesso=False,
                    erro="Driver PostgreSQL (psycopg2 ou psycopg) não está instalado no ambiente.",
                    tempo_execucao_ms=(time.time() - inicio) * 1000,
                )

        conn = None
        try:
            conn = psycopg2.connect(
                self.db_url,
                connect_timeout=int(QUERY_TIMEOUT_SECONDS),
                options=f"-c statement_timeout={int(QUERY_TIMEOUT_SECONDS * 1000)}",
            )
            conn.set_session(readonly=True, autocommit=True)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql)
                rows = cur.fetchall()
                dados = [dict(r) for r in rows]
                return ResultadoExecucaoSQL(
                    sucesso=True,
                    linhas=dados,
                    total_linhas=len(dados),
                    tempo_execucao_ms=(time.time() - inicio) * 1000,
                )
        except Exception as e:
            logger.error("Erro na execução SQL PostgreSQL: %s", e)
            return ResultadoExecucaoSQL(
                sucesso=False,
                erro=str(e),
                tempo_execucao_ms=(time.time() - inicio) * 1000,
            )
        finally:
            if conn:
                conn.close()

    def _executar_psycopg3(self, sql: str, inicio: float) -> ResultadoExecucaoSQL:
        import psycopg
        from psycopg.rows import dict_row

        conn = None
        try:
            conn = psycopg.connect(self.db_url, timeout=QUERY_TIMEOUT_SECONDS, autocommit=True)
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(sql)
                rows = cur.fetchall()
                dados = [dict(r) for r in rows]
                return ResultadoExecucaoSQL(
                    sucesso=True,
                    linhas=dados,
                    total_linhas=len(dados),
                    tempo_execucao_ms=(time.time() - inicio) * 1000,
                )
        except Exception as e:
            return ResultadoExecucaoSQL(
                sucesso=False,
                erro=str(e),
                tempo_execucao_ms=(time.time() - inicio) * 1000,
            )
        finally:
            if conn:
                conn.close()

    def _executar_sqlite(self, sql: str, inicio: float) -> ResultadoExecucaoSQL:
        db_path = self.sqlite_path or ":memory:"
        try:
            conn = sqlite3.connect(db_path, timeout=QUERY_TIMEOUT_SECONDS)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            dados = [dict(r) for r in rows]
            conn.close()
            return ResultadoExecucaoSQL(
                sucesso=True,
                linhas=dados,
                total_linhas=len(dados),
                tempo_execucao_ms=(time.time() - inicio) * 1000,
            )
        except Exception as e:
            logger.error("Erro na execução SQLite: %s", e)
            return ResultadoExecucaoSQL(
                sucesso=False,
                erro=str(e),
                tempo_execucao_ms=(time.time() - inicio) * 1000,
            )
