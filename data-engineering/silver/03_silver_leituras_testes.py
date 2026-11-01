# Databricks notebook source
# DBTITLE 1,03 · Silver · Leituras — ajustes
# MAGIC %md
# MAGIC # 03 · Silver · Leituras — ajustes para a Gold
# MAGIC
# MAGIC **Entrada:** `silver_leituras` (saída do `02_silver_leituras`) · **Saída:** `silver_leituras` (sobrescrita com colunas analíticas)
# MAGIC
# MAGIC O `02_silver_leituras` grava a tabela canônica (ids, datas, consumo declarado, tipo). A camada Gold
# MAGIC (`fact_leituras`) precisa de mais três colunas, adicionadas aqui sem reprocessar a Bronze:
# MAGIC
# MAGIC | Coluna nova | Regra |
# MAGIC |---|---|
# MAGIC | `competencia` | DATE (dia 1) derivada de `mes_referencia` `yyyy-MM` — chave de junção com faturas (`fact_faturamento`) |
# MAGIC | `status_qualidade_leitura` | `OK` · `CONSUMO_ANULADO` (consumo declarado ≤ 0 anulado na silver — virada de medidor/retificação) · `LEITURA_ANTERIOR_NULA` (sem leitura anterior) |
# MAGIC | `consumo_kwh_ajustado` + `consumo_imputado` | Nas linhas com consumo anulado, o valor é **imputado pela mediana de consumo da própria UC** (fallback: mediana global); `consumo_kwh` declarado é preservado como evidência |
# MAGIC
# MAGIC Nenhuma linha sai da tabela: a contagem de 2.152.336 leituras válidas se mantém (a quarentena de
# MAGIC medidor órfão continua em `silver_leituras_quarentena`, intocada).

# COMMAND ----------

# DBTITLE 1,Utils
# MAGIC %run ./00_utils

# COMMAND ----------

# DBTITLE 1,1. Leitura da Silver
lei = le_silver("leituras")
n_base = lei.count()
confere("Leituras da Silver (base do 02)", n_base, 2152336)

# COMMAND ----------

# DBTITLE 1,2. Ajustes analíticos (competência, qualidade, imputação)
# Mediana de consumo por UC (apenas consumos válidos) para imputar as linhas anuladas
mediana_uc = (lei.filter(F.col("consumo_kwh").isNotNull())
                 .groupBy("id_uc")
                 .agg(F.percentile_approx("consumo_kwh", 0.5, 1000).alias("mediana_consumo_uc")))
mediana_global = lei.agg(F.percentile_approx("consumo_kwh", 0.5, 10000)).first()[0]
print(f"Mediana global de consumo: {mediana_global} kWh/mês")

lei = (lei
    .join(mediana_uc, "id_uc", "left")
    .withColumn("competencia", try_data("mes_referencia", "yyyy-MM"))
    .withColumn("consumo_imputado", F.col("consumo_kwh").isNull())
    .withColumn("consumo_kwh_ajustado",
                F.coalesce("consumo_kwh", "mediana_consumo_uc", F.lit(mediana_global)))
    .withColumn("status_qualidade_leitura",
                F.when(F.col("consumo_kwh").isNull(), "CONSUMO_ANULADO")
                 .when(F.col("leitura_anterior").isNull(), "LEITURA_ANTERIOR_NULA")
                 .otherwise("OK"))
    .drop("mediana_consumo_uc")
    .select(
        "id_leitura", "id_uc", "id_medidor", "competencia", "mes_referencia",
        "data_leitura", "leitura_anterior", "leitura_atual",
        "consumo_kwh", "consumo_kwh_ajustado", "consumo_imputado",
        "tipo_leitura", "status_qualidade_leitura",
    )
)

# COMMAND ----------

# DBTITLE 1,3. Conferências
confere("Total de linhas preservado", lei.count(), n_base)
confere("Competências nulas (todas devem parsear)", lei.filter(F.col("competencia").isNull()).count(), 0)
confere("Consumos imputados (linhas anuladas no 02)", lei.filter("consumo_imputado").count(), ok=True)
confere("Ajustado = declarado fora da imputação",
        lei.filter(~F.col("consumo_imputado") & (F.col("consumo_kwh_ajustado") != F.col("consumo_kwh"))).count(), 0)
confere("Imputados sem valor ajustado", lei.filter(F.col("consumo_imputado") & F.col("consumo_kwh_ajustado").isNull()).count(), 0)
lei.groupBy("status_qualidade_leitura").count().show()

# COMMAND ----------

# DBTITLE 1,4. Gravação
grava_silver(lei, None, "leituras")
finaliza()

# COMMAND ----------

