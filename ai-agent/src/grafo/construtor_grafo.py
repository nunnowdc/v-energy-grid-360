"""
Construtor do Grafo LangGraph — Fatia 2 completa.
Inclui todos os nós de segurança, follow-up, escopo, roteamento e o fluxo SQL da Fatia 1.
"""
from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "src.grafo"

from langgraph.graph import StateGraph, START, END

from ..contratos.estado_agente import EstadoAgente
from ..interfaces.stub_validador_sql import StubValidadorSQL
from ..interfaces.validador_sql_interface import ValidadorSQLInterface
from ..nos.no_filtro_seguranca import no_filtro_seguranca, rota_pos_filtro
from ..nos.no_completa_followup import no_completa_followup
from ..nos.no_checa_escopo import no_checa_escopo, rota_pos_escopo
from ..nos.no_roteador_consulta import no_roteador_consulta, rota_pos_roteador
from ..nos.no_escreve_sql import no_escreve_sql
from ..nos.no_valida_sql import no_valida_sql, rota_pos_validacao
from ..nos.no_executa_sql import no_executa_sql, rota_pos_execucao
from ..nos.no_recusa_honesta import no_recusa_honesta
from ..nos.no_sintetiza_resposta import no_sintetiza_resposta
from ..nos.no_finaliza_auditoria import no_finaliza_auditoria
from ..nos.no_cache_parametrizado import no_cache_parametrizado
from ..nos.no_recupera_contexto import no_recupera_contexto
from ..provedores.cliente_llm import ClienteLLM
from ..services.sql_executor import SQLExecutor

logger = logging.getLogger("venergy.construtor_grafo")


def _inicializar_estado(
    pergunta: str,
    historico: list[dict] | None,
    sessao_id: str,
) -> Dict[str, Any]:
    """Preenche os campos obrigatórios do EstadoAgente antes de iniciar o grafo."""
    return {
        "sessao_id": sessao_id,
        "pergunta_original": pergunta,
        "pergunta_autonoma": pergunta,
        "historico_recente": (historico or [])[-6:],
        "contexto_rag": [],
        "hit_cache": False,
        "tentativas_sql": 0,
        "max_tentativas": 2,
        "chamadas_llm": 0,
        "tokens_prompt": 0,
        "tokens_resposta": 0,
        "passos_executados": [],
        "tempo_inicio_ts": time.time(),
        "malicioso": False,
        "dentro_escopo": True,
    }


def construir_grafo(
    llm: Optional[ClienteLLM] = None,
    validador: Optional[ValidadorSQLInterface] = None,
    executor: Optional[SQLExecutor] = None,
    db_url: Optional[str] = None,
) -> Any:
    """
    Compila e retorna o grafo LangGraph com todas as Fatias 1 e 2.
    Todas as dependências são injetadas para facilitar mocks nos testes.

    Fluxo completo (Fatias 1 + 2):

    START
      └─► no_filtro_seguranca
            ├─► [bloqueado] no_recusa_honesta ──────────────────────────────► no_finaliza_auditoria ► END
            └─► [aprovado]  no_completa_followup
                              └─► no_checa_escopo
                                    ├─► [fora_escopo] no_recusa_honesta ────► no_finaliza_auditoria ► END
                                    └─► [dentro_escopo] no_roteador_consulta
                                          ├─► [recusa]            no_recusa_honesta ─► no_finaliza_auditoria ► END
                                          └─► [recupera_contexto] no_recupera_contexto  ← Fatia 3
                                                └─► no_cache_parametrizado              ← Fatia 3
                                                      ├─► [cache_hit]  no_executa_sql
                                                      └─► [cache_miss] no_escreve_sql
                                                                          └─► no_valida_sql
                                                                                ├─► [executa]    no_executa_sql
                                                                                ├─► [retry_sql]  no_escreve_sql
                                                                                └─► [recusa]     no_recusa_honesta
                                                            no_executa_sql
                                                              ├─► [sintetiza]  no_sintetiza_resposta
                                                              ├─► [retry_sql]  no_escreve_sql
                                                              └─► [recusa]     no_recusa_honesta
                                                            no_sintetiza_resposta ─► no_finaliza_auditoria ► END

    O RAG, o cache parametrizado e a síntese seguem o fluxo de produção; o
    validador padrão continua sendo o stub até a entrega da frente de Segurança.
    """
    _llm = llm or ClienteLLM()
    _validador = validador or StubValidadorSQL()
    _executor = executor or SQLExecutor(db_url=db_url or os.getenv("DATABASE_URL"))
    _db_url = db_url or os.getenv("DATABASE_URL")

    def _rota_pos_cache(state: EstadoAgente) -> str:
        """Cache hit vai direto para execução; miss vai para geração de SQL."""
        return "cache_hit" if state.get("hit_cache") else "cache_miss"

    # ── Wrappers com injeção de dependência ──
    def _no_filtro_seguranca(s: EstadoAgente) -> Dict[str, Any]:
        return no_filtro_seguranca(s)

    def _no_completa_followup(s: EstadoAgente) -> Dict[str, Any]:
        return no_completa_followup(s, llm=_llm)

    def _no_checa_escopo(s: EstadoAgente) -> Dict[str, Any]:
        return no_checa_escopo(s, llm=_llm)

    def _no_roteador_consulta(s: EstadoAgente) -> Dict[str, Any]:
        return no_roteador_consulta(s, llm=_llm)

    def _no_recupera_contexto(s: EstadoAgente) -> Dict[str, Any]:
        return no_recupera_contexto(s)

    def _no_cache_parametrizado(s: EstadoAgente) -> Dict[str, Any]:
        return no_cache_parametrizado(s, db_url=_db_url)

    def _no_escreve_sql(s: EstadoAgente) -> Dict[str, Any]:
        return no_escreve_sql(s, llm=_llm)

    def _no_valida_sql(s: EstadoAgente) -> Dict[str, Any]:
        return no_valida_sql(s, validador=_validador)

    def _no_executa_sql(s: EstadoAgente) -> Dict[str, Any]:
        return no_executa_sql(s, executor=_executor)

    def _no_sintetiza_resposta(s: EstadoAgente) -> Dict[str, Any]:
        return no_sintetiza_resposta(s, llm=_llm)

    def _no_recusa_honesta(s: EstadoAgente) -> Dict[str, Any]:
        return no_recusa_honesta(s)

    def _no_finaliza_auditoria(s: EstadoAgente) -> Dict[str, Any]:
        return no_finaliza_auditoria(s, db_url=_db_url)

    # ── Montagem do Grafo ──
    grafo = StateGraph(EstadoAgente)

    # Registra todos os nós
    grafo.add_node("no_filtro_seguranca",     _no_filtro_seguranca)
    grafo.add_node("no_completa_followup",    _no_completa_followup)
    grafo.add_node("no_checa_escopo",         _no_checa_escopo)
    grafo.add_node("no_roteador_consulta",    _no_roteador_consulta)
    grafo.add_node("no_recupera_contexto", _no_recupera_contexto)
    grafo.add_node("no_cache_parametrizado", _no_cache_parametrizado)
    grafo.add_node("no_escreve_sql",          _no_escreve_sql)
    grafo.add_node("no_valida_sql",           _no_valida_sql)
    grafo.add_node("no_executa_sql",          _no_executa_sql)
    grafo.add_node("no_recusa_honesta",       _no_recusa_honesta)
    grafo.add_node("no_sintetiza_resposta",   _no_sintetiza_resposta)
    grafo.add_node("no_finaliza_auditoria",   _no_finaliza_auditoria)

    # ── Arestas ──

    # Nó 1: Filtro de Segurança
    grafo.add_edge(START, "no_filtro_seguranca")
    grafo.add_conditional_edges(
        "no_filtro_seguranca",
        rota_pos_filtro,
        {
            "bloqueado": "no_recusa_honesta",
            "aprovado":  "no_completa_followup",
        },
    )

    # Nó 2: Follow-up → sempre segue para Escopo
    grafo.add_edge("no_completa_followup", "no_checa_escopo")

    # Nó 3: Escopo
    grafo.add_conditional_edges(
        "no_checa_escopo",
        rota_pos_escopo,
        {
            "fora_escopo":    "no_recusa_honesta",
            "dentro_escopo":  "no_roteador_consulta",
        },
    )

    # Nó 4: Roteador
    grafo.add_conditional_edges(
        "no_roteador_consulta",
        rota_pos_roteador,
        {
            "recusa":             "no_recusa_honesta",
            "recupera_contexto":  "no_recupera_contexto",
        },
    )

    grafo.add_conditional_edges(
        "no_recupera_contexto",
        lambda state: "sintetiza" if state.get("rota") == "rag" else "cache",
        {"sintetiza": "no_sintetiza_resposta", "cache": "no_cache_parametrizado"},
    )

    # Nó 6: Cache hit/miss
    grafo.add_conditional_edges(
        "no_cache_parametrizado",
        _rota_pos_cache,
        {
            "cache_hit":  "no_executa_sql",
            "cache_miss": "no_escreve_sql",
        },
    )

    # Nó 7 → Nó 8
    grafo.add_edge("no_escreve_sql", "no_valida_sql")

    # Nó 8: Validação — retry, executa ou recusa
    grafo.add_conditional_edges(
        "no_valida_sql",
        rota_pos_validacao,
        {
            "executa":    "no_executa_sql",
            "retry_sql":  "no_escreve_sql",
            "recusa":     "no_recusa_honesta",
        },
    )

    # Nó 9: Execução — síntese, retry ou recusa
    grafo.add_conditional_edges(
        "no_executa_sql",
        rota_pos_execucao,
        {
            "sintetiza":  "no_sintetiza_resposta",
            "retry_sql":  "no_escreve_sql",
            "recusa":     "no_recusa_honesta",
        },
    )

    # Nó 11 e 10 → Nó 12 (auditoria terminal)
    grafo.add_edge("no_sintetiza_resposta", "no_finaliza_auditoria")
    grafo.add_edge("no_recusa_honesta",     "no_finaliza_auditoria")
    grafo.add_edge("no_finaliza_auditoria", END)

    return grafo.compile(), _inicializar_estado


# Mantém compat com Fatia 1
construir_grafo_final = construir_grafo


if __name__ == "__main__":
    grafo, _ = construir_grafo_final()
    grafo.get_graph().draw_mermaid_png(output_file_path="theme_code_dracula.png")