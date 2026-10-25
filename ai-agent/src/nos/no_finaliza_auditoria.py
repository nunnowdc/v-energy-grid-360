"""
Nó 12: Finalização — Gravação do registro de auditoria e montagem do estado final.
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any, Dict, Optional

from ..contratos.estado_agente import EstadoAgente

logger = logging.getLogger("venergy.no_finaliza_auditoria")

COLUNAS_AUDITORIA_BASE = (
    "id", "sessao_id", "pergunta_original", "pergunta_autonoma",
    "rota_escolhida", "hit_cache", "sql_gerado", "linhas_retornadas",
    "amostra_resultado_json", "selo_confianca", "passos_execucao",
    "tempo_execucao_ms", "tokens_prompt", "tokens_resposta", "erro_mensagem",
)
COLUNAS_AUDITORIA_OPCIONAIS = (
    "tentativas_sql", "chamadas_llm", "eh_malicioso", "motivo_recusa",
    "ids_chunks_rag", "user_id", "perfil",
)


def _montar_insert_auditoria(registro: dict, colunas_tabela: set[str]) -> str:
    """Monta o INSERT apenas com colunas existentes na tabela de auditoria."""
    colunas = [c for c in COLUNAS_AUDITORIA_BASE if c in colunas_tabela]
    opcionais = [c for c in COLUNAS_AUDITORIA_OPCIONAIS if c in colunas_tabela]
    faltantes = [c for c in COLUNAS_AUDITORIA_OPCIONAIS if c not in colunas_tabela]
    if faltantes:
        logger.warning("Colunas opcionais ausentes na auditoria: %s", faltantes)
    nomes = ", ".join(colunas + opcionais)
    valores = ", ".join(f"%({coluna})s" for coluna in colunas + opcionais)
    return f"INSERT INTO tb_auditoria_agente ({nomes}) VALUES ({valores});"


def _obter_colunas_psycopg2(conn) -> set[str]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = 'tb_auditoria_agente'"
        )
        return {linha[0] for linha in cur.fetchall()}


def _obter_colunas_psycopg3(conn) -> set[str]:
    resultado = conn.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = 'tb_auditoria_agente'"
    )
    return {linha[0] for linha in resultado.fetchall()}


def _mascarar_amostra(dados: list[dict] | None, max_linhas: int = 3) -> str:
    """
    Retorna os primeiros N registros em JSON com campos sensíveis mascarados.
    """
    if not dados:
        return "[]"
    amostra = dados[:max_linhas]
    campos_sensiveis = {"cpf", "nome", "endereco", "telefone", "email"}
    amostra_limpa = [
        {
            k: "***"
            if any(campo in k.lower() for campo in campos_sensiveis)
            else v
            for k, v in row.items()
        }
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
    audit_id = state.get("audit_id") or str(uuid.uuid4())
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
        "tentativas_sql": state.get("tentativas_sql", 0),
        "chamadas_llm": state.get("chamadas_llm", 0),
        "eh_malicioso": state.get("eh_malicioso", False),
        "motivo_recusa": state.get("motivo_recusa"),
        "ids_chunks_rag": json.dumps(
            [chunk.get("id") for chunk in state.get("contexto_rag", []) if chunk.get("id")],
            ensure_ascii=False,
        ),
        "user_id": state.get("user_id"),
        "perfil": state.get("perfil"),
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
                colunas = _obter_colunas_psycopg2(conn)
                cur.execute(_montar_insert_auditoria(registro, colunas), registro)
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
            colunas = _obter_colunas_psycopg3(conn)
            conn.execute(_montar_insert_auditoria(registro, colunas), registro)
            conn.commit()
    except Exception as e:
        logger.error("⚠️  Falha ao gravar auditoria com psycopg3 (audit_id=%s): %s", registro["id"], e)
