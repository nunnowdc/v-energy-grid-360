# Databricks notebook source
# MAGIC %md
# MAGIC ## Tratamento da camada silver para as tabelas de leitura
# MAGIC
# MAGIC Notebook feito com base nas tabelas leituras_2022 à leituras_2026 presentes na base de dados original.

# COMMAND ----------

# MAGIC %md
# MAGIC ### 1 - Carregamento de tabelas em dataframes

# COMMAND ----------

#imports
from pyspark.sql import functions as F
from pyspark.sql.window import Window
from functools import reduce

# COMMAND ----------

path = "`v-energy`.bronze_schema.bronze_leituras"

df_leit_bronze = spark.table(path)
_latest_leit = df_leit_bronze.select(F.max("_ingestion_timestamp")).head()[0]
df_leit_bronze = df_leit_bronze.filter(F.col("_ingestion_timestamp") == _latest_leit)

print(f"total de linhas: {df_leit_bronze.count()}")
display(df_leit_bronze.limit(10))

# COMMAND ----------

# MAGIC %md
# MAGIC ### 2 - Tratemento de id_leitura

# COMMAND ----------

# DBTITLE 1,verificando ids duplicados
dup_id_leit = df_leit_bronze.groupBy("id_leitura").count().filter(F.col("count") > 1)

display(dup_id_leit)

# COMMAND ----------

# MAGIC %md
# MAGIC Tendo em vista que temos ids duplicados, temos que verificar como esses dados aparecem na tabela original para só então decidir o que faremos com ele.

# COMMAND ----------

# DBTITLE 1,Investigação de linhas com id_leitura duplicado
w_dup = Window.partitionBy("id_leitura")

duplicated_rows = (
    df_leit_bronze
      .withColumn("n_duplicatas", F.count("*").over(w_dup))
      .filter(F.col("n_duplicatas") > 1)
)

print(f"total de linhas envolvidas em ids duplicados: {duplicated_rows.count()}")
display(duplicated_rows.orderBy("id_leitura").limit(50))

# COMMAND ----------

# MAGIC %md
# MAGIC veredito: as linhas com id duplicado são **EXATAMENTE** iguais em todas as colunas, ou seja, as ~43k de linhas que são duplicadas de ~21.5k ids, podem ser dropadas sem problemas.

# COMMAND ----------

df_leit_dedup = df_leit_bronze.dropDuplicates(["id_leitura"])
print(f"total de linhas: {df_leit_dedup.count()}")
display(df_leit_dedup.limit(10))

# COMMAND ----------

# DBTITLE 1,Cell 11
# MAGIC %md
# MAGIC ### 3 - Tratamento e verificação de id_uc 
# MAGIC
# MAGIC integridade referencial com unidades_consumidoras

# COMMAND ----------

# DBTITLE 1,Carregamento de bronze_unidades_consumidoras
uc_path = "`v-energy`.bronze_schema.bronze_unidades_consumidoras"

df_uc_bronze = spark.table(uc_path)
_latest_uc = df_uc_bronze.select(F.max("_ingestion_timestamp")).head()[0]
df_uc_bronze = df_uc_bronze.filter(F.col("_ingestion_timestamp") == _latest_uc)

print(f"total de unidades consumidoras: {df_uc_bronze.count()}")
display(df_uc_bronze.limit(10))

# COMMAND ----------

# DBTITLE 1,Verificações de integridade referencial de id_uc
# 1) id_uc nulo ou vazio em leituras (chave que não pode casar com nada)
nulos = df_leit_dedup.filter(F.col("id_uc").isNull() | (F.trim(F.col("id_uc")) == ""))
print(f"leituras com id_uc nulo/vazio: {nulos.count()}")

# 2) id_uc é de fato único (PK válido) em unidades_consumidoras?
dup_id_uc = df_uc_bronze.groupBy("id_uc").count().filter(F.col("count") > 1)
print(f"id_uc duplicados em unidades_consumidoras: {dup_id_uc.count()}")
display(dup_id_uc.limit(10))

# 3) Integridade referencial: id_uc de leituras sem correspondência em unidades_consumidoras
ucs_leituras = df_leit_dedup.select("id_uc").distinct()
ucs_orfas = ucs_leituras.join(df_uc_bronze.select("id_uc"), on="id_uc", how="left_anti")
print(f"id_uc distintos em leituras: {ucs_leituras.count()}")
print(f"id_uc órfãos (sem correspondência em unidades_consumidoras): {ucs_orfas.count()}")
display(ucs_orfas.limit(20))

# COMMAND ----------

# MAGIC %md
# MAGIC ### 3 - Tratamento e verificação de id_medidor
# MAGIC
# MAGIC integridade referencial com medidores

# COMMAND ----------

# DBTITLE 1,Carregamento de bronze_medidores
med_path = "`v-energy`.bronze_schema.bronze_medidores"

df_med_bronze = spark.table(med_path)
_latest_med = df_med_bronze.select(F.max("_ingestion_timestamp")).head()[0]
df_med_bronze = df_med_bronze.filter(F.col("_ingestion_timestamp") == _latest_med)

print(f"total de medidores: {df_med_bronze.count()}")
display(df_med_bronze.limit(100))

# COMMAND ----------

# DBTITLE 1,Verificações de integridade referencial de id_medidor
# 1) id_medidor nulo ou vazio em leituras (chave que não pode casar com nada)
nulos_med = df_leit_dedup.filter(F.col("id_medidor").isNull() | (F.trim(F.col("id_medidor")) == ""))
print(f"leituras com id_medidor nulo/vazio: {nulos_med.count()}")

# 2) id_medidor é de fato único (PK válido) em medidores?
dup_id_med = df_med_bronze.groupBy("id_medidor").count().filter(F.col("count") > 1)
print(f"id_medidor duplicados em medidores: {dup_id_med.count()}")
display(dup_id_med.limit(10))

# 3) Integridade referencial: id_medidor de leituras sem correspondência em medidores
meds_leituras = df_leit_dedup.select("id_medidor").distinct()
meds_orfas = meds_leituras.join(df_med_bronze.select("id_medidor"), on="id_medidor", how="left_anti")
print(f"id_medidor distintos em leituras: {meds_leituras.count()}")
print(f"id_medidor órfãos (sem correspondência em medidores): {meds_orfas.count()}")
display(meds_orfas.limit(20))

# COMMAND ----------

# MAGIC %md
# MAGIC Iremos quarentenar algumas das entradas dessa coluna já que o id_medidor não existe na tabela original de medidores, a medida de quarentena foi escolhida ao invés de simplesmente excluir os dados pois os registros que esses medidores representam correspondem a dados válidos.

# COMMAND ----------

# DBTITLE 1,### 4 - Quarentena das leituras com medidor órfão
# MAGIC %md
# MAGIC ### 4 - Tratamento de data_leitura

# COMMAND ----------

# MAGIC %md
# MAGIC primeiramente, vamos analisar os formatos presentes 

# COMMAND ----------

# DBTITLE 1,verificação de formatos de datas
fmt = (F.regexp_replace(F.regexp_replace(F.col("data_leitura"), "[0-9]", "9"), "[a-zA-Z]", "A"))

df_fmtos = (df_leit_dedup.withColumn("padrao", fmt)
    .groupBy("padrao")
    .agg(F.count("*").alias("qtd"),
         F.min("data_leitura").alias("exemplo_min"),
         F.max("data_leitura").alias("exemplo_max"),
         F.sum(F.col("data_leitura").isNull().cast("int")).alias("nulos"))
    .orderBy(F.desc("qtd")))

display(df_fmtos)

# COMMAND ----------

# DBTITLE 1,parsing de datas para o formato mais utlilzado atualmente
# Funcao de parsing da coluna data_leitura
# - 9999-99-99 (ISO) -> yyyy-MM-dd
# - 99.99.9999      -> dd.MM.yyyy
# - 99/99/9999      -> dd/MM/yyyy
# - 99-99-9999      -> ambiguo: dd-MM-yyyy OU MM-dd-yyyy
#     * 1o numero > 12  -> so pode ser dia (dd-MM)
#     * 2o numero > 12  -> so pode ser mes (MM-dd)
#     * ambos <= 12     -> desempata validando contra mes_referencia
from pyspark.sql import DataFrame

def parse_data_leitura(df: DataFrame) -> DataFrame:
    dl, mr = F.col("data_leitura"), F.col("mes_referencia")

    cand_dmy = F.to_date(dl, "dd-MM-yyyy")   # le como dia-mes-ano
    cand_mdy = F.to_date(dl, "MM-dd-yyyy")   # le como mes-dia-ano
    p1 = F.split(dl, "-").getItem(0).cast("int")
    p2 = F.split(dl, "-").getItem(1).cast("int")

    ambiguo = (
        F.when((p1 > 12) & (p2 <= 12), cand_dmy)                    # p1 so pode ser dia
        .when(p2 > 12, cand_mdy)                                     # p2 so pode ser mes
        .when(F.date_format(cand_dmy, "yyyy-MM") == mr, cand_dmy)    # desempata pelo mes de referencia
        .when(F.date_format(cand_mdy, "yyyy-MM") == mr, cand_mdy)
        .otherwise(None)                                             # invalido em ambas as leituras
    )

    return df.withColumn(
        "data_leitura_parsed",
        F.when(dl.rlike(r"^\d{4}-\d{2}-\d{2}$"), F.to_date(dl, "yyyy-MM-dd"))
        .when(dl.rlike(r"^\d{2}\.\d{2}\.\d{4}$"), F.to_date(dl, "dd.MM.yyyy"))
        .when(dl.rlike(r"^\d{2}/\d{2}/\d{4}$"), F.to_date(dl, "dd/MM/yyyy"))
        .when(dl.rlike(r"^\d{2}-\d{2}-\d{4}$"), ambiguo)
        .otherwise(None)
    )

# COMMAND ----------

# DBTITLE 1,verificando os resultados do parsing
df = parse_data_leitura(df_leit_dedup)
display(df.limit(100))

# COMMAND ----------

# DBTITLE 1,excluindo as colunas de data não parseadas
df = df.select("id_leitura", "id_uc", "id_medidor", "data_leitura_parsed", "mes_referencia", "leitura_anterior", "leitura_atual", "consumo_kwh", "tipo_leitura")
display(df.limit(10))

# COMMAND ----------

# MAGIC %md
# MAGIC ### Tratamento de mês referência

# COMMAND ----------

# MAGIC %md
# MAGIC Tendo em vista que essa coluna corresponde a uma informação de agregação e vendas, devemos mante-la afim de facilitar as leituras posteriores

# COMMAND ----------

# DBTITLE 1,verificando os formatos distintos
fmt = (F.regexp_replace(F.regexp_replace(F.col("mes_referencia"), "[0-9]", "9"), "[a-zA-Z]", "A"))

df_fmtos = (df.withColumn("padrao", fmt)
    .groupBy("padrao")
    .agg(F.count("*").alias("qtd"),
         F.sum(F.col("mes_referencia").isNull().cast("int")).alias("nulos"))
    .orderBy(F.desc("qtd")))

display(df_fmtos)
print(df.count())

# COMMAND ----------

# MAGIC %md
# MAGIC por sorte, a coluna só tem um formato atualmente, apesar disso, devemos aplicar o parsing para que entradas novas com valores em formatação diferente não quebrem ao entrar no pipeline.

# COMMAND ----------

# DBTITLE 1,parsing de mes_referencia
# Funcao de parsing da coluna mes_referencia
# - 9999-99 (yyyy-MM)  -> ano-mes
# - 9999/99, 9999.99   -> variantes de separador
# - 99-9999 (MM-yyyy)  -> mes-ano
# - 99/9999, 99.9999   -> variantes de separador
# Sem ambiguidade dia/mes: so ha 2 componentes, e o de 4 digitos so pode ser o ano.
# Desconhecido ou mes invalido -> NULL (sinal visivel para a quarentena; nesta
# computacao to_date/cast lancam excecao em valores fora do formato, entao a
# extracao via regex + guarda explicita e o caminho seguro)
from pyspark.sql import DataFrame

def parse_mes_referencia(df: DataFrame) -> DataFrame:
    mr = F.col("mes_referencia")

    # ano primeiro: yyyy[-/.]MM
    ano_am = F.regexp_extract(mr, r"^(\d{4})[-/.](\d{1,2})$", 1)
    mes_am = F.regexp_extract(mr, r"^(\d{4})[-/.](\d{1,2})$", 2)
    # mes primeiro: MM[-/.]yyyy
    mes_ma = F.regexp_extract(mr, r"^(\d{1,2})[-/.](\d{4})$", 1)
    ano_ma = F.regexp_extract(mr, r"^(\d{1,2})[-/.](\d{4})$", 2)

    data_am = F.to_date(F.concat(ano_am, F.lit("-"), F.lpad(mes_am, 2, "0"), F.lit("-01")), "yyyy-MM-dd")
    data_ma = F.to_date(F.concat(ano_ma, F.lit("-"), F.lpad(mes_ma, 2, "0"), F.lit("-01")), "yyyy-MM-dd")

    return df.withColumn(
        "mes_referencia_parsed",
        F.when((ano_am != "") & mes_am.cast("int").between(1, 12), F.date_format(data_am, "yyyy-MM"))
         .when((ano_ma != "") & mes_ma.cast("int").between(1, 12), F.date_format(data_ma, "yyyy-MM"))
         .otherwise(None)
    )

df = parse_mes_referencia(df)

# verificacao: nenhum mes deve falhar e nenhum valor deve mudar
verif_mes = df.select("mes_referencia", "mes_referencia_parsed")
print(f"meses nao parseados: {verif_mes.filter(F.col('mes_referencia_parsed').isNull()).count()}")
print(f"meses que mudaram de valor: {verif_mes.filter(F.col('mes_referencia') != F.col('mes_referencia_parsed')).count()}")
display(df.limit(10))

# COMMAND ----------

# MAGIC %md
# MAGIC ### Tratamento de leitura_anterior

# COMMAND ----------

# DBTITLE 1,parsing de leitura_anterior (sentinela -1 -> NULL)
# Tratamento de leitura_anterior
# Valores "-1" sao sentinelas que significam leitura anterior ausente -> NULL.
# A coluna tambem carrega marcadores literais ('NULL', 'N/A'); o parse numerico
# usa try_cast porque nesta computacao cast comum lanca excecao em nao-numericos.
# Tipo double para manter consistencia com o silver antigo (bronze_to_silver).
from pyspark.sql import DataFrame

def parse_leitura_anterior(df: DataFrame) -> DataFrame:
    la = F.trim(F.col("leitura_anterior"))
    return df.withColumn(
        "leitura_anterior_parsed",
        F.when(la == "-1", F.lit(None).cast("double"))
         .otherwise(F.expr("try_cast(leitura_anterior AS double)"))
    )

df = parse_leitura_anterior(df)

# verificacao: decomposicao das causas de NULL e integridade dos numericos
verif_la = df.select("leitura_anterior", "leitura_anterior_parsed")
la_trim = F.trim(F.col("leitura_anterior"))
print(f"total de linhas: {verif_la.count()}")
print(f"sentinelas -1 convertidas para NULL: {verif_la.filter(la_trim == '-1').count()}")
print(f"marcadores literais 'NULL': {verif_la.filter(la_trim == 'NULL').count()}")
print(f"marcadores 'N/A': {verif_la.filter(la_trim == 'N/A').count()}")
print(f"valores numericos parseados: {verif_la.filter(F.col('leitura_anterior_parsed').isNotNull()).count()}")
print(f"parsed <= 0 (deve ser 0): {verif_la.filter(F.col('leitura_anterior_parsed') <= 0).count()}")
inesperados = verif_la.filter(
    F.col("leitura_anterior_parsed").isNull()
    & F.col("leitura_anterior").isNotNull()
    & ~la_trim.isin("-1", "NULL", "N/A")
)
print(f"nao numericos inesperados (fora dos marcadores conhecidos): {inesperados.count()}")
display(inesperados.limit(20))

# COMMAND ----------

display(df.where("leitura_anterior_parsed IS NULL").select("leitura_anterior", "leitura_anterior_parsed"))

# COMMAND ----------

# MAGIC %md
# MAGIC ### Tratamento de leitura_atual

# COMMAND ----------

# MAGIC %md
# MAGIC Essa coluna tem dados muito limpos, um simples try_cast como forma de parsing funciona perfeitamente e evita over engineering.

# COMMAND ----------

# DBTITLE 1,try_cast in-place de leitura_atual
# try_cast direto (in-place): sem sentinelas nem marcadores nesta coluna, uma
# funcao de parsing nao agrega nada. Nota: try_cast e funcao SQL, nao metodo do
# DataFrame (df.try_cast nao existe — causa do erro anterior); o trim evita que
# espacos acidentais gerem falsos NULLs em dados futuros.
df = df.withColumn("leitura_atual", F.expr("try_cast(trim(leitura_atual) AS double)"))

# limpeza: remove a coluna da versao anterior do tratamento (com funcao de
# parsing), caso ainda exista no estado atual do kernel; em re-execucao limpa
# e um no-op
if "leitura_atual_parsed" in df.columns:
    df = df.drop("leitura_atual_parsed")

# verificacao
verif_latu = df.select("leitura_atual")
print(f"linhas: {verif_latu.count()}")
print(f"nulos (dados fora do padrao): {verif_latu.filter(F.col('leitura_atual').isNull()).count()}")
print(f"valores <= 0: {verif_latu.filter(F.col('leitura_atual') <= 0).count()}")
verif_latu.select(F.min("leitura_atual").alias("min"), F.max("leitura_atual").alias("max")).show()
display(df.limit(10))

# COMMAND ----------

# MAGIC %md
# MAGIC ### Tratamento de consumo_kwh

# COMMAND ----------

# DBTITLE 1,tratamento de consumo_kwh (anula valores <= 0)
# Tratamento de consumo_kwh
# Achados da EDA (tabelas_leituras_visualizacao):
# - 100% numerico, porem NAO e derivavel de leitura_atual - leitura_anterior
#   (536k divergentes) -> o valor declarado e autoritativo, nao recalcular
# - ~8k linhas com consumo <= 0, em duas familias:
#   * gigante (< -500): reset/troca de medidor registrada como consumo
#     (min ~ -2.1 milhoes) — quebra qualquer soma/media
#   * pequeno (-500 a 0): retificacoes ou medicao liquida (geracao distribuida)
# - Correcao: valores <= 0 viram NULL na coluna tratada para nao contaminar
#   agregacoes; a coluna bruta fica como evidencia para a quarentena unificada
#   (rotulos tipo CONSUMO_ANOMALO / VIRADA_MEDIDOR)
ck_num = F.expr("try_cast(trim(consumo_kwh) AS double)")

df = df.withColumn(
    "consumo_kwh_parsed",
    F.when(ck_num <= 0, F.lit(None).cast("double"))
     .otherwise(ck_num)
)

# verificacao: decomposicao das causas de NULL e das familias anuladas
verif_ck = df.select("consumo_kwh", "consumo_kwh_parsed")
print(f"total de linhas: {verif_ck.count()}")
print(f"consumos validos (>0): {verif_ck.filter(F.col('consumo_kwh_parsed') > 0).count()}")
print(f"consumos <= 0 anulados: {verif_ck.filter(ck_num <= 0).count()}")
print(f"nulos brutos: {verif_ck.filter(F.col('consumo_kwh').isNull()).count()}")
print(f"nao numericos inesperados: {verif_ck.filter(F.col('consumo_kwh').isNotNull() & ck_num.isNull()).count()}")
verif_ck.filter(ck_num <= 0) \
    .withColumn("familia", F.when(ck_num >= -500, "pequeno (-500 a 0)").otherwise("gigante (< -500)")) \
    .groupBy("familia") \
    .agg(F.count("*").alias("qtd"),
         F.round(F.min(ck_num), 0).alias("min_kwh"),
         F.round(F.max(ck_num), 0).alias("max_kwh")).show()
display(df.limit(10))

# COMMAND ----------

# DBTITLE 1,### Tratamento de tipo_leitura
# MAGIC %md
# MAGIC ### Tratamento de tipo_leitura
# MAGIC

# COMMAND ----------

# DBTITLE 1,tratamento de tipo_leitura (normalizacao + whitelist)
# Tratamento de tipo_leitura
# EDA: exatamente 2 valores brutos — REAL (~1.78M) e ESTIMADA (~396k) — ja
# limpos (0 variantes graficas, 0 espacos extras, 0 acentos).
# Mesmo assim, normalizacao defensiva (mesma logica testada na EDA):
#   trim -> upper -> translate de acentos
# e whitelist canonica {REAL, ESTIMADA}: variantes graficas futuras sao
# normalizadas (ex.: "real ", "Real", "REAÉL" -> "REAL"); categoria
# desconhecida vira NULL — sinal visivel para a quarentena
# (TIPO_LEITURA_DESCONHECIDO). Coluna bruta mantida como evidencia.
tl_norm = F.translate(F.trim(F.upper(F.col("tipo_leitura"))),
                      "\u00e1\u00e0\u00e2\u00e3\u00e9\u00ea\u00ed\u00f3\u00f4\u00f5\u00fa\u00fc\u00e7",
                      "aaaaeeiooouuc")

df = df.withColumn(
    "tipo_leitura_parsed",
    F.when(tl_norm == "REAL", "REAL")
     .when(tl_norm == "ESTIMADA", "ESTIMADA")
     .otherwise(None)
)

# verificacao
verif_tl = df.select("tipo_leitura", "tipo_leitura_parsed")
print(f"total de linhas: {verif_tl.count()}")
print(f"valores brutos distintos: {verif_tl.select('tipo_leitura').distinct().count()}")
verif_tl.groupBy("tipo_leitura", "tipo_leitura_parsed").count().show()
print(f"desconhecidos -> NULL (deve ser 0): {verif_tl.filter(F.col('tipo_leitura').isNotNull() & F.col('tipo_leitura_parsed').isNull()).count()}")
print(f"nulos brutos: {verif_tl.filter(F.col('tipo_leitura').isNull()).count()}")
display(df.limit(10))

# COMMAND ----------

# DBTITLE 1,### 5 - Silver final e quarentena unificada
# MAGIC %md
# MAGIC ### 5 - Silver final e quarentena unificada
# MAGIC
# MAGIC Decisões registradas:
# MAGIC
# MAGIC - `mes_referencia`: STRING `yyyy-MM` (consistência com o restante das tabelas silver)
# MAGIC - Quarentena: SOMENTE leituras com medidor órfão (série MD9/LTX) — registros válidos com vínculo de medidor inresolvível. Leituras com `leitura_anterior` nula ou `consumo_kwh <= 0` permanecem na silver com os valores nulos aplicados nos tratamentos anteriores
# MAGIC - Estrutura da quarentena: como a antiga (colunas tipadas + `consumo_bruto`/`diff_leitura` + `status_qualidade_leitura`), porém construída pós-dedup (ids únicos) e com rótulo específico por causa

# COMMAND ----------

# DBTITLE 1,montagem da silver final e da quarentena unificada
# quarentena unificada: leituras com medidor orfao (rotulo especifico por causa)
leituras_quarentena = (
    df.join(meds_orfas, on="id_medidor", how="inner")
    .select(
        "id_leitura", "id_uc", "id_medidor",
        F.col("data_leitura_parsed").alias("data_leitura"),
        F.col("mes_referencia_parsed").alias("mes_referencia"),
        F.col("leitura_anterior_parsed").alias("leitura_anterior"),
        "leitura_atual",
        F.col("consumo_kwh_parsed").alias("consumo_kwh"),
        F.col("tipo_leitura_parsed").alias("tipo_leitura"),
        # evidencia: valor bruto declarado na origem (antes da anulacao de <= 0)
        F.expr("try_cast(trim(consumo_kwh) AS double)").alias("consumo_bruto"),
        # evidencia: diferenca entre leituras (calculo antigo da quarentena)
        (F.col("leitura_atual") - F.col("leitura_anterior_parsed")).alias("diff_leitura"),
        F.lit("MEDIDOR_NAO_CADASTRADO").alias("status_qualidade_leitura"),
    )
)

# silver final: todo o resto, colunas canonicas (sem sufixo _parsed)
silver_leituras_final = (
    df.join(meds_orfas, on="id_medidor", how="left_anti")
    .select(
        "id_leitura", "id_uc", "id_medidor",
        F.col("data_leitura_parsed").alias("data_leitura"),
        F.col("mes_referencia_parsed").alias("mes_referencia"),
        F.col("leitura_anterior_parsed").alias("leitura_anterior"),
        "leitura_atual",
        F.col("consumo_kwh_parsed").alias("consumo_kwh"),
        F.col("tipo_leitura_parsed").alias("tipo_leitura"),
    )
)

# verificacao
print(f"total tratado: {df.count()}")
print(f"quarentena: {leituras_quarentena.count()} linhas")
print(f"silver final: {silver_leituras_final.count()} linhas")
print(f"soma fecha: {leituras_quarentena.count() + silver_leituras_final.count()}")
print(f"id_leitura duplicados na quarentena: {leituras_quarentena.count() - leituras_quarentena.select('id_leitura').distinct().count()}")
print(f"id_leitura duplicados na silver: {silver_leituras_final.count() - silver_leituras_final.select('id_leitura').distinct().count()}")
print("\nrotulos na quarentena:")
leituras_quarentena.groupBy("status_qualidade_leitura").count().show()
print("nulos por coluna na silver final (esperado: apenas leitura_anterior e consumo_kwh):")
silver_leituras_final.select([F.sum(F.col(c).isNull().cast("int")).alias(c) for c in silver_leituras_final.columns]).show()
display(silver_leituras_final.limit(10))

# COMMAND ----------

# DBTITLE 1,gravacao das tabelas silver finais
# gravacao das tabelas silver (substitui as versoes do bronze_to_silver)
# Nota: sem overwriteSchema, o saveAsTable com mode("overwrite") PRESERVA o
# schema antigo da tabela (insert by-name) — a silver herdaria as colunas
# consumo_bruto/diff_leitura/status_qualidade_leitura antigas, todas NULL.
# overwriteSchema=true faz o CREATE OR REPLACE com o schema novo.
silver_leituras_final.write.mode("overwrite").option("overwriteSchema", "true") \
    .saveAsTable("`v-energy`.silver_schema.silver_leituras")
leituras_quarentena.write.mode("overwrite").option("overwriteSchema", "true") \
    .saveAsTable("`v-energy`.silver_schema.silver_leituras_quarentena")

# verificacao: leitura de volta
v_silver = spark.table("`v-energy`.silver_schema.silver_leituras")
v_quar = spark.table("`v-energy`.silver_schema.silver_leituras_quarentena")
print(f"silver_leituras lida de volta: {v_silver.count()} linhas, {len(v_silver.columns)} colunas")
print(f"silver_leituras_quarentena lida de volta: {v_quar.count()} linhas, {len(v_quar.columns)} colunas")
assert v_silver.columns == silver_leituras_final.columns, f"schema divergente: {v_silver.columns}"
assert v_quar.columns == leituras_quarentena.columns, f"schema divergente: {v_quar.columns}"
print("\nschema da silver final:")
v_silver.printSchema()
print("\nschema da quarentena:")
v_quar.printSchema()
v_quar.groupBy("status_qualidade_leitura").count().show()