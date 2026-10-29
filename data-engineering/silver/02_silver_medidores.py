# Databricks notebook source
# MAGIC %md
# MAGIC # 02 · Silver · Medidores
# MAGIC
# MAGIC **Entrada:** `bronze_medidores` + `silver_unidades_consumidoras` · **Saída:** `silver_medidores` + quarentena
# MAGIC
# MAGIC Regras de `perfil_medidores.md`:
# MAGIC
# MAGIC | # | Problema na fonte | Regra |
# MAGIC |---|---|---|
# MAGIC | 1 | Duplicatas exatas (todas sem conflito) | `dropDuplicates` |
# MAGIC | 2 | `tipo` em 9 grafias (S-MED-04) | Normaliza sem acento/pontuação → ELETROMECANICO, ELETRONICO, SMART |
# MAGIC | 3 | `modelo` com espaços (3.109) | `trim` + maiúsculas |
# MAGIC | 4 | `data_instalacao` em 4 formatos; **traço = MM-dd-yyyy** (provado, S-MED-01) | `parse_data` do utils |
# MAGIC | 5 | "Não retirado" como `null` ou `9999-12-31` | Sentinela → `null` |
# MAGIC | 6 | `data_ultima_manutencao` 100% vazia (S-MED-06) | Mantida, documentada como sem dados na fonte |
# MAGIC | 7 | Modelo determina o tipo (100% coerente) | Flag `tipo_coerente_modelo`; tipo ausente é preenchido pelo modelo |
# MAGIC
# MAGIC Validação de negócio (teste de qualidade): **na troca, a instalação do novo = retirada do antigo** (6.299 trocas).

# COMMAND ----------

# MAGIC %run ../00_utils

# COMMAND ----------

# DBTITLE 1,1. Leitura
bruto = remove_cabecalho(ler_bronze("bronze_medidores"), "id_medidor")
confere("Linhas da Bronze", bruto.count(), 51812)
ucs = le_silver("unidades_consumidoras").select("id_uc")

# COMMAND ----------

# DBTITLE 1,2. Padronização
MODELO_TIPO = {"CG-500": "ELETROMECANICO", "EM-1200": "ELETROMECANICO", "EM-1400": "ELETROMECANICO",
               "EL-2200": "ELETRONICO", "EL-3000": "ELETRONICO", "NX-700": "ELETRONICO",
               "IQ-900": "SMART", "SM-4100": "SMART", "SM-4500": "SMART"}
mapa_modelo = F.create_map(*[F.lit(x) for kv in MODELO_TIPO.items() for x in kv])

med = bruto.select([limpa_texto(c).alias(c) for c in bruto.columns])
tipo_n = F.regexp_replace(normaliza("tipo"), " ", "")       # 'ELETRO MECANICO' -> 'ELETROMECANICO'

med = (med
    .withColumn("id_medidor", F.upper("id_medidor"))
    .withColumn("id_uc", F.upper("id_uc"))
    .withColumn("modelo", F.upper("modelo"))
    .withColumn("tipo", F.when(tipo_n.contains("SMART"), "SMART")
                         .when(tipo_n == "ELETROMECANICO", "ELETROMECANICO")
                         .when(tipo_n == "ELETRONICO", "ELETRONICO"))
    .withColumn("tipo_pelo_modelo", F.element_at(mapa_modelo, F.col("modelo")))
    .withColumn("tipo_coerente_modelo", F.coalesce(F.col("tipo") == F.col("tipo_pelo_modelo"), F.lit(False)))
    .withColumn("tipo", F.coalesce("tipo", "tipo_pelo_modelo"))
    .withColumn("data_instalacao", parse_data("data_instalacao"))
    .withColumn("data_retirada", parse_data(sentinela_para_nulo("data_retirada")))
    .withColumn("data_ultima_manutencao", parse_data("data_ultima_manutencao"))
    .withColumn("status", normaliza("status"))
    .withColumn("medidor_atual", F.col("data_retirada").isNull())
    .drop("tipo_pelo_modelo")
    .dropDuplicates()
)

# COMMAND ----------

# DBTITLE 1,3. Quarentena
med = med.join(ucs.withColumn("_uc_ok", F.lit(True)), "id_uc", "left")
ok, quarentena = separa_quarentena(med, [
    (F.col("id_medidor").isNull() | ~F.col("id_medidor").rlike("^MD[0-9]{6}$"), "ID_MEDIDOR_INVALIDO"),
    (F.col("_uc_ok").isNull(), "UC_INEXISTENTE_NO_CADASTRO"),
    (F.col("data_instalacao").isNull(), "SEM_DATA_INSTALACAO"),
    (F.col("data_retirada") < F.col("data_instalacao"), "RETIRADA_ANTES_DA_INSTALACAO"),
])
ok, quarentena = ok.drop("_uc_ok"), quarentena.drop("_uc_ok")

# id_medidor repetido com dados diferentes (não esperado: o perfil só achou duplicatas exatas)
ordem = Window.partitionBy("id_medidor").orderBy(F.col("data_instalacao").desc())
ok = ok.withColumn("_ordem", F.row_number().over(ordem))
quarentena = quarentena.unionByName(
    ok.filter("_ordem > 1").drop("_ordem").withColumn("motivo_quarentena", F.lit("ID_MEDIDOR_CONFLITANTE")))
silver = ok.filter("_ordem = 1").drop("_ordem")

# COMMAND ----------

# DBTITLE 1,4. Conferências
n = silver.count()
confere("Medidores distintos (45.000 atuais + 6.299 retirados)", n, 51299)
confere("Tipos fora do domínio", silver.filter(~F.col("tipo").isin("ELETROMECANICO", "ELETRONICO", "SMART")
                                               | F.col("tipo").isNull()).count(), 0)
confere("Tipo incoerente com o modelo", silver.filter(~F.col("tipo_coerente_modelo")).count(), 0)

atuais_por_uc = silver.filter("medidor_atual").groupBy("id_uc").count()
confere("UCs com exatamente 1 medidor atual", atuais_por_uc.filter("count = 1").count(), 45000)
confere("Instalações no futuro", silver.filter(F.col("data_instalacao") > F.current_date()).count(), 0)

velho = silver.filter(F.col("data_retirada").isNotNull()).select("id_uc", F.col("data_retirada").alias("dt"))
novo = silver.select("id_uc", F.col("data_instalacao").alias("dt"))
confere("Trocas em que o novo entra no dia da retirada do antigo", velho.join(novo, ["id_uc", "dt"]).count(), 6299)

# COMMAND ----------

# DBTITLE 1,5. Gravação
grava_silver(silver, quarentena, "medidores")
finaliza()
