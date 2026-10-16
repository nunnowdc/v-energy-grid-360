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
