"""
Nó 12: Finalização — Gravação do registro de auditoria e montagem do estado final.
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any, Dict, Optional

from ai_agent.src.contratos.estado_agente import EstadoAgente

logger = logging.getLogger("venergy.no_finaliza_auditoria")

INSERT_AUDIT_SQL = """
INSERT INTO tb_auditoria_agente (
    id, sessao_id, pergunta_original, pergunta_autonoma,
    rota_escolhida, hit_cache, sql_gerado, linhas_retornadas,
    amostra_resultado_json, selo_confianca, passos_execucao,
    tempo_execucao_ms, tokens_prompt, tokens_resposta, erro_mensagem
) VALUES (
    %(id)s, %(sessao_id)s, %(pergunta_original)s, %(pergunta_autonoma)s,
    %(rota_escolhida)s, %(hit_cache)s, %(sql_gerado)s, %(linhas_retornadas)s,
    %(amostra_resultado_json)s, %(selo_confianca)s, %(passos_execucao)s,
    %(tempo_execucao_ms)s, %(tokens_prompt)s, %(tokens_resposta)s, %(erro_mensagem)s
);
"""


def _mascarar_amostra(dados: list[dict] | None, max_linhas: int = 3) -> str:
    """
    Retorna os primeiros N registros em JSON com campos sensíveis mascarados.
    """
    if not dados:
        return "[]"
    amostra = dados[:max_linhas]
    campos_sensiveis = {"cpf", "nome", "endereco", "telefone", "email"}
    amostra_limpa = [
        {k: "***" if k.lower() in campos_sensiveis else v for k, v in row.items()}
        for row in amostra
    ]
    try:
        return json.dumps(amostra_limpa, ensure_ascii=False, default=str)
    except Exception:
        return "[]"


def no_finaliza_auditoria(
    state: EstadoAgente,
    db_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Grava o log de auditoria no PostgreSQL e calcula o tempo total de execução.
    Falha com segurança: se o banco de auditoria não responder, o erro é logado
    mas a resposta ao usuário NÃO é bloqueada.
    """
    audit_id = str(uuid.uuid4())
    inicio_ts = state.get("tempo_inicio_ts", time.time())
    tempo_total_ms = (time.time() - inicio_ts) * 1000

    dados = state.get("dados_sql")
    registro = {
        "id": audit_id,
        "sessao_id": state.get("sessao_id", "anonimo"),
        "pergunta_original": state.get("pergunta_original", ""),
        "pergunta_autonoma": state.get("pergunta_autonoma", ""),
        "rota_escolhida": state.get("rota", "desconhecida"),
        "hit_cache": state.get("hit_cache", False),
        "sql_gerado": state.get("sql_gerado"),
        "linhas_retornadas": state.get("total_linhas_retornadas", 0),
        "amostra_resultado_json": _mascarar_amostra(dados),
        "selo_confianca": state.get("selo_confianca", "erro_bloqueado"),
        "passos_execucao": json.dumps(state.get("passos_executados", []), ensure_ascii=False),
        "tempo_execucao_ms": round(tempo_total_ms, 2),
        "tokens_prompt": state.get("tokens_prompt", 0),
        "tokens_resposta": state.get("tokens_resposta", 0),
        "erro_mensagem": state.get("erro_validacao_ou_execucao"),
    }

    _gravar_auditoria(registro, db_url)

    return {
        "audit_id": audit_id,
        "tempo_total_ms": round(tempo_total_ms, 2),
        "passos_executados": [
            f"Nó 12 — Auditoria gravada (audit_id={audit_id} | {tempo_total_ms:.0f}ms total)."
        ],
    }


def _gravar_auditoria(registro: dict, db_url: Optional[str]) -> None:
    """Grava o registro no banco com fallback para log em caso de falha."""
    if not db_url:
        logger.info("Auditoria (modo local/mock): %s", json.dumps(registro, ensure_ascii=False, default=str)[:400])
        return

    try:
        import psycopg2
        with psycopg2.connect(db_url, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute(INSERT_AUDIT_SQL, registro)
            conn.commit()
        logger.info("Auditoria gravada no PostgreSQL: audit_id=%s", registro["id"])
    except ImportError:
        _tentar_psycopg3(registro, db_url)
    except Exception as e:
        # Falha segura: a resposta do usuário não pode ser bloqueada por falha de auditoria
        logger.error("⚠️  Falha ao gravar auditoria (audit_id=%s): %s", registro["id"], e)


def _tentar_psycopg3(registro: dict, db_url: str) -> None:
    try:
        import psycopg
        with psycopg.connect(db_url) as conn:
            conn.execute(INSERT_AUDIT_SQL, registro)
            conn.commit()
    except Exception as e:
        logger.error("⚠️  Falha ao gravar auditoria com psycopg3 (audit_id=%s): %s", registro["id"], e)
