# Plano de Solução: V-Energy Grid 360

---

# 01 - Visão Geral e Arquitetura do V-Energy Grid 360

## 1. Objetivo e Requisitos Atendidos
Este documento detalha a solução para a plataforma de visibilidade 360 da V-Energy, integrando engenharia de dados, interface web e inteligência artificial para responder a perguntas críticas de negócio, especificamente a variação de receita.

**Requisitos Atendidos:**
- Cobertura integral de REQ-DATA-01 a REQ-DIAG-03 via orquestração dos módulos.
- Alinhamento com a stack obrigatória: Databricks/PySpark, React/TS, FastAPI e Gemini 3.1.

## 2. Decisões de Projeto
- **Arquitetura Medalhão:** Adotada para garantir rastreabilidade (Bronze) e qualidade (Silver) antes da agregação (Gold).
- **Banco Local (PostgreSQL):** Escolhido para garantir performance em consultas complexas do Portal e do Agente de IA, desacoplando a entrega do ambiente Databricks.
- **Orquestração via Workflow:** Garante que a atualização dos dados seja reprodutível e agendável.
- **Agente Text-to-SQL com Schema Linking:** Decisão para eliminar alucinações, forçando a IA a mapear a pergunta do usuário para a estrutura real da Gold.

## 3. Detalhamento Técnico (Arquitetura Geral)
O fluxo de dados segue a sequência:
`Fontes Brutas` -> `Databricks (Bronze -> Silver -> Gold)` -> `Export CSV` -> `PostgreSQL` -> `FastAPI` -> `React Frontend / IA Agent`.

## 4. Interfaces
A integração é regida pelos Contratos de Interface em `coordenacao/contratos-de-interface.md`.

## 5. Riscos e Mitigação
- **Risco:** Inconsistência entre a modelagem Gold e as perguntas do Diretor Comercial.
- **Mitigação:** Validação iterativa entre o Agente Dados e o Agente Diagnóstico.
- **Risco:** Alucinações da IA em perguntas complexas.
- **Mitigação:** Implementação de trilha de auditoria e resposta "Não sei" obrigatória.

## 6. Premissas
- [PREMISSA] O volume de dados (2.1mi de leituras) é suportado por instâncias padrão de Databricks e PostgreSQL.
- [PREMISSA] A conectividade entre o backend FastAPI e o banco local é estável.

---

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
    -
act_leituras: Consumo mensal consolidado.
    -
act_faturamento: Valores, bandeiras tarifárias e status de pagamento.
    -
act_ocorrencias: Eventos de interrupção vinculados a UC e Alimentador.
    -
act_atendimentos: Histórico de chamados e notas técnicas.
- **Requisito Atendido:** REQ-DATA-04.

---

## 5. Cálculo de Indicadores ANEEL (DEC e FEC)
O cálculo será realizado na camada Gold, agregando dados de
act_ocorrencias e dim_unidade_consumidora.

### Fórmulas:
- **Fórmulas:**

- **DEC (Duração Equivalente de Interrupção por Consumidor):**
    
    $$  
    \mathrm{DEC} = \frac{\sum (\text{Duração da Interrupção} \times \text{Consumidores Afetados})}{\text{Total de Consumidores}}  
    $$
    
- **FEC (Frequência Equivalente de Interrupção por Consumidor):**
    
    $$  
    \mathrm{FEC} = \frac{\sum (\text{Número de Interrupções} \times \text{Consumidores Afetados})}{\text{Total de Consumidores}}  
    $$
    

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

---

# Módulo 2: Portal Web - V-Energy Grid 360

## 1. Objetivo e Requisitos Atendidos
O objetivo deste módulo é transformar os dados consolidados na camada Gold em ferramentas acionáveis para as lideranças da V-Energy, fornecendo visões analíticas para a diretoria, operacionais para o atendimento e táticas para a gestão de perdas e operação.

**Requisitos Atendidos:**
- **Obrigatórios:** REQ-PORTAL-01, REQ-PORTAL-02, REQ-PORTAL-03, REQ-PORTAL-04, REQ-PORTAL-05, REQ-PORTAL-06, REQ-PORTAL-07.
- **Diferenciais:** REQ-PORTAL-08, REQ-PORTAL-09, REQ-PORTAL-10, REQ-PORTAL-11.

---

## 2. Decisões de Projeto

### 2.1 Stack Tecnológica
- **Frontend:** React + TypeScript + Vite.
  - *Por que:* Padrão de mercado para SPAs rápidas, tipagem forte com TS para evitar erros de interface e Vite para desenvolvimento ágil.
- **Backend:** FastAPI (Python).
  - *Por que:* Performance superior ao Flask/Django para APIs assíncronas, documentação automática via Swagger e integração nativa com as bibliotecas de IA (PydanticAI/LangChain) que serão usadas no Módulo 3.
- **Banco de Dados Local:** PostgreSQL.
  - *Por que:* Embora o SQLite seja sugerido, o PostgreSQL é preferível para suportar concorrência de múltiplos usuários (atendentes, gerentes, diretores) e oferece melhor suporte a consultas complexas de agregação necessárias para a análise de receita.
- **Trade-off:** A escolha do PostgreSQL aumenta levemente a complexidade de infraestrutura em relação ao SQLite, mas garante escalabilidade mínima para um ambiente corporativo.

### 2.2 Modelo de Navegação e Personas
O portal será organizado por módulos de acesso baseados no perfil do usuário (REQ-PORTAL-10), garantindo que cada persona veja apenas o que é relevante para sua função:
- **Diretoria:** Foco em indicadores macro e análise de receita.
- **Comercial/Atendimento:** Foco na Visão 360 da UC para suporte ao cliente.
- **Perdas:** Foco na Fila de Inspeção e gestão de ordens de campo.
- **Operação:** Foco em indicadores de continuidade (DEC/FEC) por alimentador.

---

## 3. Detalhamento Técnico

### 3.1 Modelo do Banco de Dados Local
O banco consumirá as tabelas Gold exportadas. Além das tabelas de leitura, será implementado um esquema de **Escrita** para a gestão de inspeções.

**Tabelas de Leitura (Gold):**
- `dim_unidade_consumidora`, `fact_leituras`, `fact_faturamento`, `fact_ocorrencias`, `fact_atendimentos`, `dim_alimentadores`.

**Tabelas de Gestão (Operacionais):**
- `inspecoes`:
    - `id` (PK), `uc_id` (FK), `data_geracao`, `status` (Pendente, Em Campo, Concluída, Cancelada), `motivo_suspeita`, `energia_estimada_recuperar`, `resultado_campo` (texto), `data_conclusao`, `tecnico_responsavel`.

### 3.2 Endpoints FastAPI (Principais)
- **Indicadores:**
    - `GET /metrics/general`: Retorna KPIs macro para a diretoria.
    - `GET /metrics/revenue-variance`: Retorna a decomposição preço x volume filtrada por mun/bairro/classe.
- **Visão 360:**
    - `GET /uc/{uc_id}/360`: Agrega dados de todas as tabelas Gold para uma única UC.
- **Gestão de Perdas:**
    - `GET /inspections/queue`: Retorna a fila de suspeitas ordenada por prioridade (Energia a recuperar $\times$ Probabilidade).
    - `POST /inspections/order`: Gera uma nova ordem de inspeção.
    - `PATCH /inspections/{id}`: Atualiza status ou registra resultado de campo.
    - `DELETE /inspections/{id}`: Cancela a ordem.
- **Operação:**
    - `GET /network/continuity`: Retorna DEC/FEC por alimentador e período.

### 3.3 Mapa de Telas e Visualizações

| Tela | Persona | Funcionalidade Principal | Visualizações Sugeridas |
|---|---|---|---|
| **Dashboard Executivo** | Diretoria | Monitoramento de Receita e Volume | Gráficos de cascata (Waterfall) para variação de receita; Mapas de calor por município. |
| **Análise de Receita** | Dir. Comercial | Decomposição Preço x Volume | Tabelas comparativas; Gráficos de barras empilhadas por classe de consumo. |
| **Visão 360 UC** | Atendimento | Suporte ao Cliente / Contestação | Timeline de consumo vs. ano anterior; Cards com status de medidor e GD; Lista de chamados recentes. |
| **Fila de Inspeção** | Ger. Perdas | Priorização de Campo | Tabela ordenada por "Energia Recuperável"; Filtros por bairro/alimentador; Botão "Gerar Ordem". |
| **Gestão de Ordens** | Ger. Perdas | Registro de Resultados | Formulário de atualização de status; Upload de planilha (Diferencial). |
| **Painel de Rede** | Ger. Operação | Monitoramento DEC/FEC | Gráficos de linha temporais por alimentador; Ranking dos "Top 10 Piores" alimentadores. |

### 3.4 Fluxo de Ordens de Inspeção
1. **Identificação:** O sistema identifica UCs suspeitas (via Gold) $\rightarrow$ Alimenta a **Fila de Inspeção**.
2. **Priorização:** O Gerente de Perdas filtra a fila $\rightarrow$ Seleciona UCs $\rightarrow$ Clica em **"Gerar Ordem"**.
3. **Execução:** A ordem é enviada ao campo (via exportação CSV - Diferencial).
4. **Retorno:** O resultado é registrado no portal $\rightarrow$ Status muda para **"Concluída"** $\rightarrow$ Dados alimentam a base de conhecimento de perdas.

---

## 4. Interfaces com outros Módulos
- **Dados $\rightarrow$ Portal:** Dependência total do formato das tabelas Gold e do processo de exportação CSV $\rightarrow$ Carga no banco local.
- **Portal $\rightarrow$ IA:** O portal consumirá o endpoint `/ai/ask` para o chat e integrará boxes de insights (ex: "A UC X apresenta consumo 40% acima da média do bairro") nas telas de Visão 360 e Análise de Receita.
- **Diagnóstico $\rightarrow$ Portal:** As fórmulas de decomposição de receita validadas pelo Agente Diagnóstico serão implementadas nas queries do backend para alimentar o Dashboard Executivo.

---

## 5. Riscos e Mitigação
- **Risco:** Lentidão no carregamento da Visão 360 devido ao volume de dados (2.1mi registros).
  - **Mitigação:** Implementação de indexação nas chaves estrangeiras (`uc_id`) no PostgreSQL e paginação nos endpoints de histórico.
- **Risco:** Inconsistência entre a análise do Diagnóstico e a visualização no Portal.
  - **Mitigação:** Revisão cruzada rigorosa (Fase 3) entre Agente Portal e Agente Diagnóstico para alinhar fórmulas.

---

## 6. Premissas
- **[PREMISSA]** O banco local será atualizado mensalmente via script de carga dos CSVs exportados do Databricks.
- **[PREMISSA]** A priorização da fila de inspeção será baseada em um cálculo simples: $\text{Energia Estimada} \times \text{Score de Suspeita}$.

---

## 7. Pendências (Dados Reais)
- Definir a métrica exata de "unidade suspeita" após análise dos dados de medição vs. faturamento.
- Validar a granularidade dos dados de bairro para a implementação dos mapas de calor.

---

# Módulo 3: Inteligência Artificial

## 1. Objetivo e Requisitos Atendidos
O objetivo deste módulo é democratizar o acesso aos dados da V-Energy, permitindo que usuários não técnicos obtenham respostas precisas e fundamentadas através de linguagem natural, além de prover insights proativos integrados à interface do portal.

**Requisitos Atendidos:**
- **REQ-AI-01:** Agente Text-to-SQL para perguntas em português.
- **REQ-AI-02:** Tratamento de termos do dia a dia (ex: "conta de luz").
- **REQ-AI-03:** Trilha de auditoria das respostas.
- **REQ-AI-04:** Insights de IA integrados nas telas do portal.
- **REQ-AI-05:** Acesso ao agente diretamente no portal.
- **REQ-AI-06:** Segurança: somente leitura e proteção contra prompt injection.
- **REQ-AI-07 (Diferencial):** Capacidade de follow-up (contexto).
- **REQ-AI-08 (Diferencial):** Avaliação automatizada da qualidade.

---

## 2. Decisões de Projeto

### 2.1 Framework de Agentes e Modelo
**Decisão:** Utilização do framework **PydanticAI** com o modelo **Gemini 3.1 Flash-Lite**.
- **Por quê:** O PydanticAI oferece tipagem forte e validação de esquemas, essencial para garantir que a saída do agente (especialmente o SQL gerado) seja estruturada. O Gemini 3.1 Flash-Lite é recomendado no enunciado por sua eficiência em custo/performance e baixa latência para respostas em tempo real.
- **Alternativas:** LangChain/LangGraph. Foram descartados para evitar a complexidade excessiva de "boilerplate" em um MVP, preferindo-se a simplicidade e a integração nativa de validação do PydanticAI.
- **Trade-off:** Menor ecossistema de plugins que o LangChain, mas maior controle sobre a estrutura dos dados.

### 2.2 Arquitetura Text-to-SQL
**Decisão:** Implementação de um pipeline de três etapas: **Schema Linking $\rightarrow$ SQL Generation $\rightarrow$ Execution & Refinement**.
- **Por quê:** Para evitar alucinações, o agente não gera o SQL "no escuro". Ele primeiro identifica quais tabelas e colunas da camada Gold são relevantes (Schema Linking), gera o SQL baseado nesse subconjunto e, se a execução falhar, usa o erro do banco para refinar a query automaticamente.
- **Garantia de Honestidade:** Se o Schema Linking não encontrar colunas relacionadas à pergunta, ou se o refinamento falhar após 3 tentativas, o agente responderá obrigatoriamente: *"Sinto muito, mas não encontrei informações nos dados para responder a essa pergunta."* [ENUNCIADO].

### 2.3 Glossário e Semântica (Mapeamento de Termos)
**Decisão:** Implementação de uma camada de **Semantic Mapping** via System Prompt e Dicionário de Sinônimos.
- **Por quê:** Usuários usam "conta de luz" para `fact_faturamento` ou "falta de luz" para `fact_ocorrencias`.
- **Abordagem:** Um dicionário de mapeamento será injetado no contexto do agente, instruindo-o a traduzir termos coloquiais para a terminologia técnica da camada Gold antes da geração do SQL.

### 2.4 Segurança e Defesa
**Decisão:** Camada de **SQL Sanitization** e **Restrição de Privilégios no Banco**.
- **Por quê:** Impedir que o agente execute comandos de escrita (`UPDATE`, `DELETE`, `DROP`) ou acesse tabelas sensíveis.
- **Implementação:**
    1. **Nível de Banco:** O usuário de banco utilizado pela IA terá permissão estrita de `SELECT` nas tabelas Gold.
    2. **Nível de Aplicação:** Um parser de SQL validará a query antes da execução, bloqueando qualquer palavra-chave que não seja de leitura.
    3. **Prompt Injection:** Uso de *few-shot prompting* com exemplos de tentativas de ataque e instruções explícitas para ignorar comandos que tentem alterar a persona ou as regras do agente.

---

## 3. Detalhamento Técnico

### 3.1 Fluxo de Funcionamento do Agente
1. **Entrada:** Usuário envia pergunta via endpoint `/ai/ask` (FastAPI).
2. **Contextualização:** O agente recupera o histórico da conversa (para REQ-AI-07) e o esquema das tabelas Gold.
3. **Schema Linking:** O LLM seleciona as tabelas e colunas necessárias.
4. **Geração de SQL:** O LLM escreve a query SQL em conformidade com o banco local (SQLite/PostgreSQL).
5. **Execução:** O FastAPI executa a query no banco local.
6. **Síntese:** O LLM transforma o resultado tabular em uma resposta textual natural e clara.
7. **Auditoria:** O sistema salva em `fact_ai_audit` a pergunta, o SQL gerado, o resultado e o tempo de resposta (REQ-AI-03).

### 3.2 Insights Proativos na UI
**Implementação:** "IA Copilot" integrado nas telas de Visão 360 e Diagnóstico.
- **Mecanismo:** Ao carregar a tela de uma UC, o backend dispara prompts assíncronos para o agente analisar os dados daquela UC específica (ex: "Analise o consumo desta UC nos últimos 6 meses e identifique anomalias").
- **Fidelidade aos Dados:** O insight deve obrigatoriamente citar o valor numérico e a tabela de origem (ex: *"Notei que o consumo subiu 20% em Março [fact_leituras], o que diverge do padrão da classe residencial"*), permitindo a validação humana.

### 3.3 Avaliação Automatizada (Diferencial)
**Implementação:** Criação de um "Golden Dataset" de pares Pergunta $\rightarrow$ SQL Esperado.
- **Métrica:** O sistema executa as perguntas do dataset, compara o resultado da IA com o resultado do SQL esperado e calcula a precisão (Exact Match ou Semantic Similarity).

---

## 4. Interfaces
- **Dados $\rightarrow$ IA:** Consumo das tabelas Gold (`dim_unidade_consumidora`, `fact_leituras`, etc.) via conexão read-only.
- **Portal $\rightarrow$ IA:**
    - Requisições via endpoint `/ai/ask` (JSON: `{ "user_id": str, "message": str }`).
    - Retorno via JSON: `{ "answer": str, "sql": str, "audit_id": str }`.

---

## 5. Riscos e Mitigação
| Risco | Impacto | Mitigação |
|---|---|---|
| Alucinação de SQL (Query inválida) | Médio | Loop de refinamento baseado em erro de execução e Schema Linking rígido. |
| Resposta imprecisa por ambiguidade | Alto | Instruir o agente a pedir clarificação ao usuário se a pergunta for ambígua. |
| Prompt Injection para extração de dados | Alto | Usuário de banco com permissões mínimas e sanitização de queries. |
| Latência alta na resposta | Baixo | Uso do Gemini 3.1 Flash-Lite e cache de queries comuns. |

---

## 6. Premissas
- [PREMISSA] O banco de dados local será SQLite ou PostgreSQL, suportando SQL padrão.
- [PREMISSA] As tabelas Gold terão nomes consistentes em `snake_case` conforme acordado no contrato de interface.
- [PREMISSA] O usuário final terá acesso ao portal via autenticação, permitindo rastrear quem fez a pergunta para a auditoria.

---

## 7. Pendências (Dados Reais)
- Validar a complexidade das queries necessárias para o diagnóstico de receita para ajustar o prompt de Schema Linking.
- Analisar a frequência de termos coloquiais nos chamados do call center (`atendimentos.json`) para expandir o glossário de mapeamento semântico.

---

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

---

# 7. Plano de Execução e Cronograma

 la data final é 04/11. A apresentação prévia ocorre em 05/11 e a banca final em 10/11. O cronograma prevê: Sprints de engenharia de dados -> Desenvolvimento de API/Portal -> Integração de IA -> Validação do Diagnóstico.

---

# 8. Roteiro da Apresentação e Perguntas Prováveis

Estrutura de 15 min: Visão Geral (2min) -> Demo Portal/IA (5min) -> Diagnóstico de Receita (5min) -> Conclusão (3min). Perguntas esperadas: 'Como a IA garante a honestidade?' 'Qual a maior causa da queda de volume?'

---

# 9. Premissas, Riscos e Mitigação

Consultar premissas.md e riscos detalhados em cada seção. Risco principal: Qualidade dos dados brutos impactando a precisão do diagnóstico.

---

# 10. Estrutura do README e do Repositório

Estrutura proposta: /data-engineering, /backend, /frontend, /ai-agent, /docs. README conterá guia de setup e print do Workflow Databricks.

---

# 11. Pendências que dependem dos dados reais

1. Validação exata da decomposição de preço x volume.
2. Identificação de anomalias específicas nas 8 fontes de dados.
3. Ajuste fino do glossário de IA com base nos termos reais dos chamados.
