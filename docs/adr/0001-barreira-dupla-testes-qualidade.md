# 0001. Barreira Dupla de Testes de Qualidade Automatizados no Pipeline

## Contexto e Decisão
Para atender ao requisito diferencial de Engenharia de Dados (*"testes de qualidade automatizados no pipeline, para que uma falha nos dados seja detectada antes de chegar ao portal"*), adotamos uma arquitetura de **Barreira Dupla (*Two-Gate Quality System*)**:
1. **Gate 1 (Databricks Workflow / Upstream)**: Uma etapa dedicada e bloqueante (`05_gold_qualidade_testes.py`) executada após o cálculo das tabelas Gold e antes do notebook de exportação (`06_export_csv.py`). Se qualquer asserção crítica falhar, o Workflow é abortado (`AssertionError`), impedindo a geração dos CSVs de saída.
2. **Gate 2 (Ingestão Local / Downstream)**: Uma validação transacional automatizada executada pelo script de carga (`scripts/carga_banco_local.py`) antes do `COMMIT` no PostgreSQL ou SQLite local. Se os arquivos CSV ou os dados inseridos violarem os contratos de integridade, a transação sofre `ROLLBACK` e o banco que alimenta o backend FastAPI do Portal permanece intocado.

Optamos por essa abordagem nativa em PySpark e Python/SQL para garantir o desacoplamento do Databricks previsto no case, sem introduzir dependências ou custos de ferramentas pesadas de terceiros (ex.: Great Expectations ou Soda Core).

## Opções Consideradas
- **Apenas no Databricks**: Deixaria vulnerável o ambiente de desenvolvimento local caso novos CSVs manuais, parciais ou corrompidos fossem fornecidos sem reexecutar todo o cluster.
- **Apenas no Banco Local**: Permitiria a geração e exportação de CSVs inválidos na nuvem, desperdiçando tempo de computação e gerando artefatos inconsistentes no volume do Unity Catalog.
- **Uso de Frameworks Externos (Great Expectations / Soda Core)**: Adicionaria dependências complexas no ambiente serverless do Databricks e exigiria configurações adicionais no ambiente dos desenvolvedores web.

## Consequências
- A exportação CSV e a ingestão local tornam-se operações estritamente dependentes da aprovação em 100% dos testes críticos.
- O grafo de execução do Databricks Workflow ganha uma tarefa explícita de testes de qualidade, auditável no histórico de execuções.
- O banco local que abastece o Portal Web e o Agente de IA tem garantia formal contra dados órfãos, nulos indevidos e anomalias contábeis.
