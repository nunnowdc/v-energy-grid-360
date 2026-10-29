# Databricks notebook source
# MAGIC %md
# MAGIC # 04 · Gold · Dimensões
# MAGIC
# MAGIC Consolidação das tabelas dimensionais analíticas da camada Gold, integrando cadastro saneado,
# MAGIC histórico e estado de medidores, centrais de microgeração distribuída (GD), circuitos alimentadores
# MAGIC e o calendário de competências com bandeiras tarifárias.
# MAGIC
# MAGIC | Tabela | Grão | Origem | Destaques |
# MAGIC |---|---|---|---|
# MAGIC | `dim_unidade_consumidora` | 1 linha por UC (45.000) | `silver_unidades_consumidoras` + medidores + GD | Espinha dorsal da Visão 360; documento mascarado (LGPD); consolida medidor ativo, histórico de troca e GD |
# MAGIC | `dim_alimentador` | 1 linha por alimentador (122) | `dim_unidade_consumidora` | Município principal determinístico (G-02); perfil de classes atendidas e flag `alimentador_pequeno` |
# MAGIC | `dim_medidor` | 1 linha por medidor (51.299) | `silver_medidores` | 45.000 ativos + 6.299 retirados na campanha de modernização; tipos e datas saneados |
# MAGIC | `dim_geracao_distribuida` | 1 linha por UC com GD (3.503) | `silver_geracao_distribuida` | Potência ajustada (W -> kW) e injeção estimada reestimada pela razão real da base (~34 kWh/kWp·mês) |
# MAGIC | `dim_competencia` | 1 linha por mês (48) | `silver_faturas` | Calendário analítico (jul/2022 a jun/2026) com bandeiras tarifárias e marcos do diagnóstico de receita |

# COMMAND ----------

# MAGIC %run ../00_utils

# COMMAND ----------

# DBTITLE 1,1. dim_geracao_distribuida
# Leitura da Silver de GD saneada
gd_sil = le_silver("geracao_distribuida")

# Reestimativa da injeção: GDs que vieram com kWp x 110 exato são reestimadas pela mediana da base (~34 kWh/kWp)
dim_gd = (gd_sil
    .withColumn("energia_reestimada_kwh",
                F.when(F.col("energia_estimada"), F.round(F.col("potencia_kwp") * 34.0, 2))
                 .otherwise(F.col("energia_injetada_kwh_media_mensal")))
    .select(
        "id_uc",
        "potencia_kwp",
        "potencia_corrigida_unidade",
        "data_conexao",
        "modalidade",
        "energia_injetada_kwh_media_mensal",
        "energia_estimada",
        "energia_reestimada_kwh",
        "kwh_por_kwp_mes",
        F.current_timestamp().alias("_processado_em")
    )
)

n_gd = grava_gold(dim_gd, "dim_geracao_distribuida")
confere("dim_geracao_distribuida (esperado 3.503 GDs válidas)", n_gd, 3503)

# COMMAND ----------

# DBTITLE 1,2. dim_medidor
med_sil = le_silver("medidores")

dim_med = (med_sil
    .select(
        "id_medidor",
        "id_uc",
        "modelo",
        "tipo",
        "data_instalacao",
        "data_retirada",
        "status",
        "medidor_atual",
        "data_ultima_manutencao",
        F.current_timestamp().alias("_processado_em")
    )
)

n_med = grava_gold(dim_med, "dim_medidor")
confere("dim_medidor (45.000 atuais + 6.299 retirados)", n_med, 51299)

# COMMAND ----------

# DBTITLE 1,3. dim_competencia
# Construção do calendário analítico de 48 meses a partir do faturamento
fat_sil = le_silver("faturas")

# Intervalos de diagnóstico definidos para a diretoria comercial
# P0: primeiro ano (jul/2022 a jun/2023) | P1: últimos 12 meses (jul/2025 a jun/2026)
c_min, c_max = fat_sil.agg(F.min("competencia"), F.max("competencia")).first()
p0_ini, p0_fim = c_min, soma_meses(c_min, 11)
p1_ini, p1_fim = soma_meses(c_max, -11), c_max

dim_comp = (fat_sil
    .groupBy("competencia", "mes_referencia", "bandeira_tarifaria")
    .agg(F.count("*").alias("_qtd_faturas"))
    .withColumn("ano", F.year("competencia"))
    .withColumn("mes", F.month("competencia"))
    .withColumn("trimestre", F.quarter("competencia"))
    .withColumn("periodo_diagnostico",
                F.when(F.col("competencia").between(p0_ini, p0_fim), F.lit("PRIMEIRO_ANO"))
                 .when(F.col("competencia").between(p1_ini, p1_fim), F.lit("ULTIMOS_12M"))
                 .otherwise(None))
    .select(
        "competencia",
        "mes_referencia",
        "ano",
        "mes",
        "trimestre",
        "bandeira_tarifaria",
        "periodo_diagnostico",
        F.current_timestamp().alias("_processado_em")
    )
    .orderBy("competencia")
)

n_comp = grava_gold(dim_comp, "dim_competencia")
confere("dim_competencia (48 competências jul/2022 a jun/2026)", n_comp, 48)

# COMMAND ----------

# DBTITLE 1,4. dim_unidade_consumidora (Visão 360)
ucs_sil = le_silver("unidades_consumidoras")

# Informações do medidor ativo
med_ativo = (med_sil
    .filter("medidor_atual")
    .select(
        F.col("id_uc"),
        F.col("id_medidor").alias("id_medidor_atual"),
        F.col("tipo").alias("tipo_medidor_atual"),
        F.col("modelo").alias("modelo_medidor_atual"),
        F.col("data_instalacao").alias("data_instalacao_medidor_atual")
    )
)

# Informações da última troca de medidor
w_troca = Window.partitionBy("id_uc").orderBy(F.col("data_retirada").desc())
ult_troca = (med_sil
    .filter(F.col("data_retirada").isNotNull())
    .withColumn("_rn", F.row_number().over(w_troca))
    .filter("_rn = 1")
    .select(
        F.col("id_uc"),
        F.lit(True).alias("trocou_medidor"),
        F.col("data_retirada").alias("data_ultima_troca_medidor"),
        F.col("tipo").alias("tipo_medidor_anterior")
    )
)

# Informações de geração distribuída
gd_info = (dim_gd
    .select(
        F.col("id_uc"),
        F.lit(True).alias("possui_gd"),
        F.col("data_conexao").alias("data_conexao_gd"),
        F.col("potencia_kwp").alias("potencia_gd_kwp"),
        F.col("modalidade").alias("modalidade_gd")
    )
)

# Mascaramento LGPD: oculta todos os dígitos do CPF/CNPJ exceto os 4 últimos
cpf_mascarado = F.when(
    F.col("cpf_cnpj").isNotNull(),
    F.concat(F.lit("*******"), F.substring(F.col("cpf_cnpj"), -4, 4))
).otherwise(None)

dim_uc = (ucs_sil
    .join(med_ativo, "id_uc", "left")
    .join(ult_troca, "id_uc", "left")
    .join(gd_info, "id_uc", "left")
    .withColumn("cpf_cnpj_mascarado", cpf_mascarado)
    .withColumn("trocou_medidor", F.coalesce("trocou_medidor", F.lit(False)))
    .withColumn("possui_gd", F.coalesce("possui_gd", F.lit(False)))
    .withColumn("cadastro_conflitante", F.coalesce("cadastro_conflitante", F.lit(False)))
    .select(
        "id_uc",
        "nome_titular",
        "cpf_cnpj_mascarado",
        "tipo_pessoa",
        "logradouro",
        "numero",
        "bairro",
        "municipio",
        "uf",
        "cep",
        "latitude",
        "longitude",
        "classe",
        "subgrupo_tarifario",
        "alimentador",
        "data_ligacao",
        "status",
        "possui_gd",
        "data_conexao_gd",
        "potencia_gd_kwp",
        "modalidade_gd",
        "id_medidor_atual",
        "tipo_medidor_atual",
        "modelo_medidor_atual",
        "data_instalacao_medidor_atual",
        "trocou_medidor",
        "data_ultima_troca_medidor",
        "tipo_medidor_anterior",
        "cadastro_conflitante",
        F.current_timestamp().alias("_processado_em")
    )
)

n_uc = grava_gold(dim_uc, "dim_unidade_consumidora")
confere("dim_unidade_consumidora (45.000 UCs ativas)", n_uc, 45000)
confere("UCs com medidor atual associado", dim_uc.filter(F.col("id_medidor_atual").isNotNull()).count(), 45000)
confere("UCs com GD identificadas", dim_uc.filter("possui_gd").count(), 3503)
confere("UCs que trocaram de medidor", dim_uc.filter("trocou_medidor").count(), 6299)

# COMMAND ----------

# DBTITLE 1,5. dim_alimentador
# Determinação determinística do município principal (corrige G-02)
w_mun = Window.partitionBy("alimentador").orderBy(F.col("count").desc(), F.col("municipio").asc())
mun_rank = (dim_uc
    .groupBy("alimentador", "municipio")
    .count()
    .withColumn("_rn", F.row_number().over(w_mun))
    .filter("_rn = 1")
    .select("alimentador", F.col("municipio").alias("municipio_principal"))
)

# Agregações de perfil cadastral por alimentador
dim_alim = (dim_uc
    .groupBy("alimentador")
    .agg(
        F.count("*").alias("total_ucs"),
        F.countDistinct("municipio").alias("qtd_municipios"),
        F.countDistinct("bairro").alias("qtd_bairros"),
        F.sum((F.col("classe") == "RESIDENCIAL").cast("int")).alias("ucs_residencial"),
        F.sum((F.col("classe") == "COMERCIAL").cast("int")).alias("ucs_comercial"),
        F.sum((F.col("classe") == "INDUSTRIAL").cast("int")).alias("ucs_industrial"),
        F.sum((F.col("classe") == "RURAL").cast("int")).alias("ucs_rural"),
        F.sum((F.col("classe") == "PODER_PUBLICO").cast("int")).alias("ucs_poder_publico")
    )
    .join(mun_rank, "alimentador", "inner")
    .withColumn("regiao", F.split(F.col("alimentador"), "-").getItem(1))
    .withColumn("alimentador_pequeno", F.col("total_ucs") < 100)
    .select(
        "alimentador",
        "total_ucs",
        "qtd_municipios",
        "qtd_bairros",
        "ucs_residencial",
        "ucs_comercial",
        "ucs_industrial",
        "ucs_rural",
        "ucs_poder_publico",
        "municipio_principal",
        "regiao",
        "alimentador_pequeno",
        F.current_timestamp().alias("_processado_em")
    )
)

n_alim = grava_gold(dim_alim, "dim_alimentador")
confere("dim_alimentador (122 circuitos)", n_alim, 122)
confere("Soma das UCs nos alimentadores = 45.000", dim_alim.agg(F.sum("total_ucs")).first()[0], 45000)

finaliza()
