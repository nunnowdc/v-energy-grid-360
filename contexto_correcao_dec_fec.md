# Contexto: correção do arredondamento do DEC/FEC na Gold

**Data:** 29/10/2026 · **Responsável:** Rafael · **Status:** decidido, a implementar

> **Para o assistente que ajudar nesta tarefa:** este arquivo tem tudo o que foi decidido. Não mude o escopo; se algo não estiver aqui, pergunte ao Rafael.

---

## 1. O problema

O DEC e o FEC **não vêm dos dados brutos**: são calculados na Gold, no notebook `05_gold_continuidade`:

```
DEC = horas_x_uc ÷ total_ucs          (horas sem luz por cliente)
FEC = interrupcoes ÷ total_ucs        (vezes sem luz por cliente)
```

Hoje a Gold grava esses valores **já arredondados**: 4 casas na tabela mensal e 2 na anual. Isso causa três erros:

| # | Erro | Exemplo |
|---|---|---|
| 1 | **Somar meses acumula o erro do arredondamento** | 3 meses de 1/7 de hora: exato = 0,428571; somando os arredondados = 0,4287 |
| 2 | **O ranking muda** quando dois alimentadores estão quase empatados | O time de backend encontrou 2 posições diferentes na janela de 3 meses e 2 na de 6 |
| 3 | **O ranking anual da própria Gold empata alimentadores diferentes** | DEC 1,234 e 1,236 viram os dois "1,24" antes do `rank_dec` |

Também há um arredondamento escondido na origem: a `duracao_h` da `fact_ocorrencias` é `round(duracao_min ÷ 60, 4)`, e o `horas_x_uc` soma 180 mil desses valores arredondados.

Origem da discussão: a mensagem do time de backend sobre as janelas móveis de 3, 6 e 12 meses na tela de Continuidade.

## 2. A decisão

**A Gold guarda os valores completos, sem nenhum arredondamento. O arredondamento acontece só na apresentação.**

| Camada | Responsável | O que faz |
|---|---|---|
| Gold (Databricks) | **Dados (Rafael)** | Grava DEC, FEC e `duracao_h` sem arredondar |
| API (FastAPI) | Backend | Calcula as janelas e os rankings com o valor completo; arredonda **só na resposta** (o time propôs 6 casas) |
| Tela (React) | Frontend | Formata para exibir (ex.: 2 casas, padrão pt-BR) |
| Agente de IA | GenAI | Instrução no prompt para apresentar DEC/FEC com 2 casas |

**Fórmula recomendada ao backend para as janelas** (dá o mesmo resultado hoje e continua certa se o número de clientes variar mês a mês no futuro):

```sql
DEC da janela = SUM(horas_x_uc / total_ucs)
FEC da janela = SUM(interrupcoes / total_ucs)
-- e as mesmas fórmulas com as colunas *_sem_dia_critico
```

---

## 3. O que muda no código (só a parte de dados)

Arquivos em `C:\Users\Rafael\OneDrive\Documentos\docs_claude\pipeline\` e no workspace do Databricks em `/Users/rafaplanisa37@gmail.com/pipeline/`.

### 3.1 `04_gold_fatos.py`, linha 64 (`fact_ocorrencias`)

```python
# antes
"duracao_min", F.round(F.col("duracao_min") / 60, 4).alias("duracao_h"),

# depois
"duracao_min", (F.col("duracao_min") / 60).alias("duracao_h"),
```

### 3.2 `05_gold_continuidade.py`, linhas 49 a 52 (tabela mensal)

```python
# antes
.withColumn("dec", F.round(F.col("horas_x_uc") / F.col("total_ucs"), 4))
.withColumn("fec", F.round(F.col("interrupcoes") / F.col("total_ucs"), 4))
.withColumn("dec_sem_dia_critico", F.round(F.col("horas_x_uc_sem_dia_critico") / F.col("total_ucs"), 4))
.withColumn("fec_sem_dia_critico", F.round(F.col("interrupcoes_sem_dia_critico") / F.col("total_ucs"), 4)))

# depois
.withColumn("dec", F.col("horas_x_uc") / F.col("total_ucs"))
.withColumn("fec", F.col("interrupcoes") / F.col("total_ucs"))
.withColumn("dec_sem_dia_critico", F.col("horas_x_uc_sem_dia_critico") / F.col("total_ucs"))
.withColumn("fec_sem_dia_critico", F.col("interrupcoes_sem_dia_critico") / F.col("total_ucs")))
```

### 3.3 `05_gold_continuidade.py`, linhas 63 a 66 (tabela anual)

A mesma troca, tirando o `F.round(..., 2)` das 4 colunas. **Os rankings (`rank_dec`, `rank_dec_sem_dia_critico`, `rank_impacto_horas_x_uc`) não mudam de código**: passam a ser calculados sobre o valor completo automaticamente, porque usam as colunas acima.

### 3.4 `07_dicionario_gold.py` (dicionário de dados)

Acrescentar à regra das colunas `dec`, `fec`, `dec_sem_dia_critico` e `fec_sem_dia_critico` (no dicionário `COMUNS`) e da `duracao_h` (em `D["fact_ocorrencias"]`):

> "Valor completo, sem arredondamento; arredondar só na apresentação (API/tela)."

### Fora do escopo desta tarefa

Outras colunas da Gold também são arredondadas (`preco_medio_kwh`, `variacao_ano_anterior_pct`, os percentuais da receita). **Não mexer agora.** Se o time decidir aplicar a mesma regra a elas, é outra tarefa.

---

## 4. Como rodar

Ordem obrigatória (cada notebook depende do anterior):

1. `04_gold_fatos` (recria a `fact_ocorrencias` com a `duracao_h` completa)
2. `05_gold_continuidade` (recria as duas tabelas de DEC/FEC)
3. `07_dicionario_gold` (atualiza as descrições e os comentários das tabelas)
4. Exportar as tabelas alteradas para o Postgres local: `fact_ocorrencias`, `agg_continuidade_alimentador`, `agg_continuidade_alimentador_anual`

**Atenção ao carregar no Postgres:** se a carga recriar as tabelas (`DROP` + `CREATE`), as permissões e as views que dependem delas se perdem (ver `planejamento_permissoes_banco.md`, seção 5).

---

## 5. Como conferir que deu certo

| # | Teste | Resultado esperado |
|---|---|---|
| 1 | Somar o `dec` mensal de 2025 de um alimentador e comparar com o `dec` anual de 2025 | Iguais, com diferença menor que 0,000001 |
| 2 | ALM-REC-008, 2025 | `dec` ≈ 15,03 e `dec_sem_dia_critico` ≈ 0,20 (arredondando só para conferir) |
| 3 | Os 3 alimentadores de maior impacto em 2025 | Continuam ALM-REC-008, ALM-SAO-004 e ALM-JAB-004 |
| 4 | O `rank_dec` de 2025 | Não deve haver empates que existiam só por causa do arredondamento |
| 5 | A recomposição do backend (`SUM(horas_x_uc / total_ucs)`) para os anos completos (2023, 2024, 2025) | Igual ao `dec` anual da Gold, sem precisar arredondar para comparar |
| 6 | O resumo do notebook `05_gold_continuidade` | Continua com 5.856 linhas mensais (122 alimentadores × 48 meses) e todas as conferências ✅ |

Consulta de apoio para o teste 1 (no SQL warehouse do Databricks ou no Postgres):

```sql
SELECT m.alimentador,
       SUM(m.dec)  AS soma_mensal,
       MAX(a.dec)  AS anual,
       ABS(SUM(m.dec) - MAX(a.dec)) AS diferenca
FROM agg_continuidade_alimentador m
JOIN agg_continuidade_alimentador_anual a
  ON a.alimentador = m.alimentador AND a.ano = 2025
WHERE m.ano = 2025
GROUP BY m.alimentador
ORDER BY diferenca DESC
LIMIT 5;
```

---

## 6. O que avisar aos outros times

- **Backend:** a Gold passa a ter o DEC/FEC sem arredondamento. A abordagem de vocês para as janelas está validada; sugestão de escrever `SUM(horas_x_uc / total_ucs)`. O arredondamento fica na resposta da API.
- **Frontend:** formatar DEC e FEC na tela (ex.: `Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 })`).
- **GenAI:** instruir o agente a apresentar DEC/FEC com 2 casas e a **não somar DECs mensais arredondados**. Com a Gold sem arredondamento, somar o `dec` mensal passa a dar o valor certo.

## 7. Depois de concluído

- Registrar no `registro_de_problemas.md` (seção Gold) com o resultado dos testes.
- Atualizar o `dicionario_dados_gold.md` (é gerado pelo passo 3 da seção 4).
