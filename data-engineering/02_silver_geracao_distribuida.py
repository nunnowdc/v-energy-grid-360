# Databricks notebook source
# MAGIC %md
# MAGIC # 02 · Silver · Geração Distribuída
# MAGIC
# MAGIC **Entrada:** `bronze_geracao_distribuida` + `silver_unidades_consumidoras` · **Saída:** `silver_geracao_distribuida` + `silver_geracao_distribuida_quarentena`
# MAGIC
# MAGIC Regras levantadas em `perfil_geracao_distribuida.md` e alinhadas para a camada Silver:
# MAGIC
# MAGIC | # | Problema na fonte | Regra | Destino |
# MAGIC |---|---|---|---|
# MAGIC | 1 | Cabeçalho repetido | Remover via `remove_cabecalho` | Descarte |
# MAGIC | 2 | `potencia_kwp` com vírgula decimal (316 casos entre aspas) | `regexp_replace(',', '.')` + `to_num` | Silver |
# MAGIC | 3 | `potencia_kwp` em Watts em vez de kW (35 casos entre 3.000 e 9.000, S-GD-02) | Dividir por 1.000 quando > 1.000 com flag `potencia_corrigida_unidade = true` | Silver |
# MAGIC | 4 | Razão `kWh/kWp·mês` fisicamente impossível (> 150 kWh/kWp, 2 UCs comerciais, S-GD-05) | Rejeitar para quarentena com `POTENCIA_INCONSISTENTE` | Quarentena |
# MAGIC | 5 | Injeção estimada paramétrica (`kWp × 110` exato, ~101 casos mai–jun/2026, S-GD-04) | Flag `energia_estimada = true` para ajuste posterior na Gold | Silver |
# MAGIC | 6 | GD com data de conexão anterior à data de ligação da UC (5 casos, S-GD-06) | Rejeitar para quarentena com `GD_ANTES_DA_LIGACAO` | Quarentena |
# MAGIC | 7 | Modalidade e datas | `normaliza` (3 modalidades) e `parse_data` em `data_conexao` | Silver |
# MAGIC | 8 | Integridade referencial cadastral | `id_uc` deve existir em `silver_unidades_consumidoras` | Quarentena |
# MAGIC
# MAGIC **Nota sobre receita:** a energia injetada aqui informada é a base de créditos de GD que abatem faturamento. As potências corrigidas e os casos de energia estimada são essenciais para evitar distorções no diagnóstico analítico.

# COMMAND ----------

# MAGIC %run ./00_utils

# COMMAND ----------

# DBTITLE 1,1. Leitura
bruto = remove_cabecalho(ler_bronze("bronze_geracao_distribuida"), "id_uc")
confere("Linhas da Bronze", bruto.count(), 3510)
ucs = le_silver("unidades_consumidoras").select("id_uc", "data_ligacao")

# COMMAND ----------

# DBTITLE 1,2. Padronização
gd = bruto.select([limpa_texto(c).alias(c) for c in bruto.columns])

# Conversão de potência (tratando vírgula e escala W -> kW)
pot_raw = to_num(F.regexp_replace("potencia_kwp", ",", "."))
flag_pot_corrigida = F.coalesce(pot_raw > 1000.0, F.lit(False))
pot_kwp = F.when(flag_pot_corrigida, pot_raw / 1000.0).otherwise(pot_raw)

# Conversão de energia injetada
energia_injetada = to_num("energia_injetada_kwh_media_mensal")

# Métrica física derivada e flag de energia estimada (kWp * 110 exato)
razao_kwh_kwp = energia_injetada / pot_kwp
flag_energia_estimada = F.coalesce(F.abs(energia_injetada - (pot_kwp * 110.0)) < 0.05, F.lit(False))

gd = (gd
    .withColumn("id_uc", F.upper("id_uc"))
    .withColumn("modalidade", normaliza("modalidade"))
    .withColumn("data_conexao", parse_data("data_conexao"))
    .withColumn("potencia_kwp", pot_kwp)
    .withColumn("potencia_corrigida_unidade", flag_pot_corrigida)
    .withColumn("energia_injetada_kwh_media_mensal", energia_injetada)
    .withColumn("kwh_por_kwp_mes", razao_kwh_kwp)
    .withColumn("energia_estimada", flag_energia_estimada)
    .dropDuplicates()
)

# COMMAND ----------

# DBTITLE 1,3. Quarentena
gd = gd.join(ucs.withColumn("_uc_ok", F.lit(True)), "id_uc", "left")

ok, quarentena = separa_quarentena(gd, [
    (F.col("id_uc").isNull() | ~F.col("id_uc").rlike("^UC[0-9]{6}$"), "ID_UC_INVALIDO"),
    (F.col("_uc_ok").isNull(), "UC_INEXISTENTE_NO_CADASTRO"),
    (F.col("data_conexao").isNull(), "DATA_CONEXAO_INVALIDA"),
    (F.col("potencia_kwp").isNull() | (F.col("potencia_kwp") <= 0), "POTENCIA_INVALIDA"),
    (F.col("energia_injetada_kwh_media_mensal").isNull() | (F.col("energia_injetada_kwh_media_mensal") < 0), "ENERGIA_INJETADA_INVALIDA"),
    (F.col("data_conexao") < F.col("data_ligacao"), "GD_ANTES_DA_LIGACAO"),
    (F.col("kwh_por_kwp_mes") > 150.0, "POTENCIA_INCONSISTENTE"),
])
ok, quarentena = ok.drop("_uc_ok", "data_ligacao"), quarentena.drop("_uc_ok", "data_ligacao")

# Desempate de duplicatas conflitantes por id_uc (1 GD por UC ativa na Silver)
ordem = Window.partitionBy("id_uc").orderBy(F.col("data_conexao").desc())
ok = ok.withColumn("_ordem", F.row_number().over(ordem))
quarentena = quarentena.unionByName(
    ok.filter("_ordem > 1").drop("_ordem").withColumn("motivo_quarentena", F.lit("ID_UC_CONFLITANTE"))
)
silver = ok.filter("_ordem = 1").drop("_ordem")

# COMMAND ----------

# DBTITLE 1,4. Conferências
n = silver.count()
q = quarentena.count()
confere("Total processado (Silver + Quarentena)", n + q, 3510)
confere("GDs válidas na Silver", n, 3503)
confere("Registros em quarentena (5 ligacao + 2 inconsistentes)", q, 7)
confere("Quarentena: GD antes da ligação da UC",
        quarentena.filter(F.col("motivo_quarentena") == "GD_ANTES_DA_LIGACAO").count(), 5)
confere("Quarentena: Potência/razão inconsistente (> 150)",
        quarentena.filter(F.col("motivo_quarentena") == "POTENCIA_INCONSISTENTE").count(), 2)

total_pot_corrigida = (
    silver.filter("potencia_corrigida_unidade").count() +
    quarentena.filter("potencia_corrigida_unidade").count()
)
confere("Potências convertidas de Watts para kW", total_pot_corrigida, 35)

confere("Modalidades fora do domínio canônico", silver.filter(~F.col("modalidade").isin(
    "GERACAO NA PROPRIA UC", "AUTOCONSUMO REMOTO", "GERACAO COMPARTILHADA")).count(), 0)
confere("Conexões no futuro", silver.filter(F.col("data_conexao") > F.current_date()).count(), 0)
confere("Potências menores ou iguais a zero", silver.filter(F.col("potencia_kwp") <= 0).count(), 0)

print(f"GDs com energia estimada (kWp x 110) na Silver: {silver.filter('energia_estimada').count()}")

# COMMAND ----------

# DBTITLE 1,5. Gravação
grava_silver(silver, quarentena, "geracao_distribuida")
finaliza()
