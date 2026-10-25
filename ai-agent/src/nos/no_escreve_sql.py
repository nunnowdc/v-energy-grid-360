"""
Nó 7: Escrita de SQL Estruturado via LLM (Text-to-SQL com feedback de erro).
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict

from ..contratos.estado_agente import EstadoAgente
from ..provedores.cliente_llm import ClienteLLM

logger = logging.getLogger("venergy.no_escreve_sql")


def _limpar_sql(texto: str) -> tuple[str, list[str]]:
    """Remove apenas cercas, comentários de linha e um ponto e vírgula final."""
    bloco = re.search(r"```[^\r\n`]*\r?\n?(.*?)```", texto, flags=re.DOTALL)
    conteudo = bloco.group(1) if bloco else texto
    premissas = []
    linhas_sql = []

    for linha in conteudo.splitlines():
        linha_limpa = linha.strip()
        if linha_limpa.startswith("--"):
            if linha_limpa.lower().startswith("-- premissa:"):
                premissas.append(linha_limpa[len("-- Premissa:"):].strip())
            continue
        linhas_sql.append(linha)

    sql = "\n".join(linhas_sql).strip()
    if sql.endswith(";"):
        sql = sql[:-1].rstrip()
    if sql.upper() == "SQL_INDISPONIVEL":
        return "SQL_INDISPONIVEL", premissas
    return sql, premissas


SYSTEM_PROMPT_SQL = """
Você é um especialista em SQL para a distribuidora de energia V-Energy Grid 360 (Recife-PE).

MISSÃO: Gerar EXCLUSIVAMENTE uma consulta SQL SELECT válida para o PostgreSQL que responda à pergunta do usuário.

TABELAS AUTORIZADAS (apenas estas):
- agg_continuidade_alimentador (alimentador, competencia, total_ucs, municipio_principal, interrupcoes, horas_x_uc, dec, fec)
- agg_continuidade_alimentador_anual (alimentador, ano, total_ucs, dec, fec, rank_dec, rank_impacto_horas_x_uc)
- agg_receita_mensal (competencia, municipio, bairro, classe, possui_gd, receita_faturada, receita_recebida, consumo_kwh, faturas_atrasadas, preco_medio_kwh, ano, mes)
- agg_receita_preco_volume (municipio, bairro, classe, possui_gd, receita_p0, receita_p1, kwh_p0, kwh_p1, variacao_receita, efeito_volume, efeito_preco)
- dim_alimentador (alimentador, total_ucs, qtd_municipios, qtd_bairros, municipio_principal, regiao)
- dim_competencia (competencia, mes_referencia, ano, mes, trimestre, bandeira_tarifaria, periodo_diagnostico)
- dim_geracao_distribuida (id_uc, potencia_kwp, data_conexao, modalidade, energia_reestimada_kwh)
- dim_medidor (id_medidor, id_uc, modelo, tipo, data_instalacao, data_retirada, status, medidor_atual)
- dim_unidade_consumidora (id_uc, municipio, bairro, classe, subgrupo_tarifario, alimentador, status, possui_gd)
- fact_faturamento (id_fatura, id_uc, competencia, ano, mes, receita_faturada, receita_recebida, bandeira_tarifaria, status_pagamento, dias_atraso, consumo_kwh, preco_medio_kwh)
- fact_leituras (id_leitura, id_uc, id_medidor, competencia, ano, mes, leitura_anterior, leitura_atual, consumo_kwh, tipo_leitura, variacao_ano_anterior_pct)
- fact_ocorrencias (id_ocorrencia, id_uc, alimentador, tipo, causa, data_abertura, data_encerramento, competencia, duracao_min, duracao_h, dia_critico, duracao_truncada, eh_oscilacao)
- fact_atendimentos (protocolo, id_uc, assunto, subassunto, canal, data_abertura, data_fechamento, competencia, status_chamado, tempo_resolucao_h, nota_satisfacao)
- fact_inspecoes (id_inspecao, id_uc, data_inspecao, resultado, tipo_irregularidade, kwh_recuperado, registro_coerente)
- fila_inspecao (prioridade, id_uc, score, motivo_suspeita, kwh_recuperavel_estimado_ano, municipio, classe, alimentador, possui_gd)

Não use nomes de colunas do sistema Silver ou do dicionário antigo, como uc_id,
alimentador_id, volume_faturado_kwh, consumo_medido_kwh ou dim_alimentadores.

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
            "FROM agg_receita_mensal r "
            "WHERE r.municipio = 'Recife' AND r.ano = 2024"
        ),
    )

    sql_gerado, premissas_sql = _limpar_sql(resposta.texto)
    logger.info("Nó 7 | Tentativa %d | SQL gerado: %s", tentativas, sql_gerado[:120])

    return {
        "sql_gerado": sql_gerado,
        "premissas_sql": premissas_sql,
        "hit_cache": False,
        "tentativas_sql": tentativas,
        "chamadas_llm": chamadas_llm,
        "tokens_prompt": tokens_prompt + resposta.tokens_prompt,
        "tokens_resposta": tokens_resposta + resposta.tokens_resposta,
        "passos_executados": [
            f"Nó 7 — SQL escrito (tentativa {tentativas}): {sql_gerado[:80]}...",
            *[
                f"Nó 7 — Premissa SQL registrada: {premissa}"
                for premissa in premissas_sql
            ],
        ],
    }
