# Decisões de Negócio e Arquitetura: Camada Gold

Este documento consolida as decisões de modelagem dimensional, regras de negócio e governança adotadas na implementação dos notebooks [`04_gold_dimensoes.py`](../04_gold_dimensoes.py) e [`05_gold_perdas.py`](../05_gold_perdas.py) para o pipeline analítico da V-Energy Grid 360.

**Última atualização:** 25/10/2026  
**Contexto:** Transição da Camada Silver (saneada) para Camada Gold (analítica e consumo).

---

## 1. Notebook `04_gold_dimensoes.py`

### 1.1. `dim_unidade_consumidora` (Visão 360 do Cliente)

- **Grão:** 1 linha por Unidade Consumidora ativa (45.000 registros).
- **Decisão LGPD (Art. 13 e Art. 14):** Os campos identificadores de pessoas físicas e jurídicas (`cpf_cnpj`) são mascarados na Gold via `cpf_cnpj_mascarado` (`*******1234`), preservando apenas os últimos 4 dígitos para conferência de atendimento e call center, sem expor PII sensível em relatórios analíticos amplos. A chave de integração interna permanece `id_uc`.
- **Consolidação do Medidor Ativo:** Apenas o medidor marcado com `medidor_atual = true` na `silver_medidores` é agregado à UC. UCs com medidores retirados no histórico têm o medidor atual devidamente preenchido (45.000 UCs possuem exatamente 1 medidor ativo).
- **Rastreabilidade da Modernização de Medição:** A dinâmica da campanha de troca de medidores (set/2025–mar/2026) foi incorporada diretamente na dimensão:
  - `trocou_medidor`: booleano indicando se a UC passou por substituição;
  - `data_ultima_troca_medidor`: data de retirada do medidor substituído;
  - `tipo_medidor_anterior`: tecnologia do medidor retirado (ex.: eletromecânico substituído por smart).
- **Integridade Referencial com GD:** O relacionamento com geração distribuída é feito exclusivamente contra registros válidos de `silver_geracao_distribuida` (3.503 UCs), eliminando os falsos positivos de GDs com problemas cadastrais (resolvendo o item `G-08` do `registro_de_problemas.md`).

### 1.2. `dim_alimentador` (Circuitos de Média Tensão)

- **Grão:** 1 linha por alimentador (122 circuitos).
- **Determinação Determinística do Município Principal (Resolução do `G-02`):**
  - Anteriormente, o código utilizava `F.first("municipio")`, gerando instabilidade quando um circuito atendia áreas limítrofes entre dois municípios (ex.: Recife e Jaboatão).
  - Regra adotada: contagem de UCs por alimentador e município; o município com maior contingente de clientes vinculados é eleito `municipio_principal` (com desempate alfabético por nome do município).
- **Mitigação de Distorções Regulatórias (`alimentador_pequeno`):**
  - Alimentadores com menos de 100 UCs atendidas sofrem com volatilidade estatística severa no cálculo de DEC e FEC (qualquer interrupção isolada infla drasticamente os indicadores pelo denominador reduzido).
  - Foi criada a flag `alimentador_pequeno = total_ucs < 100` para que os dashboards de Operação e os rankings anuais permitam filtros com e sem expurgo desses circuitos atípicos.
- **Distribuição de Carga Cadastral:** Consolidação das contagens de clientes por classe de consumo (`ucs_residencial`, `ucs_comercial`, `ucs_industrial`, `ucs_rural`, `ucs_poder_publico`), alimentando análises de criticidade de rede.

### 1.3. `dim_medidor` (Parque de Medição e Ativos)

- **Grão:** 1 linha por medidor físico (51.299 registros = 45.000 ativos + 6.299 retirados).
- **Objetivo:** Permitir análise longitudinal de falhas de equipamentos, correlação entre trocas para smart meters e variação no volume faturado (resolvendo o item `G-03` do `registro_de_problemas.md`).
- **Saneamento Herança:** Mantém as datas corrigidas (`data_instalacao` sem inversão mês-dia) e tipos tecnológicos padronizados (`ELETROMECANICO`, `ELETRONICO`, `SMART`).

### 1.4. `dim_geracao_distribuida` (Micro e Minigeração)

- **Grão:** 1 linha por UC geradora (3.503 registros).
- **Correção da Energia Estimada Paramétrica (`kWp × 110`):**
  - ~101 UCs conectadas em mai–jun/2026 foram cadastradas na fonte com uma média de injeção padrão calculada artificialmente por `kWp × 110`, inflando a injeção acumulada em ~75 mil kWh/mês.
  - Regra adotada: criação da coluna `energia_reestimada_kwh`, que aplica a razão mediana empírica comprovada da base (~34 kWh/kWp·mês) para todas as UCs marcadas com `energia_estimada = true`, mantendo a injeção real nas demais.

### 1.5. `dim_competencia` (Calendário Analítico)

- **Grão:** 1 linha por mês/competência (48 registros: jul/2022 a jun/2026).
- **Alinhamento Executivo:** Mapeia os dois períodos centrais exigidos para a decomposição de receita da Diretoria Comercial:
  - `PRIMEIRO_ANO` (P0): jul/2022 a jun/2023 (12 meses base);
  - `ULTIMOS_12M` (P1): jul/2025 a jun/2026 (12 meses recentes);
  - Bandeiras tarifárias oficiais do Sistema Interligado Nacional incorporadas por competência.

---

## 2. Notebook `05_gold_perdas.py` (`fila_inspecao`)

A criação da tabela `fila_inspecao` atende diretamente à user story de Perdas Não Técnicas (resolvendo o item `G-10` do `registro_de_problemas.md`).

### 2.1. Grão e Filtragem de Risco

- **Grão:** 1 linha por Unidade Consumidora prioritária para fiscalização em campo.
- **Corte de Qualidade (`score >= 20`):** UCs com pontuação inferior a 20 pontos são desconsideradas da fila ativa para evitar custos de deslocamento inócuos de inspetores em clientes de baixo risco.
- **Ordenação Multivariada da Prioridade:** A posição na fila (`prioridade = 1, 2, ...`) é definida primeiramente pelo `score` decrescente, desempatada pelo maior volume de `kwh_recuperavel_estimado_ano`.

### 2.2. Isolamento de Sazonalidade Temporal

- Para aferir queda real de consumo (indicativo de desvio ou by-pass no medidor), a regra compara os **últimos 6 meses da base** (jan–jun/2026) contra os **6 meses homólogos do ano anterior** (jan–jun/2025).
- Isso impede falsos positivos decorrentes de sazonalidade climática (ex.: comparar verão com inverno).

### 2.3. Expurgo de Geração Distribuída (`queda_explicada_por_gd`)

- **Problema de Negócio:** UCs que instalaram sistemas solares fotovoltaicos apresentam queda expressiva no consumo medido da rede, o que poderia ser erroneamente interpretado como fraude pelo modelo.
- **Solução:** Se a UC possui GD e a `data_conexao_gd` ocorreu no período de comparação, a coluna `queda_explicada_por_gd` recebe `true`. Nesse cenário:
  - A variação de consumo **não pontua** no score de fraude;
  - O `kwh_recuperavel_estimado_ano` é cravado em `0.0`.

### 2.4. Explicabilidade Algorítmica e Governança LGPD (Art. 20)

- O artigo 20 da LGPD confere ao titular o direito de obter informações claras a respeito dos critérios e procedimentos utilizados para a tomada de decisões automatizadas que afetem seus interesses.
- A coluna `motivo_suspeita` armazena a lista textual de todas as regras específicas que pontuaram para aquela UC (ex.: `"Queda de consumo >= 50% (+40); Medidor eletromecanico (+15); Bairro com taxa de irregularidade >= 1.2x (+10)"`).

### 2.5. Tabela de Pesos do Motor Heurístico

| Critério | Condição | Impacto | Justificativa de Negócio |
|---|---|:---:|---|
| **Queda Brusca de Consumo** | $\ge 50\%$ sem GD | **+40 pts** | Maior indicador de desvio direto ou by-pass |
| | $\ge 30\%$ e $< 50\%$ sem GD | **+30 pts** | Queda moderada relevante |
| | $\ge 15\%$ e $< 30\%$ sem GD | **+15 pts** | Queda leve a monitorar |
| **Tecnologia do Medidor** | Tipo `ELETROMECANICO` | **+15 pts** | Equipamento analógico suscetível a manipulação mecânica e ímãs |
| **Fragilidade de Medição** | Leituras estimadas $\ge 50\%$ em 12M | **+15 pts** | Falta prolongada de leitura presencial mascara fraudes |
| | Leituras estimadas $\ge 25\%$ em 12M | **+8 pts** | Intermitência de medição |
| **Anomalias de Faturamento** | $\ge 2$ ocorrências em 12M | **+10 pts** | Histórico de retificações e inconsistências |
| | 1 ocorrência em 12M | **+5 pts** | Anomalia pontual |
| **Risco Geográfico (Vizinhaça)** | Taxa de fraude no bairro $\ge 1,2\times$ média | **+10 pts** | Efeito contágio em áreas com alta taxa de confirmação ($\ge 5$ inspeções) |
| **Reincidência Cadastral** | Já teve irregularidade confirmada | **+10 pts** | Reincidência histórica |
| **Atenuador de Fiscalização** | Inspecionada sem irregularidade $\le 180$ dias | **-25 pts** | Evita retrabalho e desgaste com cliente recentemente validado |

---

## 3. Resumo de Itens Saneados no Pipeline

Com a entrega desses dois notebooks, os seguintes pontos do `registro_de_problemas.md` foram oficialmente solucionados:
- **`G-02`:** Alimentadores com agregação de município determinística;
- **`G-03`:** Disponibilização analítica completa de medidores na Gold (`dim_medidor` e atributos na `dim_unidade_consumidora`);
- **`G-08`:** Join seguro entre UCs e GDs válidas;
- **`G-10`:** Geração automatizada da fila de perdas e cálculo de volume recuperável.
