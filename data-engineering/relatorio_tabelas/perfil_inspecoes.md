# Perfil de dados: `inspecoes.xlsx`

**Status:** completo
**Última atualização:** 23/10/2026
**Fonte:** `/Volumes/v-energy/raw_data/raw_data/inspecoes.xlsx` (Excel com 3 planilhas — "ago-set", "out-nov", "dez" —, lidas como texto via pandas/openpyxl)
**Notebook de análise:** `/v-energy/tabela_inspecoes`

---

## 1. Visão geral

| Item | Valor |
|---|---|
| Linhas | **1.389** (ago-set 511 · out-nov 495 · dez 383) |
| Colunas (7) | id_inspecao, id_uc, data, inspetor, resultado, tipo_irregularidade, kwh_recuperado |
| `id_inspecao` | IN0000000 a IN0001388 — 1.389 distintos, **numeração sequencial sem lacunas nem duplicatas** |
| Integridade com o cadastro | **100%**: os 1.389 id_uc existem todos em `unidades_consumidoras` (0 órfãos); cada UC foi inspecionada **uma única vez** |
| Período de `data` | 2025-08-01 a 2025-12-31, 0 datas futuras |
| `resultado` (normalizado) | IRREGULARIDADE CONFIRMADA 836 (60,2%) · SEM IRREGULARIDADE 496 (35,7%) · CONFIRMADA 35 (2,5%) · NADA CONSTA 22 (1,6%) |
| `tipo_irregularidade` | DESVIO DIRETO 182 · BY-PASS 181 · MEDIDOR ADULTERADO 180 · LIGACAO CLANDESTINA 164 · LACRE VIOLADO 164 (871 preenchidos) |
| `kwh_recuperado` (parseado) | mediana 702,4 · média 1.060,56 · p95 4.116 · máx 15.609,4 — 518 zeros (35,7% + 1,6% da base) |
| Inspetores | 40 reais (após trim), carga equilibrada de ~30 a 48 inspeções cada, 0 nulos |

Nota: o Excel precisa de `%pip install openpyxl` no notebook (não vem pré-instalado no compute serverless).

---

## 2. Problemas encontrados

| # | Problema | Evidência | Tamanho |
|---|---|---|---|
| 1 | **`data` em 4 formatos** | ISO `yyyy-MM-dd` (1.256), traço curto (46), `dd.MM.yyyy` (44), `dd/MM/yyyy` (43) | 133 linhas (9,6%) fora do ISO |
| 2 | **O traço curto é ambíguo `dd-MM` vs `MM-dd`** | Resolvidas: 35 são `MM-dd`, **0 são `dd-MM`** (seção 3). 11 ficam sem desempate possível | 46 linhas (11 irreducíveis) |
| 3 | **`resultado` com 8 variantes de caixa** | `irregularidade confirmada`, `Irregularidade Confirmada`, `sem irregularidade`, `Sem Irregularidade`… | 107 linhas (7,7%) em variante fora do canônico |
| 4 | **Domínio de `resultado` tem 4 valores, não 2** | Além do par óbvio, existem a forma curta `CONFIRMADA` (35) e `NADA CONSTA` (22) | 57 linhas (4,1%) |
| 5 | `inspetor` com espaços sobrando | 107 valores brutos → **40 inspetores reais** após trim/upper; ex. ` INSP-003`, `INSP-028  `, `  INSP-017 ` | 67 variantes (vários graus) |
| 6 | "Sem irregularidade" representado de 2 jeitos em `tipo_irregularidade` | célula vazia (441) e placeholder `-` (77) | 77 linhas com `-` |
| 7 | **Dois separadores decimais em `kwh_recuperado`** | ponto `X.X` 1.264 (91%) · vírgula `X,X` 125 (9%), ex. `1463,90`, `0,00` | 125 linhas (9%) |
| 8 | **96 datas fora do período nominal da planilha** | TODAS na planilha "dez": datas de ago (19), set (21), out (31) e nov (25). A "dez" é um lote consolidado, não o mês de dezembro | 96 linhas (6,9%) |

### O que veio limpo

- `id_inspecao`: sempre `IN9999999`, 1.389 distintos, sequência completa 0–1388, 0 duplicatas, 0 nulos.
- `id_uc`: sempre `UC999999`, 100% de integridade com o cadastro, nenhuma UC com mais de uma inspeção.
- `tipo_irregularidade`: quando preenchido, exatamente 5 valores, **sem** variantes de caixa/espaço/acentos (5 distintos antes e depois de trim/upper/sem-acento).
- **Consistência interna perfeita** (0 violações nos dois sentidos): todas as 871 inspeções irregulares têm `tipo_irregularidade` preenchido **e** `kwh_recuperado` > 0; todas as 518 sem irregularidade (496 SEM IRREGULARIDADE + 22 NADA CONSTA) têm `kwh_recuperado` = 0. Os 518 zeros fecham exatamente com a conta.
- `kwh_recuperado`: 0 negativos, 0 não-numéricos, 0 falhas de parse após trocar vírgula por ponto.
- `inspetor`: 0 nulos, sempre `INSP-999` (após trim).

---

## 3. O formato com traço é MM-dd-yyyy — e a planilha "dez" não é dezembro

### A) Traço curto = americano (mesmo comportamento do `medidores.csv`)

A desambiguação do notebook (regra: 1º número > 12 → dia; 2º > 12 → mês; ambos ≤ 12 → âncora do período da planilha):

| Modo | Linhas |
|---|---|
| `MM-dd` | 35 |
| `dd-MM` | **0** |
| AMBIGUA | 11 |

Exemplos `MM-dd` inequívocos: `08-26-2025`, `10-22-2025`, `12-18-2025` (2º número > 12, só pode ser dia). **Nenhuma** linha do traço curto exige a leitura dia-mês.

As 11 AMBIGUAS (todas na planilha "dez", ex. `08-01-2025`, `09-01-2025`, `10-04-2025`) têm os dois números ≤ 12 e nenhum dos candidatos de mês casa com dezembro. Lidas como `MM-dd`, os meses resultantes (ago–nov) batem exatamente com o perfil de datas fora do período da planilha "dez" (seção B) — a leitura mais provável delas também é `MM-dd`, mas a âncora não consegue provar, então ficam marcadas.

### B) A "dez" é um lote consolidado, não um filtro de período

Das 96 datas fora do período nominal, 100% estão na planilha "dez" — todas de ago a nov (ago 19, set 21, out 31, nov 25), nenhuma de outro período do ano. Os formatos não-ISO também se concentram nessa planilha.

**Consequências:**

1. O nome da planilha NÃO pode ser usado como dimensão temporal no gold.
2. A âncora do período (ago-set = 8-9, out-nov = 10-11, dez = 12) desempata o traço curto na maioria dos casos, mas as 11 AMBIGUAS precisam de regra própria (quarentena ou assumir `MM-dd` com flag).

---

## 4. Tratamento proposto para a Silver

| # | Regra | Destino |
|---|---|---|
| 1 | `data`: função de parsing dos 4 formatos + desambiguação do traço curto pela planilha de origem (âncora, como o `mes_referencia` foi para as leituras); como todo o traço curto resolvido é `MM-dd`, testar `MM-dd` **antes** de `dd-MM` | Silver |
| 2 | As 11 datas AMBIGUAS → quarentena `DATA_AMBIGUA` (ou aplicar `MM-dd` com flag `data_ambigua = true`) | Quarentena / flag |
| 3 | `resultado`: trim + upper + sem acentos; mapear `CONFIRMADA` → `IRREGULARIDADE_CONFIRMADA` (forma curta); manter `NADA CONSTA` como categoria própria ou agrupar em `SEM_IRREGULARIDADE` com flag | Silver |
| 4 | `inspetor`: trim (+ upper) | Silver |
| 5 | `tipo_irregularidade`: `-` e vazio → `null` (mesma semântica de inspeção sem irregularidade) | Silver |
| 6 | `kwh_recuperado`: `regexp_replace(',', '.')` + `try_cast` (defensivo; hoje 0 não-numéricos) | Silver |
| 7 | `id_inspecao` / `id_uc`: sem tratamento (já vêm perfeitos) — `id_inspecao` é a chave natural | ⚪ Não precisa |
| 8 | Validação automática cruzada: irregular ⇒ tipo preenchido e kwh > 0; sem irregularidade ⇒ kwh = 0 (hoje 0 violações — qualquer quebra em carga nova é sinal de erro) | Teste de qualidade |

---

## 5. O que o notebook atual (`bronze_to_silver`) já cobre

Analisada a célula "7. Saneamento de Inspeções" do notebook `/v-energy/bronze_to_silver`. Gravou `silver_inspecoes: 1.389` (sem tabela de quarentena para inspeções).

| # | Problema | Situação |
|---|---|---|
| 1 | Cabeçalho repetido | ✅ Filtra `id_inspecao != "id_inspecao"` |
| 2 | Vírgula em `kwh_recuperado` | ✅ `regexp_replace` + cast double (cast comum, não `try_cast` — hoje não quebra porque não há não-numéricos) |
| 3 | Formatos de data | 🟡 `coalesce` com 5 formatos, **mas testa `dd-MM-yyyy` antes de `MM-dd-yyyy`** — como todo o traço curto da tabela é `MM-dd`, as linhas com dia ≤ 12 saem com dia e mês trocados, sem aviso (mesmo bug dos perfis de leituras e medidores) |
| 4 | As 11 datas AMBIGUAS | ❌ `try_to_date("dd-MM-yyyy")` aceita silenciosamente (ex. `09-01-2025` vira 9 de janeiro) — data provavelmente errada gravada como válida |
| 5 | `resultado` | 🟡 `upper().contains("CONFIRMADA")` cobre as variantes de caixa e a forma curta, mas **`NADA CONSTA` (22) é forçado para `SEM_IRREGULARIDADE`** perdendo a distinção; sem trim |
| 6 | `inspetor` | ❌ Sem trim — os 107 valores com espaços sobrevivem na silver |
| 7 | `tipo_irregularidade` | 🟡 Só `upper()` — o placeholder `-` (77) sobrevive como categoria, incoerente com os 441 null que significam a mesma coisa |
| 8 | Validação cruzada resultado ↔ tipo ↔ kwh | ❌ Não existe |
| 9 | Datas fora do período da planilha | ⚪ Sem impacto no parse, mas o bronze precisa preservar a coluna da planilha de origem para a âncora funcionar |

---

## 6. Pendências e Decisões de Design (Silver)

- [x] **Destino das 11 datas AMBÍGUAS:** Assumir formato `MM-dd-yyyy` (padrão empírico de 100% dos traços curtos desambiguados na base), mantendo os registros na Silver com a flag `data_ambigua = true`.
- [x] **Tratamento de `resultado` e `NADA CONSTA`:** Normalizado em dois valores canônicos: `IRREGULARIDADE_CONFIRMADA` (incluindo `CONFIRMADA`) e `SEM_IRREGULARIDADE` (incluindo `NADA CONSTA`), acompanhado da flag `resultado_declarado_nada_consta = true` para rastreabilidade e integridade nas agregações analíticas da Gold.
- [x] **Tratamento de `inspetor`:** Saneado com `trim` e `upper`, reduzindo de 107 grafias com espaços para exatamente 40 inspetores reais.
- [x] **Tratamento de `tipo_irregularidade`:** Placeholder `-` e strings vazias convertidos para `null`.
- [x] **Consistência cruzada e Quarentena:** Validação embutida onde irregularidade confirmada exige tipo preenchido e kWh recuperado > 0, e sem irregularidade exige kWh recuperado = 0. Violações são direcionadas para a tabela de quarentena `silver_inspecoes_quarentena` (motivo `INCOERENCIA_RESULTADO_KWH`).
- [x] **Implementação na Silver:** Implementado no notebook [`02_silver_inspecoes.py`](../02_silver_inspecoes.py).
- [ ] Confirmar com o dono dos dados que a planilha "dez" é um lote consolidado ago–dez (e se os nomes "ago-set"/"out-nov" também são lotes).
- [ ] Cruzar as 871 UCs irregulares com faturas, leituras, GD e medidores: fraude coincide com geração distribuída? com medidor trocado na campanha set/2025–mar/2026? Qual o perfil de consumo dessas UCs?
- [ ] Taxa de confirmação por inspetor (possível viés de critério) — não analisada.
- [ ] Verificar se o `silver_to_gold` usa `inspecoes` em alguma dimensão/fato e se o mapeamento de `resultado` da silver (NADA CONSTA → SEM_IRREGULARIDADE) distorce métricas.

---

## 7. Achado para o diagnóstico de receita

**A campanha de inspeções (ago–dez/2025) confirmou fraude em 62,7% das UCs inspecionadas e recuperou ~1,47 GWh — receita que não aparece nas faturas.**

- **Alcance:** 1.389 UCs inspecionadas = 3,1% da base de 45.000; 871 confirmaram irregularidade (1,9% da base). A taxa de confirmação é estável entre os lotes (~60–63%).
- **Recuperação:** média 1.060,56 kWh × 1.389 linhas ≈ **1,47 GWh**; ~1.691 kWh por inspeção irregular (média) e mediana de 702 kWh — metade das fraudes recupera menos que ~4 meses do consumo mediano da base (~170 kWh/mês nas leituras).
- **Fraude uniforme:** os 5 tipos têm participação quase igual (18,8–20,9%) e porte independente do tipo — mediana de recuperação por tipo entre 1.045 e 1.155 kWh (LACRE VIOLADO e LIGACAO CLANDESTINA ligeiramente acima na média). Não existe um "tipo de fraude" dominante para priorizar.

**Por que importa:**

- **Receita oculta:** o `kwh_recuperado` é energia medida e não faturada que a inspeção devolve ao faturável — ~1,47 GWh no período. Se não entrar no diagnóstico, a receita aparece menor do que é.
- **Fila de inspeção inteligente:** a lista de 871 UCs irregulares + tipo + recuperação é insumo direto para modelagem de risco. Cruzamentos promissores: consumo que dispara após a troca de medidor (perfil_medidores, seção 7) e UCs geradoras (perfil_geracao_distribuida).
- **Consistência interna perfeita** (resultado ↔ tipo ↔ kwh, 0 violações): a tabela é a mais confiável do case para esses cruzamentos — qualquer incoerência futura em carga nova é bug, não dado.

Cuidados antes de afirmar na apresentação:

- A taxa de 62,7% só fecha se `CONFIRMADA` (35) for contada como irregularidade confirmada — na silver atual o mapeamento já faz isso, mas o `NADA CONSTA` (22) colapsa em `SEM_IRREGULARIDADE` sem flag.
- As 11 datas AMBIGUAS e as 96 datas fora do período nominal não podem ser filtradas pelo nome da planilha — usar sempre a `data` parseada.
- O `kwh_recuperado` médio é puxado para cima pela cauda (p95 4.116, máx 15.609): reportar mediana junto da média.
