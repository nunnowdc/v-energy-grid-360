# Perfil de dados: `leituras_2022..2026.csv`

**Status:** completo quanto às análises (faltam os itens da seção 6)
**Última atualização:** 21/10/2026
**Fonte:** `/Volumes/v-energy/raw_data/raw_data/leituras_202X.csv` (5 CSVs `,`, lidos como texto)
**Base das análises:** notebook `tabelas_leituras_visualizacao`

---

## 1. Visão geral

| Item | Valor |
|---|---|
| Linhas | **2.182.468** (o case fala em ~2,18 milhões divididos em 5 tabelas) |
| Arquivos | `leituras_2022.csv` … `leituras_2026.csv`; cobertura de **2022-07-01 a 2026-06-28** (2022 começa em julho; 2026 é ano parcial) |
| Contagem por arquivo | 2024: 545.652 · 2025: 546.908 · 2026: 273.618 (parcial) · 2022+2023: 816.290 (divisão por arquivo pendente, seção 6) |
| Colunas (9) | id_leitura, id_uc, id_medidor, data_leitura, mes_referencia, leitura_anterior, leitura_atual, consumo_kwh, tipo_leitura |
| `tipo_leitura` | REAL 1.786.380 (81,9%) · ESTIMADA 396.088 (18,1%), sem nulos |
| Tabela fato do modelo | é o grão mais fino do case: 1 linha por leitura realizada num mês de referência |

---

## 2. Problemas encontrados

| # | Problema | Evidência | Tamanho |
|---|---|---|---|
| 1 | **`data_leitura` em 4 formatos** | ISO `yyyy-MM-dd` (1.920.533), `dd.MM.yyyy` (87.618), `dd/MM/yyyy` (87.173), traço curto `99-99-9999` (87.144) | 262.935 linhas (12%) fora do ISO |
| 2 | **O formato com traço mistura `dd-MM` e `MM-dd`** | `01-01-2023` só cabe como dia-mês; `12-28-2025` só cabe como mês-dia. Não é um formato único. | 87.144 linhas |
| 3 | **Sentinela `-1` em `leitura_anterior`** | Único valor ≤ 0 da coluna, nunca aparece em `leitura_atual`, e o `consumo_kwh` declarado nessas linhas é plausível (ex.: 214) enquanto a subtração daria 89.538 | 8.068 linhas (6.604 REAL + 1.464 ESTIMADA) |
| 4 | String `'NULL'` em `leitura_anterior` | Valor literal, quebra `cast` comum | 24.667 linhas |
| 5 | **`consumo_kwh` NÃO é derivável de `atual - anterior`** | 536.473 divergentes, quase todos por ±1 (arredondamento na origem); nos resets e sentinelas a diferença chega a 89 mil | 24,6% das linhas |
| 6 | `consumo_kwh` ≤ 0, **negativos gigantes** | `leitura_atual << leitura_anterior`, valores de -3.379 a **-2.098.259 kWh**, 95% REAL | 6.595 linhas (reset/troca de medidor) |
| 7 | `consumo_kwh` ≤ 0, **negativos pequenos** | A leitura **subiu** mas o consumo declarado é negativo (-24 a -500): retificação comercial, não medição física | 1.555 linhas |
| 8 | **As leituras estimadas são "materializadas" nos números** | O erro declarado-vs-diferença é idêntico nos dois tipos (mediana 0, p95 de 1 kWh) | 396.088 linhas ESTIMADA (seção 3) |

### O que veio limpo

- `tipo_leitura`: exatamente 2 valores, **sem** variantes de caixa, acento ou espaço, sem nulos.
- `leitura_atual`: nenhum valor ≤ 0 e nenhum não-numérico.
- `consumo_kwh`: nenhum não-numérico.
- `data_leitura`: nenhum nulo; 100% das linhas parseiam com os 4 formatos mapeados.
- **`mes_referencia` é 100% coerente**: toda `data_leitura` parseada cai dentro do mês de referência (0 violações em 2,18 milhões). É a âncora de validação da tabela.

---

## 3. As duas armadilhas da tabela (evidência)

### A) O formato com traço mistura os dois sentidos — e o `mes_referencia` desempata

Diferente do `medidores.csv` (onde o traço curto parece ser sempre `MM-dd-yyyy`), aqui **os dois sentidos coexistem no mesmo padrão**. A desambiguação validada no notebook (célula 15):

1. 1º número > 12 → só pode ser dia → `dd-MM-yyyy`
2. 2º número > 12 → só pode ser mês → `MM-dd-yyyy`
3. Ambos ≤ 12 → tentar as duas leituras e escolher a que cai dentro do `mes_referencia`

**Resultado:** 0 linhas sem parse, 0 fora do mês de referência, 0 nulos — validação de 100% da base.

### B) As leituras ESTIMADAS são materializadas nas leituras

| Métrica | REAL | ESTIMADA |
|---|---|---|
| Leituras válidas | 1.751.920 | 389.778 |
| Consumo médio / mediano | 414,8 / 168 kWh | 412,4 / 170 kWh |
| Erro declarado vs `atual-anterior`: mediana / p95 | 0 / 1 kWh | 0 / 1 kWh |
| Valores exatos | ~75% | ~75% |

O erro idêntico indica que na leitura estimada o sistema gravou `leitura_atual = leitura_anterior + consumo_estimado`. **Impossível distinguir estimada de real olhando os números — o label `tipo_leitura` é a única evidência.** Além disso, o estimado fica consistentemente 0,3–0,7% abaixo do real em todos os anos, com participação estável (~19% em 2022-2025, 14,1% no parcial de 2026).

**Nota sobre geração distribuída:** só 7% das linhas com consumo negativo são de UCs com GD (proporção igual nos dois grupos), então **GD não explica os negativos** — vêm de troca de medidor (gigantes) e retificação (pequenos), não de medição líquida solar.

---

## 4. Tratamento proposto para a Silver

| # | Regra | Destino |
|---|---|---|
| 1 | `data_leitura`: função `parse_data_leitura` (célula 15): 4 regex + desambiguação pelo `mes_referencia` | Silver |
| 2 | `leitura_anterior = -1` → `null` (sentinela "sem leitura anterior"), **nunca 0** (0 é leitura legítima e inflaria o consumo) | Silver |
| 3 | `'NULL'` string → `null`, via `try_cast` em todos os casts numéricos | Silver |
| 4 | **Não recomputar `consumo_kwh` a partir do diff**: manter o valor declarado (é a medida oficial com arredondamentos e tratamentos próprios) | Silver |
| 5 | Diff < 0 (gigantes) → quarentena `ANOMALIA_VIRADA_MEDIDOR`, com **motivo separado** para anterior nulo (`ANTERIOR_AUSENTE`) | Quarentena |
| 6 | Negativos pequenos (-500 a 0) → manter o declarado + flag `RETIFICACAO` | Silver |
| 7 | Propagar `tipo_leitura` e `mes_referencia` até a gold (label é a única evidência de estimativa; `mes_referencia` é chave de faturamento) | Gold |
| 8 | Validação automática: `date_format(data_leitura, 'yyyy-MM') == mes_referencia` (0 violações hoje) — teste de qualidade diferencial no case | Silver |

---

## 5. O que o notebook atual (`bronze_to_silver.py`) já cobre

Gravou `silver_leituras: 2.151.474 | silver_leituras_quarentena: 30.994`.

| # | Problema | Situação |
|---|---|---|
| 1 | Cabeçalho repetido | ✅ Filtra `id_leitura != "id_leitura"` |
| 2 | `'NULL'` em `leitura_anterior` | ✅ `try_cast` vira null — mas o efeito colateral vai para a quarentena com o motivo errado (ver #5) |
| 3 | Formatos de data | 🟡 `coalesce` com `try_to_date` cobre ISO, ponto e barra, **mas testa `dd-MM-yyyy` antes de `MM-dd-yyyy`** — aqui os dois coexistem, então datas `MM-dd` com dia ≤ 12 saem com dia/mês trocados, sem aviso. Falta o desempate pelo `mes_referencia` |
| 4 | Sentinela `-1` | ❌ **Bug.** `diff = atual - (-1) = atual + 1` → as 8.068 linhas de primeira leitura ganham consumo absurdo (até ~96.538 kWh) com status `OK` |
| 5 | Resets de medidor | ✅ diff < 0 → quarentena `ANOMALIA_VIRADA_MEDIDOR` (6.327). Somadas às 24.667 de anterior nulo, fecham exatamente as 30.994 da quarentena — **dois problemas diferentes com um rótulo só** |
| 6 | Consumo declarado | ⚠️ `consumo_kwh` é **recomputado** do diff; o declarado fica em `consumo_bruto`. Nos 24,6% divergentes o valor muda ±1, e nas sentinelas `-1` vira absurdo (ver #4) |
| 7 | Retificações pequenas | 🟡 diff ≥ 0 → usa o diff com flag `SINAL_CORRIGIDO`; a retificação declarada só sobrevive em `consumo_bruto` |
| 8 | `tipo_leitura` / `mes_referencia` | ✅ Mantidos como estão (correto: já vêm limpos) |

---

## 6. Pendências

- [ ] Contagem bruta por arquivo de 2022 e 2023 (células 4-5) para fechar a visão geral.
- [ ] Duplicatas de `id_leitura` e de `id_uc + mes_referencia` (não verificadas).
- [ ] Granularidade: 1 leitura por UC/mês de referência?
- [ ] Continuidade da série: `leitura_atual` do mês N == `leitura_anterior` do mês N+1.
- [ ] Cruzar com a campanha de troca de medidores (perfil_medidores, seção 7): consumo antes/depois da troca.

---

## 7. Achado para o diagnóstico de receita

**As leituras estimadas (~19% do total) são indistinguíveis nos números e subestimam o consumo real em ~0,3–0,7%.**

- A receita medida em `leituras` mistura medição e estimativa sem assinatura numérica. Sem propagar `tipo_leitura` até a gold, nenhuma análise consegue segregar as duas.
- Como o viés das estimadas é sempre para baixo, o consumo agregado fica levemente menor que o realizado — relevante ao comparar períodos (o Diretor Comercial compara "últimos 12 meses" com o primeiro ano).
- **Os resets de medidor batem com a campanha de troca set/2025–mar/2026** do perfil_medidores: o consumo negativo gigante na leitura da troca é o rastro da substituição. UCs trocadas devem ter consumo medido **maior** depois da troca (medidor antigo registra menos) — cruzamento antes/depois é a confirmação.
- A hipótese "consumo negativo = geração distribuída" foi testada e **descartada** (GD aparece em só 7% dos negativos, igual à base).

Cuidados antes de afirmar na apresentação:

- O valor declarado (`consumo_kwh`) é o oficial de faturamento; qualquer recomputação pela diferença das leituras muda 24,6% dos valores e destrói os casos de reset/sentinela.
- A quarentena atual mistura reset de medidor com `leitura_anterior` ausente — antes de usar `silver_leituras_quarentena` em análise, separar os motivos.
