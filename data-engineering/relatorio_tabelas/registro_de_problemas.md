# Registro de problemas: pipeline V-Energy Grid 360

Lista única de **tudo de errado** que encontrarmos, tanto no código dos notebooks quanto nos dados brutos.
O detalhe de cada tabela fica no `perfil_<tabela>.md` correspondente.

**Última atualização:** 20/10/2026

**Legenda de status**
- 🔴 Confirmado: verificado no código ou nos dados
- 🟡 A confirmar: suspeita pelo código, falta olhar os dados
- ⚪ Refutado ou parcial: alegação verificada que não se sustenta (inteira ou em parte)
- ✅ Resolvido

**Gravidade:** Alta (distorce números que vão para a diretoria ou quebra o pipeline) · Média (fragilidade ou risco futuro) · Baixa (organização ou estilo)

---

## A. Notebook `landing_to_bronze.py`

| ID | Problema | Gravidade | Status | Evidência e observação |
|---|---|---|---|---|
| B-01 | **A Bronze acumula uma cópia completa a cada execução** (`CREATE TABLE IF NOT EXISTS ... WHERE 1=0` + `INSERT INTO`) | Média | 🔴 / ⚪ parcial | Ver a seção "Análise da alegação do Adryan" abaixo. A receita **não dobra**, porque a Silver filtra o último lote. Mas a Bronze cresce sem limite, e quem ler a Bronze direto vê duplicatas. Correção sugerida: `CREATE OR REPLACE TABLE ... AS SELECT`. **Dono: Adryan.** |
| B-02 | `INSERT INTO ... SELECT *` insere **por posição** de coluna | Média | 🔴 | Se a ordem das colunas mudar na fonte, os dados vão para a coluna errada sem nenhum erro. Também se resolve com `CREATE OR REPLACE`. |
| B-03 | Caminho do Excel de inspeções fixo no código (`/Volumes/v-energy/...`), sem usar o widget `catalog` | Baixa | 🔴 | Linha 161. Quebra se o catálogo mudar. |
| B-04 | Abas do Excel fixas no código (`["ago-set", "dez", "out-nov"]`) | Média | 🔴 | Uma aba nova seria ignorada sem aviso. Melhor ler `pd.ExcelFile(...).sheet_names`. |
| B-05 | `!pip install openpyxl` no meio do notebook | Baixa | 🔴 | O padrão no Databricks é `%pip` na primeira célula. No serverless o openpyxl já vem instalado. |
| B-06 | Widgets `database_prefix` e `ambiente` declarados e nunca usados | Baixa | 🔴 | Código morto. |
| B-07 | `_source_file` inconsistente: as leituras gravam o caminho completo, as outras tabelas só o nome do arquivo | Baixa | 🔴 | Linha 128 contra as demais. |

### Análise da alegação do Adryan (B-01)

**O que foi dito:** se a Bronze rodar duas vezes, a receita dobra, o DEC/FEC dobra e os chamados aparecem em dobro, porque a Silver só deduplica UCs e medidores.

**O que o código mostra:**

1. ✅ **É verdade que a Bronze faz append.** Cada execução insere de novo o arquivo inteiro.
2. ✅ **É verdade que a Silver só tem `dropDuplicates` em UCs e medidores.**
3. ❌ **Não é verdade que a receita ou o DEC/FEC dobram.** As 8 etapas da Silver (linhas 31, 66, 106, 166, 217, 237, 270 e 285 do `bronze_to_silver.py`) filtram `_ingestion_timestamp == max(_ingestion_timestamp)`. Cada execução da Bronze grava um único timestamp (`current_timestamp()` é avaliado uma vez por query), então a Silver lê **só o último lote**. Rodar a Bronze duas vezes não duplica nada a partir da Silver.

**O que continua sendo problema de verdade:**
- A proteção depende de **todo** consumidor da Bronze lembrar desse filtro. Um teste de qualidade, o dicionário de dados ou alguém do time que consulte a Bronze direto vai ver os números multiplicados.
- A Bronze cresce uma cópia inteira por execução. Com o Workflow mensal que o case pede, isso acumula.
- O posicionamento por coluna (B-02).
- **O risco real de duplicata está na fonte, não na reexecução:** faturas, leituras, GD, inspeções, ocorrências e atendimentos não são deduplicados na Silver (ver S-01). O arquivo de UCs veio com 900 linhas idênticas. Se as outras fontes também tiverem duplicatas, **a receita sai inflada mesmo rodando uma vez só.**

**Conclusão:** a correção proposta (`CREATE OR REPLACE`) é boa e simples, e deve ser feita. Ela não resolve o S-01, que é o problema mais grave.

---

## B. Notebook `bronze_to_silver.py`

### Geral

| ID | Problema | Gravidade | Status | Evidência e observação |
|---|---|---|---|---|
| S-01 | **Faturas, leituras, GD, inspeções, ocorrências e atendimentos não são deduplicados** | Alta | ✅ (nova Silver) | Medido na nova Silver (26/10): **leituras tinham 21.523 linhas idênticas** (~1% do volume) e **8.609 clones** (S-LEI-09). Faturas, GD, inspeções, ocorrências e atendimentos não tinham duplicatas exatas. Todas as novas Silvers aplicam `dropDuplicates` + desempate por id. |
| S-02 | Casts comuns (`.cast("double")`, `to_date`, `to_timestamp`) com o modo ANSI ligado no serverless | Média | 🔴 | Um único valor sujo quebra a célula inteira. O certo é usar `try_cast`, `try_to_date` e `try_to_timestamp`. |
| S-03 | Nenhuma verificação de integridade de leituras × UC, leituras × medidor, GD × UC, inspeções × UC, ocorrências × UC e atendimentos × UC | Alta | 🔴 | Só faturas × UC é verificada. O case exige integridade entre medição, faturamento e cadastro. |
| S-04 | Nenhum `trim` em nenhuma tabela | Média | 🔴 | O `logradouro` das UCs tem 2.797 linhas com espaço sobrando. |

### Unidades consumidoras (detalhe em `perfil_unidades_consumidoras.md`)

| ID | Problema | Gravidade | Status | Evidência e observação |
|---|---|---|---|---|
| S-UC-01 | **200 registros TESTE** (`TESTE0000`…, CPF `00000000000`) não são removidos | Alta | 🔴 | Inflam a contagem de UCs e podem levar faturas de teste para a receita. |
| S-UC-02 | Duplicatas conflitantes resolvidas de forma aleatória (`dropDuplicates(["id_uc"])`) | Baixa | ✅ | **Eram só diferenças de escrita.** Depois de padronizar (nome normalizado, CPF só com dígitos), sobram **0 conflitos**: as 45.000 UCs ficam com uma versão cada. A nova Silver mantém a regra de desempate e a flag `cadastro_conflitante` por segurança. |
| S-UC-03 | **Encoding quebrado (mojibake) em `bairro`** não é reparado | Alta | 🔴 | 60 bairros e ~356 linhas (`InhamÃ£`). Divide os bairros em dois na análise de receita. |
| S-UC-04 | CEP com lixo não tratado | Média | 🔴 | ~1.383 linhas: `NULL`, `N/A`, `-`, `-1`, `9999-12-31`, espaços. |
| S-UC-05 | `data_ligacao` com datas inválidas (1900–1948) não tratadas | Média | 🔴 | 92 linhas, todas em `01/01`, com um buraco de 48 anos depois. |
| S-UC-06 | UF forçada como `"PE"` | Baixa | 🔴 | Funciona com estes dados, mas esconderia um erro novo. |
| S-UC-07 | `data_ligacao` convertida com um único formato | Baixa | 🔴 | Hoje todas as datas vêm `yyyy-MM-dd`, então não causa erro. É uma fragilidade. |

### Medidores

| ID | Problema | Gravidade | Status | Evidência e observação |
|---|---|---|---|---|
| S-MED-01 | **O formato `99-99-9999` de `data_instalacao` é MM-dd-yyyy, mas o código testa `dd-MM-yyyy` primeiro** | Alta | 🔴 **PROVADO** (célula 9: a 1ª parte nunca passa de 12 no traço; 142/142 trocas batem lendo mês-dia contra 1/142 na ordem atual) | ~1.263 linhas em risco. Gera 6 instalações "futuras" (`2026-12-03`, que na verdade é `2026-03-12`) e falsas sobreposições de medidor: a instalação do novo é a retirada do antigo com dia e mês trocados. Ver `perfil_medidores.md` §3. |
| S-MED-02 | `data_retirada` convertida com um único formato | Baixa | ⚪ | Nos dados, a retirada está sempre em ISO. Não causa erro hoje. |
| S-MED-03 | Sem verificação de medidores sobrepostos nem de retirada antes da instalação | Média | 🔴 | Não houve nenhuma retirada antes da instalação. As sobreposições encontradas vêm do S-MED-01. Recomendação: virar teste de qualidade ("a instalação do novo é igual à retirada do antigo"). |
| S-MED-04 | **O mapeamento de `tipo` falha com acento e hífen** | Média | 🔴 | `upper("eletrônico")` vira `"ELETRÔNICO"`, que não contém `"ELETRON"`. O mesmo vale para `"ELETROMECÂNICO"` e para `"ELETRO-MECANICO"` (606 linhas). Sobram 6 categorias em vez de 3. Precisa normalizar o acento e a pontuação antes de mapear. |
| S-MED-05 | `modelo` sem `trim` | Baixa | 🔴 | 3.109 linhas com espaço sobrando. Ex.: `"  EL-3000 "` e `"EL-3000"` contam como modelos diferentes. |
| S-MED-06 | `data_ultima_manutencao` está 100% vazia na fonte | Baixa | 🔴 | 51.812 nulos. Documentar no dicionário: o case cita manutenção, mas não há dados. |
| S-MED-07 | Duplicatas exatas em medidores | Baixa | 🔴 | Todas são exatas, sem conflito. O `dropDuplicates` atual resolve. A quantidade está pendente. |

### Faturas

| ID | Problema | Gravidade | Status | Evidência e observação |
|---|---|---|---|---|
| S-FAT-01 | `valor_energia` e `tributos` convertidos com `cast("double")` direto | Baixa | ⚪ Refutado | As duas colunas estão 100% em `ponto_decimal`. O cast direto funciona. |
| S-FAT-02 | A limpeza de `valor_total` só roda quando o valor contém `R$` ou `,` | Baixa | ⚪ Refutado | Não existe nenhum valor ambíguo do tipo `1.234`. A limpeza do colega funciona para os 196.622 valores em formato brasileiro. |
| S-FAT-03 | `data_vencimento` e `data_pagamento` convertidas com um único formato | Média | 🔴 parcial | O formato é sempre ISO (ok), **mas o pagamento usa a sentinela `9999-12-31` em 61.333 faturas em aberto** (além de 113.835 nulas). O notebook não converte para null: o portal mostraria "pago em 9999" e o atraso p99 vira 2,9 milhões de dias. |
| S-FAT-04 | Faturas ligadas a UCs TESTE passariam como válidas | — | ⚪ Refutado | Não existe nenhuma fatura de UC TESTE. |
| S-FAT-05 | **`data_emissao` com traço é MM-dd-yyyy, mas o código testa `dd-MM-yyyy` primeiro** | Alta | 🔴 | **Provado:** no separador `-`, a 1ª parte nunca passa de 12 e a 2ª passa em 38.615 casos. 22.203 datas ambíguas ficam trocadas, gerando 521 emissões futuras, 11.905 "vence antes de emitir" e emissões até 11 meses fora da competência. **Correção validada (célula 13a):** com `MM-dd-yyyy`, 100% das emissões passam em `vencimento = emissão + 12`, contra 66,43% com a ordem atual. A emissão passa a cair no mês da competência (ou no seguinte) em 100% dos casos. |
| S-FAT-06 | 32.285 faturas órfãs (1,48%): `id_uc` `UC9999999` fora do cadastro, `id_fatura` `FTX…` | Média | ✅ | O notebook atual já manda para a quarentena. Representam 1,1–2,2% da receita mensal, **estável nos 48 meses**, então excluí-las não distorce a tendência. |
| S-FAT-07 | **A fonte NÃO tem coluna de kWh faturado** | Alta | 🔴 | O volume do diagnóstico precisa vir das leituras. Impacta a `fact_faturamento` proposta pelo time e o G-06. |

### Leituras

| ID | Problema | Gravidade | Status | Evidência e observação |
|---|---|---|---|---|
| S-LEI-01 | **`leitura_anterior` nula vai para a quarentena rotulada como `ANOMALIA_VIRADA_MEDIDOR`** | Alta | 🔴 | Confirmado em `perfil_leituras.md`: a quarentena atual (30.994) mistura **24.667 com a anterior nula (`'NULL'`)** e **6.327 resets reais**, com um rótulo só. Separar os motivos (`ANTERIOR_AUSENTE` × `ANOMALIA_VIRADA_MEDIDOR`). |
| S-LEI-02 | `consumo_kwh` recalculado como `leitura_atual − leitura_anterior`, descartando o valor original | Alta | 🔴 | Confirmado: o declarado difere da diferença das leituras em **24,6%** das linhas (quase sempre ±1, arredondamento da origem). O declarado é o valor oficial de faturamento. **Manter `consumo_kwh` declarado; não recalcular.** |
| S-LEI-03 | Sem verificação de leituras × UC e leituras × medidor | Alta | 🔴 | Ver S-03. Ainda não medido nas leituras (2.182.468 linhas contra 2.152.336 faturas de UCs reais: ~30 mil a mais a explicar). |
| S-LEI-04 | Coluna `arquivo` nas leituras | — | ⚪ Resolvido | O CSV tem 9 colunas, sem `arquivo`. Era o `_arquivo` criado pelo código de preview. |
| S-LEI-05 | ⚠️ **Sentinela `-1` em `leitura_anterior` gera consumo absurdo com status OK** | **Crítica** | 🔴 no notebook antigo · ✅ na nova Silver (só restam 172 consumos > 50 mil kWh, todos industriais legítimos) | 8.068 linhas. O notebook faz `atual − (−1) = atual + 1`, e a leitura acumulada do registrador (ex.: 89.537) vira "consumo" de até ~96.538 kWh, **marcado como OK**. 8.068 × ~90 mil kWh é da ordem do **consumo total da base inteira**. Se a Silver atual for usada no diagnóstico, **o volume sai quase dobrado**. Correção: `-1` → `null` (nunca 0) e usar o `consumo_kwh` declarado. |
| S-LEI-06 | String `'NULL'` em `leitura_anterior` | Média | 🔴 | 24.667 linhas. Quebra o cast comum; usar `try_cast`. |
| S-LEI-07 | `data_leitura` em 4 formatos e o traço com ordem contestada | Média | 🟡 | O `perfil_leituras.md` afirma que o traço **mistura** dd-MM e MM-dd, mas o exemplo dado (`01-01-2023`) serve nas duas ordens e não prova nada. Em medidores e faturas o traço é 100% MM-dd. **Rodar o teste por separador (> 12) nas leituras para decidir.** Seja qual for o resultado, o desempate pelo `mes_referencia` (0 violações) é robusto e pode ficar. |
| S-LEI-08 | Consumo negativo | Média | 🔴 | **6.595 negativos gigantes** (−3.379 a −2,1 milhões de kWh, 95% REAL): reset na troca de medidor. O número é próximo das 6.299 trocas da campanha (a cruzar). **1.555 negativos pequenos** (−24 a −500, com a leitura subindo): retificação comercial. Tratamento: gigantes para a quarentena, pequenos ficam com a flag `RETIFICACAO`. **Revisado (26/10):** os gigantes são exatamente os meses de troca de medidor (~890 por mês, set/2025–mar/2026). Mandá-los para a quarentena apagava o consumo desses meses e inflava a queda de volume. Na nova Silver, ficam com o status `TROCA_DE_MEDIDOR` e `consumo_kwh_ajustado` imputado (média dos 3 meses anteriores da UC): 6.215 linhas. |
| S-LEI-09 | **8.609 leituras clonadas** | Alta | ✅ (nova Silver) | Cópia exata de uma leitura real (mesma UC, mês e valores) com `id_leitura` `LTX…` e medidor `MD9…` inexistente. É o mesmo padrão das faturas órfãs. Inflavam o volume em ~0,4%. Quarentena `LEITURA_CLONADA_MEDIDOR_INEXISTENTE`. Depois disso: **1 leitura por UC por competência, 2.152.336 leituras, exatamente o número de faturas válidas**. |

### Geração distribuída, inspeções, ocorrências e atendimentos

| ID | Problema | Gravidade | Status | Evidência e observação |
|---|---|---|---|---|
| S-GD-01 | `data_conexao` com um único formato e sem verificação de GD × UC | Baixa | ⚪ | Nos dados, a data está sempre em ISO e as 3.510 GDs pertencem a UCs reais. Não causa erro hoje; manter o teste no `03_qualidade`. |
| S-GD-02 | **`potencia_kwp` em W em vez de kW** | Alta | 🔴 | 35 valores entre 4.706 e 8.994 "kWp" (devem ser 4,7–9,0 kWp). Sem nenhum valor entre 75 e 1.000. Infla o kWp somado em ~13×. Correção: dividir por 1000 quando > 1000, com flag. |
| S-GD-03 | Potência com vírgula decimal | Baixa | ✅ | 316 linhas (entre aspas no CSV). O notebook atual já trata com `regexp_replace`. |
| S-GD-04 | **Energia injetada "fabricada" como kWp × 110 exato** | Média | 🔴 | Praticamente todas as GDs de mai–jun/2026 (~101) e casos isolados de 2024. É uma estimativa padrão, não uma medição: a razão real da base é ~34. Superestima a injeção de jun/2026 em ~75 mil kWh/mês (~6,5%). Tratamento: flag `energia_estimada` e reestimativa (ou exclusão) no diagnóstico. |
| S-GD-05 | 2 GDs comerciais (AUTOCONSUMO REMOTO) com razão fisicamente impossível (168 e 328 kWh/kWp) | Baixa | 🔴 | UC104176 e UC112709. A escala da potência provavelmente está errada, mas não dá para comprovar. Tratamento: quarentena (`POTENCIA_INCONSISTENTE`). **Diverge do `perfil_geracao_distribuida_Adryan.md`**, que afirma que todas as 35 caem na faixa normal depois do ÷1000. |
| S-GD-06 | **GD conectada antes da ligação da UC** | Baixa | 🔴 | 5 UCs (UC106046, UC100259, UC102507, UC110560, UC119180), achado do Adryan. Ex.: GD em 2024-04-12, UC ligada em 2025-07-29. **Todas têm energia = kWp × 110 exato**, o mesmo padrão de "energia estimada" do S-GD-04. Isso reforça a leitura de que "× 110" é preenchido quando a UC não tem histórico. Tratamento: quarentena `GD_ANTES_DA_LIGACAO`. |
| S-INS-01 | **Qualquer `resultado` sem "CONFIRMADA" vira `SEM_IRREGULARIDADE`**, inclusive vazio e pendente | Alta | 🔴 (lógica) / 🟡 (volume) | Distorce a taxa de acerto das inspeções, que é a base da fila de perdas. |
| S-INS-02 | `data` das inspeções com o mesmo risco de ambiguidade entre dia e mês do S-MED-01 | Média | 🟡 | — |
| S-OCO-01 | `duracao_min` só remove o texto `" min"`; qualquer outro formato vira null | Baixa | ⚪ Refutado | Só existem 2 formatos: número (163.800) e `"N min"` (16.200). O código atual resolve, e a duração bate 100% com `encerramento − abertura`. |
| S-OCO-02 | `data_abertura` e `data_encerramento` com um único formato | Baixa | ⚪ Refutado | O formato é sempre ISO com hora. Não há datas inválidas, e o encerramento é sempre posterior à abertura. |
| S-OCO-03 | **`causa` sem informação em 4 formas** (`null`, `-`, `N/A`, `NULL`) | Média | 🔴 | 5.400 (3%). O notebook atual só aplica `upper`, então `-`, `N/A` e `NULL` viram 3 "causas" no portal e na IA. Tratamento: `NAO INFORMADA`, separado da categoria válida `NAO IDENTIFICADA`. |
| S-OCO-04 | **Durações truncadas em 2.880 min (48 h)** | Baixa | 🔴 | Confirmado: a cauda cai suavemente até 5–11 por faixa e salta para 30 exatamente em 2.880 (26 delas em jul/2025). O DEC de jul/2025 está levemente subestimado. Tratamento: flag `duracao_truncada` e documentação. |
| S-OCO-05 | OSCILACAO (14.562) contada como interrupção | Baixa | 🟡 Decisão | Na regulação, oscilação não é interrupção, mas o case define cada registro como "UC interrompida". Recomendação: contar tudo e oferecer um filtro no portal. Documentar no dicionário. |
| S-ATE-01 | **`historico` mantido como array**, o que quebra a exportação da Gold para CSV | Alta | 🔴 | Spark não grava array em CSV. Precisa virar uma tabela separada. |
| S-ATE-02 | **Rótulos das ações do `historico` são aleatórios** | Média | 🔴 | ~81% dos chamados desordenados, com taxa **igual** em todos os municípios e canais (o que um sorteio entre 5 ações produziria). As ações estão 100% dentro da janela do próprio chamado e no mesmo canal. Decisão: usar só as datas principais e `qtd_tratativas`; **não usar `teve_despacho`**. Ver `perfil_atendimentos.md` §4. |
| S-ATE-03 | ~~Pico de ~3× no volume de chamados em jul/2025~~ | — | ⚪ Refutado | **Não é artefato.** O excesso está espalhado nos 31 dias, os protocolos são sequenciais e não há cópias de outros meses. O mês tem comportamento próprio (nota 3,11 contra 4,10; resolução de 363 h contra 120 h). Virou o achado de negócio N-06. |
| S-ATE-04 | Chamados sem nota de satisfação | Baixa | 🔴 | 9.566 (3%). Manter null e excluir da média. |

---

## C. Notebook `silver_to_gold.py`

| ID | Problema | Gravidade | Status | Evidência e observação |
|---|---|---|---|---|
| G-01 | DEC/FEC com `coalesce(total_consumidores, 1)` | Baixa | ⚪ Sem efeito hoje | Todos os alimentadores das ocorrências existem no cadastro (100% coerentes com a UC). A fórmula do colega está correta para o grão. É frágil se aparecer um alimentador novo; trocar por um teste que falha se `total_consumidores` vier nulo. |
| G-02 | `dim_alimentadores` usa `F.first("municipio")` | Média | 🔴 | O resultado não é determinístico: um alimentador que atende 2 municípios pode mudar de município a cada execução. |
| G-03 | **Medidores não estão na Gold** | Alta | 🔴 | A visão 360 da UC, pedida pelo case, exige o medidor instalado. |
| G-04 | **`agg_receita_mensal` não decompõe preço × volume** | Alta | 🔴 | É a pergunta central do Diretor Comercial. |
| G-05 | `agg_receita_mensal` cruza com leituras por `mes_referencia` sem garantir que o formato é o mesmo nas duas tabelas | Alta | 🟡 | Se o formato divergir, o join não encontra nada e o volume fica zero. Se houver leituras duplicadas, o volume sai inflado. |
| G-06 | O volume vem das leituras (consumo medido) e não do kWh faturado | Média | ⚪ | **É a única opção:** as faturas não têm kWh (S-FAT-07). Documentar no dicionário que, com GD, o consumo medido é diferente do faturado. |
| G-07 | `receita_recebida` considera só `status == "PAGA"` | — | ⚪ Refutado | Só existem PAGA e EM ABERTO. A regra está correta. |
| G-08 | `possui_gd` é calculado sem verificar se o `id_uc` da GD é válido | Baixa | 🟡 | — |
| G-09 | `fact_atendimentos` herda o array do `historico` | Alta | 🔴 | Mesma causa do S-ATE-01. |
| G-10 | **Fila de inspeção (perdas) não existe** | Alta | 🔴 | É uma user story obrigatória do case. |

---

## D. Requisitos do case ainda não atendidos

| ID | Requisito | Status |
|---|---|---|
| R-01 | Exportar a Gold em CSV para um banco local (SQLite ou Postgres) | 🔴 Não existe |
| R-02 | Databricks Workflow (Job) ligando as 3 camadas, com agendamento justificado | 🔴 Não existe |
| R-03 | Dicionário de dados da Gold, com as métricas e as decisões de limpeza | ✅ Notebook `07_dicionario_gold` (26/10): 259 colunas e 17 métricas, com trava que falha se o dicionário divergir das tabelas. Publicado em comentários do catálogo, tabelas `meta_*`, `dicionario_dados_gold.md` e `.json` |
| R-04 | Testes de qualidade automatizados (diferencial) | 🔴 Não existe |
| R-05 | Integridade referencial entre medição, faturamento e cadastro | 🔴 Parcial (só faturas × UC) |

---

## E. Achados de negócio (não são erros, mas vão para o diagnóstico)

| ID | Achado | Fonte |
|---|---|---|
| N-01 | Quase não houve ligações novas entre 2022 e 2026: 372 no total, contra cerca de 1.900 por ano até 2021. Contradiz em parte a frase "a base cresceu". | `perfil_unidades_consumidoras.md` |
| N-05 | ⭐ **Toda a GD da base conectou entre jan/2024 e jun/2026**: zero no primeiro ano da base, 3.510 no fim, injetando ~1,16 GWh por mês (~1,08 GWh corrigindo os valores estimados × 110, S-GD-04). É a candidata número 1 para a queda de ~4% no volume. Falta quantificar com faturas e leituras. | `perfil_geracao_distribuida.md` §6 |
| N-07 | ⭐ **Bandeiras: o primeiro ano (jul/22–jun/23) foi 100% verde; os últimos 12 meses tiveram 8 meses com acréscimo** (3 amarela, 3 VP1, 2 VP2). O preço subiu mais do que o reajuste de 10,5%, então o efeito-volume precisa ser maior para a receita subir só ~8%. | `perfil_faturas.md` §7 |
| N-09 | ⭐ **"+8% de receita" confirmado nos dados**: receita total de R$ 157,1 mi para R$ 169,7 mi (+8,0%) do primeiro ano para os últimos 12 meses, com UCs +0,6%. Se o volume caiu 4%, o preço médio efetivo subiu ~12,5%. **Inadimplência descartada como causa** (estável em ~8% todo mês; recebida +7,9%). Forte sazonalidade (ticket de ~R$ 215 no inverno e ~R$ 370 no verão). | `perfil_faturas.md` §8 |
| N-10 | **O ranking de DEC/FEC é distorcido pelo tamanho do alimentador** (confirmado): os alimentadores com menos de 1.000 UCs recebem ~365 interrupções por ano **independentemente do tamanho**, então os pequenos (< 100 UCs) têm FEC médio de 8,0 contra 1,6 dos médios. 3 alimentadores (ALM-REC-008, ALM-SAO-004, ALM-JAB-004) concentram ~64 mil horas × UC em 2025, **mas só por causa do temporal de jul/2025**: sem julho, o DEC deles cai para 0,2–0,65, entre os melhores da base. **Não existe um "pior alimentador crônico"**. O risco da rede é climático e concentrado nesses 3 circuitos (72% das ocorrências de jul/2025). | `perfil_ocorrencias_rede.md` §6–7 |
| N-11 | Picos de ocorrências em nov/2025 e fev/2026 (+57%), **difusos** (todos os alimentadores a ~2× a própria média), com causas normais e sem efeito no call center. **Duplicação descartada** (ids sequenciais, sem gêmeos, aumento uniforme da taxa). Meses atípicos, sem causa identificável; aparecem UCs com 5–9 interrupções no mesmo mês. | `perfil_ocorrencias_rede.md` §7 |
| N-12 | **Dias críticos (regra simplificada do PRODIST): 31 dias, exatamente os de jul/2025.** É o candidato natural a expurgo no DEC/FEC regulatório. | `perfil_ocorrencias_rede.md` §7 |
| N-15 | ⭐⭐ **Decomposição preço × volume (Gold, 26/10):** receita +R$ 12,58 mi (+8,0%) = **efeito-preço +R$ 23,75 mi** e **efeito-volume −R$ 11,18 mi**. **76% do efeito-volume (−R$ 8,50 mi) vem das ~3,5 mil UCs com GD** (7,8% da base), cujo consumo medido caiu **~64%** (residenciais e comerciais). Sem GD, o volume cai pouco: residencial −2,6%, comercial −2,4%, industrial −0,9%, rural −5,1%, poder público +0,7%; e a receita sobe +8,6% (industrial) a +29% (rural). **A GD explica a maior parte da queda de volume; preço (reajuste + bandeiras) sustenta a receita.** | `agg_receita_preco_volume` |
| N-16 | Fila de inspeção v1: 10.618 UCs com score ≥ 20. Na calibração, score 50+ acerta 93,5% (889 inspeções) contra 7,3% abaixo de 20. **Atenção: há vazamento** (as regras "reincidente" e "bairro com alta taxa" usam as próprias inspeções). Recalibrar sem esses sinais antes de citar o número. | `fila_inspecao` |
| N-14 | ⭐ **Volume medido caiu 6,8%** (226,7 → 211,3 GWh) do primeiro ano para os últimos 12 meses, com UCs +0,6% (**−7,3% por UC**), já com clones removidos e o mês da troca de medidor imputado. O diretor fala em "quase 4%" de volume **faturado**. A diferença precisa ser explicada no diagnóstico (definição de "volume faturado", efeito da GD e da troca de medidores). | `silver_leituras` (26/10) |
| N-13 | **Leituras estimadas: 18% do total**, indistinguíveis da real nos números (só o rótulo `tipo_leitura` as identifica), com viés de −0,3% a −0,7%. A participação cai de ~19% (2022–2025) para **14,1% em 2026**, o que coincide com a campanha de smart meters (leitura remota reduz estimativa). Efeito pequeno, mas na mesma direção: **aumenta levemente o volume medido no fim do período**. | `perfil_leituras.md` §3 |
| N-08 | Base faturada estável: 44.638 UCs com 48 faturas e ~358 com histórico parcial, o que bate com as ~372 ligações novas (confirma o N-01). Inadimplência: 8,0% das faturas em aberto; atraso mediano de 11 dias. | `perfil_faturas.md` §7 |
| N-03 | **Nota de satisfação e tempo de resolução não variam entre canais e assuntos** (média de 4,04; mediana de ~125 h). A IA não deve apresentar diferenças por canal ou assunto como insight. **No tempo, variam:** ver N-06. | `perfil_atendimentos.md` §5 |
| N-06 | ⭐ **Crise de atendimento em jul/2025**: volume 2,8× em todos os assuntos, satisfação de 4,10 para 3,11 e resolução de 120 h para 363 h, afetando 14.828 UCs. É um evento legítimo e um insight pronto para o portal e a IA. **As faturas de jul/2025 estão normais** (ticket, inadimplência e atraso em linha com os anos anteriores), então não explicam a crise. ✅ **Causa identificada: evento climático.** Em jul/2025 as ocorrências foram 5,3× o normal (17.844), as horas × UC 15,7× (87.385) e **97,2% tiveram causa climática** (contra ~16% nos outros meses). Entra no conceito de "dia crítico" do PRODIST: mostrar o DEC com e sem expurgo. | `perfil_atendimentos.md` §6 · `perfil_ocorrencias_rede.md` §7 |
| N-04 | Chamados de FATURA estáveis (~870 por mês) durante todo o período, sem acompanhar o reajuste. Os chamados não ajudam a explicar o efeito-preço. | `perfil_atendimentos.md` §5 |
| N-02 | ⭐ **Campanha de troca para smart meters entre set/2025 e mar/2026**: 6.299 trocas (~14% das UCs), ~900 por mês, **90% eletromecânico → smart** (cerca de 1/3 do parque eletromecânico). Cai dentro dos "últimos 12 meses" do diagnóstico. Medidor eletromecânico antigo tende a registrar menos, então o consumo medido dessas UCs pode **subir** depois da troca. Uma UC com salto grande de consumo depois da troca é sinal para a fila de perdas. A medir nas leituras. | `perfil_medidores.md` §7 |
