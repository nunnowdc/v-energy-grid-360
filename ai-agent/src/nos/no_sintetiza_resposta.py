"""
Nó 11: Síntese da resposta final — narrativa clara a partir dos dados SQL e/ou contexto RAG.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict

from ai_agent.src.contratos.estado_agente import EstadoAgente
from ai_agent.src.provedores.cliente_llm import ClienteLLM

logger = logging.getLogger("venergy.no_sintetiza_resposta")

SYSTEM_PROMPT_SINTESE = """
Você é o assistente de dados da V-Energy Grid 360, uma distribuidora de energia elétrica.
Sua função é transformar dados tabulares em respostas claras, objetivas e executivas em português.

REGRAS ABSOLUTAS:
1. PROIBIDO inventar, estimar ou calcular qualquer número que não esteja em <DADOS_SQL>.
2. Se <DADOS_SQL> estiver vazio, diga claramente que não há dados disponíveis para a pergunta.
3. Números em formato brasileiro: use vírgula para decimais e ponto para milhar (ex.: R$ 1.250.430,00 / 22,6%).
4. Cite as fontes do contexto regulatório em rodapé se forem utilizadas.
5. Seja conciso: máximo de 4 a 6 linhas de texto para a diretoria.
6. NUNCA use dados do <CONTEXTO_RAG> como substituto de números que deveriam vir do banco.
""".strip()


def _formatar_dados_sql(dados: list[dict]) -> str:
    if not dados:
        return "(Nenhum dado retornado pelo banco)"
    try:
        return json.dumps(dados[:10], ensure_ascii=False, indent=2, default=str)
    except Exception:
        return str(dados[:5])


def _formatar_contexto_rag(chunks: list[dict]) -> str:
    if not chunks:
        return "(Nenhum contexto regulatório recuperado)"
    return "\n".join(
        f"- [{c.get('fonte', '?')}] {c.get('titulo', '')}: {c.get('conteudo', '')[:300]}"
        for c in chunks[:4]
    )


def no_sintetiza_resposta(
    state: EstadoAgente,
    llm: ClienteLLM,
) -> Dict[str, Any]:
    """
    Narra os dados do SQL em linguagem executiva clara.
    Controla estritamente a separação entre dados numéricos (SQL) e conhecimento textual (RAG).
    """
    dados_sql = state.get("dados_sql") or []
    contexto_rag = state.get("contexto_rag") or []
    pergunta = state.get("pergunta_autonoma") or state.get("pergunta_original", "")

    dados_texto = _formatar_dados_sql(dados_sql)
    rag_texto = _formatar_contexto_rag(contexto_rag)

    prompt = (
        f"Pergunta do usuário: {pergunta}\n\n"
        f"<DADOS_SQL>\n{dados_texto}\n</DADOS_SQL>\n\n"
        f"<CONTEXTO_RAG>\n{rag_texto}\n</CONTEXTO_RAG>\n\n"
        "Escreva a resposta para a diretoria:"
    )

    resposta_mock = _gerar_resposta_mock(dados_sql, pergunta)

    resposta = llm.invoke(
        prompt=prompt,
        system_prompt=SYSTEM_PROMPT_SINTESE,
        temperatura=0.2,
        resposta_mock=resposta_mock,
    )

    # Fontes citadas: extrai as fontes do RAG que foram relevantes
    fontes = list({c.get("fonte", "") for c in contexto_rag if c.get("fonte")})

    # Selo de confiança: se veio de dados SQL é "gerada_confiavel"; se só RAG é "documental_rag"
    hit_cache = state.get("hit_cache", False)
    if hit_cache:
        selo = "certificada"
    elif dados_sql and len(dados_sql) > 0:
        selo = "gerada_confiavel"
    else:
        selo = "documental_rag"

    chamadas_llm = state.get("chamadas_llm", 0) + 1
    tokens_prompt = state.get("tokens_prompt", 0) + resposta.tokens_prompt
    tokens_resposta_acc = state.get("tokens_resposta", 0) + resposta.tokens_resposta

    logger.info("Nó 11 — Síntese concluída. Selo: %s | Fontes: %s", selo, fontes)

    return {
        "texto_resposta": resposta.texto,
        "fontes_citadas": fontes,
        "selo_confianca": selo,
        "chamadas_llm": chamadas_llm,
        "tokens_prompt": tokens_prompt,
        "tokens_resposta": tokens_resposta_acc,
        "passos_executados": [
            f"Nó 11 — Síntese gerada. Selo: {selo}. {len(dados_sql)} linha(s) de dados utilizadas."
        ],
    }


def _gerar_resposta_mock(dados: list[dict], pergunta: str) -> str:
    """Fallback legível quando o modo mock está ativo."""
    if not dados:
        return "Não há dados disponíveis para responder a esta pergunta no momento."
    primeiros = dados[0] if dados else {}
    valores = " | ".join(f"{k}: {v}" for k, v in list(primeiros.items())[:4])
    return f"Com base nos dados disponíveis, a consulta retornou: {valores}."
