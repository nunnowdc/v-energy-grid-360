# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "6"
# ///
# MAGIC %md
# MAGIC # 01. Ingestão Camada Bronze — V-Energy Grid 360
# MAGIC
# MAGIC Este notebook realiza a ingestão automatizada e bruta das 8 fontes de dados do projeto V-Energy,
# MAGIC preservando a estrutura original em tabelas Delta com metadados de linhagem (`_ingestion_timestamp` e `_source_file`).
# MAGIC
# MAGIC Atende ao requisito: **REQ-DATA-01**.

# COMMAND ----------

# DBTITLE 1,1. Declaração de Parâmetros e Widgets
dbutils.widgets.text("catalog", "v-energy", "Catálogo UC")
dbutils.widgets.text("database_prefix", "v_energy", "Prefixo do Banco")
dbutils.widgets.text("ambiente", "dev", "Ambiente (dev/staging/prod)")

catalog = dbutils.widgets.get("catalog")
db_prefix = dbutils.widgets.get("database_prefix")
ambiente = dbutils.widgets.get("ambiente")

bronze_schema = f"{catalog}.bronze_schema"
raw_volume = f"/Volumes/{catalog}/raw_data/raw_data"

print(f"Schema Bronze: {bronze_schema}")
print(f"Volume de dados brutos: {raw_volume}")

# COMMAND ----------

# DBTITLE 1,2. Criação do Banco de Dados Bronze
spark.sql(f"CREATE SCHEMA IF NOT EXISTS `{catalog}`.bronze_schema")
spark.sql(f"USE `{catalog}`.bronze_schema")

# COMMAND ----------

# DBTITLE 1,3. Ingestão de Unidades Consumidoras
from pyspark.sql import functions as F

df_uc_raw = (
    spark.read.option("header", "true")
    .option("inferSchema", "false")
    .csv(f"{raw_volume}/unidades_consumidoras.csv")
    .withColumn("_ingestion_timestamp", F.current_timestamp())
    .withColumn("_source_file", F.lit("unidades_consumidoras.csv"))
)

df_uc_raw.createOrReplaceTempView("tmp_bronze_uc")
spark.sql(f"CREATE TABLE IF NOT EXISTS `{catalog}`.bronze_schema.bronze_unidades_consumidoras USING DELTA AS SELECT * FROM tmp_bronze_uc WHERE 1=0")
spark.sql(f"INSERT INTO `{catalog}`.bronze_schema.bronze_unidades_consumidoras SELECT * FROM tmp_bronze_uc")
print(f"bronze_unidades_consumidoras gravada com {df_uc_raw.count():,} registros.")

# COMMAND ----------

# DBTITLE 1,4. Ingestão de Medidores
df_med_raw = (
    spark.read.option("header", "true")
    .option("inferSchema", "false")
    .csv(f"{raw_volume}/medidores.csv")
    .withColumn("_ingestion_timestamp", F.current_timestamp())
    .withColumn("_source_file", F.lit("medidores.csv"))
)

df_med_raw.createOrReplaceTempView("tmp_bronze_medidores")
spark.sql(f"CREATE TABLE IF NOT EXISTS `{catalog}`.bronze_schema.bronze_medidores USING DELTA AS SELECT * FROM tmp_bronze_medidores WHERE 1=0")
spark.sql(f"INSERT INTO `{catalog}`.bronze_schema.bronze_medidores SELECT * FROM tmp_bronze_medidores")
print(f"bronze_medidores gravada com {df_med_raw.count():,} registros.")

# COMMAND ----------

# DBTITLE 1,5. Ingestão de Faturas (Delimitador ;)
df_fat_raw = (
    spark.read.option("header", "true")
    .option("delimiter", ";")
    .option("inferSchema", "false")
    .csv(f"{raw_volume}/faturas.csv")
    .withColumn("_ingestion_timestamp", F.current_timestamp())
    .withColumn("_source_file", F.lit("faturas.csv"))
)

df_fat_raw.createOrReplaceTempView("tmp_bronze_faturas")
spark.sql(f"CREATE TABLE IF NOT EXISTS `{catalog}`.bronze_schema.bronze_faturas USING DELTA AS SELECT * FROM tmp_bronze_faturas WHERE 1=0")
spark.sql(f"INSERT INTO `{catalog}`.bronze_schema.bronze_faturas SELECT * FROM tmp_bronze_faturas")
print(f"bronze_faturas gravada com {df_fat_raw.count():,} registros.")

# COMMAND ----------

# DBTITLE 1,6. Ingestão de Geração Distribuída
df_gd_raw = (
    spark.read.option("header", "true")
    .option("inferSchema", "false")
    .csv(f"{raw_volume}/geracao_distribuida.csv")
    .withColumn("_ingestion_timestamp", F.current_timestamp())
    .withColumn("_source_file", F.lit("geracao_distribuida.csv"))
)

df_gd_raw.createOrReplaceTempView("tmp_bronze_geracao_distribuida")
spark.sql(f"CREATE TABLE IF NOT EXISTS `{catalog}`.bronze_schema.bronze_geracao_distribuida USING DELTA AS SELECT * FROM tmp_bronze_geracao_distribuida WHERE 1=0")
spark.sql(f"INSERT INTO `{catalog}`.bronze_schema.bronze_geracao_distribuida SELECT * FROM tmp_bronze_geracao_distribuida")
print(f"bronze_geracao_distribuida gravada com {df_gd_raw.count():,} registros.")

# COMMAND ----------

# DBTITLE 1,7. Ingestão de Ocorrências de Rede
df_oco_raw = (
    spark.read.option("header", "true")
    .option("inferSchema", "false")
    .csv(f"{raw_volume}/ocorrencias_rede.csv")
    .withColumn("_ingestion_timestamp", F.current_timestamp())
    .withColumn("_source_file", F.lit("ocorrencias_rede.csv"))
)

df_oco_raw.createOrReplaceTempView("tmp_bronze_ocorrencias_rede")
spark.sql(f"CREATE TABLE IF NOT EXISTS `{catalog}`.bronze_schema.bronze_ocorrencias_rede USING DELTA AS SELECT * FROM tmp_bronze_ocorrencias_rede WHERE 1=0")
spark.sql(f"INSERT INTO `{catalog}`.bronze_schema.bronze_ocorrencias_rede SELECT * FROM tmp_bronze_ocorrencias_rede")
print(f"bronze_ocorrencias_rede gravada com {df_oco_raw.count():,} registros.")

# COMMAND ----------

# DBTITLE 1,8. Ingestão de Leituras (Multi-Ano 2022 a 2026)
df_leit_raw = (
    spark.read.option("header", "true")
    .option("inferSchema", "false")
    .csv(f"{raw_volume}/leituras_*.csv")
    .withColumn("_ingestion_timestamp", F.current_timestamp())
    .withColumn("_source_file", F.col("_metadata.file_path"))
)

df_leit_raw.createOrReplaceTempView("tmp_bronze_leituras")
spark.sql(f"CREATE TABLE IF NOT EXISTS `{catalog}`.bronze_schema.bronze_leituras USING DELTA AS SELECT * FROM tmp_bronze_leituras WHERE 1=0")
spark.sql(f"INSERT INTO `{catalog}`.bronze_schema.bronze_leituras SELECT * FROM tmp_bronze_leituras")
print(f"bronze_leituras gravada com {df_leit_raw.count():,} registros.")

# COMMAND ----------

# DBTITLE 1,9. Ingestão de Atendimentos (JSON)
df_ate_raw = (
    spark.read.option("multiline", "true")
    .json(f"{raw_volume}/atendimentos.json")
    .withColumn("_ingestion_timestamp", F.current_timestamp())
    .withColumn("_source_file", F.lit("atendimentos.json"))
)

df_ate_raw.createOrReplaceTempView("tmp_bronze_atendimentos")
spark.sql(f"CREATE TABLE IF NOT EXISTS `{catalog}`.bronze_schema.bronze_atendimentos USING DELTA AS SELECT * FROM tmp_bronze_atendimentos WHERE 1=0")
spark.sql(f"INSERT INTO `{catalog}`.bronze_schema.bronze_atendimentos SELECT * FROM tmp_bronze_atendimentos")
print(f"bronze_atendimentos gravada com {df_ate_raw.count():,} registros.")

# COMMAND ----------

# DBTITLE 1,Instalação do openpyxl para ler arquivos xlsx
!pip install openpyxl

# COMMAND ----------

# DBTITLE 1,10. Ingestão de Inspeções (Excel Multi-Aba via Pandas)
import pandas as pd

excel_path = f"/Volumes/v-energy/raw_data/raw_data/inspecoes.xlsx"
sheets = ["ago-set", "dez", "out-nov"]
dfs = []
for s in sheets:
    pdf = pd.read_excel(excel_path, sheet_name=s, dtype=str)
    pdf["aba_origem"] = s
    dfs.append(pdf)

df_ins_merged = pd.concat(dfs, ignore_index=True)
df_ins_spark = (
    spark.createDataFrame(df_ins_merged)
    .withColumn("_ingestion_timestamp", F.current_timestamp())
    .withColumn("_source_file", F.lit("inspecoes.xlsx"))
)

df_ins_spark.createOrReplaceTempView("tmp_bronze_inspecoes")
spark.sql(f"CREATE TABLE IF NOT EXISTS `{catalog}`.bronze_schema.bronze_inspecoes USING DELTA AS SELECT * FROM tmp_bronze_inspecoes WHERE 1=0")
spark.sql(f"INSERT INTO `{catalog}`.bronze_schema.bronze_inspecoes SELECT * FROM tmp_bronze_inspecoes")
print(f"bronze_inspecoes gravada com {df_ins_spark.count():,} registros.")