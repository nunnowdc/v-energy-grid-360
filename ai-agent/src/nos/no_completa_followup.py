"""
Nó 2: Reescrita Autônoma de Follow-up — resolve pronomes e referências com base no histórico.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from ..contratos.estado_agente import EstadoAgente
from ..provedores.cliente_llm import ClienteLLM

logger = logging.getLogger("venergy.no_completa_followup")

SYSTEM_PROMPT_FOLLOWUP = """
Você é um especialista em desambiguação de perguntas em contextos de dados corporativos.

TAREFA: Dada a PERGUNTA ATUAL e o HISTÓRICO RECENTE da conversa, reescreva a pergunta atual
de forma completamente autônoma — sem pronomes, referências implícitas ou dependência de contexto anterior.

REGRAS:
1. Se a pergunta atual já for completamente autônoma e clara, retorne-a EXATAMENTE como está.
2. Se a pergunta mudou completamente de assunto em relação ao histórico, retorne-a EXATAMENTE como está.
3. Nunca invente dados, cidades ou valores. Apenas resolva as referências implícitas.
4. Retorne SOMENTE a pergunta reescrita — sem explicações, sem prefixos.

EXEMPLO:
  Histórico: [Usuário: "Quantas UCs residenciais foram cortadas em Olinda no 1º semestre?"]
  Pergunta atual: "E as comerciais?"
  Saída: "Quantas UCs comerciais foram cortadas em Olinda no 1º semestre?"
""".strip()


def _formatar_historico(historico: list[dict]) -> str:
    linhas = []
    for turno in historico[-6:]:  # últimas 3 trocas
        role = "Usuário" if turno.get("role") == "user" else "Agente"
        linhas.append(f"{role}: {turno.get('content', '').strip()}")
    return "\n".join(linhas) or "(sem histórico)"


def no_completa_followup(
    state: EstadoAgente,
    llm: ClienteLLM,
) -> Dict[str, Any]:
    """
    Reescreve a pergunta para ser autônoma usando o histórico recente da sessão.
    Bypass de LLM se não houver histórico (primeira mensagem da conversa).
    """
    pergunta = state.get("pergunta_original", "")
    historico = state.get("historico_recente", [])

    # Bypass: primeira mensagem — zero custo de LLM
    if not historico:
        logger.debug("Nó 2 — Sem histórico, bypass de LLM. Pergunta mantida como autônoma.")
        return {
            "pergunta_autonoma": pergunta,
            "passos_executados": ["Nó 2 — Follow-up: sem histórico, pergunta original mantida (0 chamadas LLM)."],
        }

    historico_texto = _formatar_historico(historico)

    prompt = (
        f"HISTÓRICO RECENTE:\n{historico_texto}\n\n"
        f"PERGUNTA ATUAL: {pergunta}\n\n"
        "PERGUNTA REESCRITA:"
    )

    # Mock: retorna a própria pergunta como exemplo de bypass determinístico
    resposta = llm.invoke(
        prompt=prompt,
        system_prompt=SYSTEM_PROMPT_FOLLOWUP,
        temperatura=0.0,
        resposta_mock=pergunta,
    )

    pergunta_autonoma = resposta.texto.strip().strip('"').strip("'")

    # Sanidade: se a resposta do LLM vier vazia ou muito curta, usa a original
    if len(pergunta_autonoma) < 5:
        pergunta_autonoma = pergunta

    chamadas_llm = state.get("chamadas_llm", 0) + 1
    tokens_prompt = state.get("tokens_prompt", 0) + resposta.tokens_prompt
    tokens_resposta = state.get("tokens_resposta", 0) + resposta.tokens_resposta

    mudou = pergunta_autonoma.strip().lower() != pergunta.strip().lower()
    log_detalhe = f'reescrita para: "{pergunta_autonoma[:80]}"' if mudou else "mantida sem alteração"
    logger.info("Nó 2 — Follow-up %s.", log_detalhe)

    return {
        "pergunta_autonoma": pergunta_autonoma,
        "chamadas_llm": chamadas_llm,
        "tokens_prompt": tokens_prompt,
        "tokens_resposta": tokens_resposta,
        "passos_executados": [f"Nó 2 — Follow-up: {log_detalhe}."],
    }
