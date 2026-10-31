# Databricks notebook source
# DBTITLE 1,Exportação CSV — Camada Gold
# MAGIC %md
# MAGIC # 06 — Exportação CSV da Camada Gold
# MAGIC
# MAGIC Este notebook lê todas as tabelas do schema **gold** do catálogo `v-energy` e exporta cada uma como arquivo CSV em um volume do Unity Catalog.
# MAGIC
# MAGIC Os arquivos CSV são gravados como `{tabela}.csv` diretamente em `export_path` (pasta única), e a metadata do Spark (`_SUCCESS`, etc.) fica em `{export_path}/_staging`.
# MAGIC
# MAGIC **Parâmetros (widgets):**
# MAGIC - `catalog` — catálogo de origem (default: `v-energy`)
# MAGIC - `gold_schema` — schema gold (default: `gold_schema`)
# MAGIC - `export_path` — caminho base do volume para os CSVs (default: `/Volumes/v-energy/raw_data/raw_data/exports_gold`)

# COMMAND ----------

# DBTITLE 1,Configuração de widgets
# Widgets com defaults do projeto
try:
    dbutils.widgets.text("catalog", "v-energy")
    dbutils.widgets.text("gold_schema", "gold_schema")
    dbutils.widgets.text("export_path", "/Volumes/v-energy/raw_data/raw_data/exports_gold")
except Exception:
    pass  # widgets já criados em re-execução

catalog = dbutils.widgets.get("catalog")
gold_schema = dbutils.widgets.get("gold_schema")
export_path = dbutils.widgets.get("export_path")

print(f"Catalog: {catalog}")
print(f"Gold schema: {gold_schema}")
print(f"Export path: {export_path}")

# COMMAND ----------

# DBTITLE 1,Listar tabelas da camada gold
from pyspark.sql import functions as F

# Lista todas as tabelas no schema gold
tables_df = spark.sql(f"SHOW TABLES IN `{catalog}`.{gold_schema}")
gold_tables = [row.tableName for row in tables_df.collect() if not row.isTemporary]

print(f"Total de tabelas em {catalog}.{gold_schema}: {len(gold_tables)}")
for t in sorted(gold_tables):
    print(f"  • {t}")

# COMMAND ----------

# DBTITLE 1,Exportar tabelas como CSV
import os

# Diretório de staging (metadata do Spark: _SUCCESS, _committed_*, etc.)
staging_path = f"{export_path}/_staging"

# Garante que o diretório base existe e limpa staging anterior
dbutils.fs.mkdirs(export_path)
dbutils.fs.rm(staging_path, recurse=True)
dbutils.fs.mkdirs(staging_path)

# Limpa subdiretórios antigos (execuções anteriores com pasta por tabela)
for d in dbutils.fs.ls(export_path):
    if d.isDir() and not d.name.startswith("_"):
        dbutils.fs.rm(d.path, recurse=True)

resultados = []

for tabela in sorted(gold_tables):
    full_name = f"`{catalog}`.{gold_schema}.{tabela}"
    csv_final = f"{export_path}/{tabela}.csv"   # arquivo final com nome da tabela
    staging_table = f"{staging_path}/{tabela}"  # pasta temporária do Spark

    try:
        df = spark.table(full_name)
        num_linhas = df.count()
        num_cols = len(df.columns)

        # Remove CSV anterior se existir
        dbutils.fs.rm(csv_final, recurse=True)

        # Escreve no staging — Spark cria pasta com part-*.csv + metadata
        (
            df.coalesce(1)
            .write
            .mode("overwrite")
            .option("header", "true")
            .option("delimiter", ";")
            .option("encoding", "UTF-8")
            .csv(staging_table)
        )

        # Encontra o part-*.csv gerado e move para o caminho final
        arquivos_staging = dbutils.fs.ls(staging_table)
        part_csv = [a for a in arquivos_staging if a.name.endswith(".csv")]
        if part_csv:
            dbutils.fs.mv(part_csv[0].path, csv_final)

        # Limpa o staging desta tabela
        dbutils.fs.rm(staging_table, recurse=True)

        print(f"✅ {tabela}: {num_linhas:,} linhas, {num_cols} colunas → {csv_final}")
        resultados.append((tabela, num_linhas, num_cols, "OK", csv_final))

    except Exception as e:
        print(f"❌ {tabela}: {e}")
        resultados.append((tabela, 0, 0, f"ERRO: {e}", csv_final))

# Remove o diretório de staging inteiro
try:
    dbutils.fs.rm(staging_path, recurse=True)
except Exception:
    pass

print(f"\n{'='*60}")
print(f"Exportação concluída: {sum(1 for r in resultados if r[3] == 'OK')}/{len(resultados)} tabelas exportadas com sucesso")

# COMMAND ----------

# DBTITLE 1,Resumo dos arquivos exportados
# Lista os arquivos CSV gerados no volume (pasta única, sem subdiretórios)
print(f"Arquivos CSV em {export_path}:\n")

arquivos = dbutils.fs.ls(export_path)
csv_files = sorted(
    [a for a in arquivos if a.name.endswith(".csv")],
    key=lambda x: x.name
)

total_mb = 0
for f in csv_files:
    tamanho_mb = f.size / (1024 * 1024)
    total_mb += tamanho_mb
    print(f"  {f.name}: {tamanho_mb:.2f} MB")

print(f"\nTotal: {len(csv_files)} arquivos CSV, {total_mb:.2f} MB")

# COMMAND ----------

