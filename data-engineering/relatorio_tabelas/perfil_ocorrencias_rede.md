# Perfil de dados: `ocorrencias_rede.csv`

**Status:** quase completo (falta a célula 12, seção 8)
**Última atualização:** 25/10/2026
**Fonte:** `/Volumes/v-energy/raw_data/raw_data/ocorrencias_rede.csv` (CSV `,`, lido como texto)

---

## 1. Visão geral

| Item | Valor |
|---|---|
| Registros | **180.000** (o case fala em ~180 mil). Todas as linhas têm 8 campos; não há cabeçalho repetido. |
| Colunas (8) | id_ocorrencia, alimentador, id_uc, tipo, causa, data_abertura, data_encerramento, duracao_min |
| Período | 01/07/2022 a 30/06/2026 (aberturas) |
| **Grão** | **1 registro = 1 UC interrompida**, e cada `id_ocorrencia` é **único** (180.000 eventos, cada um com 1 UC). Bate com a definição do case. |
| `tipo` | FALTA DE ENERGIA 121.593 · DANO EM EQUIPAMENTO 14.868 · OSCILACAO 14.562 · SOBRECARGA 14.547 · FIO PARTIDO 14.430 |
| `causa` | CLIMATICA 43.692 · SOBRECARGA 26.328 · NAO IDENTIFICADA 26.328 · VEGETACAO 26.160 · TERCEIROS 26.147 · FALHA DE EQUIPAMENTO 25.945 · **sem informação 5.400** |
| Duração | mínimo de 8 min · p25 38 · **mediana 73** · p75 139 · p99 745 · **máximo 2.880 (48 h)** |

---

## 2. O que veio limpo

- **IDs:** `id_ocorrencia` sempre `OC99999999` e único; `id_uc` sempre `UC999999`; `alimentador` sempre `ALM-XXX-999`.
- **Datas:** formato único `yyyy-MM-dd HH:mm:ss`. Nenhuma data inválida, futura ou nula. **O encerramento é sempre posterior à abertura** (0 casos de encerramento antes ou no mesmo instante; 0 sem encerramento).
- **A duração bate 100% com `encerramento − abertura`** (180.000 de 180.000). Não há conflito entre as duas fontes.
- **Nenhuma interrupção com menos de 3 minutos.** O PRODIST só conta no DEC/FEC as interrupções de longa duração (≥ 3 min), então todas entram.
- **Integridade:** nenhuma ocorrência sem UC, em UC TESTE ou sem alimentador.
- **Coerência com o cadastro:** em **100%** dos registros, o alimentador da ocorrência é o mesmo alimentador da UC no cadastro.
- **`tipo`:** 5 valores, sem variação de escrita.

---

## 3. Problemas encontrados

| # | Problema | Evidência | Tamanho |
|---|---|---|---|
| 1 | **`causa` sem informação, em 4 formas diferentes** | `null` (1.356), `-` (1.363), `N/A` (1.341), `NULL` (1.340) | **5.400 (3%)** |
| 2 | `duracao_min` com o sufixo `" min"` | `"217 min"` | 16.200 (9%) |
| 3 | **Durações truncadas em 2.880 min (48 h)**, confirmado | A cauda acima de 24 h cai suavemente (60 → 47 → 29 → … → 5–11 por faixa de 2 h) e depois dá um **salto para 30 exatamente em 2.880**. É uma "parede": as interrupções mais longas foram cortadas em 48 h. **26 das 30 são de jul/2025.** | 30 registros. O DEC de jul/2025 está levemente subestimado. |
| 4 | **Decisão conceitual: OSCILACAO entra no DEC/FEC?** | Na regulação, oscilação é um problema de qualidade da energia, não uma interrupção. Mas o case diz que "cada registro corresponde a uma UC interrompida". | 14.562 (8%) |

**Atenção para não confundir:** `NAO IDENTIFICADA` (26.328) é uma **categoria válida** (a equipe foi a campo e não achou a causa). É diferente de "sem informação" (o campo não foi preenchido). As duas devem ficar separadas.

---

## 4. Tratamento proposto para a Silver

| # | Regra |
|---|---|
| 1 | `causa`: `null`, `-`, `N/A` e `NULL` → `NAO INFORMADA` (mantendo `NAO IDENTIFICADA` como está) |
| 2 | `duracao_min`: tirar o `" min"` e converter com `try_cast` (o código do colega já faz) |
| 3 | `data_abertura` / `data_encerramento`: `try_to_timestamp` no formato ISO |
| 4 | Flag `duracao_truncada = (duracao_min == 2880)`, documentando que a duração real é ≥ 48 h |
| 4a | Flag `dia_critico` (ver a seção 7) e DEC/FEC calculados **com e sem** o expurgo |
| 5 | Teste de qualidade: `duracao_min = encerramento − abertura` (hoje 100%) |
| 6 | **Decisão a documentar:** seguir o case e contar todos os tipos no DEC/FEC, oferecendo no portal um filtro que exclua OSCILACAO. A recomendação é contar tudo, para seguir o enunciado, e citar a ressalva no dicionário. |

---

## 5. O que o notebook atual (`bronze_to_silver.py`) já cobre

| Item | Situação |
|---|---|
| Duração com `" min"` | ✅ `regexp_replace(" min", "")` resolve todos os casos da base |
| Datas | ✅ O formato único funciona (mas usa cast comum, não `try_`) |
| `tipo` / `causa` em maiúsculas | 🟡 Funciona para `tipo`. **Em `causa`, mantém `-`, `N/A` e `NULL` como se fossem 3 causas diferentes.** |
| Deduplicação | ⚪ Não faz, mas não há duplicatas (`id_ocorrencia` é único) |
| Integridade | ⚪ Não verifica, mas está 100% ok |

**Na Gold (DEC/FEC):**
- A fórmula do colega (`DEC = Σ horas ÷ UCs do alimentador`; `FEC = nº de registros ÷ UCs`) **está correta para este grão**.
- O `coalesce(total_consumidores, 1)` (G-01) **não tem efeito hoje**, porque todos os alimentadores existem no cadastro. Continua sendo frágil.

---

## 6. Prévia do DEC/FEC (2025, último ano completo)

| Alimentador | UCs | Interrupções × UC | DEC (h) | FEC |
|---|---|---|---|---|
| ALM-JAB-016 | 20 | 394 | 42,49 | 19,70 |
| ALM-SAO-001 | 32 | 390 | 24,03 | 12,19 |
| ALM-JAB-015 | 34 | 368 | 22,64 | 10,82 |
| ALM-REC-039 | 32 | 329 | 21,09 | 10,28 |
| … | | | | |
| ALM-SAO-004 | 1.091 | 3.680 | 15,51 | 3,37 |
| ALM-REC-008 | 2.285 | 7.181 | 15,03 | 3,14 |

### ⚠️ Os alimentadores pequenos dominam o ranking: efeito do denominador (confirmado na 12d)

São **122 alimentadores** no total. O número de interrupções por ano é **praticamente o mesmo** em todos os que têm menos de 1.000 UCs:

| Tamanho | Alimentadores | Interrupções por ano (média) | DEC médio | FEC médio |
|---|---|---|---|---|
| < 100 UCs | 14 | 368 | **16,13** | **8,01** |
| 100–499 | 77 | 363 | 3,29 | 1,61 |
| 500–999 | 26 | 461 | 1,77 | 0,71 |
| 1.000+ | 5 | 2.388 | 6,48 | 1,49 |

A correlação entre tamanho e FEC é de −0,39. Ou seja, **os alimentadores pequenos não são piores em si**: eles recebem o mesmo número de interrupções que os médios, e o denominador pequeno infla o DEC/FEC. O ALM-JAB-016 (20 UCs) lidera o ranking por isso.

**Na apresentação:** mostrar o ranking de DEC/FEC **com o número de UCs ao lado** e uma ressalva para alimentadores com menos de 100 UCs, ou um ranking que só considere alimentadores acima de um tamanho mínimo.

### 3 alimentadores concentram o impacto absoluto

| Alimentador | UCs | Horas × UC (2025) | DEC | FEC |
|---|---|---|---|---|
| ALM-REC-008 | 2.285 | **34.347** | 15,03 | 3,14 |
| ALM-SAO-004 | 1.091 | **16.926** | 15,51 | 3,37 |
| ALM-JAB-004 | 863 | **13.244** | 15,35 | 3,42 |
| (4º lugar) ALM-OLI-003 | 359 | 897 | 2,50 | 0,98 |

Os 3 primeiros somam ~64 mil horas × UC, **~70 vezes** o 4º colocado.

### ⚠️ Mas o impacto deles vem só do evento de jul/2025 (célula 13c)

| Alimentador | DEC 2025 com jul | **DEC 2025 sem jul** | FEC com jul | FEC sem jul |
|---|---|---|---|---|
| ALM-REC-008 | 15,03 | **0,20** | 3,14 | 0,13 |
| ALM-SAO-004 | 15,51 | **0,45** | 3,37 | 0,30 |
| ALM-JAB-004 | 15,35 | **0,65** | 3,42 | 0,41 |
| (comparação) ALM-OLI-003 | 2,50 | 1,69 | 0,98 | 0,86 |

Sem julho de 2025, **os 3 estão entre os melhores alimentadores da base**. Eles não são cronicamente ruins: foram **o epicentro do temporal**. Isso muda a recomendação para a Operação:

- **Não existe um "pior alimentador crônico"** além do efeito do denominador. Fora do evento, as interrupções se distribuem de forma uniforme (~365 por alimentador por ano).
- **O principal risco da rede é climático e concentrado:** os 3 alimentadores (Recife, São Lourenço da Mata e Jaboatão, ~4,2 mil UCs, ~9,4% da base) concentraram 72% das ocorrências de jul/2025. A recomendação é de **resiliência a eventos climáticos** nesses circuitos (reforço de rede, planos de contingência), e não de manutenção de rotina.

**Recomendação para o portal (Gerente de Operação):** mostrar **dois rankings**.
- **Qualidade por cliente (DEC/FEC):** "onde o cliente sofre mais", com o número de UCs visível ao lado.
- **Impacto total (horas × UC, absoluto):** "onde a manutenção preventiva dá mais retorno". Aqui lideram os alimentadores grandes, como o ALM-REC-008, com 34.347 horas × UC em 2025.

Isso responde literalmente às duas perguntas da gerente ("quais regiões concentram as piores interrupções" e "onde a manutenção preventiva dá mais retorno").

---

## 7. ⭐ O evento climático de julho de 2025 (causa da crise de atendimento)

| Métrica | Mês normal | **jul/2025** | Razão |
|---|---|---|---|
| Ocorrências | ~3.370 | **17.844** | **5,3×** |
| Horas × UC interrompidas | ~5.550 | **87.385** | **15,7×** |
| Duração mediana | ~66 min | **197 min** | 3× |
| Durações de 48 h (truncadas) | 0–1 | **26** | — |
| **% causa CLIMÁTICA** | ~16% | **97,2%** | — |

Em jul/2025, **97,2% das ocorrências tiveram causa climática**. Não houve nenhuma por vegetação, terceiros, equipamento ou sobrecarga. Nos demais meses, as 6 causas se dividem igualmente (~16% cada). Julho é o auge das chuvas no Recife.

**Isso explica a crise de atendimento (N-06):** no mesmo mês, os chamados triplicaram (18.061), a satisfação caiu de 4,1 para 3,1 e a resolução passou de 5 para 15 dias. A história completa para a apresentação:

> *"Um evento climático em julho de 2025 multiplicou as interrupções por 5 e as horas sem energia por 16. O call center recebeu o triplo de chamados, o tempo de resolução triplicou e a satisfação caiu um ponto inteiro."*

### Impacto regulatório: dia crítico

O PRODIST (Módulo 8) prevê o **expurgo de interrupções ocorridas em "dia crítico"**: um dia em que o número de ocorrências supera muito a média (em linhas gerais, média + 3 desvios-padrão dos valores diários). Elas são acompanhadas à parte e não entram no DEC/FEC regulatório. Os dias de jul/2025 provavelmente se enquadram. **Recomendação:** mostrar no portal o DEC/FEC **com e sem** o expurgo, e documentar a regra simplificada usada.

**Resultado (célula 13b), com a regra simplificada de ocorrências do dia > média + 3 desvios-padrão em toda a base:** são **31 dias críticos, que são exatamente os 31 dias de julho de 2025** (de 541 a 628 ocorrências por dia, contra ~110 num dia normal). Nenhum outro dia da base se enquadra, nem os de nov/2025 e fev/2026. A regra do PRODIST é aplicada por conjunto de UCs; a versão por base inteira é uma simplificação que vai documentada.

### Onde o temporal caiu (célula 13a)

| Alimentador | Ocorrências em jul/2025 | Média mensal normal | Vezes o normal |
|---|---|---|---|
| **ALM-REC-008** | 6.887 | 27,7 | **249×** |
| **ALM-SAO-004** | 3.351 | 27,2 | **123×** |
| **ALM-JAB-004** | 2.598 | 27,2 | **96×** |
| Os demais (119) | 53–59 cada no topo | ~27 | ~2× |

Os 3 alimentadores somam **12.836 das 17.844 ocorrências do mês (72%)**. O resto da rede teve cerca do dobro do normal.

### Picos secundários: nov/2025 e fev/2026

| Mês | Ocorrências | Horas × UC | % climática | Chamados |
|---|---|---|---|---|
| nov/2025 | 5.317 (+58%) | 8.953 | 16,8% (normal) | 6.349 (normal) |
| fev/2026 | 5.302 (+57%) | 8.653 | 15,8% (normal) | 6.485 (normal) |

Esses dois meses têm ~1.900 ocorrências a mais, mas **com a mistura de causas normal e sem efeito no call center**.

**Resultado da célula 13a: não são localizados.** Em nov/2025 e fev/2026, **todos** os alimentadores ficam em ~1,8–2,4× a própria média, e todas as regiões crescem na mesma proporção. Um aumento difuso, sem causa climática e sem reflexo nos chamados, era suspeito de **duplicação**. **A célula 14 descartou essa hipótese:**

| Teste | Resultado |
|---|---|
| 14a. Numeração dos ids | **Sequencial e cronológica.** Nov/2025 ocupa 149.172–154.488 e fev/2026 ocupa 161.160–166.461, colados nos meses vizinhos. Não há um bloco adicionado depois. |
| 14b. Gêmeos em outros meses | Nenhum (a saída não foi enviada, o que pela convenção do time significa vazio). |
| 14c. Ocorrências por UC no mês | A distribuição cresce como esperado num **aumento uniforme da taxa**: UCs com 1 ocorrência +45%, com 2 ~2×, com 3 ~3,5× (out/25: 2.983 / 192 / 12 / 1 → nov/25: 4.319 / 396 / 43 / 11). Isso é diferente de cópia, que só duplicaria registros. |

**Conclusão:** são **aumentos genuínos e difusos**, sem causa identificável nos dados. Os registros ficam na Silver, e os meses são documentados como atípicos.

**Detalhe para a visão 360:** em nov/2025 e fev/2026 aparecem **UCs com 5 a 9 interrupções no mesmo mês** (o máximo num mês normal é 4–5). São clientes com interrupção recorrente, um dado útil para o atendente quando o cliente liga reclamando.

---

## 8. Pendências

- [x] Célula 12: evento climático de jul/2025 confirmado, teto de 48 h confirmado, efeito do denominador confirmado, chamados × ocorrências cruzados.
- [x] Célula 13a: o temporal se concentrou em 3 alimentadores (72%); os picos de nov e fev são difusos.
- [x] Célula 13b: 31 dias críticos, todos em jul/2025.
- [x] Célula 13c: sem julho, os 3 alimentadores de maior impacto estão entre os melhores da base.
- [x] Célula 14: os picos de nov/2025 e fev/2026 **não são duplicação** (ids sequenciais, sem gêmeos, aumento uniforme da taxa).

**Perfil das ocorrências: FECHADO.**
