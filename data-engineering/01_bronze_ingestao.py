# Databricks notebook source
# MAGIC %md
# MAGIC # 01 · Bronze · Ingestão das 8 fontes
# MAGIC
# MAGIC **Entrada:** arquivos brutos em `/Volumes/<catálogo>/raw_data/raw_data` · **Saída:** `bronze_schema.bronze_<fonte>`
# MAGIC
# MAGIC Regra da camada (case): **nenhuma transformação de conteúdo**. Tudo é lido como texto (CSV/Excel)
# MAGIC ou com o schema original (JSON), e só ganha duas colunas técnicas de linhagem:
# MAGIC `_ingestion_timestamp` e `_source_file`.
# MAGIC
# MAGIC Diferenças em relação ao `landing_to_bronze` original (ver `registro_de_problemas.md`):
# MAGIC - **B-01/B-02:** `CREATE OR REPLACE` em vez de `CREATE IF NOT EXISTS` + `INSERT INTO`. Reexecutar não acumula
# MAGIC   cópias e não depende da ordem das colunas.
# MAGIC - **B-03/B-04:** o Excel usa o catálogo do parâmetro e lê **todas** as abas que existirem.
# MAGIC - **B-07:** `_source_file` é sempre o nome do arquivo (`_metadata.file_name`).
# MAGIC - Uma lista de configuração substitui os 8 blocos repetidos.

# COMMAND ----------

# DBTITLE 1,Dependência para ler o Excel (o ambiente serverless de Jobs não traz o openpyxl)
# MAGIC %pip install openpyxl --quiet

# COMMAND ----------

# MAGIC %run ./00_utils

# COMMAND ----------

# DBTITLE 1,1. Fontes
# (tabela, arquivo ou padrão, formato, opções de leitura)
TEXTO = {"header": "true", "inferSchema": "false"}
FONTES = [
    ("unidades_consumidoras", "unidades_consumidoras.csv", "csv",  {**TEXTO, "delimiter": ","}),
    ("medidores",             "medidores.csv",             "csv",  {**TEXTO, "delimiter": ","}),
    ("faturas",               "faturas.csv",               "csv",  {**TEXTO, "delimiter": ";"}),
    ("geracao_distribuida",   "geracao_distribuida.csv",   "csv",  {**TEXTO, "delimiter": ","}),
    ("ocorrencias_rede",      "ocorrencias_rede.csv",      "csv",  {**TEXTO, "delimiter": ","}),
    ("leituras",              "leituras_*.csv",            "csv",  {**TEXTO, "delimiter": ","}),
    ("atendimentos",          "atendimentos.json",         "json", {"multiline": "true"}),
]

# COMMAND ----------

# DBTITLE 1,2. CSV e JSON
for tabela, arquivo, formato, opcoes in FONTES:
    df = (spark.read.format(formato).options(**opcoes).load(f"{RAW}/{arquivo}")
          .withColumn("_ingestion_timestamp", F.current_timestamp())
          .withColumn("_source_file", F.col("_metadata.file_name")))
    n = grava_tabela(df, f"bronze_{tabela}", schema=BRONZE)
    print(f"bronze_{tabela}: {n:,} linhas")

# COMMAND ----------

# DBTITLE 1,3. Excel de inspeções (todas as abas)
import pandas as pd
from pyspark.sql.types import StructType, StructField, StringType

caminho = f"{RAW}/inspecoes.xlsx"
abas = pd.read_excel(caminho, sheet_name=None, dtype=str)       # dict {aba: DataFrame}, todas as abas
partes = []
for nome_aba, pdf in abas.items():
    pdf = pdf.astype(object).where(pdf.notna(), None)            # NaN -> None (vira null no Spark)
    pdf["aba_origem"] = nome_aba
    partes.append(pdf)
pdf_ins = pd.concat(partes, ignore_index=True)

schema = StructType([StructField(c, StringType(), True) for c in pdf_ins.columns])
df_ins = (spark.createDataFrame(pdf_ins, schema=schema)
          .withColumn("_ingestion_timestamp", F.current_timestamp())
          .withColumn("_source_file", F.lit("inspecoes.xlsx")))
n = grava_tabela(df_ins, "bronze_inspecoes", schema=BRONZE)
print(f"bronze_inspecoes: {n:,} linhas | abas: {list(abas)}")

# COMMAND ----------

# DBTITLE 1,4. Conferência com os volumes do case
# Referência: o que os perfis encontraram nos arquivos (a Bronze inclui cabeçalhos repetidos e duplicatas)
referencia = {"unidades_consumidoras": "~46,5 mil", "medidores": "51.812", "faturas": "~2,18 mi",
              "geracao_distribuida": "3.510", "ocorrencias_rede": "180.000", "leituras": "2.182.468",
              "atendimentos": "318.871", "inspecoes": "1.389"}
for t, ref in referencia.items():
    confere(f"bronze_{t} (perfil: {ref})", spark.table(f"{BRONZE}.bronze_{t}").count(), ok=True)

finaliza()
