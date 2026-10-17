# Revisão Cruzada: Seção 06 (Diagnóstico)

## 1. Análise de Acessibilidade via Agente SQL
O objetivo desta revisão é garantir que as necessidades analíticas do Agente Diagnóstico sejam atendidas pela arquitetura de IA proposta na Seção 05.

**Veredito:** ✅ **Acessível / Compatível**

**Análise Detalhada:**
- **Métricas de Decomposição:** O Agente Diagnóstico exige preço médio, volume total, mix de classe e impacto de bandeira/GD. Todas essas métricas derivam de agregações (`SUM`, `AVG`) e filtros nas tabelas `fact_faturamento`, `fact_leituras` e `dim_unidade_consumidora`. Como o Agente IA terá acesso read-only a toda a camada Gold, ele consegue extrair esses dados via SQL sem a necessidade de funções complexas de banco de dados.
- **Eixos de Análise:** A necessidade de cortes por município, bairro e classe é totalmente suportada, pois essas dimensões estão presentes na `dim_unidade_consumidora` e são chaves de junção simples.
- **Validação de Hipóteses:** As hipóteses de GD e Perdas dependem de junções com tabelas de cadastro e medição. A arquitetura de *Schema Linking* da IA permite que o agente identifique essas relações para responder a perguntas como *"Qual a correlação entre a queda de volume e a instalação de painéis solares em Olinda?"*.

---

## 2. Validação da Trilha de Auditoria
O Agente Diagnóstico requer que as conclusões sejam sustentadas por dados e reprodutíveis.

**Veredito:** ✅ **Suficiente**

**Análise Detalhada:**
- A trilha de auditoria implementada na Seção 05 (`fact_ai_audit`) registra a **pergunta**, o **SQL gerado** e o **resultado tabular**.
- Isso permite que qualquer conclusão gerada pela IA no portal (ex: "O bairro X perdeu mais volume") seja validada pelo Agente Diagnóstico através da re-execução do SQL auditado, garantindo que a "ponte executiva" do relatório final não contenha alucinações.

---

## 3. Riscos Identificados e Recomendações

| Risco | Impacto | Recomendação |
|---|---|---|
| **Ambiguidade em 'Preço Médio'** | Médio | O Agente Diagnóstico define preço médio como `Receita / Volume`. Devemos garantir que o glossário da IA (Seção 5.3) use a mesma fórmula para evitar que a IA responda com "tarifa nominal" quando o usuário perguntar por "preço médio". |
| **Complexidade da Decomposição Shapley** | Baixo | A decomposição de Shapley envolve cálculos algébricos que podem ser complexos para o LLM gerar em SQL puro. **Sugestão:** O Agente Diagnóstico deve fornecer as fórmulas exatas no dicionário de dados para que a IA as utilize como *templates* de query. |
| **Consistência de Períodos** | Médio | O Diagnóstico usa "períodos equivalentes" (ex: jan-dez vs jan-dez). A IA deve ser instruída via system prompt a sempre perguntar ou assumir a mesma lógica de janelas temporais para manter a consistência com o relatório oficial. |

---

## 4. Conclusão
A seção de Diagnóstico está tecnicamente alinhada com a de IA. Não há bloqueios arquiteturais. A principal dependência agora é a definição final do dicionário de dados da camada Gold (Engenharia de Dados) para que o *Schema Linking* da IA e as fórmulas do Diagnóstico falem a mesma língua.
