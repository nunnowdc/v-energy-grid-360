# Databricks notebook source
# DBTITLE 1,03 · Silver · Atendimentos
# MAGIC %md
# MAGIC # 03 · Silver · Atendimentos
# MAGIC
# MAGIC **Entrada:** `bronze_atendimentos` (JSON multiline, schema inferido) · **Saída:** `silver_atendimentos`
# MAGIC
# MAGIC Regras da fonte (validadas na amostragem da Bronze):
# MAGIC
# MAGIC | # | Problema na fonte | Regra | Destino |
# MAGIC |---|---|---|---|
# MAGIC | 1 | Bronze acumulou lotes duplicados no ingestão antiga (956.613 = 3× 318.871) | `ler_bronze` já pega só o último lote | Silver |
# MAGIC | 2 | `protocolo` duplicado | `dropDuplicates` por protocolo | Descarte |
# MAGIC | 3 | Datas em texto `yyyy-MM-dd HH:mm:ss` | `parse_ts` | Silver |
# MAGIC | 4 | Chamado aberto (sem fechamento) | `tempo_resolucao_h` null + `status_chamado = EM_ABERTO` | Silver |
# MAGIC | 5 | Histórico de ações (array) — rótulos não confiáveis | Não vai para a Gold; fica apenas `qtd_tratativas` | Silver |
# MAGIC | 6 | `nota_satisfacao` já numérica (28.698 nulos = pesquisa não respondida) | Mantém null | Silver |
# MAGIC
# MAGIC A Gold consome: `protocolo`, `id_uc`, `assunto`, `subassunto`, `canal`, `data_abertura`, `data_fechamento`,
# MAGIC `status_chamado`, `tempo_resolucao_h`, `nota_satisfacao`, `qtd_tratativas`.

# COMMAND ----------

# DBTITLE 1,Utils
# MAGIC %run ./00_utils

# COMMAND ----------

# DBTITLE 1,1. Leitura da Bronze
bruto = ler_bronze("bronze_atendimentos")
n_bruto = bruto.count()
confere("Linhas da Bronze (último lote)", n_bruto, 318871)

# COMMAND ----------

# DBTITLE 1,2. Padronização
# Tempo de resolução em horas (null quando o chamado sigue aberto)
diff_h = (F.unix_timestamp("data_fechamento") - F.unix_timestamp("data_abertura")) / 3600.0

at = (bruto
    .select(
        F.upper(F.trim("protocolo")).alias("protocolo"),
        F.upper(F.trim("id_uc")).alias("id_uc"),
        limpa_texto("assunto").alias("assunto"),
        limpa_texto("subassunto").alias("subassunto"),
        F.upper(F.trim("canal")).alias("canal"),
        parse_ts("data_abertura").alias("data_abertura"),
        parse_ts("data_fechamento").alias("data_fechamento"),
        "nota_satisfacao",
        F.coalesce(F.size("historico").cast("int"), F.lit(0)).alias("qtd_tratativas"),
    )
    .withColumn("tempo_resolucao_h", F.round(diff_h, 4))
    .withColumn("status_chamado",
                F.when(F.col("data_fechamento").isNotNull(), "ENCERRADO").otherwise("EM_ABERTO"))
    .dropDuplicates(["protocolo"])
)

# COMMAND ----------

# DBTITLE 1,3. Conferências
n = at.count()
confere("Atendimentos na Silver", n, 318871)
confere("Protocolos únicos", at.select("protocolo").distinct().count(), n)
confere("Chamados abertos (sem fechamento)", at.filter("data_fechamento IS NULL").count(), ok=True)
confere("Tempo de resolução negativo", at.filter(F.col("tempo_resolucao_h") < 0).count(), 0)
confere("Datas de abertura nulas", at.filter("data_abertura IS NULL").count(), 0)
print("Canais e assuntos:")
display(at.groupBy("canal").count().orderBy(F.desc("count")))

# COMMAND ----------

# DBTITLE 1,4. Gravação
grava_silver(at, None, "atendimentos")
finaliza()

# COMMAND ----------

