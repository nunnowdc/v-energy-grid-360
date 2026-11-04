# Databricks notebook source
# MAGIC %md
# MAGIC # 05 · Gold · Testes de Qualidade Automatizados (Data Quality Gate)
# MAGIC
# MAGIC **Responsabilidade:** Validação bloqueante (*Quality Gate*) das tabelas analíticas da camada Gold.
# MAGIC
# MAGIC Este notebook é executado no Databricks Workflow **imediatamente antes** do notebook de exportação (`06_export_csv.py`).
# MAGIC Ele avalia o cumprimento do **Contrato de Dados da Gold** nos quatro eixos fundamentais:
# MAGIC 1. **Integridade Referencial:** Ausência total de registros órfãos entre fatos e dimensões;
# MAGIC 2. **Unicidade e Completude:** Não-nulidade e unicidade estrita de chaves primárias;
# MAGIC 3. **Consistência Contábil e Regras de Negócio:** Coerência matemática de faturamento, atrasos e indicadores ANEEL (DEC/FEC);
# MAGIC 4. **Coerência Temporal:** Cobertura de competências da concessão e datas de vencimento/emissão.
# MAGIC
# MAGIC Se qualquer verificação crítica falhar, este notebook dispara uma exceção `AssertionError`,
# MAGIC **interrompendo o Workflow do Databricks** e impedindo que arquivos CSV defeituosos cheguem ao Portal Web.

# COMMAND ----------

# MAGIC %run ../00_utils

# COMMAND ----------

# DBTITLE 1,1. Carregamento das Tabelas Gold
dim_uc = le_gold("dim_unidade_consumidora")
dim_alim = le_gold("dim_alimentador")
dim_med = le_gold("dim_medidor")
dim_gd = le_gold("dim_geracao_distribuida")
dim_comp = le_gold("dim_competencia")

fact_fat = le_gold("fact_faturamento")
fact_leit = le_gold("fact_leituras")
fact_oco = le_gold("fact_ocorrencias")
fact_atend = le_gold("fact_atendimentos")
fact_insp = le_gold("fact_inspecoes")
fila_insp = le_gold("fila_inspecao")
agg_dec_fec = le_gold("agg_continuidade_alimentador")

ERROS_CRITICOS = []

def valida_regra(descricao: str, condicao: bool, detalhe: str = ""):
    """Registra o teste no RESUMO e acumula em ERROS_CRITICOS se falhar."""
    if condicao:
        print(f"✅ PASSOU: {descricao}")
        RESUMO.append(f"PASS | {descricao}")
    else:
        msg = f"❌ FALHA: {descricao}" + (f" -> {detalhe}" if detalhe else "")
        print(msg)
        RESUMO.append(f"FAIL | {descricao}")
        ERROS_CRITICOS.append(msg)

# COMMAND ----------

# DBTITLE 1,2. Eixo 1: Integridade Referencial (Zero Órfãos)
ucs_validas = dim_uc.select("id_uc").distinct()
alims_validos = dim_alim.select("alimentador").distinct()

# Faturas sem UC no cadastro
orfaos_fat = fact_fat.join(ucs_validas, "id_uc", "left_anti").count()
valida_regra("Integridade Referencial: fact_faturamento -> dim_unidade_consumidora",
             orfaos_fat == 0, f"{orfaos_fat:,} faturas órfãs")

# Leituras sem UC no cadastro
orfaos_leit = fact_leit.join(ucs_validas, "id_uc", "left_anti").count()
valida_regra("Integridade Referencial: fact_leituras -> dim_unidade_consumidora",
             orfaos_leit == 0, f"{orfaos_leit:,} leituras órfãs")

# Ocorrências sem UC no cadastro
orfaos_oco = fact_oco.filter(F.col("id_uc").isNotNull()).join(ucs_validas, "id_uc", "left_anti").count()
valida_regra("Integridade Referencial: fact_ocorrencias -> dim_unidade_consumidora",
             orfaos_oco == 0, f"{orfaos_oco:,} ocorrências com UC órfã")

# Ocorrências sem Alimentador válido
orfaos_alim_oco = fact_oco.filter(F.col("alimentador").isNotNull()).join(alims_validos, "alimentador", "left_anti").count()
valida_regra("Integridade Referencial: fact_ocorrencias -> dim_alimentador",
             orfaos_alim_oco == 0, f"{orfaos_alim_oco:,} ocorrências com alimentador órfão")

# Chamados de atendimento sem UC
orfaos_atend = fact_atend.filter(F.col("id_uc").isNotNull()).join(ucs_validas, "id_uc", "left_anti").count()
valida_regra("Integridade Referencial: fact_atendimentos -> dim_unidade_consumidora",
             orfaos_atend == 0, f"{orfaos_atend:,} chamados órfãos")

# Fila de inspeção sem UC
orfaos_fila = fila_insp.join(ucs_validas, "id_uc", "left_anti").count()
valida_regra("Integridade Referencial: fila_inspecao -> dim_unidade_consumidora",
             orfaos_fila == 0, f"{orfaos_fila:,} UCs na fila sem cadastro")

# COMMAND ----------

# DBTITLE 1,3. Eixo 2: Unicidade e Completude de Chaves Primárias
tabelas_pk = [
    (dim_uc, "dim_unidade_consumidora", "id_uc", 45000),
    (dim_alim, "dim_alimentador", "alimentador", 122),
    (dim_med, "dim_medidor", "id_medidor", None),
    (fact_fat, "fact_faturamento", "id_fatura", None),
    (fact_leit, "fact_leituras", "id_leitura", None),
    (fact_oco, "fact_ocorrencias", "id_ocorrencia", None),
    (fact_atend, "fact_atendimentos", "protocolo", None),
    (fila_insp, "fila_inspecao", "prioridade", None),
]

for df, nome, pk, qtd_esperada in tabelas_pk:
    total = df.count()
    valida_regra(f"Volumetria Mínima: {nome}", total > 0, f"Total de linhas: {total}")
    if qtd_esperada is not None:
        valida_regra(f"Contagem Exata: {nome}", total == qtd_esperada, f"Esperado: {qtd_esperada}, Obtido: {total}")
    
    nulos = df.filter(F.col(pk).isNull() | (F.trim(F.col(pk)) == "")).count()
    valida_regra(f"Não-Nulidade PK: {nome}.{pk}", nulos == 0, f"{nulos} nulos encontrados")
    
    dups = df.groupBy(pk).count().filter("count > 1").count()
    valida_regra(f"Unicidade PK: {nome}.{pk}", dups == 0, f"{dups} valores duplicados")

# COMMAND ----------

# DBTITLE 1,4. Eixo 3: Consistência Contábil e Regras de Negócio
# Balanço contábil da fatura: receita_faturada = valor_energia + tributos
inconsistencias_contabeis = fact_fat.filter(
    F.abs(F.col("receita_faturada") - (F.col("valor_energia") + F.col("tributos"))) > 0.05
).count()
valida_regra("Consistência Contábil: receita_faturada = valor_energia + tributos",
             inconsistencias_contabeis == 0, f"{inconsistencias_contabeis:,} divergências contábeis")

# Dias de atraso não-negativos
atrasos_invalidos = fact_fat.filter(F.col("dias_atraso") < 0).count()
valida_regra("Regra de Domínio: dias_atraso >= 0 em fact_faturamento",
             atrasos_invalidos == 0, f"{atrasos_invalidos:,} faturas com atraso negativo")

# Domínio regulatório de bandeiras tarifárias
bandeiras_invalidas = fact_fat.filter(
    ~F.col("bandeira_tarifaria").isin("VERDE", "AMARELA", "VERMELHA_P1", "VERMELHA_P2")
).count()
valida_regra("Regra de Domínio: bandeira_tarifaria válida",
             bandeiras_invalidas == 0, f"{bandeiras_invalidas:,} bandeiras inválidas")

# Consumo não-negativo
consumo_negativo = fact_leit.filter(F.col("consumo_kwh") < 0).count()
valida_regra("Regra de Domínio: consumo_kwh >= 0 em fact_leituras",
             consumo_negativo == 0, f"{consumo_negativo:,} leituras com consumo negativo")

# Indicadores de continuidade ANEEL não-negativos
dec_fec_invalidos = agg_dec_fec.filter((F.col("dec") < 0) | (F.col("fec") < 0)).count()
valida_regra("Regra Regulatória ANEEL: DEC e FEC >= 0",
             dec_fec_invalidos == 0, f"{dec_fec_invalidos:,} alimentadores com DEC/FEC negativo")

# Score de suspeita entre 0 e 100
score_invalido = fila_insp.filter((F.col("score") < 0) | (F.col("score") > 100)).count()
valida_regra("Regra de Domínio: Score de Suspeita entre 0 e 100 na fila_inspecao",
             score_invalido == 0, f"{score_invalido:,} UCs com score fora do intervalo")

# COMMAND ----------

# DBTITLE 1,5. Eixo 4: Coerência Temporal
# 48 competências analíticas mensais (julho/2022 a junho/2026)
total_competencias = dim_comp.count()
valida_regra("Coerência Temporal: exatamente 48 competências em dim_competencia",
             total_competencias == 48, f"Total encontrado: {total_competencias}")

# Vencimento da fatura = emissão + 12 dias
vencimentos_invalidos = fact_fat.filter(
    F.col("data_emissao").isNotNull() &
    F.col("data_vencimento").isNotNull() &
    (F.date_add(F.col("data_emissao"), 12) != F.col("data_vencimento"))
).count()
valida_regra("Coerência Temporal: data_vencimento = data_emissao + 12 dias",
             vencimentos_invalidos == 0, f"{vencimentos_invalidos:,} faturas com vencimento incoerente")

# Duração de interrupção: encerramento >= abertura
duracao_invalida = fact_oco.filter(
    F.col("data_encerramento").isNotNull() &
    F.col("data_abertura").isNotNull() &
    (F.col("data_encerramento") < F.col("data_abertura"))
).count()
valida_regra("Coerência Temporal: data_encerramento >= data_abertura em fact_ocorrencias",
             duracao_invalida == 0, f"{duracao_invalida:,} interrupções com duração negativa")

# COMMAND ----------

# DBTITLE 1,6. Decisão do Quality Gate (Fail-Fast)
if ERROS_CRITICOS:
    total_falhas = len(ERROS_CRITICOS)
    detalhes = "\n".join(ERROS_CRITICOS)
    print("\n" + "="*80)
    print(f"⛔ FALHA BLOQUEANTE NO DATA QUALITY GATE: {total_falhas} TESTE(S) CRÍTICO(S) FALHARAM!")
    print("="*80)
    print(detalhes)
    print("\nO Workflow foi interrompido antes da exportação CSV para proteger o Portal Web.")
    raise AssertionError(f"FALHA NO DATA QUALITY GATE: {total_falhas} regra(s) crítica(s) violada(s).")

print("\n" + "="*80)
print("✨ PARABÉNS! DATA QUALITY GATE APROVADO COM 100% DE SUCESSO!")
print("Todas as tabelas da camada Gold satisfazem o Contrato de Dados.")
print("Liberação concedida para exportação CSV (06_export_csv).")
print("="*80)

finaliza()
