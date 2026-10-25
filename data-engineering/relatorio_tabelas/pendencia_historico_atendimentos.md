# Pendência: histórico fora de ordem em `atendimentos.json`

**Status:** ✅ **RESOLVIDA em 24/10/2026: ruído aleatório (H3).** Detalhes em `perfil_atendimentos.md` §4.
**Data:** 19/10/2026

> **Resultado dos testes (24/10):**
> - **Teste 1:** 100% das ações dentro da janela do próprio chamado e 100% no mesmo canal. A última ação sempre coincide com o fechamento.
> - **Teste 3:** ~81% de chamados desordenados, com taxa **igual** em todos os municípios (80,5–81,6%) e canais (80,7–81,4%). É o valor que um sorteio entre 5 ações produziria (1 − 1/5 ≈ 80%).
> - **Teste 2:** o número do cruzamento ainda não foi recebido, mas a H1 já está descartada na prática pelos testes 1 e 3.
>
> **Decisão:** datas principais como fonte da verdade; do histórico, usar só `qtd_tratativas`; **não usar `teve_despacho`** (o rótulo DESPACHO também é aleatório).

---

## 1. O problema

Cada chamado em `atendimentos.json` tem um campo `historico`, que é uma lista de ações com `acao`, `canal`, `data` e `sequencia`.

O fluxo esperado de um chamado é:

```
ABERTURA → ANALISE → DESPACHO → RETORNO AO CLIENTE → ENCERRAMENTO
```

Na amostra de 20 linhas, os rótulos das ações não seguem essa lógica:

| Protocolo | Sequência registrada | Incoerência |
|---|---|---|
| AT000000002 | RETORNO → ABERTURA → ENCERRAMENTO | Retornou ao cliente antes de abrir o chamado |
| AT000000003 | ANALISE → ABERTURA → RETORNO | Analisou antes de abrir |
| AT000000006 | ANALISE → RETORNO → ABERTURA | Termina com "abertura" no momento do fechamento |
| AT000000017 | ENCERRAMENTO → ANALISE | Analisou depois de encerrar |
| AT000000013 | só ABERTURA | Tem data de fechamento, mas nenhuma ação de encerramento |
| AT000000000 | só RETORNO | Não tem abertura nem encerramento |

**O que parece coerente (só na amostra):**

- As datas crescem junto com a `sequencia`.
- A última ação sempre cai exatamente em `data_fechamento`.
- Todas as ações ficam entre a abertura e o fechamento do próprio chamado.
- O `canal` de cada ação é igual ao do chamado.

**Por que importa:**

- Não dá para medir etapas como "tempo até o despacho".
- Não dá para usar "não tem ENCERRAMENTO" como sinal de chamado aberto.
- O histórico em formato de lista (array) impede exportar a Gold em CSV, que é um requisito do case. Isso precisa ser resolvido de qualquer forma.

---

## 2. Hipóteses

| # | Hipótese | Como verificar |
|---|---|---|
| H1 | **Ações de outros chamados misturadas** ("pessoas diferentes"). O histórico teria ações de outro chamado da mesma UC. | Testes 1 e 2 |
| H2 | **Atendentes diferentes** registrando as ações cada um do seu jeito | Não dá para testar, porque não existe coluna de atendente. Só pode entrar como suposição documentada. |
| H3 | **Ruído aleatório do sistema legado**, provavelmente colocado de propósito no case | Teste 3: se a taxa de desordem for igual em todos os recortes, é ruído. |
| H4 | **Causa sistemática**: um município, canal ou assunto concentra o erro | Teste 3: se um recorte ficar muito acima dos outros, há uma causa. |

---

## 3. Investigação (próximo passo)

Rodar a célula abaixo no Databricks. Ela lê direto do Volume.

```python
from pyspark.sql import functions as F

raw = "/Volumes/v-energy/raw_data/raw_data"
df_ate = spark.read.option("multiline", "true").json(f"{raw}/atendimentos.json")
df_uc = (spark.read.option("header", "true").csv(f"{raw}/unidades_consumidoras.csv")
         .select("id_uc", "municipio", "bairro", "classe").dropDuplicates(["id_uc"]))

ch = df_ate.select(
    "protocolo", "id_uc", "canal", "assunto", "historico",
    F.try_to_timestamp("data_abertura").alias("abertura"),
    F.try_to_timestamp("data_fechamento").alias("fechamento"),
)

h = (ch.select("protocolo", "id_uc", "canal", "abertura", "fechamento", F.explode("historico").alias("h"))
       .select("protocolo", "id_uc", "abertura", "fechamento",
               F.col("canal").alias("canal_chamado"), F.col("h.canal").alias("canal_acao"),
               "h.acao", "h.sequencia", F.try_to_timestamp("h.data").alias("data_acao")))

# TESTE 1: as tratativas pertencem mesmo ao próprio chamado?
print("TESTE 1 - Tratativas dentro do próprio chamado")
display(h.select(
    F.count("*").alias("tratativas"),
    F.round(100 * F.avg(F.col("data_acao").between(F.col("abertura"), F.col("fechamento")).cast("int")), 2).alias("pct_dentro_da_janela"),
    F.round(100 * F.avg((F.col("canal_acao") == F.col("canal_chamado")).cast("int")), 2).alias("pct_mesmo_canal"),
))

# TESTE 2: a ação "ABERTURA" fora de lugar é, na verdade, a abertura de OUTRO chamado da mesma UC?
print("TESTE 2 - Chamados por UC")
display(ch.groupBy("id_uc").count().groupBy(F.col("count").alias("chamados_por_uc")).count()
          .withColumnRenamed("count", "qtd_ucs").orderBy("chamados_por_uc"))

outras = ch.select(F.col("id_uc").alias("uc_o"), F.col("protocolo").alias("protocolo_o"), F.col("abertura").alias("abertura_o"))
ab = h.filter(F.col("acao") == "ABERTURA")
cruz = ab.join(outras, (ab.id_uc == outras.uc_o) & (ab.protocolo != outras.protocolo_o) & (ab.data_acao == outras.abertura_o), "left")
display(cruz.select(
    F.countDistinct("protocolo", "sequencia").alias("acoes_abertura"),
    F.countDistinct(F.when(F.col("protocolo_o").isNotNull(), F.struct("protocolo", "sequencia"))).alias("batem_com_outro_chamado"),
))

# TESTE 3: a desordem se concentra em algum lugar/canal/assunto?
por_chamado = h.groupBy("protocolo").agg(
    F.min_by("acao", "sequencia").alias("primeira"),
    F.max_by("acao", "sequencia").alias("ultima"),
    F.max((F.col("acao") == "ENCERRAMENTO").cast("int")).alias("tem_enc"),
)
desordem = (por_chamado
    .withColumn("desordenado", ((F.col("primeira") != "ABERTURA") |
                                ((F.col("tem_enc") == 1) & (F.col("ultima") != "ENCERRAMENTO"))).cast("int"))
    .join(ch.select("protocolo", "id_uc", "canal", "assunto"), "protocolo")
    .join(df_uc, "id_uc", "left"))

print("TESTE 3 - Taxa de desordem por recorte (se tudo der parecido, é ruído aleatório)")
for dim in ["municipio", "canal", "assunto"]:
    display(desordem.groupBy(dim).agg(
        F.count("*").alias("chamados"),
        F.round(100 * F.avg("desordenado"), 1).alias("pct_desordenado"),
    ).orderBy(F.desc("chamados")))
```

### Como interpretar

| Teste | O que mede | Interpretação |
|---|---|---|
| 1 | % das ações dentro da janela do chamado e % com o mesmo canal | Perto de 100%: o histórico é do próprio chamado, o que enfraquece a H1. |
| 2 | Quantas ações "ABERTURA" coincidem com a abertura de outro chamado da mesma UC | Muitas coincidências confirmam a H1. |
| 3 | % de chamados desordenados por município, canal e assunto | Taxas parecidas apontam para a H3. Um recorte destoando aponta para a H4. |

---

## 4. Soluções possíveis (dependem do resultado)

| Cenário | Tratamento na Silver/Gold |
|---|---|
| **H3, ruído** (o mais provável) | Usar `data_abertura` e `data_fechamento` como fonte da verdade. Do histórico, usar só `qtd_tratativas` e `teve_despacho`. Documentar no dicionário: "os rótulos de ação do histórico não são confiáveis para análise de etapas". |
| **H1, mistura entre chamados** | Reatribuir cada ação ao chamado correto pela data e pela UC, ou mandar os chamados afetados para quarentena. |
| **H4, causa sistemática** | O mesmo tratamento da H3, mais um achado para a apresentação ("o canal X tem processo inconsistente"). |

### Em qualquer cenário

- Separar em duas tabelas Gold:
  - `fact_atendimentos`: uma linha por protocolo, com `tempo_resolucao_h`, `qtd_tratativas` e `teve_despacho`.
  - `fact_atendimento_tratativas`: o histórico explodido, uma linha por ação. Isso resolve a exportação para CSV.
- Tratar a diferença de separador nas datas: espaço nas colunas principais (`2022-07-02 15:51:00`) e `T` dentro do histórico (`2022-07-10T14:51:00`). Usar o formato `"yyyy-MM-dd'T'HH:mm:ss"` ou deixar o Spark detectar sozinho.

---

## 5. Outras pendências em aberto

- Confirmar se a coluna de arquivo nas leituras se chama `arquivo` (vem do CSV de origem) ou `_arquivo` (criada pelo código de preview via `_metadata.file_name`).
- Continuar o perfil das demais tabelas para montar o mapa de relacionamentos e as junções da Gold.
