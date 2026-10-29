# Decisões de Negócio e Arquitetura: Camada Gold

Este documento consolida todas as decisões de modelagem dimensional, engenharia de dados, regras de negócio regulatórias (PRODIST/ANEEL), governança da privacidade (LGPD) e diagnósticos econômicos adotados na camada Gold do projeto **V-Energy Grid 360**.

**Data de consolidação:** 25/10/2026  
**Escopo do Pipeline:**
- [`04_gold_dimensoes.py`](../gold/04_gold_dimensoes.py)
- [`04_gold_fatos.py`](../gold/04_gold_fatos.py)
- [`05_gold_continuidade.py`](../gold/05_gold_continuidade.py)
- [`05_gold_receita.py`](../gold/05_gold_receita.py)
- [`05_gold_perdas.py`](../gold/05_gold_perdas.py)

---

## 1. Visão Geral e Princípios Arquiteturais da Camada Gold

A camada Gold opera como a **camada de apresentação e consumo analítico** do Data Warehouse Medallion. Enquanto a camada Bronze preserva a fidelidade bruta dos arquivos e a camada Silver executa a padronização, limpeza e quarentena defensiva, a camada Gold obedece aos seguintes princípios de engenharia de dados:

1. **Modelagem Dimensional Estelar/Constelação:** Separação clara entre entidades dimensionais (contexto cadastral e infraestrutura) e tabelas fato (eventos mensuráveis e transações).
2. **Desacoplamento e Segurança (LGPD):** Nenhum documento identificador direto de pessoa física ou jurídica (CPF/CNPJ) transita em formato cru na camada Gold. A chave mestra operacional e de relacionamento analítico é exclusivamente o `id_uc`.
3. **Consistência Matemática Aditiva:** As métricas agregadas na Gold são auditáveis e fecham de forma determinística em qualquer nível de corte (alimentador, classe de consumo, município, bairro e competência).
4. **Resiliência a Anomalias da Fonte:** Fragilidades documentadas nos relatórios de perfilagem (ex.: ausência de kWh na fatura, faturas órfãs, potências em Watts, rótulos de ações aleatórios em atendimentos e saturação de tempestades) são tratadas na arquitetura antes da entrega ao usuário final.

---

## 2. Decisões de Modelagem Dimensional (`04_gold_dimensoes.py`)

O notebook consolida as 5 dimensões analíticas do ecossistema:

### 2.1. `dim_unidade_consumidora` (Visão 360 do Cliente)
- **Grão:** 1 linha por Unidade Consumidora ativa (exatamente 45.000 UCs).
- **Decisão LGPD (Art. 13 e Art. 14):** Criação da coluna `cpf_cnpj_mascarado` (`*******1234`), preservando apenas os 4 últimos dígitos para suporte operacional e call center, eliminando o trânsito de PII em dashboards analíticos.
- **Consolidação do Medidor Ativo:** Apenas o medidor marcado com `medidor_atual = true` na `silver_medidores` é vinculado como medidor ativo da UC (`id_medidor_atual`, `tipo_medidor_atual`, `modelo_medidor_atual`, `data_instalacao_medidor_atual`). UCs com histórico de medidores retirados mantêm o medidor atual devidamente apontado.
- **Rastreabilidade da Modernização de Medição:** A dinâmica da campanha de troca de medidores analógicos por smart meters (set/2025–mar/2026) foi incorporada diretamente na dimensão:
  - `trocou_medidor`: indicador booleano de modernização;
  - `data_ultima_troca_medidor`: data de retirada do medidor substituído;
  - `tipo_medidor_anterior`: tecnologia do medidor substituído (ex.: eletromecânico substituído por smart).
- **Integridade com Geração Distribuída (`G-08`):** O relacionamento com GD faz join exclusivo contra as 3.503 UCs válidas de `silver_geracao_distribuida`, garantindo que UCs com GD inconsistente quarentenadas não recebam falsamente `possui_gd = true`.

### 2.2. `dim_alimentador` (Circuitos de Média Tensão)
- **Grão:** 1 linha por circuito alimentador (122 alimentadores).
- **Resolução Determinística do Município Principal (`G-02`):**
  - Anteriormente, o uso de `F.first("municipio")` gerava divergências não determinísticas em circuitos que atendem municípios limítrofes.
  - Regra adotada: contagem de UCs por alimentador e município; o município com maior número de clientes atendidos é eleito `municipio_principal` (com desempate alfabético por nome do município).
- **Mitigação de Distorções Regulatórias (`alimentador_pequeno`):**
  - Circuitos com menos de 100 UCs atendidas sofrem com volatilidade matemática severa no cálculo de DEC e FEC, pois qualquer interrupção pontual gera picos artificiais nos indicadores (`N-10`).
  - Criação da flag `alimentador_pequeno = total_ucs < 100` para permitir a filtragem e expurgo em dashboards de qualidade operacional.
- **Perfil de Carga Cadastral:** Agregação das UCs atendidas por classe de consumo (`ucs_residencial`, `ucs_comercial`, `ucs_industrial`, `ucs_rural`, `ucs_poder_publico`), alimentando análises de vulnerabilidade de rede.

### 2.3. `dim_medidor` (Parque de Medição e Ativos)
- **Grão:** 1 linha por medidor físico (51.299 registros = 45.000 ativos + 6.299 retirados).
- **Resolução do Item `G-03`:** Disponibiliza o parque completo de medição física na Gold com tecnologias e datas saneadas, permitindo auditorias de ciclo de vida de ativos, falhas de medição e campanhas de substituição.

### 2.4. `dim_geracao_distribuida` (Micro e Minigeração)
- **Grão:** 1 linha por UC geradora ativa (3.503 registros).
- **Correção da Energia Estimada Paramétrica (`S-GD-04`):**
  - ~101 UCs conectadas em mai–jun/2026 foram cadastradas na fonte com uma média de injeção padrão calculada artificialmente por `kWp × 110`, inflando a injeção acumulada em ~75 mil kWh/mês.
  - Criação da coluna `energia_reestimada_kwh`: aplica a razão mediana empírica comprovada da base (~34 kWh/kWp·mês) para todas as UCs com `energia_estimada = true`, mantendo a injeção real nas demais.

### 2.5. `dim_competencia` (Calendário Analítico)
- **Grão:** 1 linha por mês/competência (48 registros: jul/2022 a jun/2026).
- **Marcos Executivos:** Vinculação oficial das bandeiras tarifárias por competência e mapeamento dos períodos de diagnóstico executivo da diretoria comercial:
  - `PRIMEIRO_ANO` (P0): jul/2022 a jun/2023 (12 meses base);
  - `ULTIMOS_12M` (P1): jul/2025 a jun/2026 (12 meses recentes).

---

## 3. Decisões de Modelagem de Fatos e Reconciliação (`04_gold_fatos.py`)

### 3.1. `fact_faturamento`
- **Grão:** 1 linha por fatura emitida = 1 por UC por competência (2.152.336 faturas válidas).
- **Enriquecimento com Volume de Medição (`S-FAT-07`):** Como o arquivo de faturamento original não contém a quantidade de kWh cobrada, a fatura é enriquecida via join com `fact_leituras` pela chave composta `(id_uc, competencia)`, derivando o indicador oficial de `preco_medio_kwh = valor_energia / consumo_kwh`.
- **Reconciliação de Receita Recebida e Inadimplência:**
  - `receita_faturada = valor_total`;
  - `receita_recebida`: calculada como `valor_total` se `status == 'PAGA'`, e `0.0` para faturas em aberto;
  - Data de referência para atraso congelada na data máxima de emissão (`DATA_REF = 2026-06-30`), evitando que o atraso aumente artificialmente a cada reexecução do pipeline em datas posteriores.
- **Expurgo de Faturas Órfãs (`S-FAT-06`):** As 32.285 faturas associadas a UCs inexistentes no cadastro foram quarentenadas na Silver, impedindo distorções de 1,1% a 2,2% na receita da Gold.

### 3.2. `fact_leituras`
- **Grão:** 1 linha por UC × competência (2.152.336 registros).
- **Consumo Ajustado Oficial:** Adota o campo `consumo_kwh_ajustado` (onde a Silver corrigiu duplicatas, sentinelas `-1` e imputou o consumo da troca física de medidores, `S-LEI-08`).
- **Isolamento de Sazonalidade na Visão 360:** Auto-join com o consumo de 12 meses atrás (`competencia - 12 meses`), gerando `variacao_ano_anterior_pct`. Essa decisão responde diretamente à pergunta do cliente *"por que minha conta veio alta?"*, neutralizando variações climáticas anuais normais.

### 3.3. `fact_ocorrencias`
- **Grão:** 1 linha por UC interrompida (180.000 registros).
- **Preceito Regulatório:** O grão original do case estabelece que cada registro corresponde a 1 cliente interrompido.
- **Sinalização de Durações Truncadas (`S-OCO-04`):** Durações cortadas na origem em 2.880 min (48 h) recebem a flag `duracao_truncada = true` (30 casos, a maioria em jul/2025).
- **Classificação de Dia Crítico (`N-12`):** Dias com volume de ocorrências acima da média diária $+ 3$ desvios-padrão recebem `dia_critico = true` (identificando exatamente os 31 dias de julho/2025) para atender às normas do PRODIST Módulo 8 da ANEEL.
- **Filtro de Oscilação (`S-OCO-05`):** Criação da flag booleana `eh_oscilacao` para viabilizar o cálculo do DEC/FEC estrito (apenas interrupções reais) ou amplo.

### 3.4. `fact_atendimentos`
- **Grão:** 1 linha por chamado registrado no call center (318.871 registros).
- **Supressão do Histórico Randômico (`S-ATE-02`):** A perfilagem de dados comprovou que a coluna `historico` continha sequências de ações geradas aleatoriamente por simulação sintética (~81% de chamados com ações fora de ordem cronológica e taxas idênticas entre municípios). A decisão de engenharia foi não explodir o array na Gold, preservando apenas as métricas consolidadas: `tempo_resolucao_h`, `qtd_tratativas`, status e nota de satisfação.

### 3.5. `fact_inspecoes`
- **Grão:** 1 linha por inspeção de campo (1.389 inspeções).
- **Receita Oculta e Efetividade de Campo:** Consolida o resultado canônico (`IRREGULARIDADE_CONFIRMADA` e `SEM_IRREGULARIDADE`) e registra o volume total de ~1,47 GWh recuperados, servindo de base para modelos de prevenção de fraudes.

---

## 4. Decisões de Continuidade e Qualidade da Operação (`05_gold_continuidade.py`)

### 4.1. `agg_continuidade_alimentador` (Mensal)
- **Grão:** alimentador × competência (122 alimentadores × 48 competências = exatamente 5.856 linhas).
- **Decisão da Grade Completa (`crossJoin`):** O cálculo faz o produto cartesiano entre todos os alimentadores da `dim_alimentador` e todas as competências da `dim_competencia`, preenchendo meses sem ocorrências com zero (`fillna(0, METRICAS)`).
  - *Justificativa de Negócio:* Se um alimentador opera com perfeição (zero falhas em determinado mês), a ausência de registro na fato de ocorrências faria com que o alimentador desaparecesse da análise ou não contribuísse para a média da concessionária. A grade completa garante integridade das séries temporais.
- **Fórmulas de Continuidade Regulatórias:**
  - $\text{DEC} = \frac{\sum \text{duracao\_h}}{\text{total\_ucs}}$
  - $\text{FEC} = \frac{\text{interrupções}}{\text{total\_ucs}}$
- **Métricas Dualistas (Com e Sem Dia Crítico):**
  - $\text{DEC}_{\text{sem\_dia\_critico}}$ e $\text{FEC}_{\text{sem\_dia\_critico}}$ expurgam os 31 dias de jul/2025, fornecendo a métrica de continuidade regulatória limpa exigida nos relatórios operacionais.

### 4.2. `agg_continuidade_alimentador_anual` (Rankings de Operação)
- **Grão:** alimentador × ano (122 alimentadores × 5 anos).
- **Duplo Ranking Estratégico:**
  1. `rank_dec` (Visão do Cliente): Classifica os alimentadores pelo tempo médio sem energia por cliente. Mede o nível de sofrimento e percepção do consumidor.
  2. `rank_impacto_horas_x_uc` (Visão de Engenharia de Manutenção): Classifica pelo volume absoluto de $\text{horas sem energia} \times \text{clientes afetados}$. Indica exatamente onde intervenções de engenharia preventiva proporcionam o maior retorno sistêmico sobre o capital investido.
- **Constatação Operacional (`N-10`):** A análise comprovou que **não existe pior alimentador crônico** na rede da concessionária. Os 3 piores circuitos de 2025 (`ALM-REC-008`, `ALM-SAO-004`, `ALM-JAB-004`) responderam por 72% das ocorrências de julho decorrentes de tempestade severa; expurgando julho, seus indicadores voltam aos padrões normais da distribuidora.

---

## 5. Decisões do Diagnóstico Econômico de Receita (`05_gold_receita.py`)

Este módulo responde matematicamente à pergunta central da Diretoria Comercial: *por que o volume faturado caiu quase 4% enquanto a receita cresceu apenas 8% entre o primeiro ano da base e os últimos 12 meses, apesar do reajuste tarifário residencial acumulado de 10,5%?*

### 5.1. Decomposição Aditiva Exata de Preço $\times$ Volume
- **Fórmula de Decomposição por Segmento:**
  - $\text{Efeito-Volume} = (Q_1 - Q_0) \times P_0$ (variação que ocorreria apenas pela mudança de quantidade consumida, ao preço antigo do período base);
  - $\text{Efeito-Preço} = (P_1 - P_0) \times Q_1$ (variação explicada pela mudança do preço médio efetivo aplicada ao volume recente);
  - $\text{Efeito-Volume} + \text{Efeito-Preço} = R_1 - R_0$ (fechamento aditivo exato, sem resíduos).
  - Onde: $R$ é receita faturada, $Q$ é volume medido nas leituras (kWh ajustado) e $P = R / Q$ é o preço médio efetivo por kWh.
- **Segmentos Sem Consumo Anterior:** Para segmentos novos que não possuíam faturamento no período base ($Q_0 = 0$), toda a variação de receita é integralmente atribuída ao efeito-volume.

### 5.2. Janelas Homólogas P0 e P1
- **Período Base (P0):** jul/2022 a jun/2023 (primeiros 12 meses da base);
- **Período Comparado (P1):** jul/2025 a jun/2026 (últimos 12 meses da base);
- *Justificativa de Negócio:* A comparação de 12 meses fechados contra 12 meses fechados neutraliza o impacto de variações sazonais de temperatura e hábitos de consumo (inverno vs. verão).

### 5.3. Causalidade Econômica Comprovada (`N-15`)
A consolidação em `agg_receita_preco_volume` revelou os seguintes fatos econômicos:
1. **Aumento de Receita:** De R$ 157,1 mi para R$ 169,7 mi (**+R$ 12,58 mi ou +8,0%**), confirmando o enunciado (`N-09`).
2. **Decomposição:**
   - **Efeito-Preço:** **+R$ 23,75 mi**;
   - **Efeito-Volume:** **−R$ 11,18 mi**.
3. **Causa Raiz da Queda de Volume:**
   - **76% da perda de volume (−R$ 8,50 mi) provém exclusivamente das ~3,5 mil UCs com Geração Distribuída** (7,8% da base), cujo consumo medido da rede despencou **~64%** tanto no segmento residencial quanto no comercial.
   - Nas UCs convencionais (sem GD), a redução do consumo medido foi marginal: residencial −2,6%, comercial −2,4%, industrial −0,9%, rural −5,1% e poder público +0,7%.
4. **Papel das Bandeiras Tarifárias e Reajuste:**
   - O primeiro ano da base (P0) foi marcado por **100% de bandeira verde** (sem sobretaxa tarifária).
   - O período recente (P1) registrou **8 meses com bandeiras tarifárias de acréscimo** (3 amarelas, 3 vermelhas patamar 1 e 2 vermelhas patamar 2, `N-07`).
   - O efeito-preço superou o reajuste tarifário homologado de 10,5% e compensou a perda de volume da GD, sustentando o crescimento de 8% na receita final.

---

## 6. Decisões da Fila de Perdas Não Técnicas (`05_gold_perdas.py`)

### 6.1. Grão e Critério de Corte
- **Grão:** 1 linha por UC prioritária para fiscalização presencial.
- **Corte de Risco Operacional (`score >= 20`):** Filtra o ruído cadastral e foca a mobilização das equipes de campo apenas em casos com suspeita consistente de desvio ou fraude (resolvendo o item `G-10`).
- **Ordenação da Prioridade:** A posição na fila (`prioridade = 1, 2, ...`) é ordenada pelo `score` decrescente, desempatada pelo maior volume anual estimado de energia a recuperar (`kwh_recuperavel_estimado_ano desc`).

### 6.2. Isolamento de Sazonalidade Temporal
- O cálculo da variação de consumo compara os **últimos 6 meses da base** (jan–jun/2026) contra os **6 meses equivalentes do ano anterior** (jan–jun/2025).
- *Justificativa de Negócio:* Evita que reduções normais de consumo de inverno sejam falsamente apontadas como fraude por modelos de média móvel simples.

### 6.3. Expurgo de Geração Distribuída (`queda_explicada_por_gd`)
- UCs que conectaram microgeração solar fotovoltaica durante a janela temporal têm `queda_explicada_por_gd = true`.
- *Regra de Negócio:* Nesses casos, a redução no consumo da rede **não pontua** no score de fraude e o volume recuperável anual é zerado (`kwh_recuperavel_estimado_ano = 0.0`), impedindo autuações indevidas em clientes regulares que apenas geram a própria energia.

### 6.4. Explicabilidade Algorítmica e Conformidade LGPD (Art. 20)
- Em atendimento ao direito de explicabilidade de decisões automatizadas previsto na LGPD, a coluna `motivo_suspeita` armazena a lista de justificativas técnicas auditáveis que dispararam a pontuação daquela UC.

### 6.5. Tabela Paramétrica de Pesos do Motor Heurístico

| Regra | Condição Operacional | Pontos | Fundamentação de Negócio |
|---|---|:---:|---|
| **Queda Brusca de Consumo** | $\ge 50\%$ sem GD | **+40** | Forte indício de desvio direto ou ligação clandestina (by-pass) |
| | $\ge 30\%$ e $< 50\%$ sem GD | **+30** | Queda expressiva de consumo |
| | $\ge 15\%$ e $< 30\%$ sem GD | **+15** | Queda moderada |
| **Tecnologia do Medidor** | Tipo `ELETROMECANICO` | **+15** | Medidores analógicos antigos são vulneráveis a ímãs e manipulação mecânica |
| **Fragilidade de Medição** | Leituras estimadas $\ge 50\%$ (12M) | **+15** | Ausência prolongada de leitura presencial facilita fraudes |
| | Leituras estimadas $\ge 25\%$ (12M) | **+8** | Histórico com estimativas recorrentes |
| **Anomalias de Faturamento** | $\ge 2$ ocorrências em 12M | **+10** | Histórico de retificações e leituras anômalas repetidas |
| | 1 ocorrência em 12M | **+5** | Retificação isolada |
| **Risco Geográfico (Vizinhança)** | Taxa de fraude no bairro $\ge 1,2\times$ média | **+10** | Efeito contágio em bairros com histórico de fraude ($\ge 5$ inspeções) |
| **Reincidência Cadastral** | Já teve irregularidade confirmada | **+10** | Reincidência de infração na mesma UC |
| **Atenuador de Fiscalização** | Inspecionada sem irregularidade $\le 180$ dias | **-25** | Evita retrabalho e atrito com cliente recentemente vistoriado e aprovado |

---

## 7. Matriz de Rastreabilidade e Resolução do Registro de Problemas

A tabela a seguir correlaciona as regras implementadas na Gold com os itens do [`registro_de_problemas.md`](./registro_de_problemas.md):

| ID Problema | Descrição Original | Impacto no Negócio | Solução Implementada na Gold |
|:---:|---|---|---|
| **`G-02`** | `dim_alimentadores` usava `F.first("municipio")` | Classificação territorial não-determinística do alimentador | Determinação determinística por contagem de UCs e desempate alfabético em `04_gold_dimensoes.py` |
| **`G-03`** | Medidores não estavam presentes na Gold | Impossibilitava a Visão 360 e correlação com troca de medidores | Criação da `dim_medidor` e atributos na `dim_unidade_consumidora` em `04_gold_dimensoes.py` |
| **`G-04`** | `agg_receita_mensal` não decompunha preço $\times$ volume | Ocultava a causa da divergência de receita da Diretoria Comercial | Decomposição aditiva completa implementada em `05_gold_receita.py` |
| **`G-08`** | `possui_gd` calculado sem verificar validade do `id_uc` | Atribuição de GD a clientes com cadastros corrompidos | Join exclusivo com `silver_geracao_distribuida` saneada em `04_gold_dimensoes.py` |
| **`G-10`** | Fila de perdas não técnicas não existia | Desatendimento a requisito obrigatório de negócio | Implementação da tabela `fila_inspecao` em `05_gold_perdas.py` |
| **`S-GD-02`** | Potência de GD em Watts inflando soma em 13× | Distorção grave na capacidade instalada da rede | Divisão por 1.000 em `potencia_kwp` propagada para `dim_geracao_distribuida` |
| **`S-GD-04`** | Injeção estimada paramétrica (`kWp × 110`) | Superestimava injeção em ~75 mil kWh/mês em 2026 | Reestimativa pela razão real da base (~34 kWh/kWp) em `energia_reestimada_kwh` |
| **`S-OCO-04`** | Durações truncadas em 48 h (2.880 min) | Subestimação leve do DEC em dias críticos | Criação da flag `duracao_truncada` em `fact_ocorrencias` e `agg_continuidade_alimentador` |
| **`S-ATE-02`** | Rótulos de histórico de atendimento aleatórios | Risco de gerar insights falsos na camada analítica | Supressão do histórico sintético e preservação de métricas agregadas sólidas em `fact_atendimentos` |
