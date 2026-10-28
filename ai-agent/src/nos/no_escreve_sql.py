"""
Nó 7: Escrita de SQL Estruturado via LLM (Text-to-SQL com feedback de erro).
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict

from ..contratos.estado_agente import EstadoAgente
from ..provedores.cliente_llm import ClienteLLM, ErroLLMIndisponivel

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

TABELAS AUTORIZADAS E SUAS COLUNAS COMPLETAS:

-- agg_continuidade_alimentador (DEC e FEC mensais por alimentador)
-- Grão: alimentador × competência (122 × 48)
-- Origem: fact_ocorrencias + dim_alimentador
alimentador (string)           -- Código do alimentador (ex.: ALM-REC-008)
competencia (date)             -- Mês de referência (1º dia do mês)
total_ucs (bigint)             -- Número de UCs atendidas pelo alimentador
municipio_principal (string)   -- Município com mais UCs no alimentador
regiao (string)                -- Código de região (REC, JAB, OLI...)
alimentador_pequeno (boolean)  -- Menos de 100 UCs (DEC/FEC inflado)
interrupcoes (bigint)          -- UCs interrompidas no período
horas_x_uc (double)            -- Soma horas sem energia × UC (impacto absoluto)
interrupcoes_sem_dia_critico (bigint)   -- Excluindo dias críticos
horas_x_uc_sem_dia_critico (double)     -- Excluindo dias críticos
interrupcoes_climaticas (bigint)        -- Causa CLIMATICA
interrupcoes_oscilacao (bigint)         -- Tipo OSCILACAO
duracoes_truncadas (bigint)             -- Duração cortada em 48h
mes_referencia (string)        -- Formato yyyy-MM
ano (int)                      -- Ano da competência
mes (int)                      -- Mês (1-12)
dec (double)                   -- DEC: duração equivalente (h/UC)
fec (double)                   -- FEC: frequência equivalente (interrupções/UC)
dec_sem_dia_critico (double)   -- DEC sem dias críticos
fec_sem_dia_critico (double)   -- FEC sem dias críticos
_processado_em (timestamp)     -- Coluna técnica

-- agg_continuidade_alimentador_anual (DEC e FEC anuais por alimentador)
-- Grão: alimentador × ano
alimentador (string)
ano (int)
total_ucs (bigint)
municipio_principal (string)
regiao (string)
alimentador_pequeno (boolean)
interrupcoes (bigint)
horas_x_uc (double)
interrupcoes_sem_dia_critico (bigint)
horas_x_uc_sem_dia_critico (double)
interrupcoes_climaticas (bigint)
interrupcoes_oscilacao (bigint)
duracoes_truncadas (bigint)
meses (bigint)                 -- Meses do ano presentes na base
dec (double)
fec (double)
dec_sem_dia_critico (double)
fec_sem_dia_critico (double)
rank_dec (int)                 -- Ranking DEC do ano (1 = pior)
rank_dec_sem_dia_critico (int)
rank_impacto_horas_x_uc (int)  -- Ranking horas × UC (1 = maior impacto)
_processado_em (timestamp)

-- agg_receita_mensal (Receita, volume e preço por mês e segmento)
-- Grão: competência × município × bairro × classe × possui_gd
competencia (date)             -- 1º dia do mês
mes_referencia (string)        -- yyyy-MM
bandeira_tarifaria (string)    -- VERDE, AMARELA, VERMELHA_P1, VERMELHA_P2
municipio (string)             -- 14 municípios da RMR (padronizado)
bairro (string)                -- Encoding corrigido (ex.: Inhamã)
classe (string)                -- RESIDENCIAL, COMERCIAL, INDUSTRIAL, RURAL, PODER_PUBLICO
possui_gd (boolean)            -- Tem geração distribuída
receita_faturada (double)      -- Soma R$ faturada
receita_recebida (double)      -- Soma R$ recebida
receita_energia (double)       -- Soma valor_energia (sem tributos)
consumo_kwh (double)           -- Soma consumo medido (kWh)
ucs_faturadas (bigint)         -- UCs com fatura no mês
faturas (bigint)               -- Número de faturas
faturas_atrasadas (bigint)     -- Status ATRASADA
preco_medio_kwh (double)       -- Receita faturada ÷ consumo (R$/kWh)
ano (int)
mes (int)
_processado_em (timestamp)

-- agg_receita_preco_volume (Decomposição variação receita: efeito volume/preço)
-- Grão: município × bairro × classe × possui_gd
municipio (string)
bairro (string)
classe (string)
possui_gd (boolean)
receita_p0 (double)            -- Período base (primeiro ano)
receita_p1 (double)            -- Período comparado (últimos 12m)
kwh_p0 (double)                -- Consumo base (kWh)
kwh_p1 (double)                -- Consumo comparado (kWh)
ucs_p0 (bigint)                -- UCs base
ucs_p1 (bigint)                -- UCs comparado
preco_p0 (double)              -- Preço médio base (R$/kWh)
preco_p1 (double)              -- Preço médio comparado (R$/kWh)
variacao_receita (double)      -- receita_p1 - receita_p0
efeito_volume (double)         -- (kwh_p1 - kwh_p0) × preco_p0
efeito_preco (double)          -- (preco_p1 - preco_p0) × kwh_p1
variacao_receita_pct (double)  -- % variação receita
variacao_volume_pct (double)   -- % variação consumo
variacao_preco_pct (double)    -- % variação preço
kwh_por_uc_p0 (double)         -- Consumo médio/UC base
kwh_por_uc_p1 (double)         -- Consumo médio/UC comparado
periodo_p0 (string)            -- Ex.: 2022-07 a 2023-06
periodo_p1 (string)            -- Ex.: 2025-07 a 2026-06
_processado_em (timestamp)

-- dim_alimentador (Perfil dos 122 alimentadores)
-- Grão: 1 linha por alimentador
alimentador (string)           -- Código (ex.: ALM-REC-008)
total_ucs (bigint)             -- UCs atendidas (denominador DEC/FEC)
qtd_municipios (bigint)        -- Qtd municípios atendidos
qtd_bairros (bigint)           -- Qtd bairros atendidos
ucs_residencial (bigint)
ucs_comercial (bigint)
ucs_industrial (bigint)
ucs_rural (bigint)
ucs_poder_publico (bigint)
municipio_principal (string)   -- Mais frequente (determinístico)
regiao (string)                -- REC, JAB, OLI...
alimentador_pequeno (boolean)  -- < 100 UCs
_processado_em (timestamp)

-- dim_competencia (Calendário mensal: 48 meses jul/2022 a jun/2026)
competencia (date)
mes_referencia (string)        -- yyyy-MM
ano (int)
mes (int)
trimestre (int)                -- 1 a 4
bandeira_tarifaria (string)    -- VERDE, AMARELA, VERMELHA_P1, VERMELHA_P2
periodo_diagnostico (string)   -- PRIMEIRO_ANO, ULTIMOS_12M, ou nulo
_processado_em (timestamp)

-- dim_geracao_distribuida (UCs com GD: 3.503)
id_uc (string)                 -- UC + 6 dígitos (PSEUDONIMIZADO)
potencia_kwp (double)          -- Potência instalada (W→kW corrigido)
potencia_corrigida_unidade (boolean)
data_conexao (date)            -- jan/2024 a jun/2026
modalidade (string)            -- GERACAO NA PROPRIA UC, AUTOCONSUMO REMOTO, GERACAO COMPARTILHADA
energia_injetada_kwh_media_mensal (double) -- Fonte original
energia_estimada (boolean)     -- Estimativa padrão kWp×110
energia_reestimada_kwh (double) -- Valor usado nas análises (~34 kWh/kWp·mês)
kwh_por_kwp_mes (double)       -- Indicador consistência (>150 impossível)
_processado_em (timestamp)

-- dim_medidor (Histórico: 51.299 = 45k atuais + 6.299 retirados)
id_medidor (string)            -- PSEUDONIMIZADO
id_uc (string)                 -- PSEUDONIMIZADO
modelo (string)                -- Ex.: EM-1200, SM-4100
tipo (string)                  -- ELETROMECANICO, ELETRONICO, SMART
data_instalacao (date)         -- MM-dd-yyyy corrigido
data_retirada (date)           -- 9999-12-31 → nulo
status (string)                -- ATIVO ou RETIRADO
medidor_atual (boolean)        -- Exatamente 1 por UC
data_ultima_manutencao (date)  -- 100% nulo na fonte
_processado_em (timestamp)

-- dim_unidade_consumidora (Cadastro 45k UCs - visão 360)
id_uc (string)                 -- PSEUDONIMIZADO
nome_titular (string)          -- ALTO (LGPD)
cpf_cnpj_mascarado (string)    -- ALTO (últimos 4 dígitos)
tipo_pessoa (string)           -- PF (11) ou PJ (14)
logradouro (string)            -- ALTO
numero (string)                -- ALTO
bairro (string)                -- Encoding corrigido
municipio (string)             -- 14 municípios RMR
uf (string)                    -- Sempre PE
cep (string)                   -- ALTO (8 dígitos, ~1.35k nulos)
latitude (double)              -- 2 casas (~1km)
longitude (double)             -- 2 casas (~1km)
classe (string)                -- RESIDENCIAL, COMERCIAL, INDUSTRIAL, RURAL, PODER_PUBLICO
subgrupo_tarifario (string)    -- B1, B2, B3, A4...
alimentador (string)           -- ALM-REC-008
data_ligacao (date)            -- 90 nulas (1900-1948)
status (string)                -- Situação cadastral
possui_gd (boolean)
data_conexao_gd (date)
potencia_gd_kwp (double)
modalidade_gd (string)
id_medidor_atual (string)      -- PSEUDONIMIZADO
tipo_medidor_atual (string)    -- ELETROMECANICO, ELETRONICO, SMART
modelo_medidor_atual (string)
data_instalacao_medidor_atual (date)
trocou_medidor (boolean)       -- Campanha set/2025–mar/2026
data_ultima_troca_medidor (date)
tipo_medidor_anterior (string)
cadastro_conflitante (boolean) -- Sempre false hoje
_processado_em (timestamp)

-- fact_faturamento (Faturas: 2.152.336 = 1 por UC/mês)
id_fatura (string)             -- PSEUDONIMIZADO (órfãs FTX excluidas)
id_uc (string)                 -- PSEUDONIMIZADO
competencia (date)
mes_referencia (string)        -- yyyy-MM
ano (int)
mes (int)
data_emissao (date)            -- vencimento = emissão + 12 dias (100%)
data_vencimento (date)
data_pagamento (date)          -- 9999-12-31 → nulo
valor_energia (double)         -- Inclui bandeira
tributos (double)              -- ~1/3 valor_energia
receita_faturada (double)      -- Total R$ = energia + tributos
receita_recebida (double)      -- = receita_faturada se PAGA, 0 senão
bandeira_tarifaria (string)    -- VERDE, AMARELA, VERMELHA_P1, VERMELHA_P2
status (string)                -- PAGA ou EM_ABERTO
status_pagamento (string)      -- PAGA, PENDENTE, ATRASADA
dias_atraso (int)              -- 0 se em dia
consumo_kwh (double)           -- Da leitura (fatura não tem kWh)
preco_medio_kwh (double)       -- valor_energia ÷ consumo_kwh
_processado_em (timestamp)

-- fact_leituras (Leituras: 2.152.336 - única fonte volume kWh)
id_leitura (string)            -- PSEUDONIMIZADO (clones LTX excluídos)
id_uc (string)                 -- PSEUDONIMIZADO
id_medidor (string)            -- PSEUDONIMIZADO
competencia (date)
mes_referencia (string)        -- yyyy-MM
ano (int)
mes (int)
data_leitura (date)            -- Dentro do mês referência
leitura_anterior (double)      -- -1 e NULL → nulo
leitura_atual (double)
consumo_kwh (double)           -- **Usar este**: declarado ou imputado (troca medidor)
consumo_kwh_declarado (double) -- Como veio da fonte (negativo gigante na troca)
consumo_imputado (boolean)     -- True na troca de medidor (6.215 casos)
tipo_leitura (string)          -- REAL ou ESTIMADA (18% estimadas)
status_qualidade_leitura (string) -- OK, ANTERIOR_AUSENTE, RETIFICACAO, TROCA_DE_MEDIDOR
consumo_ano_anterior_kwh (double) -- Mesmo mês ano anterior
variacao_ano_anterior_pct (double) -- % vs ano anterior
_processado_em (timestamp)

-- fact_ocorrencias (Interrupções: 180k - 1 linha por UC interrompida)
id_ocorrencia (string)
id_uc (string)                 -- PSEUDONIMIZADO
alimentador (string)           -- ALM-REC-008
tipo (string)                  -- FALTA DE ENERGIA, DANO EM EQUIPAMENTO, OSCILACAO, SOBRECARGA, FIO PARTIDO
causa (string)                 -- CLIMATICA, VEGETACAO, TERCEIROS, SOBRECARGA, FALHA DE EQUIPAMENTO, NAO IDENTIFICADA, NAO INFORMADA
data_abertura (timestamp)      -- Início interrupção
data_encerramento (timestamp)  -- Fim interrupção
competencia (date)
duracao_min (double)           -- Sufixo ' min' removido
duracao_h (double)
dia_critico (boolean)          -- > média + 3 std (jul/2025 = 31 dias)
duracao_truncada (boolean)     -- 30 casos cortados em 48h
eh_oscilacao (boolean)         -- Tipo OSCILACAO
_processado_em (timestamp)

-- fact_atendimentos (Call center: 318.871 chamados)
protocolo (string)             -- PSEUDONIMIZADO
id_uc (string)                 -- PSEUDONIMIZADO
assunto (string)               -- FALTA DE ENERGIA, FATURA, DANO ELETRICO, LIGACAO NOVA, GERACAO DISTRIBUIDA, RELIGACAO
subassunto (string)            -- VALOR ALTO, SEGUNDA VIA, INTERRUPCAO TOTAL...
canal (string)                 -- WHATSAPP, TELEFONE, APP, SITE, PRESENCIAL
data_abertura (timestamp)
data_fechamento (timestamp)
competencia (date)
status_chamado (string)        -- ABERTO ou FECHADO
tempo_resolucao_h (double)     -- ~125h média, triplica jul/2025
nota_satisfacao (double)       -- 1-5 (3% nulos)
qtd_tratativas (int)           -- Histórico fora da Gold
_processado_em (timestamp)

-- fact_inspecoes (Inspeções perdas ago–dez/2025: 1.389)
id_inspecao (string)           -- PSEUDONIMIZADO
id_uc (string)                 -- PSEUDONIMIZADO
data_inspecao (date)           -- Formatos mistos, traço=MM-dd-yyyy
mes_inspecao (string)          -- Da data, não da aba Excel
inspetor (string)              -- Ex.: INSP-002
resultado (string)             -- IRREGULARIDADE_CONFIRMADA ou SEM_IRREGULARIDADE
tipo_irregularidade (string)   -- BY_PASS, MEDIDOR_ADULTERADO, DESVIO_DIRETO, LACRE_VIOLADO, LIGACAO_CLANDESTINA
kwh_recuperado (double)
registro_coerente (boolean)    -- Confirmada com tipo; sem irregularidade sem tipo e kWh 0
aba_origem (string)            -- Rastreio
_processado_em (timestamp)

-- fila_inspecao (Fila priorizada perdas não técnicas: score ≥ 20)
prioridade (int)               -- 1 = mais promissora
id_uc (string)                 -- PSEUDONIMIZADO
score (int)                    -- 0-100 (regras v1, a calibrar)
motivo_suspeita (string)       -- Regras separadas por ';'
kwh_recuperavel_estimado_ano (double)
nome_titular (string)          -- ALTO
logradouro (string)            -- ALTO
numero (string)                -- ALTO
bairro (string)
municipio (string)
classe (string)
alimentador (string)
latitude (double)
longitude (double)
tipo_medidor_atual (string)    -- ELETROMECANICO, ELETRONICO, SMART
trocou_medidor (boolean)
possui_gd (boolean)
queda_explicada_por_gd (boolean)
consumo_medio_ano_anterior_kwh (double)
consumo_medio_recente_kwh (double)
variacao_consumo_pct (double)
pct_leituras_estimadas_12m (double)
anomalias_leitura_12m (bigint)
taxa_irregularidade_bairro (double) -- Mín 5 inspeções
data_ultima_inspecao (date)
resultado_ultima_inspecao (string)
ja_teve_irregularidade (boolean)
data_referencia (date)         -- Última competência do cálculo
_processado_em (timestamp)

================================================================================
REGRAS PARA FILTRAR VALORES DE TEXTO (OBRIGATÓRIO):
1. Nunca use igualdade direta em colunas de texto (municipio, bairro, classe, alimentador, bandeira_tarifaria, causa, etc.).
2. Compare sempre ignorando maiúscula/minúscula e acento, assim:
   unaccent(lower(coluna)) = unaccent(lower('valor'))
3. Para vários valores, use IN com a mesma normalização:
   unaccent(lower(coluna)) IN (unaccent(lower('valor1')), unaccent(lower('valor2')))
4. Use o valor exatamente como o usuário escreveu. Não tente adivinhar ou corrigir a grafia.
5. Não aplique essa regra em colunas numéricas, de data ou de ID (ano, mes, id_uc, competencia).

EXEMPLOS:
Pergunta: "receita de recife em 2023"
Correto:
  WHERE unaccent(lower(r.municipio)) = unaccent(lower('recife')) AND r.ano = 2023
Errado:
  WHERE r.municipio = 'recife'

Pergunta: "inadimplência em jaboatao"
Correto:
  WHERE unaccent(lower(r.municipio)) = unaccent(lower('jaboatao'))
================================================================================

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
    Incrementa o contador de tentativas e chamadas de LLM apenas se houver sucesso.
    """
    pergunta = state.get("pergunta_autonoma") or state.get("pergunta_original", "")
    erro_anterior = state.get("erro_validacao_ou_execucao")
    tentativas = state.get("tentativas_sql", 0) + 1

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

    try:
        resposta = llm.invoke(
            prompt=prompt,
            system_prompt=system,
            temperatura=0.0,
            resposta_mock=(
                "SELECT SUM(r.receita_faturada) AS receita_total "
                "FROM agg_receita_mensal r "
                "WHERE r.municipio = 'Recife' AND r.ano = 2024"
            ),
        )
    except ErroLLMIndisponivel:
        logger.warning("Nó 7 — LLM indisponível ao tentar gerar SQL.")
        return {
            "motivo_recusa": "llm_indisponivel",
            "passos_executados": [
                "Nó 7 — LLM indisponível ao tentar gerar SQL."
            ],
        }

    chamadas_llm = state.get("chamadas_llm", 0) + 1
    tokens_prompt = state.get("tokens_prompt", 0) + resposta.tokens_prompt
    tokens_resposta = state.get("tokens_resposta", 0) + resposta.tokens_resposta

    sql_gerado, premissas_sql = _limpar_sql(resposta.texto)
    logger.info("Nó 7 | Tentativa %d | SQL gerado: %s", tentativas, sql_gerado[:120])

    return {
        "sql_gerado": sql_gerado,
        "premissas_sql": premissas_sql,
        "hit_cache": False,
        "tentativas_sql": tentativas,
        "chamadas_llm": chamadas_llm,
        "tokens_prompt": tokens_prompt,
        "tokens_resposta": tokens_resposta,
        "passos_executados": [
            f"Nó 7 — SQL escrito (tentativa {tentativas}): {sql_gerado[:80]}...",
            *[
                f"Nó 7 — Premissa SQL registrada: {premissa}"
                for premissa in premissas_sql
            ],
        ],
    }
