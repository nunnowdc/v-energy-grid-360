"""
Nó 7: Escrita de SQL Estruturado via LLM (Text-to-SQL com feedback de erro).
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from ai_agent.src.contratos.estado_agente import EstadoAgente
from ai_agent.src.provedores.cliente_llm import ClienteLLM

logger = logging.getLogger("venergy.no_escreve_sql")

SYSTEM_PROMPT_SQL = """
Você é um especialista em SQL para a distribuidora de energia V-Energy Grid 360 (Recife-PE).

MISSÃO: Gerar EXCLUSIVAMENTE uma consulta SQL SELECT válida para o PostgreSQL que responda à pergunta do usuário.

TABELAS AUTORIZADAS (apenas estas):
- dim_unidade_consumidora (uc_id, municipio, bairro, classe, subgrupo, alimentador_id, status_ligacao, tem_geracao_distribuida)
- fact_faturamento (fatura_id, uc_id, competencia, ano, mes, volume_faturado_kwh, receita_faturada, valor_tarifa, bandeira_tarifaria, valor_bandeira, status_pagamento, data_vencimento, data_pagamento)
- fact_leituras (leitura_id, uc_id, competencia, leitura_anterior, leitura_atual, consumo_medido_kwh, tipo_leitura)
- fact_ocorrencias (ocorrencia_id, alimentador_id, uc_id, data_inicio, data_fim, duracao_minutos, causa_interrupcao)
- fact_atendimentos (chamado_id, uc_id, data_abertura, motivo_contato, status, nota_satisfacao)
- dim_alimentadores (alimentador_id, subestacao, municipio, total_ucs_atendidas)

REGRAS ABSOLUTAS:
1. Retorne SOMENTE a consulta SQL pura — sem markdown, sem explicação, sem ponto e vírgula no final.
2. Nunca use INSERT, UPDATE, DELETE, DROP, ALTER, CREATE ou qualquer DDL/DML.
3. Nunca acesse tabelas fora da lista acima.
4. Se a pergunta for ambígua, faça a interpretação mais conservadora e inclua um comentário SQL: -- Premissa: <sua premissa aqui>
5. Se não houver dados suficientes nas tabelas para responder, retorne exatamente: SQL_INDISPONIVEL

CONTEXTO REGULATÓRIO EXTRA (fornecido pelo RAG, se houver):
{contexto_rag}
""".strip()


def no_escreve_sql(
    state: EstadoAgente,
    llm: ClienteLLM,
) -> Dict[str, Any]:
    """
    Gera ou corrige uma consulta SQL com base na pergunta autônoma e no contexto do RAG.
    Incrementa o contador de tentativas e chamadas de LLM.
    """
    tentativas = state.get("tentativas_sql", 0) + 1
    chamadas_llm = state.get("chamadas_llm", 0) + 1
    tokens_prompt = state.get("tokens_prompt", 0)
    tokens_resposta = state.get("tokens_resposta", 0)

    pergunta = state.get("pergunta_autonoma") or state.get("pergunta_original", "")
    erro_anterior = state.get("erro_validacao_ou_execucao")

    # Monta contexto RAG em texto se houver
    chunks_rag = state.get("contexto_rag", [])
    contexto_rag_texto = "\n".join(
        f"[{c.get('categoria', '?').upper()}] {c.get('titulo', '')}: {c.get('conteudo', '')}"
        for c in chunks_rag
    ) or "(nenhum contexto adicional)"

    system = SYSTEM_PROMPT_SQL.format(contexto_rag=contexto_rag_texto)

    prompt = f"Pergunta: {pergunta}"
    if erro_anterior and tentativas > 1:
        prompt += (
            f"\n\n⚠️  ATENÇÃO: A tentativa anterior gerou o erro abaixo. "
            f"Corrija o SQL e NÃO cometa o mesmo erro:\nErro: {erro_anterior}"
        )

    resposta = llm.invoke(
        prompt=prompt,
        system_prompt=system,
        temperatura=0.0,
        resposta_mock=(
            "SELECT SUM(f.receita_faturada) AS receita_total "
            "FROM fact_faturamento f "
            "JOIN dim_unidade_consumidora u ON f.uc_id = u.uc_id "
            "WHERE u.municipio = 'Recife' AND f.ano = 2024"
        ),
    )

    sql_gerado = resposta.texto.strip()
    logger.info("Nó 7 | Tentativa %d | SQL gerado: %s", tentativas, sql_gerado[:120])

    return {
        "sql_gerado": sql_gerado,
        "tentativas_sql": tentativas,
        "chamadas_llm": chamadas_llm,
        "tokens_prompt": tokens_prompt + resposta.tokens_prompt,
        "tokens_resposta": tokens_resposta + resposta.tokens_resposta,
        "passos_executados": [
            f"Nó 7 — SQL escrito (tentativa {tentativas}): {sql_gerado[:80]}..."
        ],
    }
