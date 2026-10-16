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
