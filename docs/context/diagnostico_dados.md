# Revisão cruzada — Engenharia de Dados revisada

**Revisor:** Agente Diagnóstico  
**Seção revisada:** `secoes/03-engenharia-de-dados.md`  
**Seção de referência:** `secoes/06-diagnostico-receita.md`  
**Escopo:** verificar se a Gold permite apropriar as hipóteses de bandeira, GD, perdas e mix.

## Parecer geral

A seção de Dados define uma boa direção arquitetural — Bronze → Silver → Gold, esquema estrela e tabelas de faturamento, leituras, ocorrências e cadastro —, mas a modelagem Gold ainda **não fecha todos os requisitos do diagnóstico**. Bandeira e mix têm cobertura parcial; geração distribuída e perdas não têm entidade ou colunas explicitamente definidas. A seção precisa transformar as “tabelas esperadas” em um contrato físico mínimo, com granularidade, chaves e métricas obrigatórias, antes de o diagnóstico e o Portal implementarem as queries.

## Achados e recomendações

| # | Severidade | Achado | Impacto no diagnóstico | Recomendação |
|---|---|---|---|---|
| 1 | Alta | `fact_faturamento` é descrita apenas como “valores, bandeiras tarifárias e status de pagamento”. Não há colunas para receita faturada, receita recebida, volume faturado, tarifa/preço efetivo, estorno/cancelamento ou unidade de energia. | Impede separar receita faturada de recebida e calcular `P = R/Q` com segurança; a hipótese de inadimplência e a decomposição preço × volume ficam ambíguas. | Definir `fact_faturamento` no grão mínimo `uc_id × competencia` (ou `fatura_id` quando houver várias faturas por competência), com `receita_faturada`, `receita_recebida`, `volume_faturado_kwh`, `valor_tarifa`, `valor_bandeira`, `valor_tributos`, `valor_desconto`, `valor_estorno`, `status_pagamento`, `data_vencimento`, `data_pagamento` e identificador da fatura. |
| 2 | Alta | A seção informa bandeira, mas não define a dimensão/coluna temporal nem o tratamento de múltiplas bandeiras dentro da mesma competência. | A hipótese de impacto de bandeira pode ser confundida com reajuste, mix ou atraso de faturamento. | Registrar `bandeira_tarifaria` e, se aplicável, `subperiodo_inicio`/`subperiodo_fim` ou regra de rateio. Publicar uma tabela Gold de tarifa/bandeira por competência ou documentar que a bandeira é atributo da fatura e como se trata mudança no mês. |
| 3 | Crítica | Não existe tabela ou coluna explícita para geração distribuída (GD), créditos de energia, potência instalada ou data de adesão. | A hipótese de que GD reduziu o volume faturado não pode ser testada nem segmentada por UCs com e sem GD. | Criar `fact_gd` ou enriquecer uma dimensão histórica com `uc_id`, `gd_flag`, `data_adesao_gd`, `data_inicio_compensacao`, `energia_gerada_kwh`, `energia_compensada_kwh`, `creditos_kwh` e modalidade. Manter histórico temporal para comparação antes/depois. |
| 4 | Crítica | Não existe tabela de perdas, inspeções ou diferença entre energia medida e faturada. | A hipótese de perdas não técnicas e a estimativa de energia/receita recuperável ficam sem evidência operacional. | Criar `fact_perdas` ou `fact_inspecoes`, com `uc_id`, competência, `energia_medida_kwh`, `energia_faturada_kwh`, `perda_estimada_kwh`, `score_suspeita`, `energia_estimada_recuperar_kwh`, motivo, resultado e data da inspeção. Separar perdas técnicas, não técnicas e diferença não explicada quando possível. |
| 5 | Alta | `dim_unidade_consumidora` é descrita como cadastro central, sem indicar histórico de classe, bairro, município, modalidade ou alimentador. | Um cadastro atual aplicado retroativamente pode criar falso efeito-mix e atribuir variações a segmentos errados. | Usar dimensão historizada (SCD tipo 2 ou snapshots mensais) ou atributos válidos na competência: `valid_from`, `valid_to`/`competencia`, `classe`, `subclasse`, `modalidade_tarifaria`, `municipio`, `bairro`, `alimentador_id`, `gd_flag`. |
| 6 | Alta | `fact_leituras` é chamada de “consumo mensal consolidado”, mas não distingue leitura medida, leitura estimada, energia faturada e qualidade da leitura. | Não é possível validar a queda de volume, a diferença medição × faturamento ou o efeito de qualidade de dados. | Definir `energia_medida_kwh`, `energia_faturada_kwh` quando a origem de leitura for essa, `tipo_leitura`, `leitura_estimada_flag`, `data_leitura`, `medidor_id`, `qualidade_leitura` e regra de fechamento mensal. Não misturar leitura medida com volume faturado sem indicador de origem. |
| 7 | Alta | `fact_ocorrencias` é vinculada a UC e alimentador, mas a seção não define duração, consumidores afetados, competência e regra de atribuição. | DEC/FEC e a hipótese de continuidade não podem ser relacionados de modo auditável à série de consumo/faturamento. | Definir `ocorrencia_id`, `alimentador_id`, `uc_id` quando disponível, `inicio`, `fim`, `duracao_minutos`, `consumidores_afetados`, causa, competência e regra para evitar dupla contagem na agregação mensal. |
| 8 | Média | O contrato menciona “mix de classe, impacto de Bandeira e GD, perdas estimadas”, mas o dicionário de dados é apenas prometido e não lista essas métricas. | Há risco de cada módulo criar sua própria interpretação e produzir números divergentes. | Publicar no dicionário Gold a definição, fórmula, grão, unidade, nulos permitidos, origem e exemplo de cada métrica; incluir a chave de período usada pelo diagnóstico. |
| 9 | Média | A integridade referencial citada cobre medição, faturamento e cadastro, mas não explicita cardinalidade e cobertura temporal. | Junções podem duplicar receita/volume, sobretudo quando há várias leituras, faturas ou alterações cadastrais na mesma competência. | Definir chaves naturais/surrogate, unicidade esperada por fato e testes de cardinalidade. Antes da agregação, validar que cada junção preserva o grão e medir órfãos, duplicatas e cobertura por período. |

## Contrato Gold mínimo recomendado

Para viabilizar o diagnóstico, a Gold deve expor pelo menos:

1. `dim_unidade_consumidora` — atributos geográficos e comerciais válidos na competência, com histórico;
2. `fact_leituras` — medição mensal, tipo/qualidade da leitura e energia medida;
3. `fact_faturamento` — receita, volume faturado, componentes tarifários, bandeira e pagamento;
4. `fact_gd` — adesão, geração, compensação e créditos por UC e período;
5. `fact_perdas` ou `fact_inspecoes` — diferença medida/faturada, suspeita, inspeção e recuperação;
6. `fact_ocorrencias` — eventos de continuidade com início, fim, duração, afetados e vínculo ao alimentador;
7. uma visão analítica `gold_receita_mensal` no grão `competencia × municipio × bairro × classe` (com cortes opcionais de bandeira, GD e alimentador), contendo `receita_faturada`, `volume_faturado_kwh`, `preco_medio`, `quantidade_ucs`, `efeito`/atributos de cobertura e flags de qualidade.

A visão agregada não substitui os fatos; ela reduz o risco de cada consumidor do Portal ou IA repetir joins sensíveis. A fórmula oficial de decomposição deve permanecer versionada e compartilhada com o endpoint `/metrics/revenue-variance`.

## Conclusão para a Fase 3

**Status: revisão com correções necessárias.** A arquitetura proposta é compatível com o diagnóstico, mas a seção de Dados deve explicitar as entidades/colunas de GD e perdas, enriquecer faturamento e leituras e historizar os atributos de mix. Sem esses ajustes, apenas as análises de receita total, bandeira em nível básico e cortes cadastrais atuais seriam suportadas; as conclusões sobre GD, perdas, migração de classe e preço × volume não seriam auditáveis.

