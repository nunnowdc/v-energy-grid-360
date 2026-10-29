# Perfil de dados: `geracao_distribuida.csv`

**Status:** quase completo (faltam os itens da seção 7)
**Última atualização:** 24/10/2026
**Fonte:** `/Volumes/v-energy/raw_data/raw_data/geracao_distribuida.csv` (CSV `,`, lido como texto)

---

## 1. Visão geral

| Item | Valor |
|---|---|
| Registros | **3.510** (o case fala em ~3,5 mil) |
| Colunas (5) | id_uc, potencia_kwp, data_conexao, modalidade, energia_injetada_kwh_media_mensal |
| Nulos e placeholders | Nenhum |
| Classes das UCs com GD | RESIDENCIAL 3.127 (mediana de 5,64 kWp) · COMERCIAL 383 (mediana de 31,24 kWp) |
| Modalidade | GERACAO NA PROPRIA UC 3.042 · AUTOCONSUMO REMOTO 321 · GERACAO COMPARTILHADA 147 |
| Período de conexão | **jan/2024 a jun/2026.** Não existe nenhuma GD antes de 2024 nesta base. |

---

## 2. O que veio limpo

- Nenhum nulo ou placeholder em nenhuma coluna.
- `data_conexao` sempre em `yyyy-MM-dd`.
- `energia_injetada_kwh_media_mensal` sempre em formato numérico com ponto (`216.70`).
- `modalidade` com 3 valores, sem variação de escrita.
- `id_uc` sempre `UC999999`, e **todas as 3.510 GDs pertencem a UCs reais do cadastro** (o join com o cadastro manteve as 3.510).

---

## 3. Problemas encontrados

| # | Problema | Evidência | Tamanho |
|---|---|---|---|
| 1 | `potencia_kwp` com vírgula decimal | `"5,03"`, `"27,34"` (o valor vem entre aspas no CSV) | 316 linhas |
| 2 | **`potencia_kwp` em W em vez de kW** | 35 valores entre ~3.050 e 8.995 (ex.: `6576.77`), sem nenhum valor entre 75 e 1.000. Uma residência com 6.576 kWp é impossível; **6,58 kWp** é o tamanho típico. | 35 linhas (1%) |
| 3 | **Energia injetada "fabricada" = potência × 110** | Um grupo de GDs tem `energia_injetada` **exatamente** igual a `kWp × 110` (razão de 110,000 sem casas decimais). Isso aparece em **praticamente todas as GDs conectadas em mai/2026 (52) e jun/2026 (49)** e em alguns casos isolados de 2024. O padrão real da base é ~34 kWh/kWp·mês. | ~105 linhas (contagem exata pendente) |
| 4 | **2 GDs comerciais com razão fisicamente impossível**, mesmo depois da correção W → kW | UC104176: 3,24 kWp com 1.063,7 kWh (328 kWh/kWp). UC112709: 5,91 kWp com 992,4 kWh (168 kWh/kWp). Um painel **gera** no máximo ~150 kWh/kWp·mês, então não dá para **injetar** mais que isso. Provavelmente a escala da potência é outra (÷100 daria 32,4 e 59,1 kWp, com razões normais), mas isso não é comprovável. | 2 linhas (ambas AUTOCONSUMO REMOTO) |

### Sobre as "linhas com 6 campos" (célula 3)

As 316 linhas com 6 campos são **falso positivo do teste**. Elas são exatamente as 316 potências com vírgula, que vêm entre aspas (`"5,03"`). O teste conta vírgulas no texto cru e não respeita as aspas, mas o leitor de CSV do Spark respeita. **Não é um problema do arquivo.** Isso também é uma lição para a célula 3 das outras tabelas.

### Validação da correção W → kW (célula 13a)

Depois de dividir por 1000, **32 das 35** potências passam a ter razão entre 13 e 60 kWh/kWp·mês, na faixa normal da base. A correção está validada. As 3 que continuam fora são UC142950 (114, provavelmente do grupo "× 110") e as duas comerciais do problema 4.

### Por que "× 110" indica um valor estimado, não medido

- A razão é **exatamente** 110,000 em todos esses casos. Um valor medido sempre varia.
- Quase todas as GDs com essa razão foram conectadas em **mai–jun/2026**, os dois últimos meses da base. Uma GD conectada em junho ainda não tem histórico para calcular uma "média mensal". O sistema parece ter preenchido a média com uma **estimativa padrão (110 kWh por kWp)**.
- Essa estimativa é ~3 vezes maior que a média real das outras GDs (~34).

**Impacto:** essas ~101 GDs aparecem com ~110 mil kWh/mês injetados. Na razão real da base, seriam ~34 mil. A energia injetada acumulada de jun/2026 fica **superestimada em ~75 mil kWh/mês (~6,5%)**.

### Penetração por bairro (célula 13d)

A penetração média é de 3.510 / 45.000 = **7,8%** das UCs. O máximo é 16% (Planalto, em Abreu e Lima), e vários bairros de Recife ficam entre 11% e 13%. **Não há um polo anômalo.** Brasília Teimosa lidera em número absoluto (167) só por ser um bairro grande; em percentual, ele não está entre os 20 primeiros. Isso corrige a observação anterior de que ele era "curioso".

### Correção de uma premissa minha

Na célula 8, usei como faixa esperada **110 a 150 kWh/kWp·mês**. Esse valor é de energia **gerada**. A coluna é de energia **injetada** na rede, que é a geração menos o que a própria UC consome na hora. Por isso a energia injetada fica naturalmente abaixo.

A distribuição observada é bem concentrada (p25 = 30, mediana = 34, p75 = 37,5 kWh/kWp·mês). Isso indica uma regra consistente, não um erro. As 3.035 linhas classificadas como "muito baixo" **não são problema**. O que merece investigação são os **extremos**: as 35 em W (razão perto de 0) e a cauda de cima (p99 = 110).

---

## 4. Tratamento proposto para a Silver

| # | Regra |
|---|---|
| 1 | `potencia_kwp`: trocar vírgula por ponto e converter com `try_cast` |
| 2 | **`potencia_kwp > 1000`: dividir por 1000** (W → kW), com a flag `potencia_corrigida_unidade = true`. A validação está na célula 13a: depois da correção, a razão kWh/kWp deve voltar para ~30–40. |
| 3 | `energia_injetada_kwh_media_mensal`: `try_cast` (o formato já está limpo) |
| 4 | `data_conexao`: `try_to_date` no formato ISO |
| 5 | `kwh_por_kwp_mes` calculado depois da correção de unidade |
| 5a | **Flag `energia_estimada = true`** quando `abs(energia − kWp × 110) < 0,05`. Para o diagnóstico, usar a energia **reestimada** pela razão mediana real (~34 × kWp), ou excluir essas linhas e documentar. |
| 5b | **Razão > 150 kWh/kWp·mês** (fisicamente impossível): mandar para a quarentena com o motivo `POTENCIA_INCONSISTENTE` |
| 6 | Integridade com o cadastro: já satisfeita (100%), mas o teste continua no `03_qualidade` |

---

## 5. O que o notebook atual (`bronze_to_silver.py`) já cobre

| Item | Situação |
|---|---|
| Vírgula decimal na potência | ✅ `regexp_replace(",", ".")` resolve |
| Potência em W | ❌ **Não trata.** As 35 linhas inflam qualquer soma de kWp: o `kwp_novos` de 2024 sai em 141 mil kWp quando deveria ser ~11 mil. |
| Energia, data e modalidade | ✅ Funcionam, porque os formatos são únicos (mas usam cast comum, não `try_`) |
| Deduplicação | ⚪ Não faz. Não há duplicatas exatas; os `id_uc` repetidos estão pendentes (célula 5). |
| Integridade | ⚪ Não verifica, mas está 100% ok |

---

## 6. Achado para o diagnóstico de receita ⭐

**A GD inteira desta base nasce dentro do período analisado.**

| Ano | GDs novas | kWh/mês injetados (novos) |
|---|---|---|
| 2024 | 1.845 | 581.663 |
| 2025 | 1.304 | 375.742 |
| 2026 (até jun) | 361 | 197.721 |
| **Acumulado em jun/2026** | **3.510** | **~1,16 milhão de kWh/mês** |

- **Primeiro ano da base (jul/2022–jun/2023):** zero GD.
- **Últimos 12 meses (jul/2025–jun/2026):** de ~2.700 a 3.510 GDs, injetando de ~0,84 a ~1,16 GWh por mês.
- O ritmo de novas conexões **desacelera**: ~180 por mês no início de 2024, ~50 por mês em 2026.

**Por que isso é forte:** a energia injetada vira crédito que abate o consumo faturado. Além disso, o autoconsumo, que nem aparece aqui, reduz o consumo medido. Isso afeta exatamente a comparação que o Diretor Comercial fez: "primeiro ano contra os últimos 12 meses". **A GD é a candidata número 1 para explicar a queda de ~4% no volume faturado.** Falta quantificar com faturas e leituras: volume total por mês, contra o crescimento da GD.

**Onde a GD está:**
- Concentrada em residências de Recife (1.263) e Jaboatão (501).
- Penetração relativamente uniforme: 7,8% em média, no máximo 16% por bairro (célula 13d).

**Dois cuidados ao usar esses números:**
1. **Potência somada:** os 35 registros em W fazem o kWp total parecer ~13 vezes maior. Corrigir antes de somar.
2. **Energia de mai–jun/2026:** os valores "× 110" superestimam a injeção em ~75 mil kWh/mês. O total realista de jun/2026 fica em **~1,08 GWh/mês**, e não em 1,16.

---

## 7. Pendências

Fechadas com o `perfil_geracao_distribuida_Adryan.md`:
- [x] Célula 5: **0 duplicatas**, 3.510 `id_uc` distintos.
- [x] Célula 9: `data_conexao` de 2024-01-01 a 2026-06-27, 100% ISO, sem datas futuras ou impossíveis.
- [x] Célula 10: **5 GDs conectadas antes da ligação da UC** (UC106046, UC100259, UC102507, UC110560, UC119180). Todas têm energia = kWp × 110, o mesmo padrão de energia estimada (S-GD-04, S-GD-06).

**Divergências com o doc do Adryan (a alinhar):**
1. Ele afirma que as 35 potências **todas** caem na faixa normal depois do ÷1000. Pela célula 13a, 32 caem; UC104176 (328 kWh/kWp) e UC112709 (168) continuam fisicamente impossíveis, e UC142950 fica em 114.
2. Ele afirma que "não existe segmento grande/comercial". Isso vale olhando por **modalidade**; por **classe**, as 383 GDs comerciais têm mediana de **31,24 kWp**, contra 5,64 das residenciais.
3. Ele não identificou o padrão "× 110" nas ~101 GDs de mai–jun/2026; as 5 UCs que ele achou são parte dele.
4. Ele supõe que "as UCs com consumo negativo devem ser majoritariamente geradoras", mas o `perfil_leituras.md` mostra que só 7% dos negativos são de UCs com GD.
- [x] Célula 13: unidade W validada, "× 110" identificado, salto de mai–jun/2026 explicado, sem polo de penetração.
- [x] **Tratamento da potência em Watts (S-GD-02):** Dividir por 1.000 quando `potencia_kwp > 1000`, marcando com a flag `potencia_corrigida_unidade = true` (35 casos tratados).
- [x] **Quarentena de potências/razões impossíveis (S-GD-05):** Casos onde `kwh_por_kwp_mes > 150` (UC104176 e UC112709) são direcionados para `silver_geracao_distribuida_quarentena` com o motivo `POTENCIA_INCONSISTENTE`.
- [x] **Identificação de energia estimada (S-GD-04):** Aplicação da flag `energia_estimada = true` quando `abs(energia - kWp * 110) < 0.05` para permitir ajuste ou expurgo no diagnóstico de receita.
- [x] **Quarentena de conexão pré-ligação (S-GD-06):** As 5 UCs conectadas antes da ligação cadastral são direcionadas para quarentena com `GD_ANTES_DA_LIGACAO`.
- [x] **Implementação na Silver:** Implementado no notebook [`02_silver_geracao_distribuida.py`](../silver/02_silver_geracao_distribuida.py).
- [ ] Contagem exata de linhas com energia = kWp × 110.
