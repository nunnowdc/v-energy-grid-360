# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "6"
# ///
# MAGIC %md
# MAGIC # 03. Modelagem Camada Gold (Star Schema e Indicadores ANEEL) — V-Energy Grid 360
# MAGIC
# MAGIC Este notebook constrói a camada Gold otimizada para o Portal Web, Agente de IA e Diagnóstico de Receita:
# MAGIC - Modelo Estrela (Dimensões e Fatos)
# MAGIC - Cálculo regulatório de continuidade ANEEL (DEC e FEC) por alimentador
# MAGIC - Visão consolidada analítica `agg_receita_mensal`
# MAGIC
# MAGIC Atende aos requisitos: **REQ-DATA-04 e REQ-DATA-05**.

# COMMAND ----------

# DBTITLE 1,1. Parâmetros e Schemas
dbutils.widgets.text("catalog", "v-energy", "Catálogo Unity")

catalog = dbutils.widgets.get("catalog")
silver_schema = f"`{catalog}`.silver_schema"
gold_schema = f"`{catalog}`.gold_schema"

spark.sql(f"CREATE SCHEMA IF NOT EXISTS `{catalog}`.gold_schema")

from pyspark.sql import functions as F

# COMMAND ----------

# DBTITLE 1,2. Dimensão: dim_unidade_consumidora
df_uc = spark.table(f"{silver_schema}.silver_unidades_consumidoras")
df_gd = spark.table(f"{silver_schema}.silver_geracao_distribuida")

df_gd_flag = df_gd.select("id_uc").distinct().withColumn("possui_gd", F.lit(True))

df_dim_uc = (
    df_uc.join(df_gd_flag, on="id_uc", how="left")
    .withColumn("possui_gd", F.coalesce(F.col("possui_gd"), F.lit(False)))
    .select(
        "id_uc",
        "cpf_cnpj",
        "nome_titular",
        "logradouro",
        "numero",
        "bairro",
        "municipio",
        "uf",
        "cep",
        "classe",
        "subgrupo_tarifario",
        "alimentador",
        "data_ligacao",
        "status",
        "latitude",
        "longitude",
        "possui_gd"
    )
)

df_dim_uc.createOrReplaceTempView("tmp_gold_dim_uc")
spark.sql(f"CREATE OR REPLACE TABLE `{catalog}`.gold_schema.dim_unidade_consumidora USING DELTA AS SELECT * FROM tmp_gold_dim_uc")
print(f"dim_unidade_consumidora gravada com {df_dim_uc.count():,} UCs.")

# COMMAND ----------

# DBTITLE 1,3. Dimensão: dim_alimentadores
df_dim_alim = (
    df_uc.filter(F.col("alimentador").isNotNull())
    .groupBy("alimentador")
    .agg(
        F.countDistinct("id_uc").alias("total_ucs_atendidas"),
        F.first("municipio").alias("municipio_principal")
    )
)

df_dim_alim.createOrReplaceTempView("tmp_gold_dim_alim")
spark.sql(f"CREATE OR REPLACE TABLE `{catalog}`.gold_schema.dim_alimentadores USING DELTA AS SELECT * FROM tmp_gold_dim_alim")
print(f"dim_alimentadores gravada com {df_dim_alim.count():,} alimentadores.")

# COMMAND ----------

# DBTITLE 1,4. Fato: fact_faturamento
df_fat = spark.table(f"{silver_schema}.silver_faturas")

df_fact_fat = (
    df_fat.withColumn("receita_faturada", F.col("valor_total"))
    .withColumn(
        "receita_recebida",
        F.when(F.col("status") == "PAGA", F.col("valor_total")).otherwise(F.lit(0.0))
    )
    .select(
        "id_fatura",
        "id_uc",
        "mes_referencia",
        "data_emissao",
        "valor_energia",
        "tributos",
        "bandeira_tarifaria",
        "receita_faturada",
        "receita_recebida",
        "data_vencimento",
        "data_pagamento",
        "status"
    )
)

df_fact_fat.createOrReplaceTempView("tmp_gold_fact_fat")
spark.sql(f"CREATE OR REPLACE TABLE `{catalog}`.gold_schema.fact_faturamento USING DELTA AS SELECT * FROM tmp_gold_fact_fat")
print(f"fact_faturamento gravada com {df_fact_fat.count():,} faturas.")

# COMMAND ----------

# DBTITLE 1,5. Fatos: fact_leituras, fact_gd, fact_inspecoes, fact_ocorrencias, fact_atendimentos
# Leituras
df_leit = spark.table(f"{silver_schema}.silver_leituras")
df_leit.select(
    "id_leitura", "id_uc", "id_medidor", "data_leitura", "mes_referencia",
    "leitura_anterior", "leitura_atual", "consumo_kwh", "tipo_leitura"
).createOrReplaceTempView("tmp_gold_fact_leituras")
spark.sql(f"CREATE OR REPLACE TABLE `{catalog}`.gold_schema.fact_leituras USING DELTA AS SELECT * FROM tmp_gold_fact_leituras")

# GD
df_gd.select(
    "id_uc", "potencia_kwp", "data_conexao", "modalidade", "energia_injetada_kwh_media_mensal"
).createOrReplaceTempView("tmp_gold_fact_gd")
spark.sql(f"CREATE OR REPLACE TABLE `{catalog}`.gold_schema.fact_gd USING DELTA AS SELECT * FROM tmp_gold_fact_gd")

# Inspeções
df_ins = spark.table(f"{silver_schema}.silver_inspecoes")
df_ins.select(
    "id_inspecao", "id_uc", "data", "inspetor", "resultado", "tipo_irregularidade", "kwh_recuperado"
).createOrReplaceTempView("tmp_gold_fact_inspecoes")
spark.sql(f"CREATE OR REPLACE TABLE `{catalog}`.gold_schema.fact_inspecoes USING DELTA AS SELECT * FROM tmp_gold_fact_inspecoes")

# Ocorrências
df_oco = spark.table(f"{silver_schema}.silver_ocorrencias_rede")
df_oco.select(
    "id_ocorrencia", "alimentador", "id_uc", "tipo", "causa", "data_abertura", "data_encerramento", "duracao_min"
).createOrReplaceTempView("tmp_gold_fact_ocorrencias")
spark.sql(f"CREATE OR REPLACE TABLE `{catalog}`.gold_schema.fact_ocorrencias USING DELTA AS SELECT * FROM tmp_gold_fact_ocorrencias")

# Atendimentos
df_ate = spark.table(f"{silver_schema}.silver_atendimentos")
df_ate.createOrReplaceTempView("tmp_gold_fact_atendimentos")
spark.sql(f"CREATE OR REPLACE TABLE `{catalog}`.gold_schema.fact_atendimentos USING DELTA AS SELECT * FROM tmp_gold_fact_atendimentos")

print("Fatos Gold gravados com sucesso.")

# COMMAND ----------

# DBTITLE 1,6. Agregado Regulatório: agg_continuidade_alimentador (DEC e FEC ANEEL)
df_oco_mes = df_oco.withColumn("mes_referencia", F.date_format(F.col("data_abertura"), "yyyy-MM"))

# Base de consumidores por alimentador derivada de dim_alimentadores
df_tot_cons = df_dim_alim.select("alimentador", F.col("total_ucs_atendidas").alias("total_consumidores"))

df_dec_fec = (
    df_oco_mes.groupBy("alimentador", "mes_referencia")
    .agg(
        F.sum(F.col("duracao_min") / 60.0).alias("soma_horas_interrupcao"),
        F.count("id_ocorrencia").alias("total_interrupcoes")
    )
    .join(df_tot_cons, on="alimentador", how="left")
    .withColumn("total_consumidores", F.coalesce(F.col("total_consumidores"), F.lit(1)))
    .withColumn("dec", F.round(F.col("soma_horas_interrupcao") / F.col("total_consumidores"), 4))
    .withColumn("fec", F.round(F.col("total_interrupcoes") / F.col("total_consumidores"), 4))
    .select(
        "alimentador",
        "mes_referencia",
        "total_consumidores",
        "total_interrupcoes",
        "dec",
        "fec"
    )
)

df_dec_fec.createOrReplaceTempView("tmp_gold_dec_fec")
spark.sql(f"CREATE OR REPLACE TABLE `{catalog}`.gold_schema.agg_continuidade_alimentador USING DELTA AS SELECT * FROM tmp_gold_dec_fec")
print(f"agg_continuidade_alimentador gravada com {df_dec_fec.count():,} registros de DEC/FEC.")

# COMMAND ----------

# DBTITLE 1,7. Agregado Analítico: agg_receita_mensal
# Cruzamento faturamento x leituras x dim_uc
df_leit_agg = df_leit.select("id_uc", "mes_referencia", "consumo_kwh")

df_rec_base = (
    df_fact_fat.join(df_leit_agg, on=["id_uc", "mes_referencia"], how="left")
    .join(df_dim_uc.select("id_uc", "municipio", "bairro", "classe", "possui_gd"), on="id_uc", how="inner")
)

df_agg_rec = (
    df_rec_base.groupBy("mes_referencia", "municipio", "bairro", "classe", "bandeira_tarifaria")
    .agg(
        F.sum("receita_faturada").alias("receita_faturada_total"),
        F.sum("receita_recebida").alias("receita_recebida_total"),
        F.sum("consumo_kwh").alias("volume_kwh_total"),
        F.countDistinct("id_uc").alias("qtd_ucs_faturadas"),
        F.sum(F.when(F.col("possui_gd") == True, 1).otherwise(0)).alias("qtd_ucs_com_gd")
    )
    .withColumn(
        "preco_medio_efetivo",
        F.when(F.col("volume_kwh_total") > 0, F.round(F.col("receita_faturada_total") / F.col("volume_kwh_total"), 4))
        .otherwise(F.lit(0.0))
    )
)

df_agg_rec.createOrReplaceTempView("tmp_gold_agg_rec")
spark.sql(f"CREATE OR REPLACE TABLE `{catalog}`.gold_schema.agg_receita_mensal USING DELTA AS SELECT * FROM tmp_gold_agg_rec")
print(f"agg_receita_mensal gravada com {df_agg_rec.count():,} células analíticas.")