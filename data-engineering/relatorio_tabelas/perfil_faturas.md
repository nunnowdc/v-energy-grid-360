# Perfil de dados: `faturas.csv`

**Status:** quase completo (faltam os itens da seção 8)
**Última atualização:** 24/10/2026
**Fonte:** `/Volumes/v-energy/raw_data/raw_data/faturas.csv` (CSV `;`, lido como texto)

---

## 1. Visão geral

| Item | Valor |
|---|---|
| Linhas de dados | **2.184.621** (o case fala em ~2,18 milhões) |
| Colunas (11) | id_fatura, id_uc, mes_referencia, data_emissao, valor_energia, tributos, bandeira_tarifaria, valor_total, data_vencimento, data_pagamento, status |
| ⚠️ **Coluna de kWh** | **NÃO EXISTE.** O volume faturado terá de vir das leituras (consumo medido). |
| Período (competência) | jul/2022 a jun/2026 (48 meses), de ~45,3 mil a ~45,7 mil faturas por mês |
| Status | PAGA 2.009.453 · EM ABERTO 175.168 (8,0%) |
| Estrutura do arquivo | Todas as linhas têm 11 campos. Há 3 linhas a mais que os dados no texto cru: o cabeçalho e, provavelmente, 2 cabeçalhos repetidos (a confirmar). |

---

## 2. O que veio limpo

- **`valor_energia` e `tributos`:** 100% no formato `ponto_decimal`, sem negativos nem zeros. `tributos` corresponde sempre a ~1/3 de `valor_energia` (alíquota constante).
- **`mes_referencia`:** sempre `yyyy-MM`, 48 meses consecutivos, sem buracos.
- **`data_vencimento`:** sempre ISO e **sempre igual a `data_emissao` + 12 dias** (p1 = mediana = p99 = 12). Isso dá uma regra para validar a emissão.
- **`bandeira_tarifaria`:** 4 valores sem variação de escrita (Verde, Amarela, Vermelha P1, Vermelha P2) e **exatamente uma bandeira por mês**, como define a ANEEL.
- **`status`:** só PAGA e EM ABERTO, coerentes com o pagamento (seção 3, item 4).
- **Nenhum nulo**, exceto `data_pagamento`, que é esperado (faturas em aberto).
- **UCs reais:** exatamente **1 fatura por UC por mês**. 44.638 UCs têm as 48 faturas, e ~358 têm entre 4 e 47, o que bate com as ~372 ligações novas do período (N-01).
- **Nenhuma fatura de UC TESTE.**

---

## 3. Problemas encontrados

| # | Problema | Evidência | Tamanho |
|---|---|---|---|
| 1 | **Faturas órfãs** | `id_uc` no padrão `UC9999999` (7 dígitos, ex.: `UC9969129`), que não existe no cadastro, e `id_fatura` no padrão `FTX9999999`. Os dois padrões têm exatamente 32.285 linhas. | **32.285 (1,48%)**, espalhadas em ~31,7 mil ids de UC falsos (1 a 3 faturas cada) |
| 2 | **`data_emissao` em 4 formatos** | ISO 2.001.260 · `dd/MM/yyyy` 61.291 · `dd.MM.yyyy` 61.252 · `99-99-9999` 60.818 | 183.361 (8,4%) fora do ISO |
| 3 | **O formato com traço é MM-dd-yyyy, provado** | Separador `-`: a 1ª parte **nunca** passa de 12 (0 casos), a 2ª passa em 38.615 casos. Nos separadores `/` e `.` acontece o contrário (dd-MM). Mesmo padrão dos medidores. | **22.203 datas ambíguas** que o notebook atual lê com dia e mês trocados |
| 4 | **"Não pago" representado de 2 jeitos** | `data_pagamento` nula (113.835) **ou** a sentinela `9999-12-31` (61.333). As duas somam exatamente os 175.168 EM ABERTO. | 61.333 sentinelas |
| 5 | **`valor_total` em formato brasileiro** | `R$ 225,53` (188.571) e `R$ 1.056,83` (8.051). O resto está em `ponto_decimal`. Nenhum valor ambíguo do tipo `1.234`. | 196.622 (9%) |

### Efeitos visíveis do problema 3 (data trocada)

As análises da célula 9 usaram a ordem errada (dia antes de mês), e isso aparece em vários lugares:
- **521 emissões no futuro** (máximo de `2026-12-06`) e mínimo de `2022-03-07`, **antes** do início da base.
- **Emissão contra competência:** 2.153.352 no mesmo mês, mas ~31 mil espalhadas de −9 a +11 meses. É a assinatura de dia e mês trocados.
- **11.905 "vencem antes de emitir"** e **10.464 "pagas antes de emitir"**: a emissão lida errada fica depois do vencimento real.

A correção (ler o traço como `MM-dd-yyyy`) é validada pela regra `vencimento = emissão + 12 dias`, que vale para 100% das faturas em ISO (célula 13a).

### Sobre as 21 "duplicatas no mesmo mês" (célula 10)

Os 21 pares de faturas da mesma UC no mesmo mês **são todos de UCs órfãs** (`UC9…`). São colisões aleatórias dos ids falsos. **Nas UCs reais não há nenhuma.**

### Sobre `dias_atraso` p99 = 2.913.212

É efeito da sentinela `9999-12-31` (problema 4). Sem ela, a mediana é de **11 dias de atraso**.

---

## 4. Tratamento proposto para a Silver

| # | Regra |
|---|---|
| 1 | Remover cabeçalhos repetidos |
| 2 | **`id_uc` fora do cadastro → `silver_faturas_quarentena`**, motivo `UC_INEXISTENTE_NO_CADASTRO` (o notebook atual já faz isso) |
| 3 | `data_emissao`: tentar ISO → `dd/MM/yyyy` → `dd.MM.yyyy` → **`MM-dd-yyyy`**. Teste de qualidade: `data_vencimento − data_emissao = 12`. |
| 4 | `data_pagamento`: `9999-12-31` → `null` |
| 5 | `valor_total`: limpar `R$`, espaço e ponto de milhar e trocar a vírgula (a lógica atual do colega funciona para todos os casos da base) |
| 6 | `valor_energia`, `tributos`: `try_cast` direto |
| 7 | Criar `status_pagamento` derivado: PAGA / EM ABERTO no prazo / EM ATRASO, comparando o vencimento com a data de referência. A regra vai para o dicionário. |
| 8 | Teste de qualidade: 1 fatura por UC por mês; 1 bandeira por mês; `valor_total = valor_energia + tributos` (pendente, célula 13b) |

---

## 5. O que o notebook atual (`bronze_to_silver.py`) já cobre

| Item | Situação |
|---|---|
| Cabeçalho repetido | ✅ Filtra |
| Faturas órfãs | ✅ **Manda para a quarentena** (correto) |
| `valor_energia` / `tributos` com cast direto | ✅ Funciona: a base está limpa (S-FAT-01 refutado) |
| `valor_total` em formato brasileiro | ✅ A limpeza de `R$` e vírgula funciona; não há valores ambíguos (S-FAT-02 refutado) |
| **`data_emissao` com traço** | ❌ **Bug:** tenta `dd-MM-yyyy` antes de `MM-dd-yyyy`, então ~22 mil emissões ficam com dia e mês trocados |
| **Sentinela `9999-12-31` no pagamento** | ❌ **Não trata.** O portal mostraria "pago em 31/12/9999", e as métricas de atraso explodem. |
| Deduplicação | ⚪ Não faz, e nas UCs reais não há duplicata por mês (a deduplicação por `id_fatura` está pendente) |
| `receita_recebida = status == "PAGA"` (Gold) | ✅ Correto: só existem PAGA e EM ABERTO (G-07 refutado) |

---

## 6. Impacto no modelo da Gold

- **`fact_faturamento` não terá `volume_faturado_kwh`.** O volume vem de `fact_leituras` (consumo medido), cruzado por UC e competência. Para as UCs com GD, o consumo medido não é igual ao faturado, e isso precisa ir para o dicionário.
- **`valor_tarifa` / preço efetivo** = receita ÷ kWh lido, calculado no agregado `agg_receita_preco_volume`.
- **`valor_bandeira` não existe separado:** o acréscimo da bandeira já está dentro de `valor_energia`.
- **`status_pagamento`** com 3 valores (Pago, Pendente, Atrasado) precisa ser **derivado**, porque a fonte só tem PAGA e EM ABERTO.

---

## 7. Achados para o diagnóstico de receita ⭐

### Bandeiras: o primeiro ano foi todo verde; os últimos 12 meses, não

| Período | Verde | Amarela | Vermelha P1 | Vermelha P2 |
|---|---|---|---|---|
| **Primeiro ano** (jul/22–jun/23) | **12** | 0 | 0 | 0 |
| **Últimos 12 meses** (jul/25–jun/26) | 4 | 3 | 3 | 2 |

Sequência completa: Verde até jun/24 · Amarela jul/24 · Verde ago/24 · VP1 set/24 · VP2 out/24 · Amarela nov/24 · Verde dez/24–abr/25 · Amarela mai/25 · **VP1 jun–jul/25 · VP2 ago–set/25 · VP1 out–nov/25** · Amarela dez/25 · Verde jan–abr/26 · Amarela mai–jun/26.

**Por que importa:** além do reajuste de 10,5%, a bandeira **aumentou ainda mais o preço** nos últimos 12 meses. Se o preço subiu mais de 10,5% e a receita subiu só ~8%, a queda de volume (ou outro efeito) precisa ser **maior** do que parece. Isso reforça o peso da GD (N-05). A decomposição preço × volume vai mostrar isso.

**Coincidência a investigar:** a crise de atendimento de jul/2025 (N-06) cai no meio do período de bandeira vermelha (jun–nov/2025).

### A base praticamente não cresceu

44.638 UCs têm as 48 faturas, e ~358 têm entre 4 e 47, o que bate com as ~372 ligações novas de 2022–2026. Isso confirma o N-01: o número de UCs faturadas cresce menos de 1% no período.

### Inadimplência

8,0% das faturas estão EM ABERTO (175.168). O atraso mediano das pagas é de 11 dias.

---

## 8. Resultados da célula 13 (fechamento)

### 13a. Correção da data validada ✅

| Formato da emissão | Qtd | Vencimento = emissão + 12 (ordem antiga) | (ordem certa) |
|---|---|---|---|
| `99-99-9999` | 60.818 | **66,43%** | **100%** |
| `99/99/9999` | 61.291 | 100% | 100% |
| `99.99.9999` | 61.252 | 100% | 100% |
| `9999-99-99` | 2.001.260 | 100% | 100% |

Com a ordem certa (traço = `MM-dd-yyyy`), **100% das faturas** passam na regra. Emissão menos competência: **0 meses em 2.173.315** e **+1 mês em 11.306** (emitida no mês seguinte, o que é legítimo). **Nenhum valor negativo nem fora da faixa.** A dispersão de −9 a +11 meses vinha só da data trocada.

### 13b. `valor_total = valor_energia + tributos` ✅

**Bate em 100%** (2.184.621 de 2.184.621), considerando os valores em formato brasileiro convertidos.

### 13c. As faturas órfãs não distorcem a tendência ✅

As órfãs são ~650–720 por mês e representam **de 1,1% a 2,2% da receita mensal**, sem tendência ao longo dos 48 meses. Excluí-las (quarentena) não muda a comparação entre os períodos.

### 13d. ⭐ O "+8%" do Diretor Comercial foi confirmado

| Métrica (faturas válidas) | Primeiro ano (jul/22–jun/23) | Últimos 12 meses (jul/25–jun/26) | Variação |
|---|---|---|---|
| UCs faturadas | 44.741 | 45.000 | **+0,6%** |
| Faturas | 536.267 | 539.768 | +0,7% |
| Receita de energia | R$ 117,8 mi | R$ 127,3 mi | +8,0% |
| **Receita total** | **R$ 157,1 mi** | **R$ 169,7 mi** | **+8,0%** |
| Receita recebida | R$ 148,4 mi | R$ 160,2 mi | +7,9% |

**Os dados batem exatamente com a fala do diretor.** Se o volume caiu ~4% (a confirmar nas leituras), o **preço médio efetivo subiu ~12,5%**: (1,08 ÷ 0,96) − 1. Isso é coerente com o reajuste de 10,5% mais as bandeiras dos últimos 12 meses (N-07).

**Os dois períodos são anos completos (jul–jun)**, então a sazonalidade se cancela na comparação.

### 13e. Série mensal

- **Sazonalidade forte:** o ticket médio fica em ~R$ 213–265 em jun–ago e em ~R$ 335–396 em dez–mar (verão, uso de ar-condicionado). Toda comparação entre períodos precisa usar 12 meses completos ou o mesmo mês do ano anterior.
- **Inadimplência estável:** 7,8% a 8,3% em aberto em **todos** os meses, com atraso mediano de 10–11 dias. **A inadimplência não explica nada** da variação de receita (a recebida acompanha a faturada: +7,9% contra +8,0%).
- **Jul/2025 (crise de atendimento):** nada de anormal nas faturas. O ticket de R$ 236,98 está em linha com jul/2024 (R$ 243,80) e jul/2023 (R$ 230,28), e a inadimplência está em 8,04%. **As faturas não explicam a crise** (N-06 continua sem causa identificada; resta cruzar com as ocorrências).
- **Crescimento da base:** de 44.638 faturas em jul/2022 para 45.000 em jun/2026, com crescimento linear e pequeno.

---

## 9. Pendências

- [ ] Célula 3: confirmar se as 2 linhas extras são cabeçalhos repetidos.
- [ ] Célula 5: duplicatas por `id_fatura` (linhas idênticas e ids repetidos).
- [x] Célula 13: correção de data validada, total consistente, órfãs estáveis, +8% confirmado.
- [ ] **Leituras:** volume em kWh do primeiro ano contra os últimos 12 meses, para fechar a decomposição preço × volume.
