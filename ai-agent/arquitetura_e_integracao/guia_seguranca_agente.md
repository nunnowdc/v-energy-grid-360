# Guia de Integração: Agentes & Segurança da Informação

Este guia define o contrato técnico entre a frente de **AGENTES** e a frente de **SEGURANÇA**, assegurando que ambas trabalhem de forma paralela e independente até a data de entrega.

---

## 1. Responsabilidades de Cada Frente

| Frente                 | Responsabilidade                                                                                                                                                                                         |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Agentes** (Você)     | Consome a interface do validador SQL, gerencia o ciclo de vida da query, lida com retries em caso de erro sintático e aciona abstenção honesta caso a query seja bloqueada.                              |
| **Segurança** (Colega) | Fornece a implementação concreta do validador de queries (usando SQLGlot / AST), define as regras de listas de permissão (whitelist de views/tabelas Gold) e garante as permissões de banco `READ-ONLY`. |

---

## 2. A Interface do Validador SQL (`ValidadorSQLInterface`)

O módulo de agentes depende **estritamente** desta interface (localizada em `ai-agent/src/interfaces/validador_sql_interface.py`):

```python
from typing import Protocol, Optional
from pydantic import BaseModel

class ResultadoValidacaoSQL(BaseModel):
    aprovado: bool
    motivo_rejeicao: Optional[str] = None
    malicioso: bool = False  # True para tentativas flagrantes de injeção/DDL

class ValidadorSQLInterface(Protocol):
    def validar(self, sql: str) -> ResultadoValidacaoSQL:
        """
        Analisa a query SQL via AST e retorna se está aprovada para execução.
        """
        ...
```

### O que o time de Segurança deve entregar

Uma classe (ex.: `ValidadorSQLGlotPostgres`) que implemente o método `.validar(sql: str) -> ResultadoValidacaoSQL`.

---

## 3. Regras de Segurança Exigidas

1. **Apenas Instruções SELECT:** Bloquear sumariamente qualquer ocorrência de `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `CREATE`, `REPLACE`, `GRANT`, `REVOKE` ou comandos administrativos.
2. **Instrução Única:** Proibir múltiplos statements separados por ponto e vírgula (defesa clássica contra SQL injection empilhado).
3. **Whitelist de Tabelas da Camada Gold:**
   A AST deve inspecionar os nós do tipo `exp.Table` e permitir **exclusivamente**:
   - `dim_unidade_consumidora`
   - `fact_leituras`
   - `fact_faturamento`
   - `fact_ocorrencias`
   - `fact_atendimentos`
   - `fact_gd` (ou colunas de geração distribuída)
   - `fact_inspecoes` / `fact_perdas`
   - `dim_alimentadores`
   - Views analíticas homologadas com prefixo `vw_gold_*`
4. **Tratamento de Dialeto:**
   O parser SQLGlot deve ser configurado explicitamente para o dialeto `postgres` (`sqlglot.parse(..., read="postgres")`).
5. **Diferenciação de Erro vs Ataque (`malicioso`):**
   - Se for apenas um erro de digitação de coluna ou sintaxe menor: `malicioso = False`. O agente tentará corrigir no laço de retry.
   - Se houver palavras-chave destrutivas ou bypass flagrante: `malicioso = True`. O agente cancelará qualquer nova tentativa e registrará o evento na auditoria.

---

## 4. Segurança no Nível de Banco de Dados (PostgreSQL)

Independentemente do validador em código, o usuário do banco utilizado pelo agente deve ser configurado com o menor privilégio possível:

```sql
-- Criação do usuário estrito para o agente
CREATE USER venergy_agent_ro WITH PASSWORD 'sua_senha_segura';

-- Conceder apenas leitura na camada Gold
GRANT CONNECT ON DATABASE venergy_grid_360 TO venergy_agent_ro;
GRANT USAGE ON SCHEMA public TO venergy_agent_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO venergy_agent_ro;

-- Revogar qualquer privilégio de criação ou modificação
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM venergy_agent_ro;
REVOKE CREATE ON SCHEMA public FROM venergy_agent_ro;
```
