# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "6"
# ///
# MAGIC %md
# MAGIC # 02. Transformação e Qualidade Camada Silver — V-Energy Grid 360
# MAGIC
# MAGIC Este notebook aplica as regras determinísticas de saneamento, deduplicação, normalização monetária e
# MAGIC segregação de quarentena mapeadas nas diretrizes técnicas (ADR-0001 e ADR-0002).
# MAGIC
# MAGIC Atende aos requisitos: **REQ-DATA-02, REQ-DATA-03 e REQ-DATA-09**.

# COMMAND ----------

# DBTITLE 1,1. Parâmetros e Schemas
dbutils.widgets.text("catalog", "v-energy", "Catálogo Unity")

catalog = dbutils.widgets.get("catalog")
bronze_schema = f"`{catalog}`.bronze_schema"
silver_schema = f"`{catalog}`.silver_schema"

spark.sql(f"CREATE SCHEMA IF NOT EXISTS `{catalog}`.silver_schema")

# COMMAND ----------

# DBTITLE 1,2. Saneamento de Unidades Consumidoras
from pyspark.sql import functions as F

df_uc_bronze = spark.table(f"{bronze_schema}.bronze_unidades_consumidoras")
_latest_uc = df_uc_bronze.select(F.max("_ingestion_timestamp")).head()[0]
df_uc_bronze = df_uc_bronze.filter(F.col("_ingestion_timestamp") == _latest_uc)

# 1. Filtro de cabeçalho duplicado
# 2. Deduplicação por id_uc
# 3. Normalização de CPF/CNPJ (apenas dígitos)
# 4. Normalização canônica de UF e Classe
df_uc_silver = (
    df_uc_bronze.filter(F.col("id_uc") != "id_uc")
    .dropDuplicates(["id_uc"])
    .withColumn("cpf_cnpj", F.regexp_replace(F.col("cpf_cnpj"), "[^0-9]", ""))
    .withColumn("uf", F.lit("PE"))
    .withColumn(
        "classe",
        F.when(F.upper(F.col("classe")).contains("RESIDENCIAL"), F.lit("RESIDENCIAL"))
        .when(F.upper(F.col("classe")).contains("COMERCIAL"), F.lit("COMERCIAL"))
        .when(F.upper(F.col("classe")).contains("INDUSTRIAL"), F.lit("INDUSTRIAL"))
        .when(F.upper(F.col("classe")).contains("RURAL"), F.lit("RURAL"))
        .when(F.upper(F.col("classe")).contains("PODER"), F.lit("PODER_PUBLICO"))
        .otherwise(F.upper(F.col("classe")))
    )
    .withColumn("data_ligacao", F.to_date(F.col("data_ligacao"), "yyyy-MM-dd"))
    .withColumn("latitude", F.col("latitude").cast("double"))
    .withColumn("longitude", F.col("longitude").cast("double"))
    .drop("_ingestion_timestamp", "_source_file")
)

df_uc_silver.createOrReplaceTempView("tmp_silver_unidades_consumidoras")
spark.sql(f"CREATE OR REPLACE TABLE `{catalog}`.silver_schema.silver_unidades_consumidoras USING DELTA AS SELECT * FROM tmp_silver_unidades_consumidoras")
print(f"silver_unidades_consumidoras gravada com {df_uc_silver.count():,} UCs saneadas.")

# COMMAND ----------

# DBTITLE 1,3. Saneamento de Medidores
df_med_bronze = spark.table(f"{bronze_schema}.bronze_medidores")
_latest_med = df_med_bronze.select(F.max("_ingestion_timestamp")).head()[0]
df_med_bronze = df_med_bronze.filter(F.col("_ingestion_timestamp") == _latest_med)

df_med_silver = (
    df_med_bronze.filter(F.col("id_medidor") != "id_medidor")
    .dropDuplicates(["id_medidor"])
    .withColumn(
        "tipo",
        F.when(F.upper(F.col("tipo")).contains("SMART"), F.lit("SMART"))
        .when(F.upper(F.col("tipo")).contains("ELETRON"), F.lit("ELETRONICO"))
        .when(F.upper(F.col("tipo")).contains("ELETROMECAN"), F.lit("ELETROMECANICO"))
        .otherwise(F.upper(F.col("tipo")))
    )
    .withColumn(
        "data_instalacao",
        F.coalesce(
            F.try_to_date(F.col("data_instalacao"), "yyyy-MM-dd"),
            F.try_to_date(F.col("data_instalacao"), "dd.MM.yyyy"),
            F.try_to_date(F.col("data_instalacao"), "dd/MM/yyyy"),
            F.try_to_date(F.col("data_instalacao"), "dd-MM-yyyy"),
            F.try_to_date(F.col("data_instalacao"), "MM-dd-yyyy"),
        )
    )
    .withColumn(
        "data_retirada",
        F.when(F.col("data_retirada") == "9999-12-31", F.lit(None))
        .otherwise(F.to_date(F.col("data_retirada"), "yyyy-MM-dd"))
    )
    .withColumn("status", F.upper(F.col("status")))
    .drop("_ingestion_timestamp", "_source_file")
)

df_med_silver.createOrReplaceTempView("tmp_silver_medidores")
spark.sql(f"CREATE OR REPLACE TABLE `{catalog}`.silver_schema.silver_medidores USING DELTA AS SELECT * FROM tmp_silver_medidores")
print(f"silver_medidores gravada com {df_med_silver.count():,} medidores.")

# COMMAND ----------

# DBTITLE 1,4. Saneamento de Faturas e Segregação de Órfãs (Quarentena)
df_fat_bronze = spark.table(f"{bronze_schema}.bronze_faturas")
_latest_fat = df_fat_bronze.select(F.max("_ingestion_timestamp")).head()[0]
df_fat_bronze = df_fat_bronze.filter(F.col("_ingestion_timestamp") == _latest_fat)

# Regex para limpar R$, espaços e vírgulas decimais em valor_total
def clean_currency_col(cname):
    cleaned = F.regexp_replace(F.col(cname), "[R$€£\\s]", "")
    cleaned = F.regexp_replace(cleaned, "\\.", "")
    cleaned = F.regexp_replace(cleaned, ",", ".")
    return cleaned.cast("double")

df_fat_cleaned = (
    df_fat_bronze.filter((F.col("id_fatura") != "id_fatura") & (F.col("status") != "status"))
    .withColumn("valor_energia", F.col("valor_energia").cast("double"))
    .withColumn("tributos", F.col("tributos").cast("double"))
    .withColumn(
        "valor_total",
        F.when(F.col("valor_total").contains("R$") | F.col("valor_total").contains(","), clean_currency_col("valor_total"))
        .otherwise(F.col("valor_total").cast("double"))
    )
    .withColumn(
        "data_emissao",
        F.coalesce(
            F.try_to_date(F.col("data_emissao"), "yyyy-MM-dd"),
            F.try_to_date(F.col("data_emissao"), "dd.MM.yyyy"),
            F.try_to_date(F.col("data_emissao"), "dd/MM/yyyy"),
            F.try_to_date(F.col("data_emissao"), "dd-MM-yyyy"),
            F.try_to_date(F.col("data_emissao"), "MM-dd-yyyy"),
        )
    )
    .withColumn("data_vencimento", F.to_date(F.col("data_vencimento"), "yyyy-MM-dd"))
    .withColumn("data_pagamento", F.to_date(F.col("data_pagamento"), "yyyy-MM-dd"))
    .withColumn("status", F.upper(F.col("status")))
    .drop("_ingestion_timestamp", "_source_file")
)

# Cruzamento com UCs válidas
df_ucs_keys = df_uc_silver.select("id_uc").distinct()

df_fat_joined = df_fat_cleaned.join(df_ucs_keys.withColumn("_uc_valida", F.lit(True)), on="id_uc", how="left")

# Tabela Silver Confiável
df_fat_silver = df_fat_joined.filter(F.col("_uc_valida") == True).drop("_uc_valida")
df_fat_silver.createOrReplaceTempView("tmp_silver_faturas")
spark.sql(f"CREATE OR REPLACE TABLE `{catalog}`.silver_schema.silver_faturas USING DELTA AS SELECT * FROM tmp_silver_faturas")

# Tabela Quarentena (Órfãs)
df_fat_quarentena = (
    df_fat_joined.filter(F.col("_uc_valida").isNull())
    .drop("_uc_valida")
    .withColumn("motivo_quarentena", F.lit("UC_INEXISTENTE_NO_CADASTRO"))
)
df_fat_quarentena.createOrReplaceTempView("tmp_silver_faturas_quarentena")
spark.sql(f"CREATE OR REPLACE TABLE `{catalog}`.silver_schema.silver_faturas_quarentena USING DELTA AS SELECT * FROM tmp_silver_faturas_quarentena")

print(f"silver_faturas: {df_fat_silver.count():,} | silver_faturas_quarentena: {df_fat_quarentena.count():,}")

# COMMAND ----------

# DBTITLE 1,5. Saneamento de Leituras e Correção de Sinal Negativo
df_leit_bronze = spark.table(f"{bronze_schema}.bronze_leituras")
_latest_leit = df_leit_bronze.select(F.max("_ingestion_timestamp")).head()[0]
df_leit_bronze = df_leit_bronze.filter(F.col("_ingestion_timestamp") == _latest_leit)

df_leit_cleaned = (
    df_leit_bronze.filter(F.col("id_leitura") != "id_leitura")
    .withColumn("leitura_anterior", F.expr("try_cast(leitura_anterior as double)"))
    .withColumn("leitura_atual", F.col("leitura_atual").cast("double"))
    .withColumn("consumo_bruto", F.col("consumo_kwh").cast("double"))
    .withColumn(
        "data_leitura",
        F.coalesce(
            F.try_to_date(F.col("data_leitura"), "yyyy-MM-dd"),
            F.try_to_date(F.col("data_leitura"), "dd.MM.yyyy"),
            F.try_to_date(F.col("data_leitura"), "dd/MM/yyyy"),
            F.try_to_date(F.col("data_leitura"), "dd-MM-yyyy"),
            F.try_to_date(F.col("data_leitura"), "MM-dd-yyyy"),
        )
    )
    .drop("_ingestion_timestamp", "_source_file")
)

# Algoritmo de correção de consumo
df_leit_transformed = (
    df_leit_cleaned.withColumn("diff_leitura", F.col("leitura_atual") - F.col("leitura_anterior"))
    .withColumn(
        "consumo_kwh",
        F.when(F.col("diff_leitura") >= 0, F.col("diff_leitura"))
        .otherwise(F.lit(None).cast("double"))
    )
    .withColumn(
        "status_qualidade_leitura",
        F.when(F.col("diff_leitura") >= 0, F.when(F.col("consumo_bruto") < 0, F.lit("SINAL_CORRIGIDO")).otherwise(F.lit("OK")))
        .otherwise(F.lit("ANOMALIA_VIRADA_MEDIDOR"))
    )
)

# Quarentena de Leituras (Viradas de medidor)
df_leit_silver = df_leit_transformed.filter(F.col("status_qualidade_leitura") != "ANOMALIA_VIRADA_MEDIDOR")
df_leit_quarentena = df_leit_transformed.filter(F.col("status_qualidade_leitura") == "ANOMALIA_VIRADA_MEDIDOR")

df_leit_silver.createOrReplaceTempView("tmp_silver_leituras")
spark.sql(f"CREATE OR REPLACE TABLE `{catalog}`.silver_schema.silver_leituras USING DELTA AS SELECT * FROM tmp_silver_leituras")
df_leit_quarentena.createOrReplaceTempView("tmp_silver_leituras_quarentena")
spark.sql(f"CREATE OR REPLACE TABLE `{catalog}`.silver_schema.silver_leituras_quarentena USING DELTA AS SELECT * FROM tmp_silver_leituras_quarentena")

print(f"silver_leituras: {df_leit_silver.count():,} | silver_leituras_quarentena: {df_leit_quarentena.count():,}")

# COMMAND ----------

# DBTITLE 1,6. Saneamento de Geração Distribuída
df_gd_bronze = spark.table(f"{bronze_schema}.bronze_geracao_distribuida")
_latest_gd = df_gd_bronze.select(F.max("_ingestion_timestamp")).head()[0]
df_gd_bronze = df_gd_bronze.filter(F.col("_ingestion_timestamp") == _latest_gd)

df_gd_silver = (
    df_gd_bronze.filter(F.col("id_uc") != "id_uc")
    .withColumn("potencia_kwp", F.regexp_replace(F.col("potencia_kwp"), ",", ".").cast("double"))
    .withColumn("energia_injetada_kwh_media_mensal", F.col("energia_injetada_kwh_media_mensal").cast("double"))
    .withColumn("data_conexao", F.to_date(F.col("data_conexao"), "yyyy-MM-dd"))
    .withColumn("modalidade", F.upper(F.col("modalidade")))
    .drop("_ingestion_timestamp", "_source_file")
)

df_gd_silver.createOrReplaceTempView("tmp_silver_geracao_distribuida")
spark.sql(f"CREATE OR REPLACE TABLE `{catalog}`.silver_schema.silver_geracao_distribuida USING DELTA AS SELECT * FROM tmp_silver_geracao_distribuida")
print(f"silver_geracao_distribuida: {df_gd_silver.count():,}")

# COMMAND ----------

# DBTITLE 1,7. Saneamento de Inspeções
df_ins_bronze = spark.table(f"{bronze_schema}.bronze_inspecoes")
_latest_ins = df_ins_bronze.select(F.max("_ingestion_timestamp")).head()[0]
df_ins_bronze = df_ins_bronze.filter(F.col("_ingestion_timestamp") == _latest_ins)

df_ins_silver = (
    df_ins_bronze.filter(F.col("id_inspecao") != "id_inspecao")
    .withColumn("kwh_recuperado", F.regexp_replace(F.col("kwh_recuperado"), ",", ".").cast("double"))
    .withColumn(
        "data",
        F.coalesce(
            F.try_to_date(F.col("data"), "yyyy-MM-dd"),
            F.try_to_date(F.col("data"), "dd.MM.yyyy"),
            F.try_to_date(F.col("data"), "dd/MM/yyyy"),
            F.try_to_date(F.col("data"), "dd-MM-yyyy"),
            F.try_to_date(F.col("data"), "MM-dd-yyyy"),
        )
    )
    .withColumn(
        "resultado",
        F.when(F.upper(F.col("resultado")).contains("CONFIRMADA"), F.lit("IRREGULARIDADE_CONFIRMADA"))
        .otherwise(F.lit("SEM_IRREGULARIDADE"))
    )
    .withColumn("tipo_irregularidade", F.upper(F.col("tipo_irregularidade")))
    .drop("_ingestion_timestamp", "_source_file")
)

df_ins_silver.createOrReplaceTempView("tmp_silver_inspecoes")
spark.sql(f"CREATE OR REPLACE TABLE `{catalog}`.silver_schema.silver_inspecoes USING DELTA AS SELECT * FROM tmp_silver_inspecoes")
print(f"silver_inspecoes: {df_ins_silver.count():,}")

# COMMAND ----------

# DBTITLE 1,8. Saneamento de Ocorrências e Atendimentos
df_oco_bronze = spark.table(f"{bronze_schema}.bronze_ocorrencias_rede")
_latest_oco = df_oco_bronze.select(F.max("_ingestion_timestamp")).head()[0]
df_oco_bronze = df_oco_bronze.filter(F.col("_ingestion_timestamp") == _latest_oco)
df_oco_silver = (
    df_oco_bronze.filter(F.col("id_ocorrencia") != "id_ocorrencia")
    .withColumn("duracao_min", F.regexp_replace(F.col("duracao_min"), " min", "").cast("double"))
    .withColumn("data_abertura", F.to_timestamp(F.col("data_abertura"), "yyyy-MM-dd HH:mm:ss"))
    .withColumn("data_encerramento", F.to_timestamp(F.col("data_encerramento"), "yyyy-MM-dd HH:mm:ss"))
    .withColumn("tipo", F.upper(F.col("tipo")))
    .withColumn("causa", F.upper(F.col("causa")))
    .drop("_ingestion_timestamp", "_source_file")
)
df_oco_silver.createOrReplaceTempView("tmp_silver_ocorrencias_rede")
spark.sql(f"CREATE OR REPLACE TABLE `{catalog}`.silver_schema.silver_ocorrencias_rede USING DELTA AS SELECT * FROM tmp_silver_ocorrencias_rede")

df_ate_bronze = spark.table(f"{bronze_schema}.bronze_atendimentos")
_latest_ate = df_ate_bronze.select(F.max("_ingestion_timestamp")).head()[0]
df_ate_bronze = df_ate_bronze.filter(F.col("_ingestion_timestamp") == _latest_ate)
df_ate_silver = (
    df_ate_bronze.withColumn("nota_satisfacao", F.col("nota_satisfacao").cast("double"))
    .withColumn("data_abertura", F.to_timestamp(F.col("data_abertura"), "yyyy-MM-dd HH:mm:ss"))
    .withColumn("data_fechamento", F.to_timestamp(F.col("data_fechamento"), "yyyy-MM-dd HH:mm:ss"))
    .drop("_ingestion_timestamp", "_source_file")
)
df_ate_silver.createOrReplaceTempView("tmp_silver_atendimentos")
spark.sql(f"CREATE OR REPLACE TABLE `{catalog}`.silver_schema.silver_atendimentos USING DELTA AS SELECT * FROM tmp_silver_atendimentos")
print("Silver concluída com sucesso!")