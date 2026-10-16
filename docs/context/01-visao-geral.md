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
