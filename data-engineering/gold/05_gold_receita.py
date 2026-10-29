# Databricks notebook source
# MAGIC %md
# MAGIC # 05 · Gold · Receita (Diretor Comercial)
# MAGIC
# MAGIC > *"Quero ver por bairro e por classe, quero saber quanto da variação foi preço e quanto foi quantidade de energia."*
# MAGIC
# MAGIC | Tabela | Grão | Para quê |
# MAGIC |---|---|---|
# MAGIC | `agg_receita_mensal` | competência × município × bairro × classe × possui_gd | Séries mensais de receita, volume e preço médio; comparar quaisquer períodos |
# MAGIC | `agg_receita_preco_volume` | município × bairro × classe × possui_gd | Decomposição da variação **primeiro ano → últimos 12 meses** em efeito-volume e efeito-preço |
# MAGIC
# MAGIC **Decomposição** (por segmento, soma exata):
# MAGIC - `efeito_volume = (Q1 − Q0) × P0` — quanto a receita teria mudado só pela quantidade, ao preço antigo
# MAGIC - `efeito_preco = (P1 − P0) × Q1` — o restante, explicado pela mudança do preço médio
# MAGIC - `efeito_volume + efeito_preco = R1 − R0`
# MAGIC
# MAGIC onde `R` = receita faturada (com tributos), `Q` = consumo **medido** nas leituras (kWh ajustado) e `P = R / Q`.
# MAGIC Somando os segmentos, os efeitos de mix (classe, bairro) ficam dentro dos efeitos de cada segmento.
# MAGIC
# MAGIC **Cuidado de interpretação:** a fatura não tem kWh (S-FAT-07), então o volume é o **medido**. Em UCs com GD,
# MAGIC parte do consumo medido é compensada por créditos, e o "preço efetivo" (R/Q) captura essa compensação.

# COMMAND ----------

# MAGIC %run ../00_utils

# COMMAND ----------

# DBTITLE 1,1. Base: faturas + dimensão da UC
ff = le_gold("fact_faturamento")
dim = le_gold("dim_unidade_consumidora").select("id_uc", "municipio", "bairro", "classe", "possui_gd")
base = ff.join(dim, "id_uc")

cmin, cmax = base.agg(F.min("competencia"), F.max("competencia")).first()
p0_ini, p0_fim = cmin, soma_meses(cmin, 11)
p1_ini, p1_fim = soma_meses(cmax, -11), cmax
print(f"Período base (P0): {p0_ini}..{p0_fim} | Período comparado (P1): {p1_ini}..{p1_fim}")

SEG = ["municipio", "bairro", "classe", "possui_gd"]

# COMMAND ----------

# DBTITLE 1,2. agg_receita_mensal
mensal = (base.groupBy("competencia", "mes_referencia", "bandeira_tarifaria", *SEG).agg(
              F.sum("receita_faturada").alias("receita_faturada"),
              F.sum("receita_recebida").alias("receita_recebida"),
              F.sum("valor_energia").alias("receita_energia"),
              F.sum("consumo_kwh").alias("consumo_kwh"),
              F.countDistinct("id_uc").alias("ucs_faturadas"),
              F.count("*").alias("faturas"),
              F.sum((F.col("status_pagamento") == "ATRASADA").cast("int")).alias("faturas_atrasadas"))
          .withColumn("preco_medio_kwh", F.when(F.col("consumo_kwh") > 0,
                                                F.round(F.col("receita_faturada") / F.col("consumo_kwh"), 4)))
          .withColumn("ano", F.year("competencia")).withColumn("mes", F.month("competencia")))
grava_gold(mensal, "agg_receita_mensal")

# COMMAND ----------

# DBTITLE 1,3. agg_receita_preco_volume
per = (F.when(F.col("competencia").between(p0_ini, p0_fim), "P0")
        .when(F.col("competencia").between(p1_ini, p1_fim), "P1"))
b = base.withColumn("_p", per).filter(F.col("_p").isNotNull())


def soma(col, p):
    return F.sum(F.when(F.col("_p") == p, F.col(col)).otherwise(F.lit(0.0)))


def ucs(p):
    return F.countDistinct(F.when(F.col("_p") == p, F.col("id_uc")))


pv = (b.groupBy(*SEG).agg(
        soma("receita_faturada", "P0").alias("receita_p0"), soma("receita_faturada", "P1").alias("receita_p1"),
        soma("consumo_kwh", "P0").alias("kwh_p0"), soma("consumo_kwh", "P1").alias("kwh_p1"),
        ucs("P0").alias("ucs_p0"), ucs("P1").alias("ucs_p1"))
    .withColumn("preco_p0", F.when(F.col("kwh_p0") > 0, F.col("receita_p0") / F.col("kwh_p0")))
    .withColumn("preco_p1", F.when(F.col("kwh_p1") > 0, F.col("receita_p1") / F.col("kwh_p1")))
    .withColumn("variacao_receita", F.col("receita_p1") - F.col("receita_p0"))
    .withColumn("efeito_volume", F.when(F.col("kwh_p0") > 0, (F.col("kwh_p1") - F.col("kwh_p0")) * F.col("preco_p0"))
                                  .otherwise(F.col("variacao_receita")))           # segmento novo: tudo é volume
    .withColumn("efeito_preco", F.col("variacao_receita") - F.col("efeito_volume"))
    .withColumn("variacao_receita_pct", F.when(F.col("receita_p0") > 0, F.round(100 * (F.col("receita_p1") / F.col("receita_p0") - 1), 2)))
    .withColumn("variacao_volume_pct", F.when(F.col("kwh_p0") > 0, F.round(100 * (F.col("kwh_p1") / F.col("kwh_p0") - 1), 2)))
    .withColumn("variacao_preco_pct", F.when(F.col("preco_p0") > 0, F.round(100 * (F.col("preco_p1") / F.col("preco_p0") - 1), 2)))
    .withColumn("kwh_por_uc_p0", F.when(F.col("ucs_p0") > 0, F.col("kwh_p0") / F.col("ucs_p0")))
    .withColumn("kwh_por_uc_p1", F.when(F.col("ucs_p1") > 0, F.col("kwh_p1") / F.col("ucs_p1")))
    .withColumn("periodo_p0", F.lit(f"{p0_ini:%Y-%m} a {p0_fim:%Y-%m}"))
    .withColumn("periodo_p1", F.lit(f"{p1_ini:%Y-%m} a {p1_fim:%Y-%m}")))
grava_gold(pv, "agg_receita_preco_volume")

# COMMAND ----------

# DBTITLE 1,4. Resumo do diagnóstico
pv = le_gold("agg_receita_preco_volume")
tot = pv.agg(*[F.sum(c).alias(c) for c in ["receita_p0", "receita_p1", "kwh_p0", "kwh_p1",
                                            "variacao_receita", "efeito_volume", "efeito_preco"]]).first()
confere("Soma dos efeitos = variação da receita",
        round(tot["efeito_volume"] + tot["efeito_preco"] - tot["variacao_receita"], 2), ok=True)
confere("Receita P0 -> P1 (R$)", f"{tot['receita_p0']:,.0f} -> {tot['receita_p1']:,.0f} "
        f"({100 * (tot['receita_p1'] / tot['receita_p0'] - 1):+.1f}%)", ok=True)
confere("Volume P0 -> P1 (kWh)", f"{tot['kwh_p0']:,.0f} -> {tot['kwh_p1']:,.0f} "
        f"({100 * (tot['kwh_p1'] / tot['kwh_p0'] - 1):+.1f}%)", ok=True)
confere("Efeito-volume (R$)", f"{tot['efeito_volume']:,.0f}", ok=True)
confere("Efeito-preço (R$)", f"{tot['efeito_preco']:,.0f}", ok=True)

print("Por classe e GD:")
por_classe = (pv.groupBy("classe", "possui_gd").agg(
        F.sum("receita_p0").alias("receita_p0"), F.sum("receita_p1").alias("receita_p1"),
        F.sum("kwh_p0").alias("kwh_p0"), F.sum("kwh_p1").alias("kwh_p1"),
        F.sum("efeito_volume").alias("efeito_volume"), F.sum("efeito_preco").alias("efeito_preco"))
    .withColumn("var_receita_pct", F.round(100 * (F.col("receita_p1") / F.col("receita_p0") - 1), 1))
    .withColumn("var_volume_pct", F.round(100 * (F.col("kwh_p1") / F.col("kwh_p0") - 1), 1))
    .orderBy("classe", "possui_gd"))
display(por_classe)
for r in por_classe.collect():
    RESUMO.append(f"CLASSE | {r['classe']} gd={r['possui_gd']}: receita {r['var_receita_pct']:+}% | volume {r['var_volume_pct']:+}% "
                  f"| ef.volume R$ {r['efeito_volume']:,.0f} | ef.preço R$ {r['efeito_preco']:,.0f}")

finaliza()
