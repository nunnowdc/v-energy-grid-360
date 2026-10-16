# 03. Engenharia de Dados - V-Energy Grid 360

## 1. Visão Geral da Arquitetura
A solução de dados será implementada utilizando a **Arquitetura Medalhão (Medallion Architecture)** no Databricks, garantindo a evolução da qualidade do dado desde a ingestão bruta até a modelagem analítica.

### Fluxo de Dados:
**Bronze (Raw)** $\rightarrow$ **Silver (Trusted)** $\rightarrow$ **Gold (Refined)**

---

## 2. Camada Bronze (Ingestão)
**Objetivo:** Armazenar os dados em seu formato original (estágio de landing).
- **Processo:** Ingestão automatizada de arquivos (CSV/JSON/Parquet) via *Auto Loader* do Databricks.
- **Armazenamento:** Tabelas Delta com particionamento por data de ingestão (ingestion_date).
- **Regra:** Sem transformações. Preservação total da linhagem do dado bruto.
- **Requisito Atendido:** REQ-DATA-01.

---

## 3. Camada Silver (Tratamento e Qualidade)
**Objetivo:** Limpeza, padronização e garantia de integridade.
- **Tratamentos:**
    - **Limpeza:** Remoção de duplicatas e tratamento de valores nulos.
    - **Padronização:** Conversão de tipos (ex: datas, valores monetários) e normalização de strings (snake_case).
    - **Qualidade:** Implementação de *Expectations* (validações) para garantir que campos obrigatórios (UC, CPF/CNPJ) estejam presentes.
- **Integridade:** Aplicação de chaves de junção para garantir a integridade referencial entre as tabelas de medição, faturamento e cadastro.
- **Requisitos Atendidos:** REQ-DATA-02, REQ-DATA-03, REQ-DATA-09.

---

## 4. Camada Gold (Modelagem de Negócio)
**Objetivo:** Tabelas otimizadas para performance de leitura e resposta a perguntas de negócio.
- **Modelo:** *Star Schema* (Fatos e Dimensões).
- **Tabelas Implementadas (Conforme Contrato):**
    - dim_unidade_consumidora: Cadastro centralizado da UC.
    - dim_alimentadores: Atributos técnicos dos alimentadores da rede.
    - act_leituras: Consumo mensal consolidado.
    - act_faturamento: Valores, bandeiras tarifárias e status de pagamento.
    - act_ocorrencias: Eventos de interrupção vinculados a UC e Alimentador.
    - act_atendimentos: Histórico de chamados e notas técnicas.
- **Requisito Atendido:** REQ-DATA-04.

---

## 5. Cálculo de Indicadores ANEEL (DEC e FEC)
O cálculo será realizado na camada Gold, agregando dados de act_ocorrencias e dim_unidade_consumidora.

### Fórmulas:
- **DEC (Duração Equivalente de Interrupção por Consumidor):**
  \text{DEC} = \sum (\text{Duração da Interrupção} \times \text{Consumidores Afetados}) / \text{Total Consumidores}
- **FEC (Frequência Equivalente de Interrupção por Consumidor):**
  \text{FEC} = \sum (\text{Número de Interrupções} \times \text{Consumidores Afetados}) / \text{Total Consumidores}

**Granularidade:** Calculado por Alimentador e período mensal.
- **Requisito Atendido:** REQ-DATA-05.

---

## 6. Exportação e Entrega
Para atender à integração com o Portal e Agente de IA:
- **Destino:** Exportação das tabelas Gold para Banco de Dados Local/CSV.
- **Formato:** UTF-8, delimitador ;, nomes de colunas em snake_case sem acentos.
- **Requisito Atendido:** REQ-DATA-06.

---

## 7. Orquestração e Governança
- **Workflow:** Utilização do **Databricks Workflow** para encadear as tarefas (Bronze $\rightarrow$ Silver $\rightarrow$ Gold $\rightarrow$ Export).
- **Agendamento:** Execução diária (Incremental) com trigger de chegada de arquivos.
- **Dicionário de Dados:** Publicação de metadados da Gold (descrição de colunas, tipos e regras de cálculo) em documento anexo.
- **Requisitos Atendidos:** REQ-DATA-07, REQ-DATA-08.
