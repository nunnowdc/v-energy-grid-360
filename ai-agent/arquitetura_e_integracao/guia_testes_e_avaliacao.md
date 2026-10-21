# Guia de Integração: Agentes & Testes e Avaliação Automatizada

Este guia orienta o responsável pela frente de **TESTES** a rodar avaliações de acurácia, golden datasets e testes de CI contra o módulo de Agentes sem dependência de interface gráfica ou servidor web.

---

## 1. Ponto de Entrada para Automação de Testes

O módulo de agentes expõe uma função pura em `ai-agent/src/grafo/executor_agente.py`:

```python
from ai_agent.src.grafo.executor_agente import executar_agente
from ai_agent.src.contratos.resposta_agente import RespostaAgente

resultado: RespostaAgente = executar_agente(
    pergunta="Qual foi o consumo total do bairro Boa Viagem em 2024?",
    historico=None,             # Ou lista de turnos anteriores: [{"role": "user", "content": "..."}, ...]
    sessao_id="sessao-teste-01" # Identificador opcional para isolar o checkpointer
)
```

---

## 2. Contrato de Saída (`RespostaAgente`)

O retorno da função é um schema Pydantic estruturado com todas as métricas analíticas e de auditoria:

```python
class RespostaAgente(BaseModel):
    audit_id: str                      # UUID único da execução (registrado em tb_auditoria_agente)
    pergunta_original: str             # Pergunta enviada
    pergunta_autonoma: str             # Pergunta após desambiguação de follow-up
    resposta_texto: str                # Texto final apresentado ao usuário
    sql_gerado: Optional[str]          # Query SQL final executada (ou None se rota for RAG/recusa)
    dados_tabela: Optional[list[dict]] # Registros retornados pelo banco
    selo_confianca: str                # "certificada" | "gerada_confiavel" | "documental_rag" | "recusa_honesta" | "erro_bloqueado"
    fontes_citadas: list[str]          # Fontes do RAG utilizadas (ex.: ["PRODIST Módulo 8 / ANEEL"])
    passos_executados: list[str]       # Trilha cronológica dos nós percorridos no LangGraph
    hit_cache: bool                    # True se a resposta foi resolvida pelo cache
    tempo_execucao_ms: float           # Latência ponta a ponta em milissegundos
    tokens_totais: int                 # Consumo de tokens (prompt + completion)
    chamadas_llm: int                  # Quantidade de chamadas a provedores de LLM
```

---

## 3. Estrutura Recomendada para o Golden Set

O time de testes deve versionar o arquivo de avaliação em `ai-agent/testes/golden_set/golden_dataset.json`.  
**Atenção à regra de sigilo:** Conforme as diretrizes do case, o golden set deve guardar a pergunta, a rota e o SQL de referência, **nunca números confidenciais de faturamento ou clientes**.

```json
[
  {
    "id": "TC-001",
    "pergunta": "Qual o faturamento total da classe comercial em Olinda no ano de 2023?",
    "rota_esperada": "sql",
    "sql_esperado": "SELECT SUM(f.receita_faturada) FROM fact_faturamento f JOIN dim_unidade_consumidora u ON f.uc_id = u.uc_id WHERE u.classe = 'Comercial' AND u.municipio = 'Olinda' AND f.ano = 2023;",
    "colunas_obrigatorias": ["receita_faturada"],
    "deve_recusar": false
  },
  {
    "id": "TC-002",
    "pergunta": "Como a ANEEL define o indicador DEC?",
    "rota_esperada": "rag",
    "sql_esperado": null,
    "termos_obrigatorios_resposta": ["Duração Equivalente", "interrupção", "PRODIST"],
    "deve_recusar": false
  },
  {
    "id": "TC-003",
    "pergunta": "Qual a receita dos clientes da Enel em São Paulo?",
    "rota_esperada": "recusa",
    "sql_esperado": null,
    "deve_recusar": true
  }
]
```

---

## 4. Métricas de Avaliação Automatizada (Diferencial REQ-AI-08)

Para medir a evolução do agente na esteira de CI, sugerimos 4 métricas calculadas pelo script de testes:
1. **Taxa de Execução Válida (Execution Rate):** % de perguntas do tipo SQL que geraram queries válidas e executáveis sem erro no banco.
2. **Similaridade Semântica de Query (Component Match):** Validação via AST se a query do agente filtrou as tabelas e colunas corretas em relação ao `sql_esperado`.
3. **Taxa de Abstenção Correta (Honesty Accuracy):** % de perguntas fora de escopo ou maliciosas que foram adequadamente recusadas pelo Nó 10.
4. **Eficiência de FinOps (Tokens / Pergunta):** Média de tokens gastos por interação (meta: < 1.800 tokens em média).
