# Databricks notebook source
# MAGIC %md
# MAGIC # 02 · Silver · Unidades Consumidoras
# MAGIC
# MAGIC **Entrada:** `bronze_unidades_consumidoras` · **Saída:** `silver_unidades_consumidoras` + `silver_unidades_consumidoras_quarentena`
# MAGIC
# MAGIC É a **referência de integridade** de todas as outras Silvers: um `id_uc` só é válido se estiver aqui.
# MAGIC Regras tiradas de `perfil_unidades_consumidoras.md` (seção 3) e `registro_de_problemas.md`:
# MAGIC
# MAGIC | # | Problema na fonte | Regra | Destino |
# MAGIC |---|---|---|---|
# MAGIC | 1 | Cabeçalho repetido (1) | Remover | Descarte |
# MAGIC | 2 | Espaços e nulos disfarçados | `limpa_texto` em todas as colunas | Silver |
# MAGIC | 3 | 900 linhas idênticas | `dropDuplicates` depois da padronização | Descarte |
# MAGIC | 4 | 200 registros `TESTE…` (CPF `000…`) | `id_uc` fora de `^UC[0-9]{6}$` | Quarentena `REGISTRO_TESTE` |
# MAGIC | 5 | 360 UCs com cadastro conflitante | Uma versão fica (critério abaixo), as outras vão para a quarentena; flag `cadastro_conflitante` | Silver + quarentena `DUPLICATA_CONFLITANTE` |
# MAGIC | 6 | CPF/CNPJ em 4 formatos | Só dígitos + `tipo_pessoa` (PF/PJ) + `cpf_cnpj_valido` | Silver |
# MAGIC | 7 | UF em 5 grafias | Variantes conhecidas viram `PE`; valor desconhecido é mantido e marcado | Silver |
# MAGIC | 8 | Classe com caixa e acento variados | 5 classes: RESIDENCIAL, COMERCIAL, INDUSTRIAL, RURAL, PODER_PUBLICO | Silver |
# MAGIC | 9 | Mojibake em 60 bairros (`InhamÃ£`) | `repara_encoding` (só onde há a assinatura do erro) | Silver |
# MAGIC | 10 | CEP com lixo (~1.383) | Válido = 8 dígitos começando com 50–56; senão `null` | Silver |
# MAGIC | 11 | 92 `data_ligacao` entre 1900 e 1948 | Vira `null` com `data_ligacao_invalida = true` | Silver |
# MAGIC
# MAGIC **Critério provisório para o cadastro conflitante (item 5):** a perfilagem da célula 8a ainda não disse se
# MAGIC as divergências são de escrita ou de titular. A deduplicação já ignora diferenças de escrita no nome
# MAGIC (compara pelo nome normalizado). Entre versões realmente diferentes, fica a de **CPF/CNPJ válido** e, em
# MAGIC seguida, a de **nome mais completo**. As demais vão para a quarentena, para auditoria.

# COMMAND ----------

# MAGIC %run ../00_utils

# COMMAND ----------

# DBTITLE 1,1. Leitura da Bronze
bruto = remove_cabecalho(ler_bronze("bronze_unidades_consumidoras"), "id_uc")
n_bruto = bruto.count()
confere("Linhas da Bronze (último lote, sem cabeçalho)", n_bruto, 46460)

# COMMAND ----------

# DBTITLE 1,2. Limpeza de texto e padronização
uc = bruto.select([limpa_texto(c).alias(c) for c in bruto.columns])

cpf_digitos = F.regexp_replace("cpf_cnpj", "[^0-9]", "")
cep_digitos = F.regexp_replace("cep", "[^0-9]", "")
classe_n = normaliza("classe")
uf_n = normaliza("uf")
dt_lig = parse_data("data_ligacao")

uc = (uc
    .withColumn("id_uc", F.upper("id_uc"))

    # 6. CPF/CNPJ
    .withColumn("cpf_cnpj", F.when(F.length(cpf_digitos) > 0, cpf_digitos))
    .withColumn("tipo_pessoa", F.when(F.length("cpf_cnpj") == 11, "PF")
                                .when(F.length("cpf_cnpj") == 14, "PJ"))
    .withColumn("cpf_cnpj_valido", F.coalesce(
        F.col("tipo_pessoa").isNotNull() & ~F.col("cpf_cnpj").rlike("^([0-9])\\1+$"), F.lit(False)))

    # 9. Encoding (bairro é a coluna afetada; as outras de texto livre ficam protegidas)
    .withColumn("bairro", repara_encoding("bairro"))
    .withColumn("municipio", repara_encoding("municipio"))
    .withColumn("logradouro", repara_encoding("logradouro"))
    .withColumn("nome_titular", repara_encoding("nome_titular"))

    # 7. UF
    .withColumn("uf", F.when(uf_n.isin("PE", "PERNAMBUCO", "P E"), F.lit("PE")).otherwise(F.upper("uf")))

    # 8. Classe
    .withColumn("classe", F.when(classe_n.contains("RESIDENCIAL"), "RESIDENCIAL")
                           .when(classe_n.contains("COMERCIAL"), "COMERCIAL")
                           .when(classe_n.contains("INDUSTRIAL"), "INDUSTRIAL")
                           .when(classe_n.contains("RURAL"), "RURAL")
                           .when(classe_n.contains("PODER PUBLICO"), "PODER_PUBLICO")
                           .otherwise(classe_n))
    .withColumn("subgrupo_tarifario", F.upper("subgrupo_tarifario"))
    .withColumn("alimentador", F.upper("alimentador"))
    .withColumn("status", normaliza("status"))

    # 10. CEP
    .withColumn("cep", F.when((F.length(cep_digitos) == 8)
                              & F.substring(cep_digitos, 1, 2).between("50", "56"), cep_digitos))

    # 11. Data de ligação (o flag é calculado antes de substituir a coluna)
    .withColumn("data_ligacao_invalida", F.coalesce(
        (dt_lig < F.lit("1950-01-01").cast("date")) | (dt_lig > F.current_date())
        | (F.col("data_ligacao").isNotNull() & dt_lig.isNull()), F.lit(False)))
    .withColumn("data_ligacao", F.when(~F.col("data_ligacao_invalida"), dt_lig))

    # Coordenadas
    .withColumn("latitude", to_num("latitude"))
    .withColumn("longitude", to_num("longitude"))
)

COLUNAS = ["id_uc", "cpf_cnpj", "tipo_pessoa", "cpf_cnpj_valido", "nome_titular", "logradouro", "numero",
           "bairro", "municipio", "uf", "cep", "classe", "subgrupo_tarifario", "alimentador",
           "data_ligacao", "data_ligacao_invalida", "status", "latitude", "longitude"]
uc = uc.select(*COLUNAS)

# COMMAND ----------

# DBTITLE 1,3. Duplicatas exatas (depois da padronização)
# O nome entra pela versão normalizada: 'Maria da Silva' e 'MARIA DA SILVA ' contam como a mesma linha.
uc = (uc.withColumn("_nome_chave", normaliza("nome_titular"))
        .dropDuplicates([c for c in COLUNAS if c != "nome_titular"] + ["_nome_chave"])
        .drop("_nome_chave"))
print(f"Depois de remover duplicatas exatas: {uc.count():,} linhas")

# COMMAND ----------

# DBTITLE 1,4. Quarentena: registros inválidos e de teste
ok, q_invalidos = separa_quarentena(uc, [
    (F.col("id_uc").isNull(), "ID_UC_AUSENTE"),
    (~F.col("id_uc").rlike("^UC[0-9]{6}$"), "REGISTRO_TESTE"),
])

# COMMAND ----------

# DBTITLE 1,5. Cadastro conflitante: uma versão por UC
por_uc = Window.partitionBy("id_uc")
prioridade = Window.partitionBy("id_uc").orderBy(
    F.col("cpf_cnpj_valido").desc(),
    F.length("nome_titular").desc_nulls_last(),
    F.col("nome_titular").asc_nulls_last(),
    F.col("cpf_cnpj").asc_nulls_last(),
)
ok = ok.withColumn("_versoes", F.count("*").over(por_uc)).withColumn("_ordem", F.row_number().over(prioridade))

q_conflito = (ok.filter("_ordem > 1").drop("_versoes", "_ordem")
                .withColumn("motivo_quarentena", F.lit("DUPLICATA_CONFLITANTE")))
silver = (ok.filter("_ordem = 1")
            .withColumn("cadastro_conflitante", F.col("_versoes") > 1)
            .drop("_versoes", "_ordem"))

quarentena = q_invalidos.unionByName(q_conflito.withColumn("cadastro_conflitante", F.lit(True)),
                                     allowMissingColumns=True)

# COMMAND ----------

# DBTITLE 1,6. Conferências antes de gravar
n = silver.count()
confere("UCs na Silver", n, 45000)
confere("id_uc único", silver.select("id_uc").distinct().count(), n)
confere("Classes fora do domínio", silver.filter(~F.col("classe").isin(
    "RESIDENCIAL", "COMERCIAL", "INDUSTRIAL", "RURAL", "PODER_PUBLICO")).count(), 0)
confere("UF diferente de PE", silver.filter(F.col("uf") != "PE").count(), 0)
confere("Bairros ainda com mojibake", silver.filter(F.col("bairro").rlike(_MOJIBAKE)).count(), 0)
confere("UCs com cadastro conflitante (mantidas com flag)", silver.filter("cadastro_conflitante").count(), ok=True)
confere("Data de ligação inválida (esperado ~92)", silver.filter("data_ligacao_invalida").count(), ok=True)
confere("CEP nulo/inválido (esperado ~1.3 mil)", silver.filter(F.col("cep").isNull()).count(), ok=True)
confere("CPF/CNPJ inválido", silver.filter(~F.col("cpf_cnpj_valido")).count(), ok=True)

print("\nDistribuição de classe e subgrupo:")
display(silver.groupBy("classe", "subgrupo_tarifario").count().orderBy("classe", "subgrupo_tarifario"))

# COMMAND ----------

# DBTITLE 1,7. Gravação
grava_silver(silver, quarentena, "unidades_consumidoras")
finaliza()
