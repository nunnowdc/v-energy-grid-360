# Guia de Integração: Agentes, Engenharia de Dados & Portal Web

Este guia estabelece os contratos entre o módulo de **AGENTES**, a camada de **ENGENHARIA DE DADOS** (tabelas Gold) e o **PORTAL WEB** (backend FastAPI e frontend React).

---

## 1. Contrato com Engenharia de Dados (Camada Gold)

O agente de Text-to-SQL e o RAG esperam que a camada Gold seja disponibilizada no PostgreSQL sob o schema `public` com as seguintes convenções mínimas:

### Tabelas Gold e granularidade

O agente usa o dicionário oficial `data-engineering/relatorio_tabelas/dicionario_dados_gold.md`.
As tabelas de consulta mais importantes são:

- **Dimensões:** `dim_unidade_consumidora`, `dim_alimentador`, `dim_competencia`,
  `dim_geracao_distribuida` e `dim_medidor`.
- **Fatos:** `fact_faturamento`, `fact_leituras`, `fact_ocorrencias`,
  `fact_atendimentos` e `fact_inspecoes`.
- **Agregações:** `agg_receita_mensal`, `agg_receita_preco_volume`,
  `agg_continuidade_alimentador` e `agg_continuidade_alimentador_anual`.
- **Prioridade de perdas:** `fila_inspecao`.

Nomes canônicos relevantes:

- A chave da UC é `id_uc`, não `uc_id`.
- O alimentador é `alimentador`, não `alimentador_id`.
- O consumo analítico é `consumo_kwh`, não `volume_faturado_kwh` ou `consumo_medido_kwh`.
- O status de atendimento é `status_chamado`; ocorrências usam `causa`, `duracao_h`
  e `data_abertura`/`data_encerramento`.

---

## 2. Tabelas de Controle dos Agentes no PostgreSQL

O módulo de IA criará e gerenciará as seguintes tabelas operacionais:

```sql
-- Extensão para o RAG
CREATE EXTENSION IF NOT EXISTS vector;

-- Base vetorial de regras, glossário e esquemas
CREATE TABLE IF NOT EXISTS tb_conhecimento_vetorial (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    categoria VARCHAR(50) NOT NULL, -- 'glossario', 'esquema', 'prodist', 'templates'
    titulo VARCHAR(255) NOT NULL,
    conteudo TEXT NOT NULL,
    fonte VARCHAR(100),
    metadados JSONB,
    embedding vector(384) -- Dimensão conforme modelo de embedding multilíngue
);

-- Tabela de Auditoria ponta a ponta
CREATE TABLE IF NOT EXISTS tb_auditoria_agente (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sessao_id VARCHAR(100) NOT NULL,
    data_hora TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    pergunta_original TEXT NOT NULL,
    pergunta_autonoma TEXT,
    rota_escolhida VARCHAR(50) NOT NULL,
    hit_cache BOOLEAN DEFAULT FALSE,
    sql_gerado TEXT,
    linhas_retornadas INT,
    amostra_resultado_json JSONB,
    selo_confianca VARCHAR(50) NOT NULL,
    passos_execucao JSONB,
    tempo_execucao_ms FLOAT NOT NULL,
    tokens_prompt INT,
    tokens_resposta INT,
    erro_mensagem TEXT,
    feedback_usuario SMALLINT -- null, 1 (útil), -1 (inútil)
);

-- Cache de Insights rápidos para as telas do portal
CREATE TABLE IF NOT EXISTS tb_insights_tela (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tela VARCHAR(50) NOT NULL, -- 'visao_360_uc', 'diagnostico_receita'
    entidade_id VARCHAR(100) NOT NULL, -- ex: id_uc '45892' ou 'global'
    fatos_calculados_json JSONB NOT NULL,
    texto_insight TEXT NOT NULL,
    selo_validacao VARCHAR(50) NOT NULL, -- 'auditado_llm', 'template_fallback'
    gerado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

---

## 3. Endpoints da API (Backend FastAPI $\rightarrow$ Frontend React)

O módulo de IA integra-se ao FastAPI através do roteador `ai_router` montado em `/ai`:

### 3.1 Conversação (`POST /ai/ask`)
- **Quem pergunta:** vem da sessão de login, não do corpo. O backend confere o cookie e o perfil e guarda a conta em `request.state.usuario`; o `ai_router` grava o `id` e o `perfil` dela na auditoria (`user_id` é UUID com chave estrangeira para `usuarios`). Um `user_id` enviado no corpo é ignorado.
- **Request Body:**
  ```json
  {
    "session_id": "c7a8b9f0-1234-5678-9abc-def012345678",
    "message": "Qual o faturamento de Olinda em 2024?",
    "context": {
      "page": "diagnostico_receita",
      "current_uc_id": null
    }
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "answer": "O faturamento total de Olinda em 2024 foi de R$ 42.150.800,00.",
    "sql": "SELECT SUM(r.receita_faturada) FROM agg_receita_mensal r WHERE r.municipio = 'Olinda' AND r.ano = 2024;",
    "audit_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "selo_confianca": "certificada",
    "fontes": [],
    "tempo_ms": 42.5
  }
  ```

### 3.2 Insights Proativos de Tela (`GET /ai/insights/{tela}/{entidade_id}`)
- **Exemplo:** `GET /ai/insights/visao_360_uc/45892`
- **Response (200 OK):**
  ```json
  {
    "tela": "visao_360_uc",
    "entidade_id": "45892",
    "insight_texto": "Esta UC apresentou aumento de 22,6% no consumo em relação ao mês anterior (380 kWh vs 310 kWh). Há 1 fatura pendente de R$ 412,50.",
    "metricas_destaque": {
      "variacao_pct": 22.58,
      "consumo_atual_kwh": 380,
      "faturas_aberto": 1
    },
    "selo": "auditado_llm",
    "tempo_ms": 14.2
  }
  ```

### 3.3 Trilha de Auditoria Transparente (`GET /ai/audit/{audit_id}`)
- Permite abrir a gaveta *"Como a IA chegou nisso?"* no portal React para ver os passos executados, a query gerada e o tempo em milissegundos.

### 3.4 Feedback do Usuário (`POST /ai/feedback`)
- Permite ao analista marcar 👍 ou 👎 na resposta, alimentando o índice de acurácia da avaliação automatizada (REQ-AI-08).
