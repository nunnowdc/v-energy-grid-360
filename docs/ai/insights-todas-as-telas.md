# Insights da IA em todas as telas de negócio

**Decidido em 07/11/2026** por Nunno e Julio · **Prazo:** congelar no dia 8 à noite; dia 9 só testes e apresentação · **Branch:** `usando-genai` (Nunno e Julio juntos; vai para a `dev` quando os insights estiverem funcionando)

Este documento **substitui a decisão** de `docs/ai/insight-visao-360-pendencias.md`. Aquele documento colocava o insight só na Visão 360. Agora o insight vai em todas as telas de negócio. As pendências antigas que ainda valem estão repetidas aqui.

Tudo o que está abaixo foi conferido na `dev` (`19d4374`) e na `usando-genai` (`5723f28`, prompt novo do narrador). As consultas SQL foram rodadas no banco local pelo `SQLExecutor` do próprio agente, e os números de exemplo são os que elas devolveram.

---

## 1. Resumo da decisão

1. **Um insight por tela**, nas 5 telas de negócio: Visão 360, Receita, Indicadores, Continuidade e Fila de inspeção. As telas de administração (Usuários, Agente IA e Avaliação) **não** têm insight.
2. **O insight não depende dos filtros da tela.** Ele fala da base inteira. A única exceção é a Visão 360, que continua por UC. O front escreve no bloco: *"Visão geral da base completa · não muda com os filtros"*.
3. **Mesmo formato de hoje.** Uma consulta fixa por tela, a IA só escreve a frase, o conferente numérico confere e, se falhar 3 vezes, entra o texto-modelo. O agente que escreve SQL (`/ai/ask`) **não** é usado para insight: é lento (15 a 30 s), muda a consulta a cada vez e não teria por que dar os mesmos números da tela.
4. **Os números do insight vêm da mesma tabela Gold e do mesmo período que a tela usa.** Se a tela mostra +8,0% e o insight diz outra coisa, a banca percebe.
5. **Toda conta é feita no SQL.** A consulta já entrega percentuais calculados, valores arredondados na unidade em que vão aparecer (milhões, GWh, MWh) e datas como texto. A IA não calcula, não converte e não arredonda, como o prompt novo do narrador já pede.
6. **Os textos são gerados antes da apresentação** por um script, para abrirem na hora sem depender do modelo ao vivo.

### Quem faz o quê

| Parte | Quem | Onde |
|---|---|---|
| Consultas de cada tela, narrador, conferente, texto-modelo, script de geração, testes do ai-agent | **Julio** | `ai-agent/` |
| Permissão por tela (quem pode ver o insight de cada tela) | **Nunno** | `backend/app/security/` |
| Bloco do insight em cada tela, hook, testes do front | **Nunno** | `frontend/` |

---

## 2. Contrato entre front, backend e ai-agent

**Isto precisa ficar igual nos três lados.** Mudanças aqui precisam ser combinadas antes.

### 2.1 Rota

A rota é a mesma de hoje, e **nenhuma rota nova é criada**:

```
GET /api/ai/insights/{tela}/{entidade_id}
```

O endpoint em `ai-agent/src/api/ai_router.py` (`get_insight`) **não muda**.

### 2.2 Nomes das telas (`tela`)

O mesmo texto é usado em três lugares:
- no front, que monta a URL;
- no mapa de permissão do backend;
- nas chaves de `QUERIES` e `FONTES_POR_TELA` em `ai-agent/src/insights/extrator_metricas_fixas.py`.

Se um lado escrever diferente, o insight dá 403 ou 400 ("Tela de insight não suportada").

| Tela do portal | `tela` | `entidade_id` | Perfis que veem (igual à rota de dados da tela) |
|---|---|---|---|
| Visão 360 | `visao_360_uc` (já existe) | ID da UC, ex.: `UC132549` | Diretoria, Atendimento, Perdas, Admin TI |
| Receita | `receita` | `global` | Diretoria, Admin TI |
| Indicadores | `indicadores` | `global` | Diretoria, Admin TI |
| Continuidade | `continuidade` | `global` | Diretoria, Operação, Admin TI |
| Fila de inspeção | `fila_inspecao` | `global` | Perdas, Admin TI |

**O nome `diagnostico_receita` deixa de existir.** A consulta de hoje com esse nome compara jul/24–jun/25 com jul/25–jun/26, mas a tela Receita compara **o primeiro ano da base (jul/22–jun/23) com os últimos 12 meses (jul/25–jun/26)**. Ela é substituída pela consulta `receita` da seção 4.1. Os testes que usam o nome antigo também mudam (seção 5.6).

### 2.3 `entidade_id = 'global'`

- Nas telas sem UC, o `entidade_id` é sempre o texto `global`. A URL exige alguma coisa nessa posição.
- O cache (`tb_insights_tela`) guarda o texto pela dupla `(tela, entidade_id)`. Por isso o script de geração e o front **precisam usar o mesmo valor**. Se o script gravar com outro valor, o front nunca acha o texto no cache.
- `global` já passa na validação atual (`[A-Za-z0-9_-]{1,100}`).
- Nas consultas das telas globais, o `entidade_id` é ignorado: o SQL não tem `{id_uc}`.

### 2.4 Resposta (o que o front usa)

A resposta não muda em relação a hoje:

| Campo | Uso no front |
|---|---|
| `insight_texto` | O texto do bloco |
| `selo` | `auditado_llm` mostra "Números conferidos"; `template_fallback` mostra "Sem conferência" |
| `fontes` | Lista de tabelas, mostrada como "Fonte: …" (o case pede citar a tabela de origem) |

`metricas_destaque` e `tempo_ms` não aparecem na tela.

Como o front reage:
- **403:** o bloco some e o resto da tela continua.
- **Outros erros:** o bloco mostra o erro, com "Tentar de novo".
- **Tempo limite:** 60 s.

---

## 3. Como funciona hoje (para referência)

`InsightsService.obter(tela, entidade_id)` em `ai-agent/src/insights/service.py`:

1. Procura o texto na `tb_insights_tela` pela dupla `(tela, entidade_id)`. Se achar, devolve na hora.
2. Se não achar, roda a consulta fixa da tela (`extrair_metricas`).
3. Formata os fatos: `competencia` vira "jun/2026" e `consumo_kwh` vira inteiro.
4. A IA narra (`narrar_insight`) e o conferente confere (`conferir`). São até 3 tentativas.
5. Se uma tentativa passar: devolve com `selo = auditado_llm` e **grava no cache**.
6. Se as 3 falharem: devolve o texto-modelo (`gerar_texto_modelo`) com `selo = template_fallback` e **não grava**.

Os passos 4 a 6 já estão certos e continuam como estão.

---

## 4. As consultas de cada tela (Julio)

### 4.0 Uma tela pode ter mais de uma consulta

Hoje `QUERIES` tem **um SQL por tela**. Indicadores, Continuidade e Fila precisam de **duas** consultas, porque juntam dados de formatos diferentes (resumo + ranking). Um `UNION` só não serve, porque as colunas são diferentes.

**Mudança sugerida em `extrair_metricas`:** o valor de `QUERIES[tela]` pode ser um texto ou uma lista de textos. Com lista, a função roda cada SQL e junta as linhas na mesma lista de fatos:

```python
templates = QUERIES.get(tela)
if templates is None:
    raise ValueError(f"Tela de insight não suportada: {tela}")
if isinstance(templates, str):
    templates = [templates]
linhas: list[Dict[str, Any]] = []
for template in templates:
    resultado = executor.executar(template.format(id_uc=id_uc))
    if not resultado.sucesso:
        raise RuntimeError(f"Falha ao extrair métricas: {resultado.erro}")
    linhas.extend(resultado.linhas)
```

**Cuidados:**
- O `.format(id_uc=...)` continua só para a Visão 360. As consultas abaixo não têm chaves `{}` soltas, então o `.format` não quebra nelas.
- O `adicionar_variacao_percentual_diagnostico_receita` **sai**. As variações agora vêm prontas do SQL.

### 4.1 `receita`

**Fonte:** `agg_receita_preco_volume`, a mesma dos blocos "Ponte da receita" e "Com e sem geração própria".
**Período:** o que vem gravado na tabela (P0 = primeiro ano da base, P1 = últimos 12 meses), igual ao padrão da tela.

```sql
SELECT CASE WHEN GROUPING(possui_gd) = 1 THEN 'todas as UCs'
            WHEN possui_gd THEN 'com geração própria' ELSE 'sem geração própria' END AS grupo,
       MAX(periodo_p0) AS periodo_base,
       MAX(periodo_p1) AS periodo_comparado,
       SUM(ucs_p1)::int AS ucs,
       ROUND(SUM(receita_p0)::numeric / 1e6, 1) AS receita_base_milhoes,
       ROUND(SUM(receita_p1)::numeric / 1e6, 1) AS receita_comparada_milhoes,
       ROUND((100 * (SUM(receita_p1) / SUM(receita_p0) - 1))::numeric, 1) AS variacao_receita_pct,
       ROUND((100 * (SUM(kwh_p1) / SUM(kwh_p0) - 1))::numeric, 1) AS variacao_consumo_pct,
       ROUND(SUM(efeito_volume)::numeric / 1e6, 1) AS efeito_volume_milhoes,
       ROUND(SUM(efeito_preco)::numeric / 1e6, 1) AS efeito_preco_milhoes
FROM agg_receita_preco_volume
GROUP BY GROUPING SETS ((possui_gd), ())
ORDER BY GROUPING(possui_gd) DESC, possui_gd DESC
```

**Dados que volta hoje:**

| grupo | ucs | receita base → comparada (mi) | receita | consumo | efeito volume (mi) | efeito preço (mi) |
|---|---|---|---|---|---|---|
| todas as UCs | 45000 | 157.1 → 169.7 | 8.0 | -4.0 | -6.8 | 19.3 |
| com geração própria | 3503 | 13.4 → 6.0 | -55.0 | -60.9 | -8.1 | 0.8 |
| sem geração própria | 41497 | 143.8 → 163.7 | 13.9 | 1.0 | 1.4 | 18.6 |

**Texto esperado** (a resposta da pergunta principal do case):
> "A receita subiu 8,0%, de R$ 157,1 milhões para R$ 169,7 milhões, porque o preço somou R$ 19,3 milhões e o volume tirou R$ 6,8 milhões; a perda de volume está nas 3.503 UCs com geração própria (−R$ 8,1 milhões), enquanto nas demais o consumo cresceu 1,0%."

**Fontes:** `["agg_receita_preco_volume"]`

### 4.2 `indicadores`

**Fonte:** `agg_receita_mensal`, a mesma da tela.
**Período:** os últimos 12 meses contra os 12 anteriores, igual ao padrão da tela. A janela é calculada a partir da última competência da tabela, não de datas fixas no código.

```python
QUERIES["indicadores"] = [INDICADORES_JANELAS, INDICADORES_CLASSES]
```

**Consulta 1: as duas janelas**

```sql
WITH lim AS (SELECT MAX(competencia) AS fim FROM agg_receita_mensal)
SELECT CASE WHEN r.competencia > l.fim - INTERVAL '12 months' THEN 'últimos 12 meses' ELSE '12 meses anteriores' END AS janela,
       TO_CHAR(MIN(r.competencia), 'MM/YYYY') AS inicio,
       TO_CHAR(MAX(r.competencia), 'MM/YYYY') AS fim,
       ROUND(SUM(r.receita_faturada)::numeric / 1e6, 1) AS receita_milhoes,
       ROUND(SUM(r.consumo_kwh)::numeric / 1e6, 1) AS consumo_gwh,
       ROUND((100.0 * SUM(r.faturas_atrasadas) / SUM(r.faturas))::numeric, 1) AS faturas_atrasadas_pct
FROM agg_receita_mensal r, lim l
WHERE r.competencia > l.fim - INTERVAL '24 months'
GROUP BY 1
ORDER BY MIN(r.competencia) DESC
```

**Consulta 2: receita por classe**

```sql
WITH lim AS (SELECT MAX(competencia) AS fim FROM agg_receita_mensal)
SELECT r.classe,
       ROUND(SUM(r.receita_faturada) FILTER (WHERE r.competencia > l.fim - INTERVAL '12 months')::numeric / 1e6, 1) AS receita_ultimos_12m_milhoes,
       ROUND((100 * (SUM(r.receita_faturada) FILTER (WHERE r.competencia > l.fim - INTERVAL '12 months')
             / NULLIF(SUM(r.receita_faturada) FILTER (WHERE r.competencia <= l.fim - INTERVAL '12 months'), 0) - 1))::numeric, 1) AS variacao_receita_pct
FROM agg_receita_mensal r, lim l
WHERE r.competencia > l.fim - INTERVAL '24 months'
GROUP BY r.classe
ORDER BY 2 DESC
```

**Dados que voltam hoje:**
- **Janelas:**
  - últimos 12 meses (07/2025–06/2026): receita 169.7 mi, consumo 217.9 GWh, faturas atrasadas 7.7%;
  - 12 meses anteriores (07/2024–06/2025): receita 171.8 mi, consumo 220.0 GWh, faturas atrasadas 8.0%.
- **Classes:**

  | Classe | Receita (mi) | Variação |
  |---|---|---|
  | RESIDENCIAL | 62.4 | +2.8% |
  | INDUSTRIAL | 59.7 | −8.6% |
  | COMERCIAL | 41.7 | +3.1% |
  | PODER_PUBLICO | 3.8 | +9.8% |
  | RURAL | 2.1 | +9.4% |

**Texto esperado:**
> "Nos últimos 12 meses (07/2025 a 06/2026), a receita foi de R$ 169,7 milhões contra R$ 171,8 milhões nos 12 anteriores; a classe industrial puxou a queda, com receita 8,6% menor, e as faturas atrasadas caíram de 8,0% para 7,7%."

**Atenção:** a IA não pode dizer "queda de 1,2%" na receita, porque esse número não está nos fatos e seria conta dela. Se quiserem esse percentual no texto, acrescentem `variacao_receita_pct` na consulta 1.

**Fontes:** `["agg_receita_mensal"]`

### 4.3 `continuidade`

**Fontes:** `agg_continuidade_alimentador` e `fact_ocorrencias`, as mesmas da tela.
**Período:** os últimos 12 meses, padrão da tela. O DEC de 12 meses é a **soma do DEC mensal**, como no backend (`_sum_window` em `backend/app/services/network.py`).

**Regra do alimentador pequeno:** o ALM-JAB-016 tem só 20 UCs, e o DEC de poucas UCs oscila muito. A tela destaca o pior **entre os que têm 100 UCs ou mais**. Por isso a consulta traz os dois, e o texto deve dizer que o primeiro é pequeno.

```python
QUERIES["continuidade"] = [CONTINUIDADE_ALIMENTADORES, CONTINUIDADE_CAUSAS]
```

**Consulta 1: pior alimentador**

```sql
WITH lim AS (SELECT MAX(competencia) AS fim FROM agg_continuidade_alimentador),
a AS (
  SELECT c.alimentador, MAX(c.municipio_principal) AS municipio, MAX(c.total_ucs) AS total_ucs,
         TO_CHAR(MIN(c.competencia), 'MM/YYYY') AS inicio, TO_CHAR(MAX(c.competencia), 'MM/YYYY') AS fim,
         ROUND(SUM(c.dec)::numeric, 1) AS dec_horas, ROUND(SUM(c.fec)::numeric, 1) AS fec_vezes
  FROM agg_continuidade_alimentador c, lim l
  WHERE c.competencia > l.fim - INTERVAL '12 months'
  GROUP BY c.alimentador)
(SELECT 'maior DEC entre todos' AS destaque, * FROM a ORDER BY dec_horas DESC LIMIT 1)
UNION ALL
(SELECT 'maior DEC com 100 UCs ou mais', * FROM a WHERE total_ucs >= 100 ORDER BY dec_horas DESC LIMIT 1)
```

**Consulta 2: principais causas**

```sql
WITH lim AS (SELECT MAX(competencia) AS fim FROM fact_ocorrencias)
SELECT o.causa,
       COUNT(*) AS ocorrencias,
       ROUND((100.0 * COUNT(*) / SUM(COUNT(*)) OVER ())::numeric, 1) AS pct_das_ocorrencias,
       ROUND((100.0 * SUM(o.duracao_h) / SUM(SUM(o.duracao_h)) OVER ())::numeric, 1) AS pct_das_horas
FROM fact_ocorrencias o, lim l
WHERE o.competencia > l.fim - INTERVAL '12 months'
GROUP BY o.causa
ORDER BY ocorrencias DESC
LIMIT 3
```

**Dados que voltam hoje** (07/2025–06/2026):
- **Alimentadores:**
  - maior DEC entre todos: ALM-JAB-016 (Jaboatão dos Guararapes), 20 UCs, DEC 43.9 h, FEC 19.7;
  - maior DEC com 100 UCs ou mais: ALM-SAO-004 (São Lourenço da Mata), 1.091 UCs, DEC 15.6 h, FEC 3.4.
- **Causas:**
  - CLIMATICA: 41.0% das ocorrências, 62.1% das horas;
  - SOBRECARGA: 11.4% e 7.3%;
  - VEGETACAO: 11.2% e 7.0%.

**Texto esperado:**
> "De 07/2025 a 06/2026, o maior DEC entre os alimentadores com 100 UCs ou mais foi o do ALM-SAO-004, em São Lourenço da Mata, com 15,6 horas; o ALM-JAB-016 chegou a 43,9 horas, mas atende só 20 UCs. A causa climática respondeu por 41,0% das ocorrências e 62,1% das horas sem energia."

**Atenção:**
- O texto usa "De 07/2025 a 06/2026", e não "Nos últimos 12 meses", porque o conferente reprova o "12": ele não está nos fatos desta tela. Se quiserem escrever "últimos 12 meses", acrescentem uma coluna de texto `'últimos 12 meses' AS janela` na consulta 1, como em Indicadores.
- Os nomes das causas vêm em maiúsculas e sem acento (`CLIMATICA`, `VEGETACAO`). A IA pode escrever "climática", porque isso não é número.
- O texto-modelo (seção 5.3) deve trocar `_` por espaço e usar minúsculas.

**Fontes:** `["agg_continuidade_alimentador", "fact_ocorrencias"]`

### 4.4 `fila_inspecao`

**Fontes:** `fila_inspecao` e `fact_inspecoes`.
**Período:** a foto atual da fila (`data_referencia`) e todas as inspeções realizadas.

**Bairros críticos** são os bairros com `taxa_irregularidade_bairro >= 0.5`, ou seja, onde pelo menos metade das inspeções confirmou irregularidade. Hoje são exatamente os 4 bairros do diagnóstico da receita: Iputinga, Jardim Jordão, Prazeres e Macaxeira.

```python
QUERIES["fila_inspecao"] = [FILA_RESUMO, FILA_BAIRROS]
```

**Consulta 1: resumo da fila e das inspeções**

```sql
WITH criticos AS (
  SELECT COUNT(DISTINCT (municipio, bairro)) AS bairros, COUNT(*) AS ucs, SUM(kwh_recuperavel_estimado_ano) AS kwh
  FROM fila_inspecao WHERE taxa_irregularidade_bairro >= 0.5),
fila AS (
  SELECT COUNT(*) AS ucs, SUM(kwh_recuperavel_estimado_ano) AS kwh, MAX(data_referencia) AS ref
  FROM fila_inspecao),
insp AS (
  SELECT COUNT(*) AS feitas, COUNT(*) FILTER (WHERE resultado = 'IRREGULARIDADE_CONFIRMADA') AS confirmadas
  FROM fact_inspecoes)
SELECT TO_CHAR(f.ref, 'MM/YYYY') AS fila_de,
       f.ucs AS ucs_na_fila,
       ROUND(f.kwh::numeric / 1e3, 1) AS mwh_recuperavel_ano,
       i.feitas AS inspecoes_realizadas,
       ROUND((100.0 * i.confirmadas / i.feitas)::numeric, 1) AS irregularidade_confirmada_pct,
       c.bairros AS bairros_criticos,
       c.ucs AS ucs_em_bairros_criticos,
       ROUND((100.0 * c.kwh / f.kwh)::numeric, 1) AS pct_da_energia_em_bairros_criticos
FROM fila f, insp i, criticos c
```

**Consulta 2: os bairros críticos**

```sql
SELECT municipio, bairro,
       COUNT(*) AS ucs_na_fila,
       ROUND(SUM(kwh_recuperavel_estimado_ano)::numeric / 1e3, 1) AS mwh_recuperavel_ano,
       ROUND(MAX(taxa_irregularidade_bairro)::numeric * 100, 1) AS irregularidade_confirmada_pct
FROM fila_inspecao
WHERE taxa_irregularidade_bairro >= 0.5
GROUP BY municipio, bairro
ORDER BY ucs_na_fila DESC
```

**Dados que voltam hoje:**
- **Resumo:**
  - fila de 06/2026: 11.586 UCs, 3.024,4 MWh/ano recuperáveis;
  - 1.389 inspeções, 62,7% com irregularidade confirmada;
  - 4 bairros críticos, com 2.200 UCs, que concentram 84,8% da energia recuperável.
- **Bairros:**

  | Bairro | UCs | MWh | Irregularidade confirmada |
  |---|---|---|---|
  | Iputinga (Recife) | 743 | 882,6 | 91,0% |
  | Jardim Jordão (Jaboatão) | 687 | 752,1 | 89,6% |
  | Prazeres (Jaboatão) | 413 | 527,5 | 89,9% |
  | Macaxeira (Recife) | 357 | 403,1 | 88,7% |

**Texto esperado:**
> "A fila tem 11.586 UCs e 3.024,4 MWh/ano a recuperar, mas 84,8% dessa energia está em 2.200 UCs de 4 bairros: Iputinga (91,0% de irregularidade confirmada), Jardim Jordão (89,6%), Prazeres (89,9%) e Macaxeira (88,7%)."

**Atenção:** "4 bairros" só passa no conferente porque a coluna `bairros_criticos` traz o 4. Qualquer número no texto (quantidade, percentual, "mais de 88%") precisa estar nos fatos. Por isso o exemplo cita os percentuais de cada bairro como vieram da consulta, em vez de um valor arredondado por cima.

**Fontes:** `["fila_inspecao", "fact_inspecoes"]`

### 4.5 `visao_360_uc`

Continua como está: últimas faturas da UC em `fact_faturamento`. Uma melhoria opcional, só se sobrar tempo, é comparar o consumo com o mesmo mês do ano anterior em `fact_leituras`.

---

## 5. Outras mudanças no ai-agent (Julio)

### 5.1 Conferente: aceitar "milhões" quando o fato já está em milhões (essencial)

Testado com `conferir` da `dev`.

**O problema:** como os fatos já vêm em milhões (`receita_base_milhoes = 157.1`), a IA escreve "R$ 157,1 milhões". O conferente vê a palavra "milhões", multiplica 157,1 por 1.000.000 e procura 157.100.000 nos fatos, mas o fato é 157.1. **O texto certo é reprovado.**

| Fatos | Texto | Resultado hoje |
|---|---|---|
| `receita_base_milhoes: 157.1` | "R$ 157,1 milhões" | ❌ reprovado (errado) |
| `receita_base_milhoes: 157.1` | "R$ 157,1 mi" | ✅ passa ("mi" não é uma escala conhecida) |
| `receita_base: 157110000.0` (valor cru) | "R$ 157,1 milhões" | ❌ reprovado: a folga de arredondamento (0,05) não é multiplicada pela escala |

**Correção sugerida** em `ai-agent/src/insights/conferente_numerico.py`: quando o número vier com escala, aceitar também a leitura sem a escala. Isso vale em `conferir` e em `numeros_nao_encontrados`:

```python
aceito = any(
    _bate(valor, casas, multiplicador, permitido, tolerancia)
    or (multiplicador != 1 and _bate(valor, casas, 1, permitido, tolerancia))
    for valor, casas in leituras
    for permitido in permitidos
)
```

Testei essa mudança com os fatos reais das consultas da seção 4. Os textos esperados de Receita, Indicadores, Continuidade e Fila passam, e "A receita subiu 12,6 milhões" (número que não está nos fatos) continua reprovado.

**Cuidado com números arredondados pela IA:** o conferente aceita a diferença de arredondamento na casa do número escrito. Por isso "90%" passa para um fato de 89,6, mas "mais de 88%" não passa. É mais um motivo para o prompt pedir os valores exatamente como vieram.

**Teste para acrescentar:** fatos `{"receita_base_milhoes": 157.1, "efeito_volume_milhoes": -6.8}`:
- "R$ 157,1 milhões … tirou R$ 6,8 milhões" → `True`;
- "R$ 12,6 milhões" → `False`.

### 5.2 Narrador: contexto por tela

O prompt novo da `usando-genai` está bom: proíbe contas, conversões e arredondamentos, e trata os fatos só como dados. Duas coisas a acrescentar:

1. **O que destacar em cada tela.** Sem isso, a IA escolhe o fato "mais relevante" sozinha. Sugestão: um dicionário `FOCO_POR_TELA`, colocado no prompt depois da linha "Tela (contexto)":

| `tela` | Foco |
|---|---|
| `receita` | Quanto a receita variou, quanto veio do preço e quanto do volume, e que a perda de volume está nas UCs com geração própria |
| `indicadores` | Receita e consumo dos últimos 12 meses contra os 12 anteriores, a classe que mais variou e as faturas atrasadas |
| `continuidade` | O pior alimentador com 100 UCs ou mais; se o maior DEC geral for de um alimentador com menos de 100 UCs, dizer que ele é pequeno; a principal causa |
| `fila_inspecao` | Tamanho da fila e energia recuperável, e quanto dela está nos bairros com irregularidade confirmada alta |
| `visao_360_uc` | O de hoje |

2. **Uma ou duas frases.** O prompt pede "uma única frase". Para Receita e Continuidade, uma frase com todos os números fica longa demais. Sugiro "no máximo duas frases curtas".

**Nomes de coluna em português ajudam a IA.** As consultas da seção 4 já usam `receita_base_milhoes`, `dec_horas`, `pct_das_horas`. Com esses nomes, a IA escreve a unidade certa sem precisar de conversão.

### 5.3 Texto-modelo por tela (essencial)

Hoje `gerar_texto_modelo` só sabe montar a frase da Visão 360. Para as outras telas, ele devolve `"Dados recentes da tela: grupo: todas as UCs, periodo_base: ..."`, com nomes técnicos na tela. Como ele aparece quando a IA falha 3 vezes, **precisa de uma frase por tela**, montada direto dos fatos, em português e com números no formato brasileiro. Exemplos:

- **receita:** "Entre {periodo_base} e {periodo_comparado}, a receita passou de R$ {base} milhões para R$ {comparada} milhões: efeito preço de R$ {preco} milhões e efeito volume de R$ {volume} milhões."
- **indicadores:** "Nos últimos 12 meses ({inicio} a {fim}), a receita foi de R$ {receita} milhões e o consumo de {consumo} GWh."
- **continuidade:** "De {inicio} a {fim}, o maior DEC entre os alimentadores com 100 UCs ou mais foi o do {alimentador}, com {dec} horas."
- **fila_inspecao:** "A fila tem {ucs} UCs e {mwh} MWh/ano de energia recuperável estimada."

O formato brasileiro já existe no ramo da Visão 360 (`replace(",", "X")...`). Vale extrair uma função `_numero_br(valor, casas)` e reusar.

**Mensagem sem dados:** quando não há fatos, `obter` responde "Não há dados disponíveis para esta unidade consumidora." Para as telas globais, use "Não há dados disponíveis para este insight no momento." (a mesma do narrador).

### 5.4 Fontes

Atualizar `FONTES_POR_TELA` com as fontes de cada tela da seção 4 e tirar `diagnostico_receita`.

### 5.5 Script de geração antecipada (essencial para a apresentação)

**Arquivo novo:** `ai-agent/scripts/gerar_insights_telas.py`. Para cada tela global (`receita`, `indicadores`, `continuidade`, `fila_inspecao`), ele:

1. **Apaga** a linha `(tela, 'global')` da `tb_insights_tela`, para gerar com os dados atuais.
2. Chama `InsightsService().obter(tela, "global")`.
3. Imprime a tela, o selo e o texto.

Se algum selo vier `template_fallback`, basta rodar de novo: o fallback não é gravado.

**Quando rodar:**
- depois de cada carga da Gold, porque o texto em cache fica velho se os dados mudarem;
- uma vez no dia 9, antes da apresentação.

Para a Visão 360 não precisa: cada UC gera o seu texto na primeira abertura.

Ler o `.env.local` do backend do mesmo jeito que os outros scripts de `ai-agent/scripts/`. **Nunca imprimir a URL do banco.**

### 5.6 Testes

- **Atualizar ou apagar** os testes que usam `diagnostico_receita`:
  - `test_diagnostico_receita_compara_janelas_de_12_meses.py`
  - `test_variacao_percentual_diagnostico_receita.py`
  - partes de `test_insights_meses_fontes_fixas_e_formato_brasileiro.py`
- **Novos:**
  - `extrair_metricas` com lista de SQL junta as linhas;
  - cada tela nova tem consulta e fontes;
  - tela desconhecida dá `ValueError`;
  - texto-modelo de cada tela sem nome técnico de campo;
  - conferente com "milhões" (seção 5.1).

---

## 6. O que o Nunno faz (para o Julio saber)

### 6.1 Backend: permissão por tela

**O problema:** hoje a rota tem uma permissão só (`CUSTOMER_SERVICE` em `backend/app/security/permissions.py`). Com ela, a Operação não veria o insight da Continuidade, e a Diretoria nunca veria o da Fila.

**A mudança:**
- A rota passa a aceitar todos os perfis.
- Um mapa novo, `INSIGHT_PERMISSIONS`, diz quem vê cada `tela`, com os perfis da tabela da seção 2.2.
- `authorize_business_route` (`backend/app/security/dependencies.py`) passa a ler `request.path_params["tela"]` nessa rota.
- Tela fora do mapa, ou perfil sem acesso, recebe **403**.

O ai-agent não muda nada por causa disso.

### 6.2 Front

- `TelaInsight` em `frontend/src/hooks/use-insight-ia.ts` passa a aceitar as 5 telas.
- O componente `InsightIa` entra no topo de Receita, Indicadores, Continuidade e Fila, com `entidade_id = 'global'` e a frase "Visão geral da base completa · não muda com os filtros".
- Testes de cada tela.

---

## 7. Ordem de trabalho e quando está pronto

1. **Combinar os nomes da seção 2.2** (feito neste documento).
2. **Julio:** seções 4.0, 4.1, 5.1 e 5.3 (receita). **Nunno:** seção 6 inteira. As duas partes podem andar em paralelo, porque o contrato já está fixo.
3. **Julio:** continuidade (4.3), depois indicadores (4.2) e fila (4.4). **Se o tempo apertar, parem em receita + continuidade.** É melhor ter 2 insights confiáveis do que 4 com risco de número errado.
4. **Julio:** script de geração (5.5) e testes (5.6).
5. **Juntos:** abrir cada tela com cada perfil e conferir os números do insight contra os blocos da tela.
6. **Dia 8 à noite:** PR da `usando-genai` para a `dev` e congelar.
7. **Dia 9:** rodar o script de geração antes da apresentação.

**Pronto quando:**
- [ ] As 4 telas globais abrem o insight na hora (cache gerado pelo script), com selo "Números conferidos".
- [ ] Cada número do insight é igual ao número do bloco correspondente da tela.
- [ ] Cada perfil vê só os insights das telas que pode abrir (os outros dão 403 e o bloco some).
- [ ] O texto-modelo de cada tela está em português, sem nome de coluna.
- [ ] Testes do ai-agent, do backend e do front passando.

---

## 8. Observações

- **PR #92 (permissões no banco, do Ladstone): ficou para depois da entrega.**
  - Ele muda a assinatura de `InsightsService.obter` (ganha `perfil`) e o `_ler_cache` / `_gravar_cache`.
  - Quando for juntado, vai ter conflito em `ai-agent/src/insights/service.py`. É simples de resolver: manter as mudanças dos dois lados.
- **Nada de dado pessoal no insight.**
  - Nenhuma consulta da seção 4 lê nome, CPF ou endereço.
  - A `fila_inspecao` tem `nome_titular` e `logradouro`. As consultas acima não usam essas colunas, e não devem passar a usar.
