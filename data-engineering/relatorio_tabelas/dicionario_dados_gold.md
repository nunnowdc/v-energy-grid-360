# Dicionário de dados: camada Gold · V-Energy Grid 360

Gerado automaticamente pelo notebook `07_dicionario_gold` em 25/10/2026. Não edite à mão: altere o notebook e rode de novo.

Os códigos entre parênteses (ex.: S-FAT-05) apontam para o `registro_de_problemas.md`.

**Classificação LGPD:** ALTO = identifica a pessoa ou a associa a infração/inadimplência · MEDIO = comportamento pessoal (consumo, gasto) · BAIXO = atributo pouco revelador · PSEUDONIMIZADO = chave que reidentifica via cadastro · NAO_PESSOAL. Detalhes em `levantamento_lgpd.md`.

## Índice

- [`agg_continuidade_alimentador`](#agg_continuidade_alimentador): DEC e FEC mensais por alimentador, com e sem dias críticos. Inclui os meses sem interrupção (zero).
- [`agg_continuidade_alimentador_anual`](#agg_continuidade_alimentador_anual): DEC e FEC anuais por alimentador, com rankings de pior DEC e de maior impacto (horas × UC).
- [`agg_receita_mensal`](#agg_receita_mensal): Receita, volume e preço médio por mês e segmento. Base para comparar quaisquer períodos.
- [`agg_receita_preco_volume`](#agg_receita_preco_volume): Decomposição da variação de receita do primeiro ano para os últimos 12 meses em efeito-volume e efeito-preço.
- [`dim_alimentador`](#dim_alimentador): Alimentadores (circuitos de média tensão) com o perfil das UCs atendidas.
- [`dim_competencia`](#dim_competencia): Calendário mensal da base, com a bandeira do mês e o período do diagnóstico de receita.
- [`dim_geracao_distribuida`](#dim_geracao_distribuida): UCs com geração distribuída (painel solar) conectada.
- [`dim_medidor`](#dim_medidor): Histórico de medidores, inclusive os retirados na campanha de troca por smart meters.
- [`dim_unidade_consumidora`](#dim_unidade_consumidora): Cadastro das unidades consumidoras (1 linha por UC), com o medidor atual, a GD e a troca de medidor. Base da visão 360.
- [`fact_atendimentos`](#fact_atendimentos): Chamados do call center.
- [`fact_faturamento`](#fact_faturamento): Faturas mensais com receita, pagamento e o consumo medido no mês.
- [`fact_inspecoes`](#fact_inspecoes): Inspeções de campo da equipe de perdas (ago–dez/2025).
- [`fact_leituras`](#fact_leituras): Leituras mensais de consumo por UC. É a única fonte de volume (kWh) da base.
- [`fact_ocorrencias`](#fact_ocorrencias): Interrupções de fornecimento. Cada registro é uma UC interrompida (definição do case).
- [`fila_inspecao`](#fila_inspecao): Fila priorizada de UCs suspeitas de perdas não técnicas, com motivo e energia estimada a recuperar (v1: regras, a calibrar).

## Métricas

| Métrica | Definição | Fórmula | Onde | Decisões que a afetam |
|---|---|---|---|---|
| **Receita faturada** | Valor total cobrado nas faturas (energia + tributos). | `SUM(fact_faturamento.receita_faturada)` | `fact_faturamento.receita_faturada` | Faturas órfãs fora (S-FAT-06, 1,1–2,2% da receita/mês, estável); R$ 1.234,56 convertido. |
| **Receita recebida** | Receita das faturas pagas. | `SUM(receita_faturada WHERE status = 'PAGA')` | `fact_faturamento.receita_recebida` | Inadimplência estável em ~8% (N-09). |
| **Volume (consumo medido)** | Energia consumida, medida nas leituras. | `SUM(fact_leituras.consumo_kwh)` | `fact_leituras.consumo_kwh` | A fatura não tem kWh (S-FAT-07). Clones excluídos (S-LEI-09), duplicatas exatas excluídas (S-01), troca de medidor imputada (S-LEI-08), sentinela -1 tratada (S-LEI-05). |
| **Preço médio efetivo** | Quanto se fatura por kWh consumido. | `receita_faturada ÷ consumo_kwh` | `agg_receita_preco_volume.preco_p0/p1` | Inclui tributos e o efeito das bandeiras; em UCs com GD, captura a compensação de créditos. |
| **Efeito-volume** | Variação de receita que viria só da mudança de quantidade, ao preço do período base. | `(kwh_p1 − kwh_p0) × preco_p0` | `agg_receita_preco_volume.efeito_volume` | Segmento sem consumo no período base: toda a variação vai para volume. |
| **Efeito-preço** | Variação de receita explicada pela mudança do preço médio. | `(preco_p1 − preco_p0) × kwh_p1` | `agg_receita_preco_volume.efeito_preco` | efeito_volume + efeito_preco = receita_p1 − receita_p0 (exato). |
| **DEC** | Duração equivalente de interrupção por UC (h). | `Σ duracao_h ÷ total_ucs do alimentador` | `agg_continuidade_alimentador.dec` | Grão do case: 1 ocorrência = 1 UC interrompida. Durações truncadas em 48 h (S-OCO-04). Valores simplificados: comparam alimentadores, não os limites regulatórios. |
| **FEC** | Frequência equivalente de interrupção por UC. | `nº de interrupções ÷ total_ucs` | `agg_continuidade_alimentador.fec` | Alimentadores com < 100 UCs ficam inflados (N-10). |
| **Dia crítico** | Dia com ocorrências muito acima do normal, expurgado do DEC/FEC regulatório (PRODIST, Módulo 8). | `ocorrências do dia > média diária + 3 desvios-padrão (base inteira)` | `fact_ocorrencias.dia_critico` | Regra simplificada (o PRODIST aplica por conjunto de UCs). Resultado: os 31 dias de jul/2025 (N-12). |
| **Status de pagamento** | Situação da fatura. | `PAGA se status = PAGA; senão PENDENTE se vencimento ≥ data de referência; senão ATRASADA` | `fact_faturamento.status_pagamento` | Data de referência = última emissão da base (fim da extração), não a data de hoje. |
| **Dias de atraso** | Atraso do pagamento. | `max(0, (data_pagamento ou data de referência) − data_vencimento)` | `fact_faturamento.dias_atraso` |  |
| **Variação contra o ano anterior** | Consumo do mês contra o mesmo mês do ano anterior (visão 360). | `100 × (consumo_kwh ÷ consumo_ano_anterior_kwh − 1)` | `fact_leituras.variacao_ano_anterior_pct` | Forte sazonalidade: sempre comparar o mesmo mês. |
| **Score da fila de inspeção** | Pontuação de suspeita de perda não técnica (v1, regras). | `queda de consumo ≥50/30/15% (+40/30/15, não conta se ligou GD) + medidor eletromecânico (+15) + leituras estimadas ≥50/25% (+15/8) + anomalias de leitura (+10/5) + bairro com taxa ≥1,2× a média (+10) + reincidente (+10) − inspecionada há ≤180 dias sem irregularidade (−25), limitado a 0–100` | `fila_inspecao.score` | Pesos a calibrar; a calibração atual tem vazamento (N-16). |
| **kWh recuperável** | Energia estimada a recuperar por ano. | `max(0, consumo médio do ano anterior − consumo médio recente) × 12` | `fila_inspecao.kwh_recuperavel_estimado_ano` | Zero quando a queda é explicada por GD. |
| **Taxa de irregularidade** | Fração das inspeções com irregularidade confirmada. | `AVG(resultado = 'IRREGULARIDADE_CONFIRMADA')` | `fact_inspecoes.resultado` | 62,7% na base (ago–dez/2025). |
| **Tempo de resolução** | Duração do chamado. | `(data_fechamento − data_abertura) em horas` | `fact_atendimentos.tempo_resolucao_h` |  |
| **Energia injetada pela GD** | Energia que as UCs com GD injetam na rede por mês. | `SUM(dim_geracao_distribuida.energia_reestimada_kwh)` | `dim_geracao_distribuida.energia_reestimada_kwh` | Valores estimados como kWp × 110 reestimados pela razão real (S-GD-04). |

## agg_continuidade_alimentador

DEC e FEC mensais por alimentador, com e sem dias críticos. Inclui os meses sem interrupção (zero).

- **Grão:** alimentador × competência (122 × 48)
- **Origem:** fact_ocorrencias + dim_alimentador
- **Notebook:** `05_gold_continuidade`
- **Termos do dia a dia:** DEC, FEC, continuidade, qualidade do fornecimento, interrupções por alimentador

| Coluna | Tipo | Descrição | Regra / decisão | LGPD |
|---|---|---|---|---|
| `alimentador` | string | Código do alimentador, o circuito de média tensão que atende a UC (ex.: ALM-REC-008). |  | NAO_PESSOAL |
| `competencia` | date | Mês de referência do registro, representado pelo 1º dia do mês. | Convertida de mes_referencia (yyyy-MM). | NAO_PESSOAL |
| `total_ucs` | bigint | Número de UCs atendidas pelo alimentador (denominador do DEC e do FEC). | Contado no cadastro de UCs reais. | NAO_PESSOAL |
| `municipio_principal` | string | Município com mais UCs no alimentador. | Escolhido pelo mais frequente, de forma determinística (corrige G-02). | NAO_PESSOAL |
| `regiao` | string | Código de região do alimentador (parte do meio do código: REC, JAB, OLI...). |  | NAO_PESSOAL |
| `alimentador_pequeno` | boolean | Alimentador com menos de 100 UCs. | Ressalva: DEC/FEC desses alimentadores fica inflado pelo denominador pequeno (N-10). | NAO_PESSOAL |
| `interrupcoes` | bigint | Número de UCs interrompidas no período da linha (cada ocorrência = 1 UC interrompida, definição do case). |  | NAO_PESSOAL |
| `horas_x_uc` | double | Soma das horas sem energia de todas as UCs interrompidas no período (impacto absoluto). | Usada no ranking de 'onde a manutenção dá mais retorno'. | NAO_PESSOAL |
| `interrupcoes_sem_dia_critico` | bigint | Interrupções excluindo as ocorridas em dias críticos. | Ver a métrica 'Dia crítico'. | NAO_PESSOAL |
| `horas_x_uc_sem_dia_critico` | double | Horas × UC excluindo os dias críticos. |  | NAO_PESSOAL |
| `interrupcoes_climaticas` | bigint | Interrupções com causa CLIMATICA. |  | NAO_PESSOAL |
| `interrupcoes_oscilacao` | bigint | Interrupções do tipo OSCILACAO. | Contadas no DEC/FEC por definição do case; use esta coluna para descontá-las (S-OCO-05). | NAO_PESSOAL |
| `duracoes_truncadas` | bigint | Interrupções cuja duração foi cortada em 48 h na origem. | A duração real é maior; o DEC fica levemente subestimado (S-OCO-04). | NAO_PESSOAL |
| `mes_referencia` | string | Competência em texto, no formato yyyy-MM. |  | NAO_PESSOAL |
| `ano` | int | Ano da competência. |  | NAO_PESSOAL |
| `dec` | double | DEC: duração equivalente de interrupção por UC, em horas, no período da linha. | Ver a métrica 'DEC'. | NAO_PESSOAL |
| `fec` | double | FEC: frequência equivalente de interrupção por UC, no período da linha. | Ver a métrica 'FEC'. | NAO_PESSOAL |
| `dec_sem_dia_critico` | double | DEC excluindo os dias críticos (expurgo simplificado do PRODIST). | Ver 'Dia crítico'. | NAO_PESSOAL |
| `fec_sem_dia_critico` | double | FEC excluindo os dias críticos. | Ver 'Dia crítico'. | NAO_PESSOAL |
| `_processado_em` | timestamp | Data e hora em que o pipeline gravou a linha. | Coluna técnica. | NAO_PESSOAL |

## agg_continuidade_alimentador_anual

DEC e FEC anuais por alimentador, com rankings de pior DEC e de maior impacto (horas × UC).

- **Grão:** alimentador × ano
- **Origem:** agg_continuidade_alimentador
- **Notebook:** `05_gold_continuidade`
- **Termos do dia a dia:** piores alimentadores, ranking de DEC, onde fazer manutenção

| Coluna | Tipo | Descrição | Regra / decisão | LGPD |
|---|---|---|---|---|
| `alimentador` | string | Código do alimentador, o circuito de média tensão que atende a UC (ex.: ALM-REC-008). |  | NAO_PESSOAL |
| `ano` | int | Ano da competência. |  | NAO_PESSOAL |
| `total_ucs` | bigint | Número de UCs atendidas pelo alimentador (denominador do DEC e do FEC). | Contado no cadastro de UCs reais. | NAO_PESSOAL |
| `municipio_principal` | string | Município com mais UCs no alimentador. | Escolhido pelo mais frequente, de forma determinística (corrige G-02). | NAO_PESSOAL |
| `regiao` | string | Código de região do alimentador (parte do meio do código: REC, JAB, OLI...). |  | NAO_PESSOAL |
| `alimentador_pequeno` | boolean | Alimentador com menos de 100 UCs. | Ressalva: DEC/FEC desses alimentadores fica inflado pelo denominador pequeno (N-10). | NAO_PESSOAL |
| `interrupcoes` | bigint | Número de UCs interrompidas no período da linha (cada ocorrência = 1 UC interrompida, definição do case). |  | NAO_PESSOAL |
| `horas_x_uc` | double | Soma das horas sem energia de todas as UCs interrompidas no período (impacto absoluto). | Usada no ranking de 'onde a manutenção dá mais retorno'. | NAO_PESSOAL |
| `interrupcoes_sem_dia_critico` | bigint | Interrupções excluindo as ocorridas em dias críticos. | Ver a métrica 'Dia crítico'. | NAO_PESSOAL |
| `horas_x_uc_sem_dia_critico` | double | Horas × UC excluindo os dias críticos. |  | NAO_PESSOAL |
| `interrupcoes_climaticas` | bigint | Interrupções com causa CLIMATICA. |  | NAO_PESSOAL |
| `interrupcoes_oscilacao` | bigint | Interrupções do tipo OSCILACAO. | Contadas no DEC/FEC por definição do case; use esta coluna para descontá-las (S-OCO-05). | NAO_PESSOAL |
| `duracoes_truncadas` | bigint | Interrupções cuja duração foi cortada em 48 h na origem. | A duração real é maior; o DEC fica levemente subestimado (S-OCO-04). | NAO_PESSOAL |
| `meses` | bigint | Meses do ano presentes na base (2022 e 2026 são parciais). |  | NAO_PESSOAL |
| `dec` | double | DEC: duração equivalente de interrupção por UC, em horas, no período da linha. | Ver a métrica 'DEC'. | NAO_PESSOAL |
| `fec` | double | FEC: frequência equivalente de interrupção por UC, no período da linha. | Ver a métrica 'FEC'. | NAO_PESSOAL |
| `dec_sem_dia_critico` | double | DEC excluindo os dias críticos (expurgo simplificado do PRODIST). | Ver 'Dia crítico'. | NAO_PESSOAL |
| `fec_sem_dia_critico` | double | FEC excluindo os dias críticos. | Ver 'Dia crítico'. | NAO_PESSOAL |
| `rank_dec` | int | Posição no ranking de DEC do ano (1 = pior). | Ressalva para alimentadores pequenos (N-10). | NAO_PESSOAL |
| `rank_dec_sem_dia_critico` | int | Posição no ranking de DEC sem dias críticos. |  | NAO_PESSOAL |
| `rank_impacto_horas_x_uc` | int | Posição no ranking de horas × UC (1 = maior impacto absoluto). | Em 2025, os 3 primeiros só lideram por causa do temporal de jul/2025. | NAO_PESSOAL |
| `_processado_em` | timestamp | Data e hora em que o pipeline gravou a linha. | Coluna técnica. | NAO_PESSOAL |

## agg_receita_mensal

Receita, volume e preço médio por mês e segmento. Base para comparar quaisquer períodos.

- **Grão:** competência × município × bairro × classe × possui_gd
- **Origem:** fact_faturamento + dim_unidade_consumidora
- **Notebook:** `05_gold_receita`
- **Termos do dia a dia:** receita mensal, faturamento por mês, evolução da receita

| Coluna | Tipo | Descrição | Regra / decisão | LGPD |
|---|---|---|---|---|
| `competencia` | date | Mês de referência do registro, representado pelo 1º dia do mês. | Convertida de mes_referencia (yyyy-MM). | NAO_PESSOAL |
| `mes_referencia` | string | Competência em texto, no formato yyyy-MM. |  | NAO_PESSOAL |
| `bandeira_tarifaria` | string | Bandeira tarifária do mês: VERDE, AMARELA, VERMELHA_P1 ou VERMELHA_P2. | Uma bandeira por competência (validado). O acréscimo da bandeira está embutido em valor_energia. | NAO_PESSOAL |
| `municipio` | string | Município da UC (14 municípios da Região Metropolitana do Recife). | Do cadastro, padronizado. | BAIXO |
| `bairro` | string | Bairro da UC. | Encoding corrigido em 60 bairros que vinham com mojibake, ex.: 'InhamÃ£' -> 'Inhamã' (S-UC-03). | BAIXO |
| `classe` | string | Classe de consumo: RESIDENCIAL, COMERCIAL, INDUSTRIAL, RURAL ou PODER_PUBLICO. | Normalizada de várias grafias (caixa e acento). | BAIXO |
| `possui_gd` | boolean | Indica se a UC tem geração distribuída (painel solar) conectada. | Vem das GDs válidas; 7 GDs inconsistentes ficaram na quarentena (S-GD-05, S-GD-06). | BAIXO |
| `receita_faturada` | double | Soma da receita faturada (R$). |  | NAO_PESSOAL |
| `receita_recebida` | double | Soma da receita recebida (R$). |  | NAO_PESSOAL |
| `receita_energia` | double | Soma de valor_energia (R$, sem tributos). |  | NAO_PESSOAL |
| `consumo_kwh` | double | Soma do consumo medido (kWh). |  | NAO_PESSOAL |
| `ucs_faturadas` | bigint | UCs com fatura no mês. |  | NAO_PESSOAL |
| `faturas` | bigint | Número de faturas. |  | NAO_PESSOAL |
| `faturas_atrasadas` | bigint | Faturas com status_pagamento = ATRASADA. |  | NAO_PESSOAL |
| `preco_medio_kwh` | double | Receita faturada ÷ consumo (R$/kWh, com tributos). |  | NAO_PESSOAL |
| `ano` | int | Ano da competência. |  | NAO_PESSOAL |
| `mes` | int | Mês da competência (1 a 12). |  | NAO_PESSOAL |
| `_processado_em` | timestamp | Data e hora em que o pipeline gravou a linha. | Coluna técnica. | NAO_PESSOAL |

## agg_receita_preco_volume

Decomposição da variação de receita do primeiro ano para os últimos 12 meses em efeito-volume e efeito-preço.

- **Grão:** município × bairro × classe × possui_gd
- **Origem:** fact_faturamento + dim_unidade_consumidora
- **Notebook:** `05_gold_receita`
- **Termos do dia a dia:** preço e volume, efeito preço, efeito volume, por que a receita mudou

| Coluna | Tipo | Descrição | Regra / decisão | LGPD |
|---|---|---|---|---|
| `municipio` | string | Município da UC (14 municípios da Região Metropolitana do Recife). | Do cadastro, padronizado. | BAIXO |
| `bairro` | string | Bairro da UC. | Encoding corrigido em 60 bairros que vinham com mojibake, ex.: 'InhamÃ£' -> 'Inhamã' (S-UC-03). | BAIXO |
| `classe` | string | Classe de consumo: RESIDENCIAL, COMERCIAL, INDUSTRIAL, RURAL ou PODER_PUBLICO. | Normalizada de várias grafias (caixa e acento). | BAIXO |
| `possui_gd` | boolean | Indica se a UC tem geração distribuída (painel solar) conectada. | Vem das GDs válidas; 7 GDs inconsistentes ficaram na quarentena (S-GD-05, S-GD-06). | BAIXO |
| `receita_p0` | double | Receita faturada no período base (primeiro ano). |  | NAO_PESSOAL |
| `receita_p1` | double | Receita faturada no período comparado (últimos 12 meses). |  | NAO_PESSOAL |
| `kwh_p0` | double | Consumo medido no período base (kWh). |  | NAO_PESSOAL |
| `kwh_p1` | double | Consumo medido no período comparado (kWh). |  | NAO_PESSOAL |
| `ucs_p0` | bigint | UCs faturadas no período base. |  | NAO_PESSOAL |
| `ucs_p1` | bigint | UCs faturadas no período comparado. |  | NAO_PESSOAL |
| `preco_p0` | double | Preço médio efetivo no período base = receita_p0 ÷ kwh_p0 (R$/kWh). |  | NAO_PESSOAL |
| `preco_p1` | double | Preço médio efetivo no período comparado (R$/kWh). |  | NAO_PESSOAL |
| `variacao_receita` | double | receita_p1 − receita_p0 (R$). |  | NAO_PESSOAL |
| `efeito_volume` | double | Parte da variação explicada pela quantidade: (kwh_p1 − kwh_p0) × preco_p0. | Ver a métrica 'Efeito-volume'. | NAO_PESSOAL |
| `efeito_preco` | double | Parte da variação explicada pelo preço: (preco_p1 − preco_p0) × kwh_p1. | Ver a métrica 'Efeito-preço'. | NAO_PESSOAL |
| `variacao_receita_pct` | double | Variação % da receita. |  | NAO_PESSOAL |
| `variacao_volume_pct` | double | Variação % do consumo. |  | NAO_PESSOAL |
| `variacao_preco_pct` | double | Variação % do preço médio efetivo. |  | NAO_PESSOAL |
| `kwh_por_uc_p0` | double | Consumo médio por UC no período base. |  | NAO_PESSOAL |
| `kwh_por_uc_p1` | double | Consumo médio por UC no período comparado. |  | NAO_PESSOAL |
| `periodo_p0` | string | Meses do período base (ex.: 2022-07 a 2023-06). |  | NAO_PESSOAL |
| `periodo_p1` | string | Meses do período comparado (ex.: 2025-07 a 2026-06). |  | NAO_PESSOAL |
| `_processado_em` | timestamp | Data e hora em que o pipeline gravou a linha. | Coluna técnica. | NAO_PESSOAL |

## dim_alimentador

Alimentadores (circuitos de média tensão) com o perfil das UCs atendidas.

- **Grão:** 1 linha por alimentador (122)
- **Origem:** silver_unidades_consumidoras
- **Notebook:** `04_gold_dimensoes`
- **Termos do dia a dia:** alimentador, circuito, rede elétrica

| Coluna | Tipo | Descrição | Regra / decisão | LGPD |
|---|---|---|---|---|
| `alimentador` | string | Código do alimentador, o circuito de média tensão que atende a UC (ex.: ALM-REC-008). |  | NAO_PESSOAL |
| `total_ucs` | bigint | Número de UCs atendidas pelo alimentador (denominador do DEC e do FEC). | Contado no cadastro de UCs reais. | NAO_PESSOAL |
| `qtd_municipios` | bigint | Quantidade de municípios atendidos pelo alimentador. |  | NAO_PESSOAL |
| `qtd_bairros` | bigint | Quantidade de bairros atendidos. |  | NAO_PESSOAL |
| `ucs_residencial` | bigint | UCs residenciais no alimentador. |  | NAO_PESSOAL |
| `ucs_comercial` | bigint | UCs comerciais no alimentador. |  | NAO_PESSOAL |
| `ucs_industrial` | bigint | UCs industriais no alimentador. |  | NAO_PESSOAL |
| `ucs_rural` | bigint | UCs rurais no alimentador. |  | NAO_PESSOAL |
| `ucs_poder_publico` | bigint | UCs de poder público no alimentador. |  | NAO_PESSOAL |
| `municipio_principal` | string | Município com mais UCs no alimentador. | Escolhido pelo mais frequente, de forma determinística (corrige G-02). | NAO_PESSOAL |
| `regiao` | string | Código de região do alimentador (parte do meio do código: REC, JAB, OLI...). |  | NAO_PESSOAL |
| `alimentador_pequeno` | boolean | Alimentador com menos de 100 UCs. | Ressalva: DEC/FEC desses alimentadores fica inflado pelo denominador pequeno (N-10). | NAO_PESSOAL |
| `_processado_em` | timestamp | Data e hora em que o pipeline gravou a linha. | Coluna técnica. | NAO_PESSOAL |

## dim_competencia

Calendário mensal da base, com a bandeira do mês e o período do diagnóstico de receita.

- **Grão:** 1 linha por mês (48: jul/2022 a jun/2026)
- **Origem:** silver_faturas
- **Notebook:** `04_gold_dimensoes`
- **Termos do dia a dia:** mês, calendário, período

| Coluna | Tipo | Descrição | Regra / decisão | LGPD |
|---|---|---|---|---|
| `competencia` | date | Mês de referência do registro, representado pelo 1º dia do mês. | Convertida de mes_referencia (yyyy-MM). | NAO_PESSOAL |
| `mes_referencia` | string | Competência em texto, no formato yyyy-MM. |  | NAO_PESSOAL |
| `ano` | int | Ano da competência. |  | NAO_PESSOAL |
| `mes` | int | Mês da competência (1 a 12). |  | NAO_PESSOAL |
| `trimestre` | int | Trimestre do ano (1 a 4). |  | NAO_PESSOAL |
| `bandeira_tarifaria` | string | Bandeira tarifária do mês: VERDE, AMARELA, VERMELHA_P1 ou VERMELHA_P2. | Uma bandeira por competência (validado). O acréscimo da bandeira está embutido em valor_energia. | NAO_PESSOAL |
| `periodo_diagnostico` | string | PRIMEIRO_ANO (12 primeiros meses da base), ULTIMOS_12M (12 últimos) ou nulo. | Os dois períodos comparados pelo Diretor Comercial. | NAO_PESSOAL |
| `_processado_em` | timestamp | Data e hora em que o pipeline gravou a linha. | Coluna técnica. | NAO_PESSOAL |

## dim_geracao_distribuida

UCs com geração distribuída (painel solar) conectada.

- **Grão:** 1 linha por UC com GD (3.503)
- **Origem:** silver_geracao_distribuida
- **Notebook:** `04_gold_dimensoes`
- **Termos do dia a dia:** geração distribuída, painel solar, energia solar, GD

| Coluna | Tipo | Descrição | Regra / decisão | LGPD |
|---|---|---|---|---|
| `id_uc` | string | Identificador da unidade consumidora (UC), a chave que liga todas as tabelas. | Só UCs reais do cadastro (UC + 6 dígitos). Registros TESTE e de UC inexistente ficam na quarentena da Silver (S-UC-01, S-FAT-06). | PSEUDONIMIZADO |
| `potencia_kwp` | double | Potência instalada em kWp. | 35 valores em W divididos por 1000 (S-GD-02). | BAIXO |
| `potencia_corrigida_unidade` | boolean | A potência foi corrigida de W para kW. |  | NAO_PESSOAL |
| `data_conexao` | date | Data de conexão da GD (entre jan/2024 e jun/2026). |  | BAIXO |
| `modalidade` | string | GERACAO NA PROPRIA UC, AUTOCONSUMO REMOTO ou GERACAO COMPARTILHADA. |  | NAO_PESSOAL |
| `energia_injetada_kwh_media_mensal` | double | Energia média injetada na rede por mês (kWh), como veio da fonte. |  | BAIXO |
| `energia_estimada` | boolean | A energia da fonte é uma estimativa padrão (kWp × 110 exato), não uma medição. | 101 GDs, quase todas conectadas em mai–jun/2026 (S-GD-04). | NAO_PESSOAL |
| `energia_reestimada_kwh` | double | Energia injetada usada nas análises: a da fonte, ou a reestimada pela razão real da base (~34 kWh/kWp·mês) quando energia_estimada. | Corrige a superestimativa de ~75 mil kWh/mês (S-GD-04). | BAIXO |
| `kwh_por_kwp_mes` | double | Energia injetada por kWp por mês (indicador de consistência). | Valores > 150 são fisicamente impossíveis e foram para a quarentena (S-GD-05). | NAO_PESSOAL |
| `_processado_em` | timestamp | Data e hora em que o pipeline gravou a linha. | Coluna técnica. | NAO_PESSOAL |

## dim_medidor

Histórico de medidores, inclusive os retirados na campanha de troca por smart meters.

- **Grão:** 1 linha por medidor (51.299 = 45.000 atuais + 6.299 retirados)
- **Origem:** silver_medidores
- **Notebook:** `04_gold_dimensoes`
- **Termos do dia a dia:** medidor, relógio de luz

| Coluna | Tipo | Descrição | Regra / decisão | LGPD |
|---|---|---|---|---|
| `id_medidor` | string | Identificador do medidor. |  | PSEUDONIMIZADO |
| `id_uc` | string | Identificador da unidade consumidora (UC), a chave que liga todas as tabelas. | Só UCs reais do cadastro (UC + 6 dígitos). Registros TESTE e de UC inexistente ficam na quarentena da Silver (S-UC-01, S-FAT-06). | PSEUDONIMIZADO |
| `modelo` | string | Modelo do medidor (ex.: EM-1200, SM-4100). | Espaços removidos (S-MED-05). | NAO_PESSOAL |
| `tipo` | string | ELETROMECANICO, ELETRONICO ou SMART. | Normalizado de 9 grafias e validado contra o modelo (S-MED-04). | NAO_PESSOAL |
| `data_instalacao` | date | Data de instalação. | Traço lido como MM-dd-yyyy (S-MED-01). Na troca, é igual à retirada do medidor anterior. | BAIXO |
| `data_retirada` | date | Data de retirada (nula se o medidor está instalado). | Sentinela 9999-12-31 convertida em nulo. | BAIXO |
| `status` | string | ATIVO ou RETIRADO. |  | NAO_PESSOAL |
| `medidor_atual` | boolean | É o medidor instalado hoje na UC. | Exatamente 1 por UC (validado). | NAO_PESSOAL |
| `data_ultima_manutencao` | date | Data da última manutenção. | Coluna 100% vazia na fonte (S-MED-06). | NAO_PESSOAL |
| `_processado_em` | timestamp | Data e hora em que o pipeline gravou a linha. | Coluna técnica. | NAO_PESSOAL |

## dim_unidade_consumidora

Cadastro das unidades consumidoras (1 linha por UC), com o medidor atual, a GD e a troca de medidor. Base da visão 360.

- **Grão:** 1 linha por UC (45.000)
- **Origem:** silver_unidades_consumidoras + silver_medidores + silver_geracao_distribuida
- **Notebook:** `04_gold_dimensoes`
- **Termos do dia a dia:** cliente, cadastro, unidade consumidora, consumidor

| Coluna | Tipo | Descrição | Regra / decisão | LGPD |
|---|---|---|---|---|
| `id_uc` | string | Identificador da unidade consumidora (UC), a chave que liga todas as tabelas. | Só UCs reais do cadastro (UC + 6 dígitos). Registros TESTE e de UC inexistente ficam na quarentena da Silver (S-UC-01, S-FAT-06). | PSEUDONIMIZADO |
| `nome_titular` | string | Nome do titular da UC. | Texto padronizado (espaços, encoding). | ALTO |
| `cpf_cnpj_mascarado` | string | CPF/CNPJ do titular com todos os dígitos ocultos, exceto os 4 últimos. | Mascarado na Gold (LGPD); a Silver guarda só os dígitos. | ALTO |
| `tipo_pessoa` | string | PF (CPF, 11 dígitos) ou PJ (CNPJ, 14 dígitos). | Derivado do tamanho do documento. | BAIXO |
| `logradouro` | string | Logradouro (rua) da UC. | Texto padronizado. | ALTO |
| `numero` | string | Número do imóvel. |  | ALTO |
| `bairro` | string | Bairro da UC. | Encoding corrigido em 60 bairros que vinham com mojibake, ex.: 'InhamÃ£' -> 'Inhamã' (S-UC-03). | BAIXO |
| `municipio` | string | Município da UC (14 municípios da Região Metropolitana do Recife). | Do cadastro, padronizado. | BAIXO |
| `uf` | string | Unidade da federação (sempre PE). | Unificada de 5 grafias: PE, pe, Pernambuco, P.E. (S-UC-06). | NAO_PESSOAL |
| `cep` | string | CEP da UC (8 dígitos). | Nulo quando inválido: ~1,35 mil vinham com lixo (NULL, N/A, -, -1, 9999-12-31) (S-UC-04). | ALTO |
| `latitude` | double | Latitude da UC (2 casas decimais, precisão de ~1 km). |  | BAIXO |
| `longitude` | double | Longitude da UC (2 casas decimais, precisão de ~1 km). |  | BAIXO |
| `classe` | string | Classe de consumo: RESIDENCIAL, COMERCIAL, INDUSTRIAL, RURAL ou PODER_PUBLICO. | Normalizada de várias grafias (caixa e acento). | BAIXO |
| `subgrupo_tarifario` | string | Subgrupo tarifário (B1, B2, B3, A4...). |  | BAIXO |
| `alimentador` | string | Código do alimentador, o circuito de média tensão que atende a UC (ex.: ALM-REC-008). |  | NAO_PESSOAL |
| `data_ligacao` | date | Data em que a UC passou a receber energia. | Nula em 90 UCs com data inválida (1900–1948) (S-UC-05). | BAIXO |
| `status` | string | Situação cadastral da UC. |  | BAIXO |
| `possui_gd` | boolean | Indica se a UC tem geração distribuída (painel solar) conectada. | Vem das GDs válidas; 7 GDs inconsistentes ficaram na quarentena (S-GD-05, S-GD-06). | BAIXO |
| `data_conexao_gd` | date | Data de conexão da GD, se houver. |  | BAIXO |
| `potencia_gd_kwp` | double | Potência da GD em kWp, se houver. | 35 potências vinham em W e foram divididas por 1000 (S-GD-02). | BAIXO |
| `modalidade_gd` | string | Modalidade da GD (geração na própria UC, autoconsumo remoto, compartilhada). |  | BAIXO |
| `id_medidor_atual` | string | Medidor instalado hoje. |  | PSEUDONIMIZADO |
| `tipo_medidor_atual` | string | Tipo do medidor instalado hoje: ELETROMECANICO, ELETRONICO ou SMART. | Tipo normalizado e validado contra o modelo (S-MED-04). | BAIXO |
| `modelo_medidor_atual` | string | Modelo do medidor atual. |  | NAO_PESSOAL |
| `data_instalacao_medidor_atual` | date | Data de instalação do medidor atual. | Datas com traço lidas como MM-dd-yyyy, provado (S-MED-01). | BAIXO |
| `trocou_medidor` | boolean | A UC teve o medidor substituído (campanha de troca set/2025–mar/2026). |  | BAIXO |
| `data_ultima_troca_medidor` | date | Data da última troca de medidor. |  | BAIXO |
| `tipo_medidor_anterior` | string | Tipo do medidor retirado na última troca. |  | BAIXO |
| `cadastro_conflitante` | boolean | Havia mais de uma versão do cadastro com dados diferentes. | Hoje sempre falso: as 360 divergências eram só de escrita (S-UC-02). | NAO_PESSOAL |
| `_processado_em` | timestamp | Data e hora em que o pipeline gravou a linha. | Coluna técnica. | NAO_PESSOAL |

## fact_atendimentos

Chamados do call center.

- **Grão:** 1 linha por chamado (318.871)
- **Origem:** silver_atendimentos
- **Notebook:** `04_gold_fatos`
- **Termos do dia a dia:** chamado, atendimento, reclamação, protocolo, call center, SAC

| Coluna | Tipo | Descrição | Regra / decisão | LGPD |
|---|---|---|---|---|
| `protocolo` | string | Número do protocolo. |  | PSEUDONIMIZADO |
| `id_uc` | string | Identificador da unidade consumidora (UC), a chave que liga todas as tabelas. | Só UCs reais do cadastro (UC + 6 dígitos). Registros TESTE e de UC inexistente ficam na quarentena da Silver (S-UC-01, S-FAT-06). | PSEUDONIMIZADO |
| `assunto` | string | Assunto: FALTA DE ENERGIA, FATURA, DANO ELETRICO, LIGACAO NOVA, GERACAO DISTRIBUIDA ou RELIGACAO. |  | MEDIO |
| `subassunto` | string | Detalhe do assunto (ex.: VALOR ALTO, SEGUNDA VIA, INTERRUPCAO TOTAL). |  | MEDIO |
| `canal` | string | WHATSAPP, TELEFONE, APP, SITE ou PRESENCIAL. |  | NAO_PESSOAL |
| `data_abertura` | timestamp | Abertura do chamado. |  | NAO_PESSOAL |
| `data_fechamento` | timestamp | Fechamento do chamado. |  | NAO_PESSOAL |
| `competencia` | date | Mês de referência do registro, representado pelo 1º dia do mês. | Convertida de mes_referencia (yyyy-MM). | NAO_PESSOAL |
| `status_chamado` | string | ABERTO ou FECHADO (pela existência de data_fechamento). |  | NAO_PESSOAL |
| `tempo_resolucao_h` | double | Horas entre a abertura e o fechamento. | Não varia entre assuntos (~125 h), mas triplica em jul/2025 (N-03, N-06). | NAO_PESSOAL |
| `nota_satisfacao` | double | Nota de satisfação (1 a 5). | Nula em 9.566 chamados (3%), fora das médias. Não varia entre canais e assuntos (N-03). | BAIXO |
| `qtd_tratativas` | int | Número de ações registradas no chamado. | O histórico de ações fica fora da Gold: os rótulos são aleatórios na fonte (S-ATE-02). | NAO_PESSOAL |
| `_processado_em` | timestamp | Data e hora em que o pipeline gravou a linha. | Coluna técnica. | NAO_PESSOAL |

## fact_faturamento

Faturas mensais com receita, pagamento e o consumo medido no mês.

- **Grão:** 1 linha por fatura = 1 por UC por competência (2.152.336)
- **Origem:** silver_faturas + silver_leituras
- **Notebook:** `04_gold_fatos`
- **Termos do dia a dia:** conta de luz, fatura, boleto, cobrança, receita

| Coluna | Tipo | Descrição | Regra / decisão | LGPD |
|---|---|---|---|---|
| `id_fatura` | string | Identificador da fatura. | Faturas órfãs (FTX…, UC inexistente) excluídas (S-FAT-06). | PSEUDONIMIZADO |
| `id_uc` | string | Identificador da unidade consumidora (UC), a chave que liga todas as tabelas. | Só UCs reais do cadastro (UC + 6 dígitos). Registros TESTE e de UC inexistente ficam na quarentena da Silver (S-UC-01, S-FAT-06). | PSEUDONIMIZADO |
| `competencia` | date | Mês de referência do registro, representado pelo 1º dia do mês. | Convertida de mes_referencia (yyyy-MM). | NAO_PESSOAL |
| `mes_referencia` | string | Competência em texto, no formato yyyy-MM. |  | NAO_PESSOAL |
| `ano` | int | Ano da competência. |  | NAO_PESSOAL |
| `mes` | int | Mês da competência (1 a 12). |  | NAO_PESSOAL |
| `data_emissao` | date | Data de emissão. | Traço lido como MM-dd-yyyy; validado: vencimento = emissão + 12 dias em 100% (S-FAT-05). | NAO_PESSOAL |
| `data_vencimento` | date | Data de vencimento. |  | NAO_PESSOAL |
| `data_pagamento` | date | Data de pagamento (nula se em aberto). | Sentinela 9999-12-31 convertida em nulo (S-FAT-03). | MEDIO |
| `valor_energia` | double | Valor da energia em R$ (inclui o acréscimo da bandeira). |  | MEDIO |
| `tributos` | double | Tributos em R$ (~1/3 de valor_energia). |  | MEDIO |
| `receita_faturada` | double | Valor total da fatura em R$ = valor_energia + tributos. | R$ 1.234,56 convertido; soma validada em 100%. | MEDIO |
| `receita_recebida` | double | Valor recebido em R$: igual a receita_faturada se PAGA, senão 0. |  | MEDIO |
| `bandeira_tarifaria` | string | Bandeira tarifária do mês: VERDE, AMARELA, VERMELHA_P1 ou VERMELHA_P2. | Uma bandeira por competência (validado). O acréscimo da bandeira está embutido em valor_energia. | NAO_PESSOAL |
| `status` | string | Status da fonte: PAGA ou EM_ABERTO. |  | ALTO |
| `status_pagamento` | string | PAGA, PENDENTE (em aberto, ainda no prazo) ou ATRASADA (em aberto, vencida). | Ver a métrica 'Status de pagamento'. | ALTO |
| `dias_atraso` | int | Dias entre o vencimento e o pagamento (ou a data de referência, se em aberto); 0 se em dia. |  | ALTO |
| `consumo_kwh` | double | Consumo medido no mês (kWh), vindo da leitura da mesma UC e competência. | A fatura não tem kWh (S-FAT-07). Usa o consumo ajustado da leitura (S-LEI-08, S-LEI-09). | MEDIO |
| `preco_medio_kwh` | double | Preço médio da energia no mês (R$/kWh) = valor_energia ÷ consumo_kwh. | Nulo quando o consumo é zero. | MEDIO |
| `_processado_em` | timestamp | Data e hora em que o pipeline gravou a linha. | Coluna técnica. | NAO_PESSOAL |

## fact_inspecoes

Inspeções de campo da equipe de perdas (ago–dez/2025).

- **Grão:** 1 linha por inspeção (1.389)
- **Origem:** silver_inspecoes
- **Notebook:** `04_gold_fatos`
- **Termos do dia a dia:** inspeção, fiscalização, vistoria, fraude, gato, perdas

| Coluna | Tipo | Descrição | Regra / decisão | LGPD |
|---|---|---|---|---|
| `id_inspecao` | string | Identificador da inspeção. |  | PSEUDONIMIZADO |
| `id_uc` | string | Identificador da unidade consumidora (UC), a chave que liga todas as tabelas. | Só UCs reais do cadastro (UC + 6 dígitos). Registros TESTE e de UC inexistente ficam na quarentena da Silver (S-UC-01, S-FAT-06). | PSEUDONIMIZADO |
| `data_inspecao` | date | Data da inspeção. | Formatos mistos convertidos; traço = MM-dd-yyyy. | NAO_PESSOAL |
| `mes_inspecao` | string | Mês da inspeção (yyyy-MM). | Vem da data, não da aba do Excel (a aba 'dez' tem inspeções de agosto). | NAO_PESSOAL |
| `inspetor` | string | Código do inspetor (ex.: INSP-002). |  | BAIXO |
| `resultado` | string | IRREGULARIDADE_CONFIRMADA ou SEM_IRREGULARIDADE. | Unificado de 8 grafias; 'NADA CONSTA' = sem irregularidade. | ALTO |
| `tipo_irregularidade` | string | BY_PASS, MEDIDOR_ADULTERADO, DESVIO_DIRETO, LACRE_VIOLADO ou LIGACAO_CLANDESTINA. | '-', 'NULL' e 'N/A' convertidos em nulo. | ALTO |
| `kwh_recuperado` | double | Energia recuperada (kWh) com a regularização. | Vírgula e ponto decimal convertidos. | MEDIO |
| `registro_coerente` | boolean | O resultado é coerente com o tipo e o kWh (confirmada com tipo; sem irregularidade sem tipo e com kWh 0). |  | NAO_PESSOAL |
| `aba_origem` | string | Aba do Excel de origem (rastreio). |  | NAO_PESSOAL |
| `_processado_em` | timestamp | Data e hora em que o pipeline gravou a linha. | Coluna técnica. | NAO_PESSOAL |

## fact_leituras

Leituras mensais de consumo por UC. É a única fonte de volume (kWh) da base.

- **Grão:** 1 linha por UC por competência (2.152.336)
- **Origem:** silver_leituras
- **Notebook:** `04_gold_fatos`
- **Termos do dia a dia:** leitura, consumo, consumo de energia, kWh

| Coluna | Tipo | Descrição | Regra / decisão | LGPD |
|---|---|---|---|---|
| `id_leitura` | string | Identificador da leitura. | 8.609 leituras clonadas (LTX…, medidor inexistente) excluídas (S-LEI-09). | PSEUDONIMIZADO |
| `id_uc` | string | Identificador da unidade consumidora (UC), a chave que liga todas as tabelas. | Só UCs reais do cadastro (UC + 6 dígitos). Registros TESTE e de UC inexistente ficam na quarentena da Silver (S-UC-01, S-FAT-06). | PSEUDONIMIZADO |
| `id_medidor` | string | Medidor que fez a leitura. |  | PSEUDONIMIZADO |
| `competencia` | date | Mês de referência do registro, representado pelo 1º dia do mês. | Convertida de mes_referencia (yyyy-MM). | NAO_PESSOAL |
| `mes_referencia` | string | Competência em texto, no formato yyyy-MM. |  | NAO_PESSOAL |
| `ano` | int | Ano da competência. |  | NAO_PESSOAL |
| `mes` | int | Mês da competência (1 a 12). |  | NAO_PESSOAL |
| `data_leitura` | date | Data da leitura (sempre dentro do mês de referência). | Formato com traço desempatado pelo mês de referência (S-LEI-07). | NAO_PESSOAL |
| `leitura_anterior` | double | Registro do medidor na leitura anterior. | Sentinela -1 e 'NULL' convertidos em nulo (S-LEI-05, S-LEI-06). | MEDIO |
| `leitura_atual` | double | Registro do medidor nesta leitura. |  | MEDIO |
| `consumo_kwh` | double | **Consumo do mês (kWh) a usar nas análises**: o declarado, ou a média dos 3 meses anteriores da UC no mês da troca de medidor. | Consumo declarado mantido, sem recálculo (S-LEI-02); troca de medidor imputada (S-LEI-08). | MEDIO |
| `consumo_kwh_declarado` | double | Consumo como veio da fonte. | Negativo gigante no mês da troca de medidor. | MEDIO |
| `consumo_imputado` | boolean | O consumo do mês foi imputado (mês da troca de medidor, 6.215 casos). |  | NAO_PESSOAL |
| `tipo_leitura` | string | REAL ou ESTIMADA. | As estimadas (18%) são indistinguíveis nos números; só este rótulo as identifica (N-13). | NAO_PESSOAL |
| `status_qualidade_leitura` | string | OK, ANTERIOR_AUSENTE, RETIFICACAO ou TROCA_DE_MEDIDOR. |  | NAO_PESSOAL |
| `consumo_ano_anterior_kwh` | double | Consumo da mesma UC no mesmo mês do ano anterior. | Para a visão 360 ('a conta veio alta?'). | MEDIO |
| `variacao_ano_anterior_pct` | double | Variação % do consumo contra o mesmo mês do ano anterior. |  | MEDIO |
| `_processado_em` | timestamp | Data e hora em que o pipeline gravou a linha. | Coluna técnica. | NAO_PESSOAL |

## fact_ocorrencias

Interrupções de fornecimento. Cada registro é uma UC interrompida (definição do case).

- **Grão:** 1 linha por UC interrompida (180.000)
- **Origem:** silver_ocorrencias_rede
- **Notebook:** `04_gold_fatos`
- **Termos do dia a dia:** falta de luz, falta de energia, queda de energia, apagão, interrupção, blecaute

| Coluna | Tipo | Descrição | Regra / decisão | LGPD |
|---|---|---|---|---|
| `id_ocorrencia` | string | Identificador da ocorrência. |  | NAO_PESSOAL |
| `id_uc` | string | Identificador da unidade consumidora (UC), a chave que liga todas as tabelas. | Só UCs reais do cadastro (UC + 6 dígitos). Registros TESTE e de UC inexistente ficam na quarentena da Silver (S-UC-01, S-FAT-06). | PSEUDONIMIZADO |
| `alimentador` | string | Código do alimentador, o circuito de média tensão que atende a UC (ex.: ALM-REC-008). |  | NAO_PESSOAL |
| `tipo` | string | Tipo: FALTA DE ENERGIA, DANO EM EQUIPAMENTO, OSCILACAO, SOBRECARGA ou FIO PARTIDO. |  | NAO_PESSOAL |
| `causa` | string | Causa: CLIMATICA, VEGETACAO, TERCEIROS, SOBRECARGA, FALHA DE EQUIPAMENTO, NAO IDENTIFICADA ou NAO INFORMADA. | NAO INFORMADA unifica null, '-', 'N/A' e 'NULL' (5.400); NAO IDENTIFICADA é categoria válida (S-OCO-03). | NAO_PESSOAL |
| `data_abertura` | timestamp | Início da interrupção. |  | NAO_PESSOAL |
| `data_encerramento` | timestamp | Fim da interrupção. |  | NAO_PESSOAL |
| `competencia` | date | Mês de referência do registro, representado pelo 1º dia do mês. | Convertida de mes_referencia (yyyy-MM). | NAO_PESSOAL |
| `duracao_min` | double | Duração em minutos. | Sufixo ' min' removido; bate 100% com encerramento − abertura. | NAO_PESSOAL |
| `duracao_h` | double | Duração em horas. |  | NAO_PESSOAL |
| `dia_critico` | boolean | A interrupção ocorreu num dia crítico. | Ver a métrica 'Dia crítico'. | NAO_PESSOAL |
| `duracao_truncada` | boolean | Duração cortada em 48 h na origem (30 casos). | S-OCO-04. | NAO_PESSOAL |
| `eh_oscilacao` | boolean | A ocorrência é do tipo OSCILACAO. | Filtro opcional para o DEC/FEC (S-OCO-05). | NAO_PESSOAL |
| `_processado_em` | timestamp | Data e hora em que o pipeline gravou a linha. | Coluna técnica. | NAO_PESSOAL |

## fila_inspecao

Fila priorizada de UCs suspeitas de perdas não técnicas, com motivo e energia estimada a recuperar (v1: regras, a calibrar).

- **Grão:** 1 linha por UC com score ≥ 20
- **Origem:** fact_leituras + fact_inspecoes + dim_unidade_consumidora
- **Notebook:** `05_gold_perdas`
- **Termos do dia a dia:** fila de inspeção, suspeitos, fraude, gato, perdas, onde inspecionar

| Coluna | Tipo | Descrição | Regra / decisão | LGPD |
|---|---|---|---|---|
| `prioridade` | int | Posição na fila (1 = mais promissora). | Ordenada por score e depois por kWh recuperável. | ALTO |
| `id_uc` | string | Identificador da unidade consumidora (UC), a chave que liga todas as tabelas. | Só UCs reais do cadastro (UC + 6 dígitos). Registros TESTE e de UC inexistente ficam na quarentena da Silver (S-UC-01, S-FAT-06). | PSEUDONIMIZADO |
| `score` | int | Pontuação de suspeita (0 a 100). | Ver a métrica 'Score da fila de inspeção'. | ALTO |
| `motivo_suspeita` | string | Regras que dispararam, separadas por ';'. | Explica cada suspeita (LGPD art. 20). | ALTO |
| `kwh_recuperavel_estimado_ano` | double | Energia estimada a recuperar por ano (kWh). | Ver a métrica 'kWh recuperável'. | ALTO |
| `nome_titular` | string | Nome do titular da UC. | Texto padronizado (espaços, encoding). | ALTO |
| `logradouro` | string | Logradouro (rua) da UC. | Texto padronizado. | ALTO |
| `numero` | string | Número do imóvel. |  | ALTO |
| `bairro` | string | Bairro da UC. | Encoding corrigido em 60 bairros que vinham com mojibake, ex.: 'InhamÃ£' -> 'Inhamã' (S-UC-03). | BAIXO |
| `municipio` | string | Município da UC (14 municípios da Região Metropolitana do Recife). | Do cadastro, padronizado. | BAIXO |
| `classe` | string | Classe de consumo: RESIDENCIAL, COMERCIAL, INDUSTRIAL, RURAL ou PODER_PUBLICO. | Normalizada de várias grafias (caixa e acento). | BAIXO |
| `alimentador` | string | Código do alimentador, o circuito de média tensão que atende a UC (ex.: ALM-REC-008). |  | NAO_PESSOAL |
| `latitude` | double | Latitude da UC (2 casas decimais, precisão de ~1 km). |  | BAIXO |
| `longitude` | double | Longitude da UC (2 casas decimais, precisão de ~1 km). |  | BAIXO |
| `tipo_medidor_atual` | string | Tipo do medidor instalado hoje: ELETROMECANICO, ELETRONICO ou SMART. | Tipo normalizado e validado contra o modelo (S-MED-04). | BAIXO |
| `trocou_medidor` | boolean | A UC teve o medidor substituído (campanha de troca set/2025–mar/2026). |  | BAIXO |
| `possui_gd` | boolean | Indica se a UC tem geração distribuída (painel solar) conectada. | Vem das GDs válidas; 7 GDs inconsistentes ficaram na quarentena (S-GD-05, S-GD-06). | BAIXO |
| `queda_explicada_por_gd` | boolean | A UC ligou GD no período comparado, então a queda de consumo não conta como suspeita. |  | NAO_PESSOAL |
| `consumo_medio_ano_anterior_kwh` | double | Consumo médio nos 6 meses equivalentes do ano anterior. |  | MEDIO |
| `consumo_medio_recente_kwh` | double | Consumo médio nos últimos 6 meses. |  | MEDIO |
| `variacao_consumo_pct` | double | Variação % do consumo recente contra o ano anterior. |  | MEDIO |
| `pct_leituras_estimadas_12m` | double | Fração das leituras dos últimos 12 meses que foram estimadas. |  | MEDIO |
| `anomalias_leitura_12m` | bigint | Leituras com retificação ou anterior ausente nos últimos 12 meses. |  | MEDIO |
| `taxa_irregularidade_bairro` | double | Taxa de irregularidade confirmada nas inspeções do bairro (mínimo de 5 inspeções). |  | NAO_PESSOAL |
| `data_ultima_inspecao` | date | Data da última inspeção da UC. |  | ALTO |
| `resultado_ultima_inspecao` | string | Resultado da última inspeção. |  | ALTO |
| `ja_teve_irregularidade` | boolean | A UC já teve irregularidade confirmada. |  | ALTO |
| `data_referencia` | date | Última competência usada no cálculo. |  | NAO_PESSOAL |
| `_processado_em` | timestamp | Data e hora em que o pipeline gravou a linha. | Coluna técnica. | NAO_PESSOAL |
