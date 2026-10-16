# 6. Diagnóstico da Receita

## 1. Objetivo e requisitos atendidos

O objetivo é explicar, de forma reproduzível e sustentada pelos dados Gold, por que o volume faturado caiu quase 4% enquanto a receita cresceu apenas 8% entre o primeiro ano da base e os últimos 12 meses, apesar do reajuste tarifário residencial acumulado de 10,5% desde meados de 2022 `[ENUNCIADO]`. O diagnóstico deve separar o que ocorreu por preço, quantidade e composição da carteira, localizar a variação por município, bairro e classe e terminar com recomendações acionáveis para a diretoria comercial.

**Requisitos atendidos:**

- **REQ-DIAG-01:** diagnóstico da variação de receita com causas sustentadas por dados.
- **REQ-DIAG-02:** recomendações acionáveis com ordem de grandeza do impacto, calculada após a validação dos dados.
- **REQ-DIAG-03:** registro do diagnóstico no repositório, na pasta `docs/`.

Nenhum número de causa, segmento ou impacto é antecipado neste documento. Os dados reais ainda precisam ser processados; portanto, conclusões causais são `[HIPÓTESE]` até a execução das validações descritas abaixo.

## 2. Decisões de projeto

### 2.1 Comparar períodos equivalentes e preservar a granularidade mensal

**Decisão:** comparar o primeiro ano completo disponível com os últimos 12 meses completos, alinhando cada mês do período inicial ao mesmo mês do período final. O período de referência deve ser parametrizado e registrado no relatório.

**Por quê:** evita confundir sazonalidade, mudanças de calendário ou meses incompletos com efeito econômico. A granularidade mensal permite decompor a trajetória, identificar pontos de inflexão e relacionar mudanças com bandeira tarifária, faturamento, pagamento e eventos operacionais.

**Alternativa considerada:** comparar apenas os totais acumulados dos dois períodos. Foi descartada como análise principal porque oculta sazonalidade e mudanças graduais; pode ser usada apenas como validação de reconciliação.

**Trade-off:** exige tratamento explícito de meses sem leitura ou sem faturamento. Esses meses não devem ser silenciosamente preenchidos com zero; devem ser marcados como ausentes e tratados conforme a regra de qualidade definida pela Engenharia de Dados.

### 2.2 Usar decomposição aditiva de Shapley para preço e volume

**Decisão:** calcular a decomposição total por segmento com uma variante de Shapley, que divide igualmente o termo de interação entre preço e volume.

Para cada segmento `s` e período `t`:

- `R(s,t) = P(s,t) × Q(s,t)`, em que `R` é receita faturada, `P = R/Q` é preço médio efetivo por unidade de energia e `Q` é volume de energia faturada.
- `ΔR(s) = R(s,1) - R(s,0)`.
- `Efeito-preço(s) = 0,5 × [(P1-P0)×Q0 + (P1-P0)×Q1]`.
- `Efeito-volume(s) = 0,5 × [(Q1-Q0)×P0 + (Q1-Q0)×P1]`.
- `Efeito-preço(s) + Efeito-volume(s) = ΔR(s)`, salvo diferenças de arredondamento.

O preço médio deve ser calculado sobre a receita faturada e o volume faturado no mesmo escopo, sem misturar unidades monetárias, créditos, impostos ou componentes que não estejam disponíveis de forma consistente. Quando houver detalhamento suficiente, a receita será aberta em tarifa base, bandeira, tributos, descontos e outros componentes, mantendo uma ponte entre o total faturado e as parcelas.

**Por quê:** a decomposição é auditável, fecha matematicamente e não atribui todo o termo de interação arbitrariamente a preço ou volume.

**Alternativas consideradas:** usar apenas a decomposição de Laspeyres ou Paasche. São úteis como análises de sensibilidade, mas privilegiam um dos períodos e podem produzir leitura diferente quando há grande mudança de mix. Recomenda-se apresentar Shapley como número oficial e Laspeyres/Paasche apenas se a diferença for material.

**Trade-off:** um preço médio agregado pode esconder migração de clientes entre classes, faixas de consumo ou modalidades tarifárias. Por isso, a decomposição oficial deve ser calculada primeiro em células homogêneas e depois agregada:

`mês × município × bairro × classe × modalidade/bandeira`, conforme disponibilidade e qualidade dos campos.

### 2.3 Separar efeito-preço, efeito-volume e efeito-mix

**Decisão:** tratar o mix de clientes como eixo explicativo separado, e não como “preço” ou “volume” automaticamente.

**Por quê:** a receita pode crescer porque a tarifa subiu, porque o consumo por UC mudou ou porque a participação de classes com preços médios diferentes se alterou. A ponte executiva deve mostrar:

1. receita no período inicial;
2. efeito-preço dentro das células comparáveis;
3. efeito-volume dentro das células comparáveis;
4. efeito-mix/migração entre classes ou modalidades;
5. ajustes de cobertura e qualidade de dados;
6. receita no período final.

O efeito-mix será estimado comparando a decomposição dentro das células com a variação obtida após fixar a composição do período inicial. A regra exata será documentada no `docs/` junto com o SQL ou notebook que gera a tabela de resultados.

### 2.4 Distinguir diagnóstico descritivo de causa validada

**Decisão:** toda conclusão será classificada como fato observado, hipótese ou causa sustentada.

- `[ENUNCIADO]`: informação fornecida no caso.
- `[PREMISSA]`: regra adotada porque o enunciado não especifica o comportamento.
- `[HIPÓTESE]`: explicação plausível que ainda depende de teste.
- `VALIDADA`: hipótese suportada por reconciliação, corte comparável, teste de sensibilidade e evidência operacional.

**Por quê:** correlação temporal, por si só, não prova causalidade. O relatório deverá mostrar a métrica, o denominador, o período, o recorte e a limitação de cada evidência.

## 3. Detalhamento técnico

### 3.1 Base analítica e reconciliação

O diagnóstico usará prioritariamente as tabelas Gold previstas no contrato:

- `fact_faturamento`: receita, volume faturado quando disponível, período, bandeira, vencimento e pagamento;
- `fact_leituras`: energia medida/faturada e histórico mensal;
- `dim_unidade_consumidora`: UC, município, bairro, classe e atributos cadastrais;
- `fact_ocorrencias` e `dim_alimentadores`: continuidade e eventos de rede para avaliar se interrupções ajudam a explicar a queda de consumo;
- atributos de geração distribuída e perdas, caso estejam presentes na Gold após a exploração das fontes.

Antes dos cálculos, será feita uma reconciliação entre:

1. soma de receita por mês na Gold e soma da origem;
2. soma de volume por mês na Gold e soma da origem;
3. número de UCs ativas e cobertura de município, bairro e classe;
4. chaves entre faturamento, medição e cadastro;
5. meses, unidades e segmentos sem observação;
6. duplicatas e faturamentos cancelados/estornados.

Uma linha só entra na decomposição se tiver receita e volume comparáveis, ou se houver uma regra de imputação aprovada e explicitamente sinalizada. Valores impossíveis, negativos não explicados e duplicidades devem ser excluídos do cálculo principal e reportados em uma tabela de impacto da qualidade.

### 3.2 Eixos de análise

Os resultados serão disponibilizados nos seguintes eixos, sempre com total, variação absoluta, variação percentual, participação na carteira e contribuição para `ΔR`:

| Eixo | Pergunta | Saída mínima |
|---|---|---|
| Total e mês | Quando a receita e o volume se desviaram? | Série mensal e ponte entre períodos |
| Município | Onde está concentrada a variação? | Ranking de contribuição e mapa/tabela |
| Bairro | Quais áreas explicam a queda ou crescimento? | Ranking com cobertura e volume |
| Classe | Residencial, comercial e demais classes se comportaram como? | Preço médio, volume, receita e mix |
| Bandeira/modalidade | A composição tarifária alterou o preço efetivo? | Receita e preço por bandeira/modalidade |
| GD | A geração distribuída reduziu energia faturada? | UCs com GD, volume antes/depois e efeito estimado |
| Perdas | Há indícios de perda não técnica ou recuperação? | Diferença medida/faturada e priorização |
| Continuidade | Interrupções podem explicar consumo não faturado? | Relação temporal com DEC/FEC e ocorrências |

Município, bairro e classe são dimensões obrigatórias para a análise de receita e para o portal, conforme o contrato Diagnóstico → Portal.

### 3.3 Hipóteses e validação

| Hipótese | Evidência a testar | Critério de validação | Ação se confirmada |
|---|---|---|---|
| `[HIPÓTESE]` O reajuste não se refletiu integralmente no preço médio por causa do mix | Preço médio efetivo por classe, faixa, modalidade e mês | Decomposição dentro de células mostra efeito-preço inferior ao reajuste de referência e mudança relevante de composição | Rever segmentação tarifária, comunicação e política comercial |
| `[HIPÓTESE]` Bandeiras tarifárias alteraram a receita/preço efetivo | Receita, volume e bandeira por mês e classe | Variação coincide com mudança de bandeira após controlar volume e mix | Separar efeito regulatório de efeito comercial na ponte executiva |
| `[HIPÓTESE]` Geração distribuída reduziu o volume faturado | Cadastro de GD, data de entrada, créditos e consumo antes/depois | UCs com GD apresentam queda de volume estatisticamente e operacionalmente consistente com a data de adesão, contra grupo comparável sem GD | Criar acompanhamento de prosumidores e revisar projeções de volume |
| `[HIPÓTESE]` Perdas não técnicas explicam parte da diferença entre energia medida e faturada | Comparação medição × faturamento, histórico de anomalias e inspeções | Diferença persistente, concentrada em áreas/UCs e não explicada por qualidade ou eventos legítimos | Priorizar inspeções pelo valor recuperável e probabilidade de confirmação |
| `[HIPÓTESE]` Migração de classe ou cadastro incorreto distorceu o mix | Classe ao longo do tempo, alterações cadastrais e distribuição por UC | Mudanças abruptas de classe sem evidência operacional ou regulatória | Corrigir cadastro e recalcular a ponte |
| `[HIPÓTESE]` Inadimplência reduziu arrecadação, mas não necessariamente receita faturada | Status de pagamento, vencimento, estorno e faturamento | Queda de recebimento sem queda equivalente de faturamento | Separar receita faturada de receita recebida e atuar em cobrança |
| `[HIPÓTESE]` Interrupções e qualidade de serviço reduziram consumo/faturamento | Ocorrências, duração, DEC/FEC e série de consumo por alimentador | Quedas concentram-se em alimentadores com interrupções anormais, após controlar sazonalidade | Priorizar manutenção e investigar faturamento após interrupções |
| `[HIPÓTESE]` Problemas de qualidade de dados criaram variação artificial | Nulos, duplicatas, mudanças de layout, chaves órfãs e meses ausentes | Reconciliação falha ou a variação desaparece após saneamento | Corrigir pipeline e não recomendar ação comercial com base no dado defeituoso |

Para hipóteses quantitativas, será usado teste de sensibilidade por período, segmento e grupo comparável. Quando não houver desenho causal suficiente, o texto deverá dizer “consistente com” em vez de “causou”.

### 3.4 Ordem de grandeza do impacto

Para cada recomendação, o relatório apresentará:

`impacto anual estimado = população elegível × energia/receita incremental por unidade × taxa de sucesso × preço médio aplicável`

ou, para perdas e cobrança:

`impacto recuperável = base identificada × taxa de recuperação esperada × preço médio efetivo`

Os parâmetros serão derivados da Gold, de resultados históricos de inspeção/cobrança ou de cenários explicitamente rotulados como `[PREMISSA]`. Serão apresentados três cenários — conservador, base e alto — sem transformar uma estimativa em promessa. A ordem de grandeza será expressa em faixas monetárias e, quando útil, em percentual da variação total observada.

Recomendações só serão consideradas executivas quando contiverem: público-alvo, ação, dono, prazo, indicador de sucesso, custo/complexidade relativa e faixa de impacto.

### 3.5 Estrutura do relatório em `docs/`

O arquivo principal será `docs/diagnostico-receita.md`, acompanhado, se aplicável, pelos artefatos reprodutíveis:

```text
docs/
├── diagnostico-receita.md
├── dicionario-dados-gold.md
├── diagnostico/
│   ├── sql/
│   │   ├── 01_reconciliacao.sql
│   │   ├── 02_decomposicao_preco_volume.sql
│   │   └── 03_cortes_municipio_bairro_classe.sql
│   └── resultados/
│       ├── ponte_receita.csv
│       └── hipoteses.csv
```

O relatório seguirá esta ordem:

1. resumo executivo e pergunta de negócio;
2. escopo, períodos e regras de inclusão;
3. qualidade, cobertura e reconciliação;
4. evolução mensal de receita, volume e preço médio;
5. decomposição preço × volume e efeito-mix;
6. cortes por município, bairro e classe;
7. hipóteses, evidências, limitações e status de validação;
8. recomendações priorizadas e ordem de grandeza;
9. plano de acompanhamento e indicadores;
10. pendências dependentes da exploração dos dados reais.

## 4. Interfaces com os outros módulos

### 4.1 Dados → Diagnóstico

O diagnóstico depende das métricas do contrato: preço médio, volume total, mix de classe, impacto de bandeira e GD e perdas estimadas. A Engenharia de Dados deve publicar essas colunas com nomes em `snake_case`, tipos estáveis, granularidade documentada e chaves de junção auditáveis.

O diagnóstico não deve recalcular silenciosamente regras de negócio conflitantes com a Gold. Se uma métrica necessária não existir, a lacuna será registrada para o Hermes e a recomendação será tratada como pendência, não como número inventado.

### 4.2 Diagnóstico → Portal

O endpoint `GET /metrics/revenue-variance` deverá retornar, no mínimo, período inicial/final, receita inicial/final, volume inicial/final, preço médio inicial/final, efeito-preço, efeito-volume, efeito-mix quando disponível, contribuição absoluta e percentual e filtros aplicados. Os filtros obrigatórios são município, bairro e classe; bandeira, modalidade, GD e alimentador são filtros adicionais quando houver cobertura.

O Portal exibirá a ponte em gráfico waterfall, tabelas de ranking e drill-down até a célula analítica. O número exibido deve usar a mesma definição e o mesmo período do relatório em `docs/`, evitando divergência entre apresentação e aplicação.

### 4.3 Diagnóstico → IA

O agente Text-to-SQL poderá consultar as tabelas Gold em modo somente leitura para responder perguntas como “qual bairro mais perdeu volume residencial?” ou “quanto da variação foi preço?”. O glossário e o schema linking devem apontar para as métricas e fórmulas documentadas nesta seção. Respostas sem cobertura ou com dados insuficientes devem retornar “não sei”/pedido de esclarecimento, sem completar lacunas por inferência.

## 5. Riscos e mitigação

| Risco | Impacto | Mitigação |
|---|---|---|
| Receita faturada e receita recebida serem confundidas | Alto | Nomear métricas separadamente e usar status de pagamento apenas na análise de inadimplência |
| Preço médio agregado esconder efeito-mix | Alto | Calcular em células homogêneas e apresentar mix separadamente |
| Meses sem leitura/faturamento serem tratados como zero | Alto | Regras de cobertura, flags de ausência e reconciliação antes da decomposição |
| Bandeira, tributos ou GD terem semântica incompleta | Alto | Dicionário de dados, cortes de sensibilidade e classificação como pendência |
| Correlação ser apresentada como causalidade | Alto | Matriz de hipóteses, grupo comparável e linguagem de evidência |
| Portal e relatório usarem fórmulas diferentes | Médio | SQL/fórmula única versionada e revisão cruzada Diagnóstico ↔ Dados/Portal |
| Estimativa de impacto ser interpretada como meta garantida | Médio | Cenários conservador/base/alto, premissas explícitas e indicador de acompanhamento |

## 6. Premissas

- `[PREMISSA]` “Receita” será tratada como receita faturada no diagnóstico principal; receita recebida será uma análise separada de inadimplência.
- `[PREMISSA]` Os períodos serão dois blocos de 12 meses completos e comparáveis, definidos após inspeção das datas disponíveis.
- `[PREMISSA]` A unidade de volume será a mesma em todos os períodos e segmentos incluídos; conversões serão documentadas.
- `[PREMISSA]` A decomposição oficial usará Shapley aditivo e será reconciliada com a variação total.
- `[PREMISSA]` O banco local e o Portal consumirão a mesma Gold exportada, sem transformação divergente da regra de negócio.
- `[PREMISSA]` Recomendações com impacto financeiro serão apresentadas como faixas de cenário, nunca como resultado observado antes da execução.

## 7. Pendências que dependem de explorar os dados reais

1. Confirmar quais fontes contêm volume faturado, receita, tarifa, bandeira, GD, classe, município e bairro.
2. Confirmar se a receita está em valor bruto, líquido, com tributos, descontos, estornos e cancelamentos.
3. Definir a regra de inclusão de faturas corrigidas, duplicadas, canceladas e meses sem leitura.
4. Verificar se existe histórico de alterações de classe, modalidade, cadastro e GD por UC.
5. Medir a cobertura e a consistência das chaves entre `fact_leituras`, `fact_faturamento` e `dim_unidade_consumidora`.
6. Confirmar se perdas estimadas e inspeções possuem histórico suficiente para estimar recuperação.
7. Avaliar se ocorrências e DEC/FEC têm granularidade temporal e geográfica adequada para o teste de continuidade.
8. Calibrar os cenários de impacto com taxas históricas ou, na ausência delas, registrar as premissas aprovadas pela diretoria.

