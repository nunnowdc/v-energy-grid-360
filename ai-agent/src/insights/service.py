"""Serviço de leitura, geração e persistência de insights de tela."""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional

from ..provedores.cliente_llm import ClienteLLM
from ..services.sql_executor import SQLExecutor
from .conferente_numerico import conferir
from .extrator_metricas_fixas import extrair_metricas
from .narrador_insights import narrar_insight

logger = logging.getLogger("venergy.insights.service")


class InsightsService:
    def __init__(
        self,
        executor: Optional[SQLExecutor] = None,
        llm: Optional[ClienteLLM] = None,
        db_url: Optional[str] = None,
    ):
        self.db_url = db_url or os.getenv("DATABASE_URL")
        self.executor = executor or SQLExecutor(db_url=self.db_url)
        self.llm = llm or ClienteLLM()

    def obter(self, tela: str, entidade_id: str) -> Dict[str, Any]:
        cached = self._ler_cache(tela, entidade_id)
        if cached is not None:
            return cached

        fatos = extrair_metricas(tela, entidade_id, self.executor)
        texto = narrar_insight(tela, fatos, self.llm)
        selo = "auditado_llm" if conferir(fatos, texto) else "template_fallback"
        if selo == "template_fallback":
            texto = "Não foi possível validar numericamente o texto gerado; consulte os dados exibidos."
        resultado = {
            "tela": tela,
            "entidade_id": entidade_id,
            "insight_texto": texto,
            "metricas_destaque": fatos[0] if fatos else {},
            "selo": selo,
            "tempo_ms": 0.0,
        }
        self._gravar_cache(resultado, fatos)
        return resultado

    def _ler_cache(self, tela: str, entidade_id: str) -> Optional[Dict[str, Any]]:
        if not self.db_url:
            return None
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            with psycopg2.connect(self.db_url, connect_timeout=3) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        "SELECT tela, entidade_id, fatos_calculados_json, texto_insight, "
                        "selo_validacao FROM tb_insights_tela "
                        "WHERE tela = %s AND entidade_id = %s;",
                        (tela, entidade_id),
                    )
                    row = cur.fetchone()
            if not row:
                return None
            fatos = row["fatos_calculados_json"]
            if isinstance(fatos, str):
                fatos = json.loads(fatos)
            return {
                "tela": row["tela"], "entidade_id": row["entidade_id"],
                "insight_texto": row["texto_insight"],
                "metricas_destaque": fatos[0] if fatos else {},
                "selo": row["selo_validacao"], "tempo_ms": 0.0,
            }
        except Exception as exc:
            logger.warning("Cache de insights indisponível: %s", exc)
            return None

    def _gravar_cache(self, resultado: Dict[str, Any], fatos: list[Dict[str, Any]]) -> None:
        if not self.db_url:
            return
        try:
            import psycopg2
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO tb_insights_tela "
                        "(tela, entidade_id, fatos_calculados_json, texto_insight, selo_validacao) "
                        "VALUES (%s, %s, %s, %s, %s) "
                        "ON CONFLICT (tela, entidade_id) DO UPDATE SET "
                        "fatos_calculados_json = EXCLUDED.fatos_calculados_json, "
                        "texto_insight = EXCLUDED.texto_insight, "
                        "selo_validacao = EXCLUDED.selo_validacao, gerado_em = CURRENT_TIMESTAMP;",
                        (resultado["tela"], resultado["entidade_id"], json.dumps(fatos, default=str),
                         resultado["insight_texto"], resultado["selo"]),
                    )
                conn.commit()
        except Exception as exc:
            logger.warning("Não foi possível persistir insight: %s", exc)