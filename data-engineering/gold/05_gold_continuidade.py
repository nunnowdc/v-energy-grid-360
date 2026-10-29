# Databricks notebook source
# MAGIC %md
# MAGIC # 05 · Gold · Continuidade (Gerente de Operação)
# MAGIC
# MAGIC > *"Quero acompanhar DEC e FEC por alimentador, saber quais regiões concentram as piores interrupções e onde a manutenção preventiva dá mais retorno."*
# MAGIC
# MAGIC | Tabela | Grão | Para quê |
# MAGIC |---|---|---|
# MAGIC | `agg_continuidade_alimentador` | alimentador × competência (todos os meses, inclusive sem interrupção) | DEC/FEC mensal, **com e sem dias críticos** |
# MAGIC | `agg_continuidade_alimentador_anual` | alimentador × ano | Rankings: por DEC (sofrimento por cliente) e por horas × UC (retorno da manutenção) |
# MAGIC
# MAGIC Fórmulas (grão do case: 1 ocorrência = 1 UC interrompida):
# MAGIC - `DEC = Σ duração (h) ÷ total de UCs do alimentador` · `FEC = nº de interrupções ÷ total de UCs`
# MAGIC - `*_sem_dia_critico`: exclui os dias críticos (regra simplificada do PRODIST; na base, os 31 dias de jul/2025)
# MAGIC
# MAGIC Ressalvas para o portal: alimentadores com menos de 100 UCs têm DEC/FEC inflado pelo denominador (N-10);
# MAGIC os 3 alimentadores de maior impacto em 2025 só aparecem por causa do temporal de jul/2025.

# COMMAND ----------

# MAGIC %run ../00_utils

# COMMAND ----------

# DBTITLE 1,1. Base
oc = le_gold("fact_ocorrencias")
alim = le_gold("dim_alimentador").select("alimentador", "total_ucs", "municipio_principal", "regiao", "alimentador_pequeno")
comps = le_gold("dim_competencia").select("competencia")

# COMMAND ----------

# DBTITLE 1,2. agg_continuidade_alimentador (mensal)
normal = ~F.col("dia_critico")
mes = oc.groupBy("alimentador", "competencia").agg(
    F.count("*").alias("interrupcoes"),
    F.sum("duracao_h").alias("horas_x_uc"),
    F.sum(normal.cast("int")).alias("interrupcoes_sem_dia_critico"),
    F.sum(F.when(normal, F.col("duracao_h")).otherwise(0)).alias("horas_x_uc_sem_dia_critico"),
    F.sum((F.col("causa") == "CLIMATICA").cast("int")).alias("interrupcoes_climaticas"),
    F.sum(F.col("eh_oscilacao").cast("int")).alias("interrupcoes_oscilacao"),
    F.sum(F.col("duracao_truncada").cast("int")).alias("duracoes_truncadas"))

METRICAS = ["interrupcoes", "horas_x_uc", "interrupcoes_sem_dia_critico", "horas_x_uc_sem_dia_critico",
            "interrupcoes_climaticas", "interrupcoes_oscilacao", "duracoes_truncadas"]
grade = alim.crossJoin(comps)                                   # todos os meses, mesmo sem interrupção
cont = (grade.join(mes, ["alimentador", "competencia"], "left").fillna(0, METRICAS)
    .withColumn("mes_referencia", F.date_format("competencia", "yyyy-MM"))
    .withColumn("ano", F.year("competencia"))
    .withColumn("dec", F.round(F.col("horas_x_uc") / F.col("total_ucs"), 4))
    .withColumn("fec", F.round(F.col("interrupcoes") / F.col("total_ucs"), 4))
    .withColumn("dec_sem_dia_critico", F.round(F.col("horas_x_uc_sem_dia_critico") / F.col("total_ucs"), 4))
    .withColumn("fec_sem_dia_critico", F.round(F.col("interrupcoes_sem_dia_critico") / F.col("total_ucs"), 4)))
n = grava_gold(cont, "agg_continuidade_alimentador")
confere("Linhas = alimentadores × 48 meses", n, alim.count() * 48)

# COMMAND ----------

# DBTITLE 1,3. agg_continuidade_alimentador_anual (rankings)
anual = (le_gold("agg_continuidade_alimentador")
    .groupBy("alimentador", "ano", "total_ucs", "municipio_principal", "regiao", "alimentador_pequeno")
    .agg(*[F.sum(c).alias(c) for c in METRICAS],
         F.countDistinct("competencia").alias("meses"))
    .withColumn("dec", F.round(F.col("horas_x_uc") / F.col("total_ucs"), 2))
    .withColumn("fec", F.round(F.col("interrupcoes") / F.col("total_ucs"), 2))
    .withColumn("dec_sem_dia_critico", F.round(F.col("horas_x_uc_sem_dia_critico") / F.col("total_ucs"), 2))
    .withColumn("fec_sem_dia_critico", F.round(F.col("interrupcoes_sem_dia_critico") / F.col("total_ucs"), 2)))
por_ano = Window.partitionBy("ano")
anual = (anual
    .withColumn("rank_dec", F.rank().over(por_ano.orderBy(F.desc("dec"))))
    .withColumn("rank_dec_sem_dia_critico", F.rank().over(por_ano.orderBy(F.desc("dec_sem_dia_critico"))))
    .withColumn("rank_impacto_horas_x_uc", F.rank().over(por_ano.orderBy(F.desc("horas_x_uc")))))
grava_gold(anual, "agg_continuidade_alimentador_anual")

top = (le_gold("agg_continuidade_alimentador_anual").filter("ano = 2025")
       .orderBy("rank_impacto_horas_x_uc").limit(5).collect())
for r in top:
    RESUMO.append(f"IMPACTO 2025 | {r['alimentador']}: {r['horas_x_uc']:,.0f} h×UC | DEC {r['dec']} "
                  f"(sem dia crítico {r['dec_sem_dia_critico']}) | {r['total_ucs']} UCs")

finaliza()
