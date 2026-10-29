# Engenharia de Dados

Notebooks Databricks (formato `.py` com `# Databricks notebook source`) do pipeline Bronze → Silver → Gold.

## Estrutura

```
data-engineering/
├── 00_utils.py           # funções compartilhadas; fica na raiz porque as três camadas usam
├── input/                # entrada de dados novos via API do Databricks (Jobs)
├── bronze/               # 01: ingestão das fontes brutas
├── silver/               # 02: limpeza e regras por tabela
├── gold/                 # 04 e 05: modelo dimensional e tabelas analíticas; 06: export CSV
└── relatorio_tabelas/    # perfis, decisões, dicionário da Gold e registro de problemas
```

O prefixo numérico indica a ordem de execução no Workflow: `01` → `02_*` → `04_*` → `05_*` → `06`.

## Caminhos que dependem desta estrutura

Ao mover ou renomear um notebook, atualize:

| Quem aponta | Para onde | Observação |
|---|---|---|
| Notebooks de `bronze/`, `silver/` e `gold/` | `%run ../00_utils` | Caminho relativo à pasta do notebook |
| Tarefas do Databricks Workflow | Caminho de cada notebook no workspace | Configurado no Databricks, fora deste repositório |
| `ai-agent/src/rag/indexador_relatorios_eng_dados.py` | `data-engineering/relatorio_tabelas/` | Caminho fixo no código do RAG |
| Links em `relatorio_tabelas/*.md` | `../silver/...` e `../gold/...` | |
| Comentários em `frontend/src/config/motivos.ts` e `frontend/src/mocks/inspecoes.ts` | `gold/05_gold_perdas.py` | |
