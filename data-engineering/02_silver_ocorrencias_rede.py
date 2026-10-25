# Databricks notebook source
# MAGIC %md
# MAGIC # 02 · Silver · Ocorrências de Rede
# MAGIC
# MAGIC **Entrada:** `bronze_ocorrencias_rede` + `silver_unidades_consumidoras` · **Saída:** `silver_ocorrencias_rede` + quarentena
# MAGIC
# MAGIC **Grão:** 1 registro = 1 UC interrompida (definição do case; `id_ocorrencia` é único).
# MAGIC
# MAGIC Regras de `perfil_ocorrencias_rede.md`:
# MAGIC
# MAGIC | # | Problema na fonte | Regra |
# MAGIC |---|---|---|
# MAGIC | 1 | `causa` sem informação em 4 formas (5.400) (S-OCO-03) | `NAO INFORMADA`, separada da categoria válida `NAO IDENTIFICADA` |
# MAGIC | 2 | `duracao_min` com `" min"` (16.200) | Remove o sufixo e converte |
# MAGIC | 3 | Durações truncadas em 2.880 min (S-OCO-04) | Flag `duracao_truncada` |
# MAGIC | 4 | Evento climático de jul/2025 (N-06, N-12) | Flag `dia_critico` (ocorrências do dia > média + 3 desvios-padrão), para o DEC com e sem expurgo |
# MAGIC | 5 | OSCILACAO conta como interrupção? (S-OCO-05) | Mantida (definição do case); a Gold oferece o filtro |

# COMMAND ----------

# MAGIC %run ./00_utils

# COMMAND ----------

# DBTITLE 1,1. Leitura
bruto = remove_cabecalho(ler_bronze("bronze_ocorrencias_rede"), "id_ocorrencia")
confere("Linhas da Bronze", bruto.count(), 180000)
ucs = le_silver("unidades_consumidoras").select("id_uc")

# COMMAND ----------

# DBTITLE 1,2. Padronização
oc = bruto.select([limpa_texto(c).alias(c) for c in bruto.columns])
oc = (oc
    .withColumn("id_ocorrencia", F.upper("id_ocorrencia"))
    .withColumn("id_uc", F.upper("id_uc"))
    .withColumn("alimentador", F.upper("alimentador"))
    .withColumn("tipo", normaliza("tipo"))
    .withColumn("causa", F.coalesce(normaliza("causa"), F.lit("NAO INFORMADA")))   # null/-/N/A/NULL já viraram null
    .withColumn("data_abertura", parse_ts("data_abertura"))
    .withColumn("data_encerramento", parse_ts("data_encerramento"))
    .withColumn("duracao_min", to_num(F.regexp_replace("duracao_min", "(?i)\\s*min$", "")))
    .withColumn("duracao_truncada", F.coalesce(F.col("duracao_min") == 2880, F.lit(False)))
    .withColumn("duracao_coerente", F.coalesce(F.abs(
        (F.unix_timestamp("data_encerramento") - F.unix_timestamp("data_abertura")) / 60 - F.col("duracao_min")) <= 1,
        F.lit(False)))
    .dropDuplicates()
)

# Dia crítico (regra simplificada do PRODIST, aplicada à base inteira)
diario = oc.groupBy(F.to_date("data_abertura").alias("_dia")).count()
media, dp = diario.agg(F.avg("count"), F.stddev("count")).first()
limite = media + 3 * dp
criticos = diario.filter(F.col("count") > limite).select("_dia").withColumn("dia_critico", F.lit(True))
print(f"Dia crítico: mais de {limite:.0f} ocorrências no dia (média {media:.0f}, desvio {dp:.0f})")
oc = (oc.withColumn("_dia", F.to_date("data_abertura"))
        .join(F.broadcast(criticos), "_dia", "left")
        .withColumn("dia_critico", F.coalesce("dia_critico", F.lit(False)))
        .drop("_dia"))

# COMMAND ----------

# DBTITLE 1,3. Quarentena
oc = oc.join(ucs.withColumn("_uc_ok", F.lit(True)), "id_uc", "left")
ok, quarentena = separa_quarentena(oc, [
    (F.col("id_ocorrencia").isNull(), "ID_OCORRENCIA_AUSENTE"),
    (F.col("_uc_ok").isNull(), "UC_INEXISTENTE_NO_CADASTRO"),
    (F.col("data_abertura").isNull() | F.col("duracao_min").isNull(), "DATA_OU_DURACAO_INVALIDA"),
    (F.col("data_encerramento") < F.col("data_abertura"), "ENCERRA_ANTES_DE_ABRIR"),
])
ok, quarentena = ok.drop("_uc_ok"), quarentena.drop("_uc_ok")

ordem = Window.partitionBy("id_ocorrencia").orderBy(F.col("data_abertura").desc())
ok = ok.withColumn("_ordem", F.row_number().over(ordem))
quarentena = quarentena.unionByName(
    ok.filter("_ordem > 1").drop("_ordem").withColumn("motivo_quarentena", F.lit("ID_OCORRENCIA_CONFLITANTE")))
silver = ok.filter("_ordem = 1").drop("_ordem")

# COMMAND ----------

# DBTITLE 1,4. Conferências
confere("Ocorrências válidas", silver.count(), 180000)
confere("Duração = encerramento − abertura", silver.filter(~F.col("duracao_coerente")).count(), 0)
confere("Durações truncadas em 48 h", silver.filter("duracao_truncada").count(), 30)
dias = silver.filter("dia_critico").select(F.to_date("data_abertura").alias("d")).distinct()
confere("Dias críticos (esperado: os 31 dias de jul/2025)", dias.count(), 31)
confere("Causas fora do domínio", silver.filter(~F.col("causa").isin(
    "CLIMATICA", "SOBRECARGA", "NAO IDENTIFICADA", "VEGETACAO", "TERCEIROS", "FALHA DE EQUIPAMENTO",
    "NAO INFORMADA")).count(), 0)

# COMMAND ----------

# DBTITLE 1,5. Gravação
grava_silver(silver, quarentena, "ocorrencias_rede")
finaliza()
