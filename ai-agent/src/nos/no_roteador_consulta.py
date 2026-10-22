"""
Nó 4: Roteador Semântico — classifica a pergunta como SQL, RAG, Ambos ou Recusa.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Literal

from pydantic import BaseModel, Field

from ..contratos.estado_agente import EstadoAgente
from ..provedores.cliente_llm import ClienteLLM

logger = logging.getLogger("venergy.no_roteador_consulta")

CONFIANCA_MINIMA = 0.60

SYSTEM_PROMPT_ROTEADOR = """
Você é o roteador de perguntas da distribuidora de energia V-Energy Grid 360.

TAREFA: Classifique a pergunta em uma das quatro rotas abaixo e indique sua confiança de 0.0 a 1.0.

ROTAS DISPONÍVEIS:
- "sql"    → A resposta requer consulta ao banco de dados (métricas, valores, contagens, rankings, comparações históricas).
- "rag"    → A resposta requer explicação de conceito ou norma regulatória (ANEEL, PRODIST, DEC, FEC, bandeiras, tarifas, GD).
- "ambos"  → A resposta requer tanto dados do banco quanto explicação regulatória ou contextual.
- "recusa" → A pergunta é ambígua demais, não é possível determinar uma interpretação segura, ou está fora do escopo.

EXEMPLOS:
- "Quantas UCs residenciais estão inadimplentes em Paulista?" → sql, 0.97
- "O que é o indicador DEC e como é calculado?" → rag, 0.98
- "Por que a receita de Olinda caiu se o volume aumentou? O que poderia explicar?" → ambos, 0.90
- "Me conta uma história sobre energia elétrica" → recusa, 0.95
- "Como tá?" → recusa, 0.99

Responda EXCLUSIVAMENTE no formato JSON:
{"rota": "<sql|rag|ambos|recusa>", "confianca": <float>, "motivo": "<até 15 palavras>"}
""".strip()


class _DecisaoRota(BaseModel):
    rota: Literal["sql", "rag", "ambos", "recusa"] = "recusa"
    confianca: float = Field(default=0.0, ge=0.0, le=1.0)
    motivo: str = ""


def _parsear_resposta_roteador(texto: str) -> _DecisaoRota:
    """Extrai o JSON da resposta do LLM com fallback seguro."""
    import json, re
    try:
        # Extrai bloco JSON mesmo que o LLM adicione texto ao redor
        match = re.search(r"\{.*?\}", texto, re.DOTALL)
        if match:
            dados = json.loads(match.group())
            return _DecisaoRota(**dados)
    except Exception:
        pass
    return _DecisaoRota(rota="recusa", confianca=0.0, motivo="Falha ao parsear resposta do roteador.")


def no_roteador_consulta(
    state: EstadoAgente,
    llm: ClienteLLM,
) -> Dict[str, Any]:
    """
    Determina a rota da pergunta usando classificação estruturada Pydantic via LLM.
    Aplica abstenção automática se a confiança estiver abaixo do limiar.
    """
    pergunta = state.get("pergunta_autonoma") or state.get("pergunta_original", "")

    resposta = llm.invoke(
        prompt=f"Pergunta: {pergunta}",
        system_prompt=SYSTEM_PROMPT_ROTEADOR,
        temperatura=0.0,
        resposta_mock='{"rota": "sql", "confianca": 0.92, "motivo": "Consulta de dados operacionais da distribuidora"}',
    )

    chamadas_llm = state.get("chamadas_llm", 0) + 1
    tokens_prompt = state.get("tokens_prompt", 0) + resposta.tokens_prompt
    tokens_resposta = state.get("tokens_resposta", 0) + resposta.tokens_resposta

    decisao = _parsear_resposta_roteador(resposta.texto)

    # Aplica limiar de confiança: baixa confiança = abstenção honesta
    if decisao.confianca < CONFIANCA_MINIMA:
        logger.info(
            "Nó 4 — Confiança %.2f abaixo do limiar %.2f. Redirecionando para recusa.",
            decisao.confianca, CONFIANCA_MINIMA,
        )
        decisao.rota = "recusa"
        decisao.motivo = f"Confiança insuficiente ({decisao.confianca:.0%}) para determinar rota segura."

    logger.info("Nó 4 — Rota: %s | Confiança: %.2f | Motivo: %s", decisao.rota, decisao.confianca, decisao.motivo)

    return {
        "rota": decisao.rota,
        "confianca_rota": decisao.confianca,
        "motivo_rota": decisao.motivo,
        "chamadas_llm": chamadas_llm,
        "tokens_prompt": tokens_prompt,
        "tokens_resposta": tokens_resposta,
        "passos_executados": [
            f"Nó 4 — Roteador: '{decisao.rota}' (confiança {decisao.confianca:.0%}). {decisao.motivo}"
        ],
    }


def rota_pos_roteador(state: EstadoAgente) -> str:
    """Roteamento condicional após o classificador."""
    rota = state.get("rota", "recusa")
    if rota == "recusa":
        return "recusa"
    # "rag", "sql" e "ambos" todos passam pelo RAG para enriquecer o contexto
    # (o RAG filtra o que buscar com base na rota)
    return "recupera_contexto"
