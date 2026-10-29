# Engenharia de Dados

Notebooks Databricks (formato `.py` com `# Databricks notebook source`) do pipeline Bronze → Silver → Gold.

## Estrutura

```
data-engineering/
├── 00_utils.py           # funções compartilhadas; fica na raiz porque as três camadas usam
├── input/                # entrada de dados novos via API do Databricks (Jobs)
├── bronze/               # 01: ingestão das fontes brutas
├── silver/               # 02: limpeza e regras por tabela
├── gold/                 # 04 e 05: modelo dimensional e tabelas analíticas; 05_gold_qualidade_testes: Quality Gate; 06: export CSV
└── relatorio_tabelas/    # perfis, decisões, dicionário da Gold, testes de qualidade e registro de problemas
```

O prefixo numérico indica a ordem de execução no Workflow:
`01` (Bronze) → `02_*` (Silver) → `04_*` (Gold Dimensões/Fatos) → `05_*` (Gold Especializadas) → `05_gold_qualidade_testes` (Quality Gate) → `06_export_csv`.

## Data Quality Gate (Barreira de Qualidade)

Antes da exportação das tabelas Gold em arquivos CSV (`06_export_csv`), o notebook `gold/05_gold_qualidade_testes.py` executa validações bloqueantes de contrato (integridade referencial, unicidade de PKs, consistência contábil e coerência temporal). Se qualquer teste crítico falhar, o Workflow do Databricks é interrompido com `AssertionError`, impedindo que dados inconsistentes cheguem ao Portal Web.

No ambiente local desacoplado, o mesmo contrato é validado automaticamente por `scripts/carga_banco_local.py` antes de efetivar o commit no PostgreSQL ou SQLite (ou via `scripts/test_data_quality.py`). Para detalhes, consulte o [relatorio_qualidade_dados.md](relatorio_tabelas/relatorio_qualidade_dados.md) e a [ADR 0001](../docs/adr/0001-barreira-dupla-testes-qualidade.md).

## Caminhos que dependem desta estrutura

Ao mover ou renomear um notebook, atualize:

| Quem aponta | Para onde | Observação |
|---|---|---|
| Notebooks de `bronze/`, `silver/` e `gold/` | `%run ../00_utils` | Caminho relativo à pasta do notebook |
| Tarefas do Databricks Workflow | Caminho de cada notebook no workspace | Configurado no Databricks, fora deste repositório |
| `ai-agent/src/rag/indexador_relatorios_eng_dados.py` | `data-engineering/relatorio_tabelas/` | Caminho fixo no código do RAG |
| Links em `relatorio_tabelas/*.md` | `../silver/...` e `../gold/...` | |
| Comentários em `frontend/src/config/motivos.ts` e `frontend/src/mocks/inspecoes.ts` | `gold/05_gold_perdas.py` | |
