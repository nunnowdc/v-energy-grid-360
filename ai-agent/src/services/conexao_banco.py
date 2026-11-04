"""
Conexão do agente com o PostgreSQL: escolha da URL e troca de role por perfil.

Com USE_DB_ROLES desligada nada muda: vale a DATABASE_URL e nenhum SET ROLE roda.
Ligada, o agente conecta como portal_app (PORTAL_APP_DATABASE_URL) e cada
transação assume o role do perfil da sessão. O perfil nunca vem do corpo da requisição.
"""
from __future__ import annotations

import os
import re
from typing import Any, Optional

_VALORES_VERDADEIROS = {"1", "true", "yes", "on", "sim"}

# Mapa fixo: o nome do role nunca vem de dado do cliente nem é montado a partir dele
PERFIL_PARA_ROLE = {
    "DIRETORIA": "perfil_diretoria",
    "ATENDIMENTO": "perfil_atendimento",
    "PERDAS": "perfil_perdas",
    "OPERACAO": "perfil_operacao",
    "ADMIN_TI": "perfil_admin_ti",
}


def usa_roles() -> bool:
    return os.getenv("USE_DB_ROLES", "").strip().lower() in _VALORES_VERDADEIROS


def url_do_banco() -> Optional[str]:
    """DATABASE_URL com a variável desligada; PORTAL_APP_DATABASE_URL (postgresql://) ligada."""
    if not usa_roles():
        return os.getenv("DATABASE_URL")
    url = os.getenv("PORTAL_APP_DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError("USE_DB_ROLES ligada, mas PORTAL_APP_DATABASE_URL não está definida.")
    # Remove o driver da URL (postgresql+psycopg2:// -> postgresql://)
    return re.sub(r"^(postgres(?:ql)?)\+[A-Za-z0-9_]+://", r"\1://", url)


def aplicar_perfil(cursor: Any, perfil: Optional[str]) -> None:
    """Roda SET LOCAL ROLE do perfil. Não faz nada com USE_DB_ROLES desligada."""
    if not usa_roles():
        return
    if perfil is None:
        raise ValueError("Perfil não definido para a conexão.")
    role = PERFIL_PARA_ROLE.get(perfil)
    if role is None:
        raise ValueError("Perfil desconhecido.")
    cursor.execute(f'SET LOCAL ROLE "{role}"')


class ExecutorComPerfil:
    """Fixa o perfil da sessão num executor compartilhado (só usado com roles ligadas)."""

    def __init__(self, executor: Any, perfil: Optional[str]):
        self._executor = executor
        self._perfil = perfil

    def executar(self, sql: str, *args: Any, **kwargs: Any):
        return self._executor.executar(sql, *args, perfil=self._perfil, **kwargs)
