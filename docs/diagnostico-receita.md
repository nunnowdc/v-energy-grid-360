# Diagnóstico da receita: por que o volume caiu e a receita subiu só 8%

**Pergunta da Diretoria Comercial:** a tarifa residencial acumulou reajuste de 10,5% desde meados de 2022. Mesmo assim, comparando os últimos 12 meses com o primeiro ano da base, o volume de energia caiu quase 4% e a receita subiu só 8%. Por quê?

## Resumo executivo

1. **Os números do enunciado se confirmam.** A receita foi de R$ 157,1 mi para R$ 169,7 mi (**+8,0%**) e o volume de 227,1 para 217,9 milhões de kWh (**−4,0%**), com 0,6% mais UCs.
2. **A queda de volume tem duas causas:**
   - **Painéis solares (geração própria):** 3.503 UCs ligaram painel entre 2024 e 2026 e passaram a comprar **69% menos energia** da distribuidora. Efeito na receita: **−R$ 8,1 mi**.
   - **Perda não técnica em 4 bairros** (Iputinga, Jardim Jordão, Prazeres e Macaxeira): desde mai/2025, o consumo medido das UCs sem painel caiu 15,7%, e o comércio caiu pela metade. Nesses bairros, **90% das inspeções** encontraram irregularidade. Efeito: **−R$ 1,9 mi**.
   - O resto da base (38 mil UCs) consumiu **2,4% a mais** (+R$ 3,3 mi).
3. **A receita só subiu porque o preço subiu ~12,5%.** O reajuste tarifário explica a maior parte. Mas **cerca de R$ 6,6 mi vieram de bandeiras amarela e vermelha** em 8 dos últimos 12 meses (no primeiro ano, as 12 bandeiras foram verdes). Sem as bandeiras, a receita teria crescido só **3,8%**.
4. **Inadimplência e tributos não explicam a variação:** a parte atrasada ficou em ~5,5% e os tributos em 25% da fatura nos dois períodos.
5. **Recomendações, com ordem de grandeza (seção 6):**
   - regularizar as UCs fraudadas, cuja energia não voltou depois da inspeção: **R$ 0,8 a 1,8 mi/ano**;
   - incluir a geração própria na projeção de receita: **R$ 1,0 mi** de perda já contratada e **R$ 1,1 a 3,8 mi/ano** por ano de novas ligações;
   - não orçar a receita de bandeira: **até R$ 6,6 mi** de risco;
   - cobrar o estoque de faturas atrasadas: **R$ 1,8 a 7,3 mi** de caixa.

### A ponte da receita

| | R$ mi |
|---|---:|
| Receita do primeiro ano (jul/2022 a jun/2023) | 157,1 |
| Volume: UCs com painel solar | −8,1 |
| Volume: perda não técnica nos 4 bairros | −1,9 |
| Volume: resto da base | +3,3 |
| Preço: bandeiras tarifárias (temporário) | +6,6 |
| Preço: reajuste tarifário e demais efeitos | +12,7 |
| **Receita dos últimos 12 meses (jul/2025 a jun/2026)** | **169,7** |

## 1. Escopo, definições e números de partida

| Item | Definição |
|---|---|
| Períodos | **P0** = jul/2022 a jun/2023 (primeiro ano da base); **P1** = jul/2025 a jun/2026 (últimos 12 meses). Os mesmos meses do ano nos dois lados, sem efeito de estação |
| Receita | Receita faturada, com tributos (`fact_faturamento.receita_faturada`) |
| Volume | Consumo medido nas leituras (`fact_leituras.consumo_kwh`); a fatura não traz kWh |
| Preço médio | Receita ÷ volume (R$/kWh), já com tributos e bandeira |
| Decomposição | A da Gold e da tela de Receita, por segmento município × bairro × classe × geração própria: efeito-volume = (kWh P1 − kWh P0) × preço P0; efeito-preço = (preço P1 − preço P0) × kWh P1. A soma fecha exatamente com a variação da receita |

| | P0 | P1 | Variação |
|---|---:|---:|---:|
| Receita (R$ mi) | 157,1 | 169,7 | +8,0% |
| Volume (milhões de kWh) | 227,1 | 217,9 | −4,0% |
| Preço médio (R$/kWh) | 0,692 | 0,779 | +12,5% |
| UCs faturadas | 44.741 | 45.000 | +0,6% |

**Decomposição:** variação de **+R$ 12,6 mi** = efeito-volume **−R$ 6,8 mi** + efeito-preço **+R$ 19,3 mi**.

## 2. Volume: de onde veio a queda

| Grupo | UCs (P1) | Volume | Efeito-volume (R$ mi) |
|---|---:|---:|---:|
| Com painel solar | 3.503 | −60,9% | −8,1 |
| Sem painel, nos 4 bairros com irregularidade alta | 3.299 | −15,7% | −1,9 |
| Sem painel, resto da base | 38.198 | +2,4% | +3,3 |
| **Total** | **45.000** | **−4,0%** | **−6,8** |

### 2.1 Geração própria: causa confirmada

- **Os painéis foram ligados depois do primeiro ano:** 1.838 em 2024, 1.304 em 2025 e 361 no 1º semestre de 2026, nenhum antes de 2024. A queda vem do residencial (3.122 UCs, −61,2%) e do comercial (381 UCs, −60,5%).
- **A queda acontece no mês da ligação.** Comparando cada UC com ela mesma no mesmo mês do ano anterior, para tirar a sazonalidade:

| Mês em relação à ligação do painel | −6 a −1 | 0 | 1 a 11 |
|---|---:|---:|---:|
| Consumo ÷ mesmo mês do ano anterior | 1,00 a 1,01 | 0,65 | 0,30 a 0,31 |

- **Em kWh:** antes da ligação, a UC média consumia **447 kWh/mês**; depois, **135 kWh/mês**. É a energia que ela passa a gerar e deixa de comprar. Isso é legítimo e não é fraude: a fila de inspeção não conta essa queda como suspeita e zera a energia a recuperar dessas UCs (`queda_explicada_por_gd`).
- **Parte da queda ainda vai aparecer.** 916 UCs ligaram o painel durante P1 e ainda consumiram 4.257 meses-UC sem painel nesse período. Nos próximos 12 meses esse consumo some da receita, mesmo sem nenhuma ligação nova.

### 2.2 Perda não técnica em 4 bairros: causa provável

Quatro bairros concentram as irregularidades encontradas em campo:

| Bairro | Município | Inspeções | Irregularidade | Efeito-volume total (R$ mi) |
|---|---|---:|---:|---:|
| Iputinga | Recife | 310 | 91,0% | −0,95 |
| Prazeres | Jaboatão dos Guararapes | 168 | 89,9% | −0,48 |
| Jardim Jordão | Jaboatão dos Guararapes | 299 | 89,6% | −0,79 |
| Macaxeira | Recife | 151 | 88,7% | −0,39 |

No resto da base, só 7,8% das inspeções encontraram irregularidade; o 5º bairro com mais irregularidade tem 21%. Nesses 4 bairros, sem contar as UCs com painel:

- **Comércio:** o consumo por UC caiu **48,6%** (de 9.979 para 5.113 kWh/ano).
- **Residências:** caiu 15,5%.
- **Indústria, rural e poder público:** estáveis.
- **O degrau começa em mai/2025.** Até abr/2025, o consumo era igual ao do ano anterior (razão 1,00). De mai/2025 em diante fica entre 0,81 e 0,92. Em jun/2026 a razão volta a 1,00 só porque a comparação passa a ser com meses que já estavam baixos.
- **Fila de suspeitas:** 2.200 UCs desses bairros estão na fila (eles têm 3.299 UCs sem painel), com **2,57 milhões de kWh/ano** a recuperar. São **85%** da energia recuperável da fila inteira (3,02 milhões).

**A energia não voltou depois da inspeção.** As 871 UCs com irregularidade confirmada (ago a dez/2025) consumiam 49% do mesmo mês do ano anterior antes da inspeção, e 50% depois. Nos últimos 3 meses da base, consomem 224 kWh/mês, contra 492 no primeiro ano. A inspeção encontra a fraude, mas o consumo faturado não se recupera.

**Por que "causa provável" e não "confirmada":** a coincidência entre o degrau de mai/2025, a concentração geográfica e os 90% de irregularidade é forte. Ainda assim, falta confirmar com a Gerência de Perdas o que aconteceu em mai/2025 nesses bairros e se a regularização depois da inspeção é feita e só não está registrada na base.

### 2.3 O resto da base cresceu

As 38.198 UCs sem painel fora desses bairros consumiram **2,4% a mais** (+R$ 3,3 mi), e nenhuma classe caiu de forma relevante. A base de clientes saudável cresce. A queda do volume total não é perda de mercado.

## 3. Preço: reajuste e bandeiras

**Reajuste.** O preço médio das UCs residenciais sem painel nos meses de bandeira verde mostra os degraus da tarifa:

| Período | Preço (R$/kWh) |
|---|---:|
| jul/2022 a abr/2023 | 0,707 |
| mai/2023 a abr/2025 | ~0,757 a 0,759 |
| jan a abr/2026 | ~0,781 a 0,786 |

São **+10,9% acumulados**, em linha com o reajuste de 10,5% do enunciado. Por classe, o preço médio subiu: residencial +13,2%, comercial +18,8%, industrial +8,0%.

**Bandeiras.** O primeiro ano teve 12 meses de bandeira verde. Os últimos 12 tiveram só 4: houve 3 meses de amarela, 3 de vermelha patamar 1 e 2 de vermelha patamar 2. Na tarifa residencial, a amarela soma cerca de 3% ao preço, a vermelha patamar 1 cerca de 8% e a vermelha patamar 2 cerca de 14%.

Recalculando cada mês não verde de P1 com o preço dos meses verdes de P1 (mesma classe e mesmo grupo de geração própria), as bandeiras somaram **R$ 6,6 mi**. A receita de P1 sem bandeiras seria de R$ 163,1 mi: **+3,8%** sobre P0, e não +8,0%. Esse valor é uma estimativa e provavelmente está um pouco abaixo do real (veja a seção 7).

**Tributos.** Ficaram em 25,0% da receita faturada nos dois períodos e não mudam a variação.

## 4. Onde está a queda

| Município | Efeito-volume (R$ mi) | Com painel | Sem painel |
|---|---:|---:|---:|
| Recife | −2,94 | −3,19 | +0,25 |
| Jaboatão dos Guararapes | −1,92 | −1,43 | −0,49 |
| Paulista | −0,41 | −0,79 | +0,38 |
| Cabo de Santo Agostinho | −0,33 | −0,51 | +0,18 |
| Olinda | −0,23 | −0,66 | +0,43 |

- **Recife e Jaboatão** somam 72% do efeito-volume (−R$ 4,9 mi de −R$ 6,8 mi).
- **Jaboatão** é o único município onde as UCs sem painel também perderam volume, por causa de Jardim Jordão e Prazeres.
- Em todos os outros municípios, as UCs sem painel cresceram.
- **Bairros:** 228 dos 297 perderam volume. Os 20 piores somam −R$ 4,0 mi dos −R$ 7,0 mi de queda.

No portal, a tela **Receita** mostra o mesmo corte: o bloco "Com e sem geração própria" e a tabela "Onde está a variação", que desce de município para bairro e de bairro para classe.

## 5. Hipóteses testadas

| Hipótese | Resultado | Evidência |
|---|---|---|
| Geração própria reduziu o volume | **Confirmada** | Degrau de −69% no mês da ligação; −R$ 8,1 mi |
| Perda não técnica reduziu o volume | **Provável, em 4 bairros** | Degrau em mai/2025, 90% de irregularidade nas inspeções; −R$ 1,9 mi |
| O reajuste não chegou ao preço | Descartada | Tarifa verde residencial +10,9% |
| Bandeiras mudaram o preço efetivo | **Confirmada** | 8 meses não verdes em P1 contra 0 em P0; +R$ 6,6 mi |
| Inadimplência reduziu a receita | Descartada | Não altera a receita faturada; parte atrasada estável (5,5% em P0, 5,4% em P1) |
| Tributos mudaram | Descartada | 25,0% nos dois períodos |
| Perda de clientes | Descartada | UCs faturadas +0,6% |
| Queda geral de consumo | Descartada | Fora das duas causas acima, o volume cresceu 2,4% |
| Problema de qualidade dos dados | Descartada para os totais | Receita e volume batem entre as tabelas mensais e a decomposição (`01_reconciliacao.sql`); limpeza documentada no dicionário da Gold |

## 6. Recomendações

Os impactos são **ordens de grandeza em três cenários**, não metas. Cada premissa está escrita ao lado. O preço usado para converter kWh em reais é o preço médio de P1, R$ 0,779/kWh.

### 6.1 Regularizar as UCs fraudadas nos 4 bairros

- **Dono:** Gerência de Perdas.
- **Ação:**
  - concentrar as equipes de campo nas 2.200 UCs da fila nos 4 bairros;
  - **depois de cada irregularidade confirmada, garantir a regularização:** troca ou lacre do medidor, religação correta e faturamento da energia recuperada;
  - voltar à UC em 60 dias para conferir.
- **Prazo:** começar no próximo mês. A capacidade atual (~200 inspeções/mês) cobre os 4 bairros em menos de um ano.
- **Indicador:** consumo faturado das UCs regularizadas contra o mesmo mês do ano anterior. Deve voltar para perto de 1,00.
- **Impacto anual recorrente**, sobre os 2,57 milhões de kWh/ano recuperáveis desses bairros:

| Conservador (40%) | Base (70%) | Alto (90%) |
|---:|---:|---:|
| R$ 0,8 mi | R$ 1,4 mi | R$ 1,8 mi |

- **Conferência pela outra ponta:** as 871 UCs já flagradas consomem 268 kWh/mês a menos que no primeiro ano, ou 2,8 milhões de kWh/ano (~R$ 2,2 mi). É a mesma ordem de grandeza.
- **Ganho pontual adicional:** as inspeções registraram 1.691 kWh recuperados por irregularidade, ou 1,47 milhão de kWh nas 871 UCs. Se essa energia for faturada, são **~R$ 1,1 mi**.

### 6.2 Incluir a geração própria na projeção de volume e receita

- **Dono:** Diretoria Comercial, com a área de Planejamento.
- **Ação:**
  - projetar o volume separando as UCs com painel;
  - acompanhar as ligações de painel por mês como indicador antecedente;
  - avaliar com a área regulatória o efeito das regras de compensação da geração distribuída (Lei 14.300/2022) sobre as próximas ligações.
- **Prazo:** na próxima revisão do orçamento.
- **Indicador:** ligações de painel por mês e kWh deixados de comprar por essas UCs.
- **Impacto (perda de receita a prever, não a evitar):**
  - **já contratado:** as 916 UCs ligadas durante P1 ainda vão tirar ~1,3 milhão de kWh, ou **~R$ 1,0 mi** nos próximos 12 meses;
  - **por ano de ligações novas:** cada UC com painel deixa de comprar ~3.700 kWh/ano (~R$ 2,9 mil). O ritmo de ligações vem caindo: 1.838 em 2024, 1.304 em 2025 e 361 no 1º semestre de 2026.

| Ligações por ano | Conservador: 360 (metade do ritmo de 2026) | Base: 720 (ritmo de 2026) | Alto: 1.300 (ritmo de 2025) |
|---|---:|---:|---:|
| Perda anual de receita | R$ 1,1 mi | R$ 2,1 mi | R$ 3,8 mi |

### 6.3 Não orçar a receita de bandeira como se fosse recorrente

- **Dono:** Diretoria Comercial, com o Financeiro.
- **Ação:** acompanhar a receita **com e sem bandeira** e orçar com cenários de bandeira. A bandeira repassa o custo de geração do mês e não é crescimento do negócio.
- **Prazo:** no próximo ciclo de orçamento.
- **Indicador:** receita do mês recalculada com o preço da bandeira verde.
- **Impacto (risco de superestimar a receita):** com o mesmo volume, os próximos 12 meses podem ter até **R$ 6,6 mi** a menos que P1:

| Bandeiras iguais às de P1 | Metade dos meses não verdes | Todos os meses verdes |
|---:|---:|---:|
| R$ 0 | −R$ 3,3 mi | −R$ 6,6 mi |

### 6.4 Cobrar o estoque de faturas atrasadas

- **Dono:** Financeiro e Cobrança.
- **Ação:** campanha de cobrança e negociação priorizada por valor.
- **Prazo:** 6 meses.
- **Indicador:** valor recuperado por mês.
- **Impacto:** a inadimplência não explica a variação da receita faturada, mas é caixa parado. A base tem **R$ 36,3 mi** em 170.853 faturas atrasadas. Impacto pontual, em caixa:

| Conservador (5%) | Base (10%) | Alto (20%) |
|---:|---:|---:|
| R$ 1,8 mi | R$ 3,6 mi | R$ 7,3 mi |

## 7. Limitações e premissas

- **Bandeiras:** a estimativa de R$ 6,6 mi usa o preço dos meses verdes de P1 (jan a abr/2026). A amarela soma ~3,3% sobre a verde em 2024 e em 2026; aplicando isso aos meses de amarela de mai/2025 e dez/2025, a tarifa base de 2025 fica ~1,5% abaixo da de 2026. Então a parte da bandeira está provavelmente subestimada, em algo como R$ 1 mi.
- **Decomposição:** a fórmula da Gold põe a interação entre preço e volume no efeito-preço (preço × kWh de P1). A decomposição de Shapley, prevista no plano do time, divide essa interação ao meio. Os totais não mudam; só a divisão entre os dois efeitos mudaria um pouco. Usamos a fórmula da Gold para o documento bater com a tela de Receita.
- **Perda não técnica:** "provável" até a Gerência de Perdas confirmar o que aconteceu em mai/2025 e se a regularização depois da inspeção acontece e não foi registrada. As inspeções não são uma amostra aleatória: a equipe vai onde a suspeita é maior, então os 90% contra 7,8% exageram a diferença entre os bairros. O que sustenta a conclusão é o degrau de consumo em mai/2025 no bairro inteiro, que não depende de onde a equipe escolheu ir.
- **kWh recuperado nas inspeções:** tratado como energia pontual a faturar. Se for anual, o ganho da seção 6.1 aumenta.
- **Fila de inspeção:** os 2,57 milhões de kWh/ano são a estimativa da Gold (consumo médio do ano anterior menos o recente, × 12). A pontuação da fila não foi usada como taxa de acerto, porque a calibração atual tem vazamento (registro N-16).
- **Base de dados:** Gold local, consultada em 01/11/2026. O registro N-15 do relatório de decisões da Gold (`data-engineering/relatorio_tabelas/decisoes_de_negocio_gold.md`) traz efeito-volume −R$ 11,18 mi e efeito-preço +R$ 23,75 mi, de uma versão anterior da Gold. Os números certos são os deste documento, que batem com o portal.

## 8. Como reproduzir

Todas as tabelas deste documento saem das consultas em `docs/diagnostico/sql/`, que rodam direto no PostgreSQL local:

| Arquivo | O que responde |
|---|---|
| `01_reconciliacao.sql` | Receita, volume, preço e UCs dos dois períodos, nas duas tabelas da Gold; peso dos tributos |
| `02_decomposicao_preco_volume.sql` | Efeito-volume e efeito-preço: total, com e sem painel, por classe; preço por classe |
| `03_onde_esta_a_queda.sql` | Municípios, bairros, os bairros com irregularidade alta e quando a queda começou |
| `04_geracao_distribuida.sql` | Ligações de painel por semestre, consumo antes e depois da ligação, queda ainda por vir |
| `05_preco_reajuste_bandeiras.sql` | Preço mês a mês, bandeiras por período e quanto as bandeiras somaram |
| `06_hipoteses_e_impacto.sql` | Inadimplência, inspeções, fila e consumo das UCs flagradas antes e depois da inspeção |

Da raiz do repositório, com o banco do setup rodando (funciona no PowerShell, no macOS e no Linux):

```powershell
docker cp docs/diagnostico/sql/02_decomposicao_preco_volume.sql postgres-venergy:/tmp/consulta.sql
docker exec postgres-venergy psql -U postgres -d v_energy -P pager=off -f /tmp/consulta.sql
```

## 9. Próximos passos

1. Validar a hipótese de perda não técnica com a Gerência de Perdas: o que aconteceu em mai/2025 e como é feita a regularização.
2. Atualizar o registro N-15 do relatório da Gold com os números atuais.
3. Medir em 60 dias o consumo das primeiras UCs regularizadas, para calibrar o cenário da seção 6.1.
