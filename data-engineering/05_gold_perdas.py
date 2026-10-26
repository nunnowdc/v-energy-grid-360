# Databricks notebook source
# MAGIC %md
# MAGIC # 05 · Gold · Perdas (Fila de Inspeção Priorizada)
# MAGIC
# MAGIC Geração da fila analítica priorizada de Unidades Consumidoras suspeitas de perdas não técnicas (fraude/desvio de medição)
# MAGIC para direcionamento inteligente das equipes de campo, com pontuação explicável (LGPD Art. 20) e estimativa de recuperação de energia.
# MAGIC
# MAGIC | Tabela | Grão | Origem | Destaques |
# MAGIC |---|---|---|---|
# MAGIC | `fila_inspecao` | 1 linha por UC com score >= 20 | `fact_leituras` + `fact_inspecoes` + `dim_unidade_consumidora` | Priorização por score (0 a 100) e volume a recuperar; isolamento de efeito de GD; auditabilidade de motivos |
# MAGIC
# MAGIC **Motor Heurístico de Score (0 a 100 pts):**
# MAGIC - Queda de consumo nos últimos 6 meses contra 6 meses homólogos do ano anterior:
# MAGIC   - Queda >= 50%: **+40 pts** | Queda >= 30%: **+30 pts** | Queda >= 15%: **+15 pts** (zerado se GD nova);
# MAGIC - Medidor eletromecânico ativo: **+15 pts**;
# MAGIC - Leituras estimadas nos últimos 12 meses: >= 50% (**+15 pts**) ou >= 25% (**+8 pts**);
# MAGIC - Anomalias de leitura nos últimos 12 meses: >= 2 (**+10 pts**) ou 1 (**+5 pts**);
# MAGIC - Bairro crítico (taxa histórica de confirmação de fraude >= 1,2x a média): **+10 pts**;
# MAGIC - Reincidência histórica de irregularidade na UC: **+10 pts**;
# MAGIC - Atenuador: inspeção concluída há <= 180 dias sem irregularidade: **-25 pts**.

# COMMAND ----------

# MAGIC %run ./00_utils

# COMMAND ----------

# DBTITLE 1,1. Leitura e marcos temporais
lei = le_gold("fact_leituras")
dim_uc = le_gold("dim_unidade_consumidora")
insp = le_gold("fact_inspecoes")

# Marco temporal: última competência da base
dt_ref = lei.agg(F.max("competencia")).first()[0]
dt_rec_ini = soma_meses(dt_ref, -5)       # 6 meses recentes (jan a jun/2026)
dt_rec_fim = dt_ref

dt_ant_ini = soma_meses(dt_ref, -17)      # 6 meses homólogos (jan a jun/2025)
dt_ant_fim = soma_meses(dt_ref, -12)

dt_12m_ini = soma_meses(dt_ref, -11)      # 12 meses para anomalias/estimativas (jul/2025 a jun/2026)

print(f"Data de referência: {dt_ref}")
print(f"Período Recente (6M): {dt_rec_ini} a {dt_rec_fim}")
print(f"Período Homólogo (6M): {dt_ant_ini} a {dt_ant_fim}")
print(f"Período 12M: {dt_12m_ini} a {dt_ref}")

# COMMAND ----------

# DBTITLE 1,2. Análise de consumo e anomalias nas leituras
# Consumo médio recente (últimos 6 meses)
rec = (lei
    .filter(F.col("competencia").between(dt_rec_ini, dt_rec_fim))
    .groupBy("id_uc")
    .agg(F.round(F.avg("consumo_kwh"), 2).alias("consumo_medio_recente_kwh"))
)

# Consumo médio homólogo (mesmos 6 meses do ano anterior)
ant = (lei
    .filter(F.col("competencia").between(dt_ant_ini, dt_ant_fim))
    .groupBy("id_uc")
    .agg(F.round(F.avg("consumo_kwh"), 2).alias("consumo_medio_ano_anterior_kwh"))
)

# Indicadores de medição dos últimos 12 meses (estimadas e anomalias de faturamento/leitura)
indicadores_12m = (lei
    .filter(F.col("competencia").between(dt_12m_ini, dt_ref))
    .groupBy("id_uc")
    .agg(
        F.count("*").alias("_total_leituras_12m"),
        F.sum(F.when(F.col("tipo_leitura") == "ESTIMADA", 1).otherwise(0)).alias("_estimadas_12m"),
        F.sum(F.when(
            (F.col("status_qualidade_leitura").isNotNull() & (F.col("status_qualidade_leitura") != "OK")) |
            (F.col("tipo_leitura") == "ESTIMADA"), 1).otherwise(0)
        ).alias("anomalias_leitura_12m")
    )
    .withColumn("pct_leituras_estimadas_12m",
                F.round(F.col("_estimadas_12m") / F.col("_total_leituras_12m"), 4))
    .select("id_uc", "pct_leituras_estimadas_12m", "anomalias_leitura_12m")
)

# COMMAND ----------

# DBTITLE 1,3. Histórico de inspeções e taxa de risco do bairro
# Taxa de irregularidade por bairro (mínimo de 5 inspeções realizadas)
insp_com_bairro = insp.join(dim_uc.select("id_uc", "bairro"), "id_uc", "left")

taxa_bairro = (insp_com_bairro
    .groupBy("bairro")
    .agg(
        F.count("*").alias("_qtd_insp_bairro"),
        F.sum(F.when(F.col("resultado") == "IRREGULARIDADE_CONFIRMADA", 1).otherwise(0)).alias("_qtd_irreg_bairro")
    )
    .withColumn("taxa_irregularidade_bairro",
                F.when(F.col("_qtd_insp_bairro") >= 5,
                       F.round(F.col("_qtd_irreg_bairro") / F.col("_qtd_insp_bairro"), 4)))
    .select("bairro", "taxa_irregularidade_bairro")
)

# Média global de confirmação da base (~62,7%)
taxa_media_global = 0.627

# Histórico individual de cada UC
w_insp = Window.partitionBy("id_uc").orderBy(F.col("data").desc())
hist_uc = (insp
    .withColumn("_rn", F.row_number().over(w_insp))
    .withColumn("_teve_irreg", F.col("resultado") == "IRREGULARIDADE_CONFIRMADA")
    .groupBy("id_uc")
    .agg(
        F.max(F.when(F.col("_rn") == 1, F.col("data"))).alias("data_ultima_inspecao"),
        F.max(F.when(F.col("_rn") == 1, F.col("resultado"))).alias("resultado_ultima_inspecao"),
        F.max("_teve_irreg").alias("ja_teve_irregularidade")
    )
)

# COMMAND ----------

# DBTITLE 1,4. Consolidação de atributos e flags de mitigação
base_suspeita = (dim_uc
    .join(rec, "id_uc", "left")
    .join(ant, "id_uc", "left")
    .join(indicadores_12m, "id_uc", "left")
    .join(taxa_bairro, "bairro", "left")
    .join(hist_uc, "id_uc", "left")
    .withColumn("consumo_medio_recente_kwh", F.coalesce("consumo_medio_recente_kwh", F.lit(0.0)))
    .withColumn("consumo_medio_ano_anterior_kwh", F.coalesce("consumo_medio_ano_anterior_kwh", F.lit(0.0)))
    .withColumn("pct_leituras_estimadas_12m", F.coalesce("pct_leituras_estimadas_12m", F.lit(0.0)))
    .withColumn("anomalias_leitura_12m", F.coalesce("anomalias_leitura_12m", F.lit(0)))
    .withColumn("ja_teve_irregularidade", F.coalesce("ja_teve_irregularidade", F.lit(False)))
)

# Variação percentual de consumo
base_suspeita = base_suspeita.withColumn(
    "variacao_consumo_pct",
    F.when(F.col("consumo_medio_ano_anterior_kwh") > 0,
           F.round(100.0 * (F.col("consumo_medio_recente_kwh") / F.col("consumo_medio_ano_anterior_kwh") - 1.0), 2))
     .otherwise(None)
)

# Identificação de queda explicada por GD (GD conectada após o início do período comparado)
queda_explicada_gd = (
    F.col("possui_gd") &
    F.col("data_conexao_gd").isNotNull() &
    (F.col("data_conexao_gd") >= F.lit(dt_ant_ini))
)
base_suspeita = base_suspeita.withColumn("queda_explicada_por_gd", F.coalesce(queda_explicada_gd, F.lit(False)))

# Volume recuperável estimado (kWh/ano)
kwh_rec = F.when(
    F.col("queda_explicada_por_gd"), F.lit(0.0)
).otherwise(
    F.greatest(F.lit(0.0),
               F.round((F.col("consumo_medio_ano_anterior_kwh") - F.col("consumo_medio_recente_kwh")) * 12.0, 2))
)
base_suspeita = base_suspeita.withColumn("kwh_recuperavel_estimado_ano", kwh_rec)

# COMMAND ----------

# DBTITLE 1,5. Motor de regras, cálculo do score e explicabilidade (LGPD Art. 20)
# Regra 1: Queda brusca de consumo (zerada se a UC instalou GD)
pts_queda = (
    F.when(F.col("queda_explicada_por_gd"), F.lit(0))
     .when(F.col("variacao_consumo_pct") <= -50.0, F.lit(40))
     .when(F.col("variacao_consumo_pct") <= -30.0, F.lit(30))
     .when(F.col("variacao_consumo_pct") <= -15.0, F.lit(15))
     .otherwise(F.lit(0))
)
motivo_queda = (
    F.when(F.col("queda_explicada_por_gd"), None)
     .when(F.col("variacao_consumo_pct") <= -50.0, F.lit("Queda de consumo >= 50% (+40)"))
     .when(F.col("variacao_consumo_pct") <= -30.0, F.lit("Queda de consumo >= 30% (+30)"))
     .when(F.col("variacao_consumo_pct") <= -15.0, F.lit("Queda de consumo >= 15% (+15)"))
     .otherwise(None)
)

# Regra 2: Medidor eletromecânico ativo
pts_medidor = F.when(F.col("tipo_medidor_atual") == "ELETROMECANICO", F.lit(15)).otherwise(F.lit(0))
motivo_medidor = F.when(F.col("tipo_medidor_atual") == "ELETROMECANICO", F.lit("Medidor eletromecanico (+15)")).otherwise(None)

# Regra 3: Leituras estimadas frequentes
pts_estimadas = (
    F.when(F.col("pct_leituras_estimadas_12m") >= 0.50, F.lit(15))
     .when(F.col("pct_leituras_estimadas_12m") >= 0.25, F.lit(8))
     .otherwise(F.lit(0))
)
motivo_estimadas = (
    F.when(F.col("pct_leituras_estimadas_12m") >= 0.50, F.lit("Leituras estimadas >= 50% (+15)"))
     .when(F.col("pct_leituras_estimadas_12m") >= 0.25, F.lit("Leituras estimadas >= 25% (+8)"))
     .otherwise(None)
)

# Regra 4: Anomalias de leitura
pts_anomalias = (
    F.when(F.col("anomalias_leitura_12m") >= 2, F.lit(10))
     .when(F.col("anomalias_leitura_12m") == 1, F.lit(5))
     .otherwise(F.lit(0))
)
motivo_anomalias = (
    F.when(F.col("anomalias_leitura_12m") >= 2, F.lit("Multiplas anomalias de leitura (+10)"))
     .when(F.col("anomalias_leitura_12m") == 1, F.lit("Anomalia de leitura recente (+5)"))
     .otherwise(None)
)

# Regra 5: Bairro de alto risco (>= 1,2x a média da rede)
limite_bairro = 1.2 * taxa_media_global
pts_bairro = F.when(F.col("taxa_irregularidade_bairro") >= limite_bairro, F.lit(10)).otherwise(F.lit(0))
motivo_bairro = F.when(F.col("taxa_irregularidade_bairro") >= limite_bairro, F.lit("Bairro com taxa de irregularidade >= 1.2x (+10)")).otherwise(None)

# Regra 6: Reincidência histórica
pts_reincidencia = F.when(F.col("ja_teve_irregularidade"), F.lit(10)).otherwise(F.lit(0))
motivo_reincidencia = F.when(F.col("ja_teve_irregularidade"), F.lit("Historico de irregularidade anterior (+10)")).otherwise(None)

# Regra 7: Atenuador de inspeção recente regular (<= 180 dias)
dias_desde_insp = F.datediff(F.lit(dt_ref), F.col("data_ultima_inspecao"))
insp_recente_ok = (
    (F.col("resultado_ultima_inspecao") == "SEM_IRREGULARIDADE") &
    (dias_desde_insp <= 180)
)
pts_atenuador = F.when(insp_recente_ok, F.lit(-25)).otherwise(F.lit(0))
motivo_atenuador = F.when(insp_recente_ok, F.lit("Inspecionada regular ha <= 180 dias (-25)")).otherwise(None)

# Score consolidado (clamp entre 0 e 100)
score_bruto = (pts_queda + pts_medidor + pts_estimadas + pts_anomalias + pts_bairro + pts_reincidencia + pts_atenuador)
score_final = F.least(F.lit(100), F.greatest(F.lit(0), score_bruto))

# Concatenação dos motivos acionados
array_motivos = F.array_compact(F.array(
    motivo_queda, motivo_medidor, motivo_estimadas, motivo_anomalias, motivo_bairro, motivo_reincidencia, motivo_atenuador
))
motivo_suspeita = F.array_join(array_motivos, "; ")

fila = (base_suspeita
    .withColumn("score", score_final)
    .withColumn("motivo_suspeita", motivo_suspeita)
    .withColumn("data_referencia", F.lit(dt_ref))
    .filter(F.col("score") >= 20)
)

# Prioridade na fila de campo: maior score e maior kWh recuperável
w_prioridade = Window.orderBy(F.col("score").desc(), F.col("kwh_recuperavel_estimado_ano").desc(), F.col("id_uc").asc())
fila = (fila
    .withColumn("prioridade", F.row_number().over(w_prioridade))
    .select(
        "prioridade",
        "id_uc",
        "score",
        "motivo_suspeita",
        "kwh_recuperavel_estimado_ano",
        "nome_titular",
        "logradouro",
        "numero",
        "bairro",
        "municipio",
        "classe",
        "alimentador",
        "latitude",
        "longitude",
        "tipo_medidor_atual",
        "trocou_medidor",
        "possui_gd",
        "queda_explicada_por_gd",
        "consumo_medio_ano_anterior_kwh",
        "consumo_medio_recente_kwh",
        "variacao_consumo_pct",
        "pct_leituras_estimadas_12m",
        "anomalias_leitura_12m",
        "taxa_irregularidade_bairro",
        "data_ultima_inspecao",
        "resultado_ultima_inspecao",
        "ja_teve_irregularidade",
        "data_referencia",
        F.current_timestamp().alias("_processado_em")
    )
)

# COMMAND ----------

# DBTITLE 1,6. Conferências e Gravação
n_fila = grava_gold(fila, "fila_inspecao")
print(f"fila_inspecao gerada com sucesso: {n_fila:,} UCs elegíveis (score >= 20)")

confere("Prioridade 1 existe", fila.filter("prioridade = 1").count(), 1)
confere("Score fora da faixa 20-100", fila.filter((F.col("score") < 20) | (F.col("score") > 100)).count(), 0)
confere("Motivo suspeita nulo ou vazio", fila.filter(F.col("motivo_suspeita").isNull() | (F.length("motivo_suspeita") == 0)).count(), 0)
confere("Queda explicada por GD com kWh recuperavel > 0", fila.filter("queda_explicada_por_gd and kwh_recuperavel_estimado_ano > 0").count(), 0)

finaliza()
