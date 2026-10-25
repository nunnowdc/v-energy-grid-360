# Databricks notebook source
# MAGIC %md
# MAGIC # 02 · Silver · Faturas
# MAGIC
# MAGIC **Entrada:** `bronze_faturas` + `silver_unidades_consumidoras` · **Saída:** `silver_faturas` + quarentena
# MAGIC
# MAGIC Regras de `perfil_faturas.md`:
# MAGIC
# MAGIC | # | Problema na fonte | Regra |
# MAGIC |---|---|---|
# MAGIC | 1 | Cabeçalho repetido | Remover |
# MAGIC | 2 | **32.285 faturas órfãs** (`UC9999999`, `FTX…`) (S-FAT-06) | Quarentena `UC_INEXISTENTE_NO_CADASTRO` |
# MAGIC | 3 | `data_emissao` em 4 formatos; **traço = MM-dd-yyyy** (S-FAT-05, validado 100%) | `parse_data` do utils |
# MAGIC | 4 | "Não pago" como `null` ou `9999-12-31` (S-FAT-03) | Sentinela → `null` |
# MAGIC | 5 | `valor_total` em `R$ 1.234,56` (196.622) | `to_num` |
# MAGIC | 6 | A fonte **não tem kWh** (S-FAT-07) | O volume vem da `silver_leituras` |
# MAGIC | 7 | Status só PAGA / EM ABERTO | `status_pagamento` derivado: PAGA, PENDENTE (no prazo), ATRASADA |
# MAGIC
# MAGIC **Data de referência do `status_pagamento`:** a data da última emissão da base (fim da extração).
# MAGIC Usar a data de hoje faria todas as faturas em aberto parecerem atrasadas.
# MAGIC
# MAGIC Testes embutidos (todos passaram na perfilagem): `vencimento = emissão + 12 dias`,
# MAGIC `valor_total = valor_energia + tributos`, 1 fatura por UC por competência, 1 bandeira por mês.

# COMMAND ----------

# MAGIC %run ./00_utils

# COMMAND ----------

# DBTITLE 1,1. Leitura
bruto = remove_cabecalho(remove_cabecalho(ler_bronze("bronze_faturas"), "id_fatura"), "status")
confere("Linhas da Bronze", bruto.count(), 2184621)
ucs = le_silver("unidades_consumidoras").select("id_uc")

# COMMAND ----------

# DBTITLE 1,2. Padronização
fat = bruto.select([limpa_texto(c).alias(c) for c in bruto.columns])
band_n = normaliza("bandeira_tarifaria")

fat = (fat
    .withColumn("id_fatura", F.upper("id_fatura"))
    .withColumn("id_uc", F.upper("id_uc"))
    .withColumn("competencia", F.coalesce(try_data("mes_referencia", "yyyy-MM"),
                                          try_data("mes_referencia", "MM/yyyy")))
    .withColumn("mes_referencia", F.date_format("competencia", "yyyy-MM"))
    .withColumn("data_emissao", parse_data("data_emissao"))
    .withColumn("data_vencimento", parse_data("data_vencimento"))
    .withColumn("data_pagamento", parse_data(sentinela_para_nulo("data_pagamento")))
    .withColumn("valor_energia", to_num("valor_energia"))
    .withColumn("tributos", to_num("tributos"))
    .withColumn("valor_total", to_num("valor_total"))
    .withColumn("bandeira_tarifaria", F.regexp_replace(band_n, " ", "_"))     # VERDE, AMARELA, VERMELHA_P1, VERMELHA_P2
    .withColumn("status", F.regexp_replace(normaliza("status"), " ", "_"))    # PAGA, EM_ABERTO
    .dropDuplicates()
)

# Data de referência = última emissão da base (momento da extração)
DATA_REF = fat.agg(F.max("data_emissao")).first()[0]
print(f"Data de referência para atraso: {DATA_REF}")

fat = (fat
    .withColumn("status_pagamento",
                F.when(F.col("status") == "PAGA", "PAGA")
                 .when(F.col("data_vencimento") >= F.lit(DATA_REF), "PENDENTE")
                 .otherwise("ATRASADA"))
    .withColumn("dias_atraso", F.greatest(F.lit(0), F.datediff(
                F.coalesce("data_pagamento", F.lit(DATA_REF)), "data_vencimento")))
    .withColumn("data_coerente", F.coalesce(F.date_add("data_emissao", 12) == F.col("data_vencimento"), F.lit(False)))
    .withColumn("valor_coerente", F.coalesce(
                F.abs(F.col("valor_total") - (F.col("valor_energia") + F.col("tributos"))) <= 0.05, F.lit(False)))
)

# COMMAND ----------

# DBTITLE 1,3. Quarentena
fat = fat.join(ucs.withColumn("_uc_ok", F.lit(True)), "id_uc", "left")
ok, quarentena = separa_quarentena(fat, [
    (F.col("id_fatura").isNull(), "ID_FATURA_AUSENTE"),
    (F.col("_uc_ok").isNull(), "UC_INEXISTENTE_NO_CADASTRO"),
    (F.col("competencia").isNull(), "COMPETENCIA_INVALIDA"),
    (F.col("valor_total").isNull(), "VALOR_TOTAL_INVALIDO"),
])
ok, quarentena = ok.drop("_uc_ok"), quarentena.drop("_uc_ok")

ordem = Window.partitionBy("id_fatura").orderBy(F.col("data_emissao").desc())
ok = ok.withColumn("_ordem", F.row_number().over(ordem))
quarentena = quarentena.unionByName(
    ok.filter("_ordem > 1").drop("_ordem").withColumn("motivo_quarentena", F.lit("ID_FATURA_CONFLITANTE")))
silver = ok.filter("_ordem = 1").drop("_ordem")

# COMMAND ----------

# DBTITLE 1,4. Conferências
n = silver.count()
confere("Faturas válidas", n, 2152336)
confere("Vencimento = emissão + 12 dias", silver.filter(~F.col("data_coerente")).count(), 0)
confere("valor_total = energia + tributos", silver.filter(~F.col("valor_coerente")).count(), 0)
confere("UC com 2+ faturas na mesma competência",
        silver.groupBy("id_uc", "competencia").count().filter("count > 1").count(), 0)
confere("Meses com mais de uma bandeira",
        silver.groupBy("competencia").agg(F.countDistinct("bandeira_tarifaria").alias("b")).filter("b > 1").count(), 0)
confere("Bandeiras fora do domínio", silver.filter(~F.col("bandeira_tarifaria").isin(
        "VERDE", "AMARELA", "VERMELHA_P1", "VERMELHA_P2")).count(), 0)
confere("Pagamento com data 9999 (deve ter virado null)", silver.filter(F.year("data_pagamento") > 2100).count(), 0)

print("Status de pagamento:")
display(silver.groupBy("status_pagamento").count())

# COMMAND ----------

# DBTITLE 1,5. Gravação
grava_silver(silver, quarentena, "faturas")
finaliza()
