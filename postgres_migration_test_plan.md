# Testes do AI Agent com PostgreSQL local

> Para a documentação completa da suíte de testes e de suas fixtures, consulte
> [`ai-agent/tests/README.md`](ai-agent/tests/README.md). Este documento resume
> a configuração do banco local usada na migração.

## Objetivo

A suíte de `ai-agent` deve exercitar PostgreSQL real quando `TEST_DATABASE_URL` estiver configurada e acessível. Os testes não provisionam nem iniciam o banco: o desenvolvedor administra uma instalação local existente. Sem a variável ou sem conexão, a suíte usa SQLite sintético como fallback.

## Conexão e isolamento

- A fixture `postgres_test_info` lê somente `TEST_DATABASE_URL`; não usa a variável genérica `DATABASE_URL`, que pode apontar para outro ambiente.
- A conexão deve apontar para um banco dedicado a testes. O usuário precisa poder criar e remover schemas.
- Cada execução cria um schema isolado com prefixo `TEST_POSTGRES_SCHEMA` (padrão: `venergy_test_gold`) e um sufixo único.
- A fixture carrega DDL e dados sintéticos nesse schema e, no teardown, remove somente o schema criado pela execução.
- Se a URL não estiver configurada ou a conexão inicial falhar, os testes usam o banco SQLite temporário.
- Se a conexão inicial funcionar, mas a criação ou carga do schema falhar, a fixture falha explicitamente; esse erro não deve ser mascarado por fallback.
- O SQLGlot usa dialeto PostgreSQL no runner de avaliação. O executor PostgreSQL mantém timeout, acesso read-only e normalização de valores `Decimal`.

## Configuração local

`ai-agent/.env.test.example` é somente um exemplo; ele não é carregado automaticamente. Ajuste a URL para as credenciais e para o banco dedicado já criado na instalação local. O exemplo usa `localhost` e a porta PostgreSQL padrão (`5432`).

No PowerShell, defina a variável na sessão antes de iniciar os testes:

```powershell
$env:TEST_DATABASE_URL="postgresql://<usuario>:<senha>@localhost:5432/v_energy_test_db"
$env:TEST_POSTGRES_SCHEMA="venergy_test_gold"
python -m pytest ai-agent/tests -v -s
```

Para deixar a suíte usar SQLite fallback, remova `TEST_DATABASE_URL` do ambiente:

```powershell
Remove-Item Env:TEST_DATABASE_URL -ErrorAction SilentlyContinue
python -m pytest ai-agent/tests -v
```

## Verificação

### Fallback SQLite

```powershell
Remove-Item Env:TEST_DATABASE_URL -ErrorAction SilentlyContinue
python -m pytest ai-agent/tests -v
```

Critério: todos os testes passam e o log informa que o SQLite fallback está sendo utilizado.

### PostgreSQL local

1. Iniciar o serviço PostgreSQL local de forma independente dos testes.
2. Criar um banco dedicado de teste e configurar `TEST_DATABASE_URL` com um usuário que tenha permissão para criar e descartar schemas.
3. Executar a suíte:

```powershell
$env:TEST_DATABASE_URL="postgresql://<usuario>:<senha>@localhost:5432/v_energy_test_db"
python -m pytest ai-agent/tests -v -s
```

Critérios: conexão com PostgreSQL estabelecida; schema exclusivo criado e populado; consultas de agregação, join e limite executadas; parsing AST no dialeto PostgreSQL validado; schema temporário removido ao final.
