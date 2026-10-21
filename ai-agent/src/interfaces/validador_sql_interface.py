"""
Interface abstrata para o validador de consultas SQL (Contrato com a Frente de Segurança).
"""
from __future__ import annotations

from typing import Optional, Protocol
from pydantic import BaseModel, Field


class ResultadoValidacaoSQL(BaseModel):
    """Resultado da análise estática de segurança do SQL."""
    aprovado: bool = Field(description="True se o SQL for seguro e permitido para execução.")
    motivo_rejeicao: Optional[str] = Field(default=None, description="Mensagem explicando o motivo do bloqueio.")
    eh_malicioso: bool = Field(default=False, description="True se for tentativa de ataque deliberado (DDL, injeção).")
    tabelas_detectadas: list[str] = Field(default_factory=list, description="Lista de tabelas identificadas na query.")


class ValidadorSQLInterface(Protocol):
    """
    Protocolo tipado que define o contrato do validador SQL.
    A frente de Segurança implementará esta interface usando SQLGlot.
    """
    def validar(self, sql: str) -> ResultadoValidacaoSQL:
        """Valida se uma consulta SQL é segura e autorizada."""
        ...
