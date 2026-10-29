# Tarefa: tirar o arredondamento do DEC/FEC da Gold no Databricks

**Data:** 29/10/2026 · **Responsável:** Rafael · **Status:** código corrigido no repositório; falta aplicar no Databricks

> **Para o assistente:** aplique as mudanças abaixo nos notebooks do workspace Databricks, rode-os na ordem da seção 4 e confira com os testes da seção 5. Não mude nada fora do escopo. Se algo não bater com o que está descrito aqui, pare e pergunte ao Rafael.

---

## 1. Por que

O DEC e o FEC são calculados na Gold, no notebook `05_gold_continuidade`:

```
DEC = horas_x_uc ÷ total_ucs
FEC = interrupcoes ÷ total_ucs
```

A Gold gravava esses valores já arredondados (4 casas na tabela mensal, 2 na anual), e a `duracao_h` da `fact_ocorrencias` também saía arredondada (4 casas). Por causa disso:

- somar os meses acumulava o erro do arredondamento;
- o ranking das janelas de 3 e 6 meses do backend mudava entre alimentadores quase empatados;
- o `rank_dec` anual empatava alimentadores diferentes (1,234 e 1,236 viravam os dois 1,24).

**Decisão:** a Gold guarda o valor completo, sem arredondar. O arredondamento acontece só na apresentação: na API, na tela e no agente de IA.

## 2. Onde estão os notebooks

Workspace: `/Users/rafaplanisa37@gmail.com/pipeline/`

No repositório Git, os notebooks foram reorganizados em pastas (`bronze/`, `silver/`, `gold/`), e os `%run` viraram `%run ../00_utils`. **Essa reorganização não faz parte desta tarefa.** No workspace, mantenha a estrutura atual e os `%run` como estão.

## 3. O que mudar

Os números de linha são da versão do repositório e devem bater com o workspace. Se não baterem, localize pelo trecho de código.

### 3.1 `04_gold_fatos`, célula "3. fact_ocorrencias" (linha 64)

```python
# antes
"duracao_min", F.round(F.col("duracao_min") / 60, 4).alias("duracao_h"),

# depois
"duracao_min", (F.col("duracao_min") / 60).alias("duracao_h"),
```

Não mexa nos outros `F.round` desse notebook (`variacao_ano_anterior_pct` e `preco_medio_kwh`). Eles estão fora do escopo.

### 3.2 `05_gold_continuidade`, célula "2. agg_continuidade_alimentador (mensal)" (linhas 49 a 52)

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

### 3.3 `05_gold_continuidade`, célula "3. agg_continuidade_alimentador_anual (rankings)" (linhas 63 a 66)

A mesma troca nas mesmas 4 colunas, desta vez tirando o `F.round(..., 2)`. O resultado fica idêntico ao do 3.2.

Não altere os rankings (`rank_dec`, `rank_dec_sem_dia_critico`, `rank_impacto_horas_x_uc`). Eles leem essas colunas e passam a ordenar pelo valor completo sem nenhuma mudança de código.

Depois da troca, `05_gold_continuidade` não deve ter nenhum `F.round`.

### 3.4 `07_dicionario_gold` (dicionário de dados)

Na regra destas colunas, acrescente o texto: **"Valor completo, sem arredondamento; arredondar só na apresentação (API/tela)."**

- `dec`, `fec`, `dec_sem_dia_critico` e `fec_sem_dia_critico`, no dicionário `COMUNS`;
- `duracao_h`, em `D["fact_ocorrencias"]`.

Esse notebook não está no repositório, então confira a estrutura dele antes de editar. Se `COMUNS` ou `D["fact_ocorrencias"]` não existirem com esses nomes, pare e pergunte.

### O que não fazer

- Não arredondar outras colunas nem tirar o arredondamento delas (`preco_medio_kwh`, `variacao_ano_anterior_pct`, os percentuais da receita). Se o time decidir, isso vira outra tarefa.
- Não mudar a linha do `RESUMO` que imprime `DEC {r['dec']}` no fim do `05_gold_continuidade`. Ela passa a mostrar o valor com várias casas, e isso é esperado.

## 4. Ordem de execução

Cada notebook depende do anterior:

1. `04_gold_fatos`, que recria a `fact_ocorrencias` com a `duracao_h` completa
2. `05_gold_continuidade`, que recria as duas tabelas de DEC/FEC
3. `07_dicionario_gold`, que atualiza as descrições e os comentários das tabelas
4. O notebook de export para CSV (`06_export_csv`), se o Rafael pedir. As tabelas alteradas são `fact_ocorrencias`, `agg_continuidade_alimentador` e `agg_continuidade_alimentador_anual`

## 5. Como conferir

| # | Teste | Resultado esperado |
|---|---|---|
| 1 | Somar o `dec` mensal de 2025 de cada alimentador e comparar com o `dec` anual de 2025 | Diferença menor que 0,000001 em todos |
| 2 | ALM-REC-008, 2025 | `dec` ≈ 15,03 e `dec_sem_dia_critico` ≈ 0,20 (arredonde só para comparar) |
| 3 | Os 3 alimentadores de maior impacto em 2025 (`rank_impacto_horas_x_uc`) | ALM-REC-008, ALM-SAO-004 e ALM-JAB-004 |
| 4 | `rank_dec` de 2025 | Nenhum empate entre alimentadores com DEC diferente |
| 5 | `SUM(horas_x_uc / total_ucs)` da tabela mensal para 2023, 2024 e 2025 | Igual ao `dec` anual, sem precisar arredondar para comparar |
| 6 | Resumo do `05_gold_continuidade` | 5.856 linhas mensais (122 alimentadores × 48 meses) e todas as conferências ✅ |
| 7 | `fact_ocorrencias` | Continua com 180.000 linhas (conferência do `04_gold_fatos`) |

Consulta para o teste 1:

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

Consulta para o teste 4:

```sql
SELECT rank_dec, COUNT(*) AS alimentadores, COUNT(DISTINCT dec) AS valores_distintos
FROM agg_continuidade_alimentador_anual
WHERE ano = 2025
GROUP BY rank_dec
HAVING COUNT(*) > 1;
-- Esperado: nenhuma linha, ou só linhas com valores_distintos = 1 (empate real)
```

Se um teste falhar, não tente corrigir mudando outras partes do pipeline. Relate o resultado ao Rafael.

## 6. O que devolver ao Rafael

- A confirmação de cada mudança da seção 3, com o trecho final de cada notebook.
- O resultado dos testes 1 a 7: o valor obtido e ✅ ou ❌.
- O `dicionario_dados_gold.md` gerado pelo `07_dicionario_gold`, para ele atualizar o repositório em `data-engineering/relatorio_tabelas/`.
- Qualquer diferença entre os notebooks do workspace e o que está descrito aqui.

Fora do Databricks, e a cargo do Rafael: recarregar as 3 tabelas no Postgres local, registrar o resultado no `registro_de_problemas.md` e avisar os times de backend, frontend e GenAI.
