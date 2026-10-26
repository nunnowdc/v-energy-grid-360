# Databricks notebook source
# MAGIC %md
# MAGIC # 02 · Silver · Inspeções
# MAGIC
# MAGIC **Entrada:** `bronze_inspecoes` + `silver_unidades_consumidoras` · **Saída:** `silver_inspecoes` + `silver_inspecoes_quarentena`
# MAGIC
# MAGIC Regras levantadas em `perfil_inspecoes.md` e alinhadas para a camada Silver:
# MAGIC
# MAGIC | # | Problema na fonte | Regra | Destino |
# MAGIC |---|---|---|---|
# MAGIC | 1 | Cabeçalho repetido | Remover via `remove_cabecalho` | Descarte |
# MAGIC | 2 | `data` em 4 formatos; traço curto é americano `MM-dd-yyyy` (S-INS-02) | Priorizar `MM-dd-yyyy` no traço curto com `data_ambigua = true` nas 11 linhas com dia e mês <= 12 | Silver |
# MAGIC | 3 | `resultado` com variantes de caixa e termos curtos (`CONFIRMADA`, `NADA CONSTA`) | `IRREGULARIDADE_CONFIRMADA` e `SEM_IRREGULARIDADE`; flag `resultado_declarado_nada_consta` | Silver |
# MAGIC | 4 | `inspetor` com espaços extras (107 variantes -> 40 inspetores) | `limpa_texto` + `upper` + `trim` | Silver |
# MAGIC | 5 | `tipo_irregularidade` com placeholder `-` e vazios | Converter `-` e string vazia para `null` | Silver |
# MAGIC | 6 | `kwh_recuperado` com vírgula decimal | `regexp_replace(',', '.')` + `to_num` | Silver |
# MAGIC | 7 | Consistência de negócio: irregularidade exige tipo preenchido e kWh > 0; sem irregularidade exige kWh = 0 | Validação cruzada (violações vão para quarentena) | Quarentena |
# MAGIC | 8 | Integridade referencial cadastral | `id_uc` deve existir em `silver_unidades_consumidoras` | Quarentena |
# MAGIC
# MAGIC **Nota sobre temporalidade:** o nome da planilha de origem (`aba_origem`) não deve ser usado como filtro temporal, pois a aba "dez" é um lote consolidado com inspeções realizadas de agosto a dezembro.

# COMMAND ----------

# MAGIC %run ./00_utils

# COMMAND ----------

# DBTITLE 1,1. Leitura
bruto = remove_cabecalho(ler_bronze("bronze_inspecoes"), "id_inspecao")
confere("Linhas da Bronze", bruto.count(), 1389)
ucs = le_silver("unidades_consumidoras").select("id_uc")

# COMMAND ----------

# DBTITLE 1,2. Padronização
# Limpeza genérica de texto em todas as colunas
ins = bruto.select([limpa_texto(c).alias(c) for c in bruto.columns])

# Normalização de resultado
res_n = normaliza("resultado")
eh_nada_consta = F.coalesce(res_n == "NADA CONSTA", F.lit(False))
resultado_canonico = (
    F.when(res_n.contains("CONFIRMADA"), "IRREGULARIDADE_CONFIRMADA")
     .otherwise("SEM_IRREGULARIDADE")
)

# Tipo de irregularidade: '-' e strings vazias viram null
tipo_n = normaliza("tipo_irregularidade")
tipo_canonico = F.when(tipo_n.isin("-", ""), None).otherwise(tipo_n)

# Parsing de datas com desambiguação empírica (MM-dd-yyyy antes de dd-MM-yyyy no traço)
eh_traco = F.col("data").rlike("^[0-9]{2}-[0-9]{2}-[0-9]{4}$")
p1 = F.split(F.col("data"), "-").getItem(0).cast("int")
p2 = F.split(F.col("data"), "-").getItem(1).cast("int")
flag_data_ambigua = F.coalesce(eh_traco & (p1 <= 12) & (p2 <= 12), F.lit(False))

dt_parsed = F.coalesce(
    F.to_date(F.col("data"), "yyyy-MM-dd"),
    F.to_date(F.col("data"), "MM-dd-yyyy"),
    F.to_date(F.col("data"), "dd.MM.yyyy"),
    F.to_date(F.col("data"), "dd/MM/yyyy"),
    parse_data("data")
)

kwh_parsed = to_num(F.regexp_replace("kwh_recuperado", ",", "."))

ins = (ins
    .withColumn("id_inspecao", F.upper("id_inspecao"))
    .withColumn("id_uc", F.upper("id_uc"))
    .withColumn("data", dt_parsed)
    .withColumn("data_ambigua", flag_data_ambigua)
    .withColumn("inspetor", F.upper(F.trim("inspetor")))
    .withColumn("resultado_declarado_nada_consta", eh_nada_consta)
    .withColumn("resultado", resultado_canonico)
    .withColumn("tipo_irregularidade", tipo_canonico)
    .withColumn("kwh_recuperado", kwh_parsed)
    .dropDuplicates()
)

# Validação cruzada de negócio
# Irregularidade confirmada => tipo informado e kWh > 0
# Sem irregularidade => tipo nulo e kWh == 0
regra_coerente = F.coalesce(
    ((F.col("resultado") == "IRREGULARIDADE_CONFIRMADA") & F.col("tipo_irregularidade").isNotNull() & (F.col("kwh_recuperado") > 0)) |
    ((F.col("resultado") == "SEM_IRREGULARIDADE") & F.col("tipo_irregularidade").isNull() & (F.col("kwh_recuperado") == 0.0)),
    F.lit(False)
)
ins = ins.withColumn("regra_coerente", regra_coerente)

# COMMAND ----------

# DBTITLE 1,3. Quarentena
ins = ins.join(ucs.withColumn("_uc_ok", F.lit(True)), "id_uc", "left")

ok, quarentena = separa_quarentena(ins, [
    (F.col("id_inspecao").isNull() | ~F.col("id_inspecao").rlike("^IN[0-9]{7}$"), "ID_INSPECAO_INVALIDO"),
    (F.col("_uc_ok").isNull(), "UC_INEXISTENTE_NO_CADASTRO"),
    (F.col("data").isNull(), "DATA_INVALIDA"),
    (~F.col("regra_coerente"), "INCOERENCIA_RESULTADO_KWH"),
])
ok, quarentena = ok.drop("_uc_ok", "regra_coerente"), quarentena.drop("_uc_ok", "regra_coerente")

# Desempate de duplicatas conflitantes por id_inspecao (se houver)
ordem = Window.partitionBy("id_inspecao").orderBy(F.col("data").desc())
ok = ok.withColumn("_ordem", F.row_number().over(ordem))
quarentena = quarentena.unionByName(
    ok.filter("_ordem > 1").drop("_ordem").withColumn("motivo_quarentena", F.lit("ID_INSPECAO_CONFLITANTE"))
)
silver = ok.filter("_ordem = 1").drop("_ordem")

# COMMAND ----------

# DBTITLE 1,4. Conferências
n = silver.count()
confere("Inspeções válidas na Silver", n, 1389)
confere("Quarentena vazia (base sem rejeições impeditivas)", quarentena.count(), 0)
confere("UCs inspecionadas únicas", silver.select("id_uc").distinct().count(), 1389)
confere("Resultados fora do domínio canônico",
        silver.filter(~F.col("resultado").isin("IRREGULARIDADE_CONFIRMADA", "SEM_IRREGULARIDADE")).count(), 0)
confere("Irregularidades confirmadas", silver.filter(F.col("resultado") == "IRREGULARIDADE_CONFIRMADA").count(), 871)
confere("Inspeções sem irregularidade", silver.filter(F.col("resultado") == "SEM_IRREGULARIDADE").count(), 518)
confere("Casos declarados como NADA CONSTA", silver.filter("resultado_declarado_nada_consta").count(), 22)
confere("Datas ambíguas no lote consolidado", silver.filter("data_ambigua").count(), 11)
confere("Datas futuras", silver.filter(F.col("data") > F.current_date()).count(), 0)
confere("Total de inspetores únicos após trim", silver.select("inspetor").distinct().count(), 40)

# COMMAND ----------

# DBTITLE 1,5. Gravação
grava_silver(silver, quarentena, "inspecoes")
finaliza()
