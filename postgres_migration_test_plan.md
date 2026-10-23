# Plano de Implementação: Refatoração da Suíte de Testes para PostgreSQL

**Projeto:** V-Energy Grid 360  
**Módulo:** `ai-agent/tests`  
**Alvo:** Substituição da infraestrutura de testes de SQLite para PostgreSQL  
**Status:** Planejamento Consolidado via Grilling (Aprovado em 4/4 decisões)

---

## 1. Visão Geral e Objetivos

Atualmente, a suíte de testes do `ai-agent` emprega SQLite sintético in-memory para validar consultas, limites e métricas analíticas. Embora rápido, o SQLite apresenta divergências sutis de dialeto em relação ao banco de produção (PostgreSQL), tais como sensibilidade a maiúsculas/minúsculas, funções de agregação, operadores de string (`ILIKE`), formatação de datas e dialeto de parsing no SQLGlot.

Esta refatoração tem como objetivo:
1. **Migrar a execução para PostgreSQL real**, conectando via `TEST_DATABASE_URL` ou `DATABASE_URL`.
2. **Garantir isolamento hermético** criando um schema temporário de teste (ex: `venergy_test_gold`) com DDL PostgreSQL nativo e dados sintéticos, com `DROP SCHEMA CASCADE` ao final.
3. **Manter fallback transparente para SQLite**: se nenhum PostgreSQL estiver ativo no ambiente local do desenvolvedor ou na esteira de CI, a suíte faz fallback gracioso para não interromper execuções locais rápidas.
4. **Padronizar o dialeto para `postgres`** no `SQLValidator` e no validador AST do `sqlglot` no runner de avaliação do Golden Dataset (`REQ-AI-08`).
5. **Prover infraestrutura local imediata** através de um `docker-compose.test.yml` e arquivo `.env.test.example`.

---

## 2. Decisões Arquiteturais Alinhadas

| Dimensão | Decisão Adotada | Justificativa |
|---|---|---|
| **Estratégia de Conexão** | Híbrida / Auto-detectável | Testa PostgreSQL se `TEST_DATABASE_URL` ou `DATABASE_URL` estiver disponível e acessível; se inacessível, ativa o fallback SQLite com aviso claro no log. |
| **Isolamento de Dados** | Schema exclusivo por execução, com prefixo `venergy_test_gold` | Permite rodar testes mesmo em um banco Postgres compartilhado sem colisão entre execuções; somente o schema criado pela execução atual é removido. |
| **Dialeto SQLGlot** | `read="postgres"`, `dialect="postgres"` | Alinha 100% dos testes e do validador de segurança com o dialeto real do PostgreSQL de produção. |
| **Provisionamento Local** | `ai-agent/docker-compose.test.yml` | Um container PostgreSQL 16 oficial, rápido de subir (`docker compose up -d`) e com portas mapeadas para teste. |

---

## 3. Modificações Propostas por Componente

### 3.1 Infraestrutura e Ergonomia (Docker & Env)

#### [NEW] `ai-agent/docker-compose.test.yml`
Container PostgreSQL 16 isolado para testes:
- Serviço: `postgres-test`
- Imagem: `postgres:16-alpine`
- Porta exposta: `5433:5432` (evita conflito caso o desenvolvedor já tenha um Postgres rodando na 5432 padrão)
- Banco padrão: `v_energy_test_db`
- Credenciais: `postgres` / `postgres`

#### [NEW] `ai-agent/.env.test.example`
Exemplo de configuração para execução dos testes com PostgreSQL:
```env
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5433/v_energy_test_db
TEST_POSTGRES_SCHEMA=venergy_test_gold
LLM_MOCK_MODE=true
```

---

### 3.2 Fixtures Globais e DDL (`ai-agent/tests/conftest.py`)

#### [MODIFY] `ai-agent/tests/conftest.py`
- **DDL Compatível com PostgreSQL e SQLite**:
  - `dim_unidade_consumidora`, `fact_faturamento`, `fact_ocorrencias` adaptadas para sintaxe universal suportada por ambos os motores.
- **Fixture `postgres_test_info`**:
  - Verifica disponibilidade de conexão com PostgreSQL via `TEST_DATABASE_URL` ou `DATABASE_URL`.
  - Se conectável:
    1. Cria um schema exclusivo com prefixo `venergy_test_gold`.
    2. Define `search_path` para o schema exclusivo criado na execução e `public`.
    3. Executa DDL das tabelas Gold e carrega dados sintéticos.
    4. Fornece a URL de conexão contextualizada para os testes.
    5. No teardown do pytest (fim da sessão de teste), executa `DROP SCHEMA <schema-criado-pela-execução> CASCADE;`
  - Se PostgreSQL estiver indisponível ou não configurado, registra um aviso e usa SQLite. Falhas na limpeza do schema são propagadas, não ocultadas.
  - Se a conexão inicial for estabelecida, falhas ao criar ou popular o schema interrompem os testes em vez de ativar fallback para SQLite.
- **Fixture `sql_executor_teste`**:
  - Retorna `SQLExecutor(db_url=postgres_url)` caso Postgres esteja ativo, ou `SQLExecutor(sqlite_path=...)` no modo fallback.
  - Injeta a flag informativa `executor.is_postgres` ou fixture `usando_postgres: bool`.
- **Fixture `validador_sql_padrao`**:
  - Atualizado para `SQLValidator(dialect="postgres")`.

---

### 3.3 Testes Unitários do SQLExecutor (`ai-agent/tests/test_sql_executor.py`)

#### [MODIFY] `ai-agent/tests/test_sql_executor.py`
- Adicionar teste unitário para validar a configuração do método `_executar_postgres` (`readonly=True`, `statement_timeout` e `search_path`).
- Validação das consultas agregadas com dialeto PostgreSQL (tratamento de tipos numéricos `Decimal` / `float`).
- Manter validação de captura graciosa de erros em ambos os dialetos.

---

### 3.4 Golden Dataset e Runner de Avaliação (`ai-agent/tests/test_avaliacao_golden_set.py`)

#### [MODIFY] `ai-agent/tests/test_avaliacao_golden_set.py`
- Alterar o parser AST de:
  ```python
  # De:
  arvore = sqlglot.parse_one(sql, read="sqlite")
  # Para:
  arvore = sqlglot.parse_one(sql, read="postgres")
  ```
- Atualizar o log do relatório consolidado para indicar explicitamente qual motor de banco foi utilizado na rodada (`PostgreSQL (schema exclusivo)` ou `SQLite (fallback)`).

---

### 3.5 Ajustes no `sql_executor.py` e Nós do Grafo (se aplicável)

#### [MODIFY] `ai-agent/src/services/sql_executor.py`
- Garantir que `_executar_postgres` suporte tanto strings de conexão com schema explícito quanto execução de queries com schema no search path.
- Configurar o `search_path` do psycopg2 com identificador quoted para preservar nomes de schema com maiúsculas, como já ocorre no caminho psycopg3.
- Tratar conversão de tipos nativos do PostgreSQL (`Decimal` retornado pelo psycopg2/psycopg convertido para `float`/`int` para compatibilidade com o contrato JSON do Pydantic).

---

## 4. Plano de Verificação

### 4.1 Testes em Modo Fallback (Sem Postgres ativo)
```powershell
python -m pytest ai-agent/tests -v
```
- **Critério de Sucesso:** Todos os testes da suíte devem passar usando o fallback com aviso informativo nos logs. A rodada atual executa 59 testes; o tempo depende do ambiente local.

### 4.2 Testes em Modo PostgreSQL Real (Com Container Docker)
```powershell
# 1. Subir container de teste
docker compose -f ai-agent/docker-compose.test.yml up -d

# 2. Rodar a suíte apontando para o PostgreSQL
$env:TEST_DATABASE_URL="postgresql://postgres:postgres@localhost:5433/v_energy_test_db"
python -m pytest ai-agent/tests -v -s

# 3. Derrubar container de teste ao terminar
docker compose -f ai-agent/docker-compose.test.yml down -v
```
- **Critério de Sucesso:**
  1. Conexão real estabelecida com PostgreSQL 16.
  2. Schema exclusivo da execução, com prefixo `venergy_test_gold`, criado e populado.
  3. Todas as queries de agregação, join e limite executadas com sucesso.
  4. AST parsing via `sqlglot(read="postgres")` aprovado com 100% nas 4 métricas.
  5. Schema descartado sem resíduos.
