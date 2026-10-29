# Databricks notebook source
# MAGIC %md
# MAGIC # 04 · Gold · Fatos
# MAGIC
# MAGIC | Tabela | Grão | Destaques |
# MAGIC |---|---|---|
# MAGIC | `fact_faturamento` | 1 por fatura | `receita_faturada`, `receita_recebida`, `status_pagamento`; **`consumo_kwh` vem da leitura** da mesma UC e competência (a fatura não tem kWh) e dá o `preco_medio_kwh` |
# MAGIC | `fact_leituras` | 1 por UC × competência | `consumo_kwh` = **ajustado** (troca de medidor imputada); consumo do mesmo mês no ano anterior e a variação (visão 360: "a conta veio alta?") |
# MAGIC | `fact_ocorrencias` | 1 por UC interrompida | `duracao_h`, `dia_critico`, `duracao_truncada`, `eh_oscilacao` (filtro opcional no DEC/FEC) |
# MAGIC | `fact_atendimentos` | 1 por chamado | Tempo de resolução, status, nota, `qtd_tratativas` (o histórico de ações fica fora da Gold: rótulos não confiáveis) |
# MAGIC | `fact_inspecoes` | 1 por inspeção | Resultado e tipo canônicos, kWh recuperado |

# COMMAND ----------

# MAGIC %run ../00_utils

# COMMAND ----------

# DBTITLE 1,1. fact_leituras
lei = le_silver("leituras")
anterior = lei.select("id_uc", F.add_months("competencia", 12).alias("competencia"),
                      F.col("consumo_kwh_ajustado").alias("consumo_ano_anterior_kwh"))
fact_lei = (lei.join(anterior, ["id_uc", "competencia"], "left")
    .select("id_leitura", "id_uc", "id_medidor", "competencia", "mes_referencia",
            F.year("competencia").alias("ano"), F.month("competencia").alias("mes"),
            "data_leitura", "leitura_anterior", "leitura_atual",
            F.col("consumo_kwh_ajustado").alias("consumo_kwh"),
            F.col("consumo_kwh").alias("consumo_kwh_declarado"),
            "consumo_imputado", "tipo_leitura", "status_qualidade_leitura",
            "consumo_ano_anterior_kwh",
            F.when(F.col("consumo_ano_anterior_kwh") > 0,
                   F.round(100 * (F.col("consumo_kwh_ajustado") / F.col("consumo_ano_anterior_kwh") - 1), 1))
             .alias("variacao_ano_anterior_pct")))
n = grava_gold(fact_lei, "fact_leituras")
confere("fact_leituras", n, 2152336)

# COMMAND ----------

# DBTITLE 1,2. fact_faturamento
fat = le_silver("faturas")
consumo = le_gold("fact_leituras").select("id_uc", "competencia", "consumo_kwh")
fact_fat = (fat.join(consumo, ["id_uc", "competencia"], "left")
    .select("id_fatura", "id_uc", "competencia", "mes_referencia",
            F.year("competencia").alias("ano"), F.month("competencia").alias("mes"),
            "data_emissao", "data_vencimento", "data_pagamento",
            "valor_energia", "tributos",
            F.col("valor_total").alias("receita_faturada"),
            F.when(F.col("status") == "PAGA", F.col("valor_total")).otherwise(F.lit(0.0)).alias("receita_recebida"),
            "bandeira_tarifaria", "status", "status_pagamento", "dias_atraso",
            "consumo_kwh",
            F.when(F.col("consumo_kwh") > 0, F.round(F.col("valor_energia") / F.col("consumo_kwh"), 4))
             .alias("preco_medio_kwh")))
n = grava_gold(fact_fat, "fact_faturamento")
confere("fact_faturamento", n, 2152336)
confere("Faturas sem leitura correspondente", le_gold("fact_faturamento").filter(F.col("consumo_kwh").isNull()).count(), 0)

# COMMAND ----------

# DBTITLE 1,3. fact_ocorrencias
oc = le_silver("ocorrencias_rede")
fact_oc = oc.select("id_ocorrencia", "id_uc", "alimentador", "tipo", "causa",
                    "data_abertura", "data_encerramento",
                    F.date_trunc("month", "data_abertura").cast("date").alias("competencia"),
                    "duracao_min", F.round(F.col("duracao_min") / 60, 4).alias("duracao_h"),
                    "dia_critico", "duracao_truncada", (F.col("tipo") == "OSCILACAO").alias("eh_oscilacao"))
n = grava_gold(fact_oc, "fact_ocorrencias")
confere("fact_ocorrencias", n, 180000)

# COMMAND ----------

# DBTITLE 1,4. fact_atendimentos
at = le_silver("atendimentos")
fact_at = at.select("protocolo", "id_uc", "assunto", "subassunto", "canal",
                    "data_abertura", "data_fechamento",
                    F.date_trunc("month", "data_abertura").cast("date").alias("competencia"),
                    "status_chamado", "tempo_resolucao_h", "nota_satisfacao", "qtd_tratativas")
n = grava_gold(fact_at, "fact_atendimentos")
confere("fact_atendimentos", n, 318871)

# COMMAND ----------

# DBTITLE 1,5. fact_inspecoes
ins = le_silver("inspecoes")
fact_ins = ins.select("id_inspecao", "id_uc", F.col("data").alias("data_inspecao"), "mes_inspecao", "inspetor",
                      "resultado", "tipo_irregularidade", "kwh_recuperado", "registro_coerente", "aba_origem")
n = grava_gold(fact_ins, "fact_inspecoes")
confere("fact_inspecoes", n, 1389)

finaliza()
