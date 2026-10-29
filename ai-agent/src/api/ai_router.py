"""
Ponto de integração do módulo de IA com o FastAPI.
Monta o roteador /ai com os endpoints: /ask, /insights, /audit e /feedback.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..contratos.resposta_agente import TelaDashboard
from ..grafo.executor_agente import executar_agente
from ..insights.service import InsightsService

logger = logging.getLogger("venergy.api_ai")

router = APIRouter(prefix="/ai", tags=["Agente de IA"])


# --- Schemas de Request e Response ---

class RequisicaoChat(BaseModel):
    user_id: str = Field(description="Identificador do usuário autenticado no portal.")
    session_id: str = Field(description="Identificador único da sessão de conversa.")
    message: str = Field(description="Texto da pergunta em linguagem natural.")
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Contexto da tela (page, id_uc, etc.) para enriquecer a resposta."
    )
    history: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description="Histórico de turnos anteriores [{'role': 'user'/'assistant', 'content': '...'}]."
    )


class RespostaChat(BaseModel):
    answer: str
    sql: Optional[str] = None
    audit_id: str
    selo_confianca: str
    fontes: List[str] = []
    tempo_ms: float
    # Tela e filtros que o portal abre ao lado da resposta (None = não muda a tela)
    dashboard: Optional[TelaDashboard] = None


class RequisicaoFeedback(BaseModel):
    audit_id: str
    feedback: int = Field(description="1 para útil, -1 para inútil.")


# --- Endpoints ---

@router.post("/ask", response_model=RespostaChat, summary="Pergunta em linguagem natural ao agente")
def ask(req: RequisicaoChat) -> RespostaChat:
    """
    Recebe uma pergunta do portal React, executa o agente LangGraph e retorna
    a resposta, o SQL gerado e o audit_id para inspeção de trilha.
    """
    try:
        resultado = executar_agente(
            pergunta=req.message,
            historico=req.history,
            sessao_id=req.session_id,
            user_id=req.user_id,
            contexto_tela=req.context,
        )
    except Exception as e:
        logger.error("Erro no endpoint /ai/ask: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Erro interno no processamento da pergunta.")

    return RespostaChat(
        answer=resultado.resposta_texto,
        sql=resultado.sql_gerado,
        audit_id=resultado.audit_id,
        selo_confianca=resultado.selo_confianca,
        fontes=resultado.fontes_citadas,
        tempo_ms=resultado.tempo_execucao_ms,
        dashboard=resultado.dashboard,
    )


@router.get("/insights/{tela}/{entidade_id}", summary="Insight proativo pré-calculado para a tela")
def get_insight(tela: str, entidade_id: str) -> Dict[str, Any]:
    """
    Retorna o insight pré-calculado e validado numericamente para uma tela específica do portal.
    Resposta em < 30ms via cache na tabela tb_insights_tela.
    """
    try:
        return InsightsService().obter(tela, entidade_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Erro ao gerar insight %s/%s: %s", tela, entidade_id, exc)
        raise HTTPException(status_code=500, detail="Erro ao gerar insight.") from exc


@router.get("/audit/{audit_id}", summary="Trilha de auditoria detalhada de uma resposta")
def get_audit(audit_id: str) -> Dict[str, Any]:
    """
    Retorna os detalhes completos de auditoria de uma execução para a gaveta de
    inspeção 'Como a IA chegou nisso?' no portal React.
    """
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise HTTPException(status_code=503, detail="Banco de auditoria não configurado.")

    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        with psycopg2.connect(db_url) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM tb_auditoria_agente WHERE id = %s;", (audit_id,))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Registro de auditoria não encontrado.")
                return dict(row)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erro ao consultar auditoria %s: %s", audit_id, e)
        raise HTTPException(status_code=500, detail="Erro ao recuperar trilha de auditoria.")


@router.post("/feedback", summary="Registro de feedback do usuário sobre uma resposta")
def post_feedback(req: RequisicaoFeedback) -> Dict[str, str]:
    """
    Recebe 👍 (1) ou 👎 (-1) do usuário e registra na tabela de auditoria
    para alimentar as métricas de avaliação automatizada (REQ-AI-08).
    """
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        return {"status": "mock", "mensagem": "Feedback registrado localmente (modo dev)."}

    try:
        import psycopg2
        with psycopg2.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE tb_auditoria_agente SET feedback_usuario = %s WHERE id = %s;",
                    (req.feedback, req.audit_id),
                )
            conn.commit()
        return {"status": "ok", "mensagem": "Feedback registrado com sucesso."}
    except Exception as e:
        logger.error("Erro ao registrar feedback %s: %s", req.audit_id, e)
        raise HTTPException(status_code=500, detail="Erro ao salvar o feedback.")
