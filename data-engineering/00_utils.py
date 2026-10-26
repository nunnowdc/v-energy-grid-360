# Databricks notebook source
# MAGIC %md
# MAGIC # 00 · Utils: funções compartilhadas do pipeline V-Energy Grid 360
# MAGIC
# MAGIC Incluído nas Silvers com `%run ./00_utils`. Concentra as regras que valem para mais de uma tabela,
# MAGIC para que uma correção seja feita num lugar só:
# MAGIC
# MAGIC | Função | Para quê | Decisão documentada |
# MAGIC |---|---|---|
# MAGIC | `limpa_texto` | `trim`, espaços repetidos e nulos disfarçados (`NULL`, `N/A`, `-`) viram `null` | S-04, S-OCO-03 |
# MAGIC | `normaliza` | Chave de comparação sem acento, maiúscula e sem pontuação | S-MED-04 |
# MAGIC | `repara_encoding` | Desfaz o mojibake (`InhamÃ£` → `Inhamã`) só onde há a assinatura do erro | S-UC-03 |
# MAGIC | `parse_data` | Datas em 4 formatos; o **traço é MM-dd-yyyy** (provado em medidores e faturas) | S-MED-01, S-FAT-05 |
# MAGIC | `to_num` | Números em formato BR/US/`R$` para double, sem quebrar no modo ANSI | S-02, S-FAT-02 |
# MAGIC | `ler_bronze` | Lê só o último lote da Bronze (proteção enquanto a Bronze fizer append) | B-01 |
# MAGIC | `separa_quarentena` / `grava_silver` | Padrão `silver_<t>` + `silver_<t>_quarentena` com `motivo_quarentena` | Arquitetura |

# COMMAND ----------

# DBTITLE 1,Parâmetros e schemas
import json
from pyspark.sql import functions as F, DataFrame, Column
from pyspark.sql.window import Window
from functools import reduce

dbutils.widgets.text("catalog", "v-energy", "Catálogo Unity")
# Para testar sem sobrescrever a Silver atual do time, rode com silver_schema = "silver_v2"
dbutils.widgets.text("silver_schema", "silver_schema", "Schema da Silver")
dbutils.widgets.text("gold_schema", "gold_schema", "Schema da Gold")
CATALOG = dbutils.widgets.get("catalog")
RAW = f"/Volumes/{CATALOG}/raw_data/raw_data"
BRONZE = f"`{CATALOG}`.bronze_schema"
SILVER = f"`{CATALOG}`.{dbutils.widgets.get('silver_schema')}"
GOLD = f"`{CATALOG}`.{dbutils.widgets.get('gold_schema')}"

for _s in (BRONZE, SILVER, GOLD):
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {_s}")
print(f"Raw: {RAW} | Bronze: {BRONZE} | Silver: {SILVER} | Gold: {GOLD}")

# Resumo da execução: cada conferência e gravação entra aqui, e o notebook termina devolvendo a lista
# (aparece no resultado da task do Workflow)
RESUMO = []

# COMMAND ----------

# DBTITLE 1,Texto
ACENTOS = "ÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇáàâãäéèêëíìîïóòôõöúùûüç"
SEM_ACE = "AAAAAEEEEIIIIOOOOOUUUUCaaaaaeeeeiiiiooooouuuuc"

# Valores que significam "não informado" nos dados brutos (comparados em minúsculas, depois do trim)
PLACEHOLDERS = ["", "null", "none", "nan", "n/a", "na", "-", "--", "?", "nulo",
                "sem informacao", "nao informado", "#n/d", "undefined"]


def _col(c):
    return F.col(c) if isinstance(c, str) else c


def limpa_texto(c) -> Column:
    """trim + espaços internos repetidos viram um só + nulos disfarçados viram null."""
    s = F.trim(F.regexp_replace(_col(c), "\\s+", " "))
    return F.when(s.isNull() | F.lower(s).isin(PLACEHOLDERS), F.lit(None).cast("string")).otherwise(s)


def normaliza(c) -> Column:
    """Chave de comparação: sem acento, MAIÚSCULA, pontuação vira espaço, espaços colapsados.
    Ex.: 'Eletro-Mecânico ' -> 'ELETRO MECANICO'."""
    s = F.upper(F.translate(_col(c), ACENTOS, SEM_ACE))
    s = F.regexp_replace(s, "[^A-Z0-9]", " ")
    return F.trim(F.regexp_replace(s, "\\s+", " "))


# Assinatura do mojibake: 'Ã' seguido de um byte de continuação UTF-8 lido como Latin-1 (U+0080 a U+00BF).
# 'InhamÃ£', 'BrasÃ­lia', 'Ãgua' batem; um 'SÃO' legítimo em maiúsculas NÃO bate (o 'O' está fora da faixa).
_MOJIBAKE = "Ã[\u0080-¿]"


def repara_encoding(c) -> Column:
    """Desfaz texto UTF-8 que foi lido como Latin-1. Só age onde há a assinatura do erro,
    porque aplicar o reparo num texto correto o estragaria."""
    x = _col(c)
    return F.when(x.rlike(_MOJIBAKE), F.decode(F.encode(x, "ISO-8859-1"), "UTF-8")).otherwise(x)

# COMMAND ----------

# DBTITLE 1,Datas
# Ordem PROVADA nos perfis (medidores célula 9, faturas célula 13):
#   traço  99-99-9999 -> MM-dd-yyyy (nunca o 1º número passa de 12)
#   barra  99/99/9999 -> dd/MM/yyyy
#   ponto  99.99.9999 -> dd.MM.yyyy
FORMATOS_DATA = ["yyyy-MM-dd", "dd/MM/yyyy", "dd.MM.yyyy", "MM-dd-yyyy"]
FORMATOS_TS = ["yyyy-MM-dd HH:mm:ss", "yyyy-MM-dd'T'HH:mm:ss", "yyyy-MM-dd HH:mm"]


def try_ts(c, formato: str) -> Column:
    """try_to_timestamp via SQL: devolve null em vez de quebrar no ANSI e funciona em qualquer versão do
    ambiente serverless (o F.try_to_date do PySpark não existe nos ambientes mais antigos dos Jobs)."""
    return F.call_function("try_to_timestamp", _col(c), F.lit(formato))


def try_data(c, formato: str) -> Column:
    return F.to_date(try_ts(c, formato))


def parse_data(c, formatos=FORMATOS_DATA) -> Column:
    """Primeiro formato que converter."""
    return F.coalesce(*[try_data(c, f) for f in formatos])


def parse_ts(c, formatos=FORMATOS_TS) -> Column:
    return F.coalesce(*[try_ts(c, f) for f in formatos])


def sentinela_para_nulo(c, sentinelas=("9999-12-31", "1900-01-01")) -> Column:
    """Datas-sentinela que significam 'não aconteceu / não informado' viram null."""
    x = _col(c)
    return F.when(x.isin(*sentinelas), F.lit(None).cast("string")).otherwise(x)

# COMMAND ----------

# DBTITLE 1,Números
def to_num(c) -> Column:
    """Texto numérico -> double.
    Aceita '1234.56', '1234,56', 'R$ 1.234,56', '1,234.56' e espaços.
    Qualquer coisa fora disso vira null. O cast só roda quando o regex garante um número válido,
    então nunca quebra no modo ANSI."""
    s = F.regexp_replace(F.trim(_col(c)), "(?i)r\\$|\\s", "")
    norm = (F.when(s.rlike("^-?[0-9]{1,3}(\\.[0-9]{3})+,[0-9]+$") | s.rlike("^-?[0-9]+,[0-9]+$"),
                   F.regexp_replace(F.regexp_replace(s, "\\.", ""), ",", "."))       # 1.234,56 / 1234,56
             .when(s.rlike("^-?[0-9]{1,3}(,[0-9]{3})+\\.[0-9]+$"),
                   F.regexp_replace(s, ",", ""))                                     # 1,234.56
             .otherwise(s))
    return F.when(norm.rlike("^-?[0-9]+(\\.[0-9]+)?$"), norm.cast("double"))

# COMMAND ----------

# DBTITLE 1,Leitura da Bronze
def ler_bronze(tabela: str) -> DataFrame:
    """Lê a Bronze ficando só com o ÚLTIMO lote ingerido.
    Enquanto a Bronze fizer append (B-01), isso evita duplicar tudo. Depois do CREATE OR REPLACE,
    continua correto (há um lote só). Remove as colunas técnicas da Bronze."""
    df = spark.table(f"{BRONZE}.{tabela}")
    if "_ingestion_timestamp" in df.columns:
        ultimo = df.agg(F.max("_ingestion_timestamp")).first()[0]
        df = df.filter(F.col("_ingestion_timestamp") == ultimo)
    return df.drop("_ingestion_timestamp", "_source_file")


def remove_cabecalho(df: DataFrame, coluna: str) -> DataFrame:
    """Remove linhas em que o valor é o próprio nome da coluna (cabeçalho repetido no meio do arquivo)."""
    return df.filter(F.col(coluna).isNull() | (F.col(coluna) != coluna))

# COMMAND ----------

# DBTITLE 1,Quarentena e gravação
def separa_quarentena(df: DataFrame, regras) -> tuple:
    """regras = [(condição, 'MOTIVO'), ...]. A PRIMEIRA regra verdadeira define o motivo.
    Condição nula conta como falsa. Devolve (confiáveis, quarentena com a coluna motivo_quarentena)."""
    motivo = F.lit(None).cast("string")
    for cond, nome in reversed(regras):
        motivo = F.when(cond, F.lit(nome)).otherwise(motivo)
    d = df.withColumn("motivo_quarentena", motivo)
    ok = d.filter(F.col("motivo_quarentena").isNull()).drop("motivo_quarentena")
    quarentena = d.filter(F.col("motivo_quarentena").isNotNull())
    return ok, quarentena


def grava_tabela(df: DataFrame, tabela: str, schema: str = None) -> int:
    """CREATE OR REPLACE da tabela (com a coluna técnica _processado_em). Devolve a contagem gravada."""
    destino = f"{schema or SILVER}.{tabela}"
    (df.withColumn("_processado_em", F.current_timestamp())
       .write.mode("overwrite").option("overwriteSchema", "true")
       .saveAsTable(destino))
    n = spark.table(destino).count()
    RESUMO.append(f"GRAVADO | {tabela}: {n:,}")
    return n


def grava_silver(ok: DataFrame, quarentena: DataFrame, nome: str):
    """Grava silver_<nome> e silver_<nome>_quarentena (CREATE OR REPLACE) e mostra o resumo."""
    n_ok = grava_tabela(ok, f"silver_{nome}")
    n_q = grava_tabela(quarentena, f"silver_{nome}_quarentena")
    print(f"✅ silver_{nome}: {n_ok:,} linhas | silver_{nome}_quarentena: {n_q:,} linhas")
    if n_q:
        motivos = (spark.table(f"{SILVER}.silver_{nome}_quarentena")
                   .groupBy("motivo_quarentena").count().orderBy(F.desc("count")).collect())
        for m in motivos:
            RESUMO.append(f"QUARENTENA | {m['motivo_quarentena']}: {m['count']:,}")
            print(f"   quarentena {m['motivo_quarentena']}: {m['count']:,}")
    return n_ok, n_q


def le_silver(nome: str) -> DataFrame:
    return spark.table(f"{SILVER}.silver_{nome}").drop("_processado_em")


def le_gold(nome: str) -> DataFrame:
    return spark.table(f"{GOLD}.{nome}").drop("_processado_em")


def grava_gold(df: DataFrame, nome: str) -> int:
    """Grava uma tabela Gold. A Gold é exportada em CSV, então não pode ter colunas array/map/struct."""
    complexas = [f.name for f in df.schema.fields if f.dataType.typeName() in ("array", "map", "struct")]
    if complexas:
        raise ValueError(f"{nome}: colunas complexas não exportáveis em CSV: {complexas}")
    n = grava_tabela(df, nome, schema=GOLD)
    print(f"✅ {nome}: {n:,} linhas")
    return n


def soma_meses(d, n: int):
    """Soma n meses a uma data (datetime.date), devolvendo o 1º dia do mês."""
    m = d.month - 1 + n
    return d.replace(year=d.year + m // 12, month=m % 12 + 1, day=1)


def finaliza():
    """Último comando de cada notebook: devolve o resumo para o Workflow."""
    dbutils.notebook.exit(json.dumps(RESUMO, ensure_ascii=False))

# COMMAND ----------

# DBTITLE 1,Conferências
def confere(descricao: str, valor, esperado=None, ok=None) -> bool:
    """Imprime ✅/❌. Use 'esperado' para igualdade ou 'ok' para uma condição já calculada."""
    passou = (valor == esperado) if esperado is not None else bool(ok)
    fmt = lambda v: f"{v:,}" if isinstance(v, (int, float)) and not isinstance(v, bool) else f"{v}"
    extra = f" (esperado {fmt(esperado)})" if esperado is not None else ""
    print(f"{'✅' if passou else '❌'} {descricao}: {fmt(valor)}{extra}")
    RESUMO.append(f"{'OK' if passou else 'FALHA'} | {descricao}: {fmt(valor)}{extra}")
    return passou

print("00_utils carregado.")
