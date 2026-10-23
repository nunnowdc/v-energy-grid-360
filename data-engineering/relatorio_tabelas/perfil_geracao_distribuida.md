# Perfil de dados: `geracao_distribuida.csv`

**Status:** completo
**Última atualização:** 22/10/2026
**Fonte:** `/Volumes/v-energy/raw_data/raw_data/geracao_distribuida.csv` (CSV `,`, lido como texto)
**Notebook de análise:** `/v-energy/tabela_geracao_distribuida_visualizacao`

---

## 1. Visão geral

| Item | Valor |
|---|---|
| Linhas | 3.510 (o case fala em ~3,5k) |
| Cabeçalho repetido / linhas vazias | 0 / 0 |
| Colunas (5) | id_uc, potencia_kwp, data_conexao, modalidade, energia_injetada_kwh_media_mensal |
| `id_uc` distintos | 3.510 — zero duplicatas |
| Integridade com o cadastro | **100%**: os 3.510 id_uc existem todos em `unidades_consumidoras` (anti-join exato, normalizado trim/upper e cross-check na silver: 0 órfãos) |
| Modalidade | GERACAO NA PROPRIA UC 3.042 · AUTOCONSUMO REMOTO 321 · GERACAO COMPARTILHADA 147 |
| Período de `data_conexao` | 2024-01-01 a 2026-06-27, 100% ISO, 0 datas impossíveis ou futuras |
| Potência (parseada) | mediana 5,87 kWp · p25 5,0 · p75 7,5 — 76% da base entre 4 e 8 kWp |
| Energia injetada | mediana 198,6 kWh/mês · p95 1.090 · máx 8.250 — 77% entre 100 e 300 kWh/mês |

---

## 2. Problemas encontrados

| # | Problema | Evidência | Tamanho |
|---|---|---|---|
| 1 | **Dois separadores decimais em `potencia_kwp`** | ponto `X.X` 3.194 (91%) · vírgula `X,X` 316 (9%), ex. `5,03` (UC100150), `8994,91` | 316 linhas (9%) |
| 2 | **35 potências infladas ~1000x** | valores de 3.398 a 8.994,91 kWp — "usinas" de 9 MW numa base residencial. A razão energia/potência dessas linhas é 0,01–0,06 kWh/kWp/mês, contra mediana de 33,75 do restante. Dividindo por 1000, todas caem na faixa normal (seção 3) | 35 linhas (1%) |
| 3 | `data_conexao` anterior à ligação da UC | UC106046, UC100259, UC102507, UC110560, UC119180. Ex.: UC106046 conectou a GD em 2024-04-12, mas a UC só foi ligada em 2025-07-29 — a geração existiu ~15 meses antes da unidade | 5 linhas |
| 4 | Cadastro de UC com ids repetidos (só ao cruzar) | o CSV bruto tem 46.461 linhas / 45.201 ids distintos; o join GD→UC multiplica linhas se não deduplicar. A silver já vem deduplicada (45.200) | afeta joins, não a GD em si |

Conjunto de linhas suspeitas: 35 (potência) + 5 (data) = **40 linhas, 1,1% da base, sem sobreposição entre os dois grupos** (as 5 UCs do problema 3 têm potência normal, 3–6,7 kWp).

### O que veio limpo

- `id_uc`: sempre `UC999999`, 3.510 distintos, 0 nulos, 0 duplicatas, 100% de integridade com o cadastro (verificado por 3 métodos independentes).
- `data_conexao`: 100% ISO `yyyy-MM-dd` (nenhum dos 4 formatos misturados de `data_instalacao`/`data_leitura`), 0 datas impossíveis (mês 1–12, dia 1–31 validados), 0 datas futuras.
- `modalidade`: exatamente 3 valores, sem variantes de caixa/espaço/acentos (3 distintos antes e depois de trim/upper/sem-acento — mesmo comportamento do `tipo_leitura`).
- `energia_injetada_kwh_media_mensal`: 100% com ponto decimal (zero vírgulas, ao contrário da potência), 0 nulos, 0 negativos, 0 zeros, mínimo 30,4 kWh/mês.
- A razão energia/potência da base é estável — mediana 33,75 kWh/kWp/mês (p5 24,5 · p95 44,1) — e serve como âncora interna de consistência entre as duas colunas.

---

## 3. Evidência de que as 35 potências são erro de unidade (kW ↔ W)

**A) A razão energia/potência.** A base tem mediana de 33,75 kWh/kWp/mês. As 35 "usinas" têm razão de 0,01 a 0,06 — entre 500 e 3.000x abaixo do resto, sem gradiente: não existe nenhuma potência intermediária entre 15 e 3.398 kWp.

**B) A correção ÷1000 é exata.** Dividindo por 1000, todas as 35 caem na faixa normal. Exemplo: UC120737, `8994,91` → 8,99 kWp com 298,3 kWh/mês dá razão 33,2, colada na mediana da base.

**C) A energia injetada não acompanha.** Se fossem usinas reais de 3–9 MW, a injeção esperada seria ~100x maior (centenas de milhares de kWh/mês). O máximo injetado na base é 8.250 kWh/mês, e só 3 UCs passam de 5.000.

**D) Dois critérios independentes selecionam as mesmas 35 linhas.** `potencia > 75 kWp` e `razão fora de [5, 200]` retornam 35 cada, com interseção de 35 (verificado na silver). Não é cauda estatística: é um bloco discreto de dados.

Conclusão: potência em W registrada como kW (deslocamento de 3 casas decimais). **Não são instalações legítimas de porte utilitário** — a leitura inicial de "usinas grandes consistentes" foi refutada pela razão energia/potência.

---

## 4. Tratamento proposto para a Silver

| # | Regra | Destino |
|---|---|---|
| 1 | `potencia_kwp`: trocar vírgula por ponto antes do cast | Silver (já feito) |
| 2 | `potencia_kwp`: corrigir as 35 linhas com ÷1000 — ou quarentenar com motivo `POTENCIA_INFLADA`. Critério objetivo: razão energia/potência fora de [5, 200] kWh/kWp/mês (seleciona exatamente as 35; equivalente a `potencia > 75`) | Silver / quarentena |
| 3 | `data_conexao`: manter cast ISO + validar contra `data_ligacao` da UC; conexão anterior à ligação → quarentena `GD_ANTES_DA_LIGACAO` | Quarentena (5 linhas) |
| 4 | `modalidade`: manter upper + validação defensiva de domínio (3 valores); valor fora do domínio gera flag em vez de passar silenciosamente | Silver |
| 5 | `energia_injetada_kwh_media_mensal`: cast double direto (coluna é 100% ponto) | Silver (já funciona) |
| 6 | Teste de qualidade recorrente: razão kWh/kWp/mês dentro da faixa plausível — pega o problema 2 (e qualquer regressão futura) em cargas novas | Teste de qualidade |

---

## 5. O que o notebook atual (`bronze_to_silver`) já cobre

Analisada a célula "6. Saneamento de Geração Distribuída" do notebook `/v-energy/bronze_to_silver`:

| # | Problema | Situação |
|---|---|---|
| 1 | Separador de vírgula em potência | ✅ `regexp_replace(",", ".")` + cast double |
| 2 | 35 potências infladas | ❌ **Não trata.** Confirmado na silver gravada: média 71,05 kWp, máx 8.994,91, 35 linhas > 75 kWp — o erro está propagado. Qualquer agregação de potência sai distorcida (a média fica 12x a mediana). |
| 3 | `data_conexao` | ✅ `to_date` ISO — funciona porque a coluna é 100% ISO |
| 4 | GD antes da ligação da UC | ❌ Sem validação cruzada com `data_ligacao` |
| 5 | `modalidade` | 🟡 `upper()` funciona hoje (a coluna já vem limpa), mas sem validação de domínio um valor novo passaria sem alerta |
| 6 | `energia_injetada` | ✅ cast double direto |
| 7 | id_uc / duplicatas | ⚪ Não precisa: 0 duplicatas e 100% de integridade. O filtro de cabeçalho (`id_uc != "id_uc"`) é inócuo, mas inofensivo |

---

## 6. Pendências

- [ ] Confirmar com o dono dos dados o erro kW↔W nas 35 potências (ou aplicar ÷1000 direto: as 35 caem exatamente na faixa normal após a correção).
- [ ] Investigar as 5 UCs com GD antes da ligação: o registro de GD delas é internamente consistente (potência normal de 3–6,7 kWp e razão uniforme de exatamente 110 kWh/kWp/mês em todas as 5), o que sugere que o erro está no `data_ligacao` do cadastro, não na GD.
- [ ] Conferir como o `silver_to_gold` deriva `dim_unidade_consumidora.possui_gd` e se a correção da potência muda métricas do gold.
- [ ] Cruzar as 3.510 UCs geradoras com faturas/leituras: quanto da energia injetada aparece como consumo negativo/compensação e o impacto na receita faturada.

---

## 7. Achado para o diagnóstico de receita

**A adoção de geração distribuída é residencial, madura e em queda acelerada.**

- **Curva descendente:** 1.845 conexões em 2024, 1.304 em 2025 (−29%), 361 no 1º semestre de 2026. O pico foi jan/2024 (183 conexões) e jun/2026 teve 49 — queda contínua mês a mês, sem sazonalidade.
- **Penetração:** 3.510 de 45.000 UCs reais = **7,8% da base** já gera.
- **Perfil homogêneo e residencial:** mediana de potência de 5,87 kWp praticamente igual nas 3 modalidades (inclusive autoconsumo remoto e compartilhada) — não existe segmento grande/comercial. A mediana de injeção (198,6 kWh/mês) é da ordem do consumo mediano da base (~170 kWh/mês nas leituras): para o cliente gerador típico, a GD compensa praticamente a conta inteira.

**Por que importa:**

- **Receita:** cada UC conectada passa a injetar em média 329 kWh/mês que deixam de ser faturados ou viram crédito (medição líquida — as UCs com consumo negativo nas leituras devem ser majoritariamente geradoras).
- **Estoque, não fluxo:** como a curva de novas conexões caiu ~4x do pico, a erosão de receita por GD já está quase toda materializada no período analisado. A perda é um estoque de 3.510 UCs, não um fluxo crescente — candidata a hipótese no status report do Diretor Comercial, cruzando com faturas por mês.

A confirmar com faturas e leituras: quanto da energia injetada de fato volta como crédito/desconto na fatura dessas UCs.