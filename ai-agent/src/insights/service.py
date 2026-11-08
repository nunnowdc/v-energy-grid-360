"""Serviço de leitura, geração e persistência de insights de tela."""
from __future__ import annotations

import json
import logging
import os
from datetime import date, datetime
from typing import Any, Dict, Optional

from ..provedores.cliente_llm import ClienteLLM
from ..services.conexao_banco import ExecutorComPerfil, aplicar_perfil, url_do_banco, usa_roles
from ..services.sql_executor import SQLExecutor
from .conferente_numerico import conferir
from .extrator_metricas_fixas import extrair_metricas, fontes_da_tela
from .narrador_insights import narrar_insight, gerar_texto_modelo

logger = logging.getLogger("venergy.insights.service")


class InsightsService:
    def __init__(
        self,
        executor: Optional[SQLExecutor] = None,
        llm: Optional[ClienteLLM] = None,
        db_url: Optional[str] = None,
    ):
        self.db_url = db_url or url_do_banco()
        self.executor = executor or SQLExecutor(db_url=self.db_url)
        self.llm = llm or ClienteLLM()

    def obter(
        self, tela: str, entidade_id: str, perfil: Optional[str] = None
    ) -> Dict[str, Any]:
        # O perfil vem da sessão (ai_router), nunca do corpo da requisição
        executor = ExecutorComPerfil(self.executor, perfil) if usa_roles() else self.executor
        cached = self._ler_cache(tela, entidade_id, perfil)
        if cached is not None:
            return cached

        fatos = extrair_metricas(tela, entidade_id, executor)
        if not fatos:
            # Retorna 404/vazio caso não haja fatos (tratado pelo endpoint se necessário)
            return {
                "tela": tela,
                "entidade_id": entidade_id,
                "insight_texto": (
                    "Não há dados disponíveis para esta unidade consumidora."
                    if tela == "visao_360_uc"
                    else "Não há dados disponíveis para este insight no momento."
                ),
                "metricas_destaque": {},
                "selo": "template_fallback",
                "tempo_ms": 0.0,
                "fontes": [],
            }

        # Prepara fatos para a narração: converte datas para formato curto (ex.: "jun/2026")
        MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
        fatos_formatados = []
        for f in fatos:
            f_copy = f.copy()
            if isinstance(f_copy.get("competencia"), (datetime, date)):
                c = f_copy["competencia"]
                f_copy["competencia"] = f"{MESES[c.month - 1]}/{c.year}"
            if "consumo_kwh" in f_copy and f_copy["consumo_kwh"] is not None:
                try:
                    f_copy["consumo_kwh"] = int(round(float(f_copy["consumo_kwh"])))
                except (ValueError, TypeError):
                    pass
            fatos_formatados.append(f_copy)

        # Tentativa de geração com retry até 3 vezes se a conferência falhar
        max_tentativas = 3
        selo = "template_fallback"
        texto = ""
        for tentativa in range(1, max_tentativas + 1):
            texto = narrar_insight(tela, fatos_formatados, self.llm)
            if conferir(fatos_formatados, texto):
                selo = "auditado_llm"
                break
            logger.warning("Tentativa %d de geração de insight falhou (conferência). Texto rejeitado: %s", tentativa, texto)

        # Se todas as tentativas falharem, usa texto-modelo fallback sem gravar cache
        # Se todas as tentativas falharem, usa texto-modelo fallback sem gravar cache
        if selo == "template_fallback":
            texto = gerar_texto_modelo(tela, fatos_formatados)

        fontes = fontes_da_tela(tela)

        resultado = {
            "tela": tela,
            "entidade_id": entidade_id,
            "insight_texto": texto,
            "metricas_destaque": fatos_formatados[0] if fatos_formatados else {},
            "selo": selo,
            "tempo_ms": 0.0,
            "fontes": fontes,
        }

        # Apenas grava no cache se obteve sucesso auditado pela LLM
        if selo == "auditado_llm":
            self._gravar_cache(resultado, fatos, perfil)

        return resultado

    def _ler_cache(
        self, tela: str, entidade_id: str, perfil: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        if not self.db_url:
            return None
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            with psycopg2.connect(self.db_url, connect_timeout=3) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    aplicar_perfil(cur, perfil)
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
                "tela": row["tela"],
                "entidade_id": row["entidade_id"],
                "insight_texto": row["texto_insight"],
                "metricas_destaque": fatos[0] if fatos else {},
                "selo": row["selo_validacao"],
                "tempo_ms": 0.0,
                "fontes": fontes_da_tela(tela) if fatos else [],
            }
        except Exception as exc:
            logger.warning("Cache de insights indisponível: %s", exc)
            return None

    def _gravar_cache(
        self, resultado: Dict[str, Any], fatos: list[Dict[str, Any]], perfil: Optional[str] = None
    ) -> None:
        if not self.db_url:
            return
        try:
            import psycopg2
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    aplicar_perfil(cur, perfil)
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
