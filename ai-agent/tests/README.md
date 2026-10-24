# Testes do AI Agent

Este guia descreve a suíte em `ai-agent/tests`, suas fixtures e como executá-la
com PostgreSQL local ou SQLite sintético. Os testes não iniciam nem provisionam
bancos. Para instruções de configuração do PostgreSQL, consulte também
[`postgres_migration_test_plan.md`](../../postgres_migration_test_plan.md).

## Escopo da suíte

| Arquivo | Responsabilidade |
| --- | --- |
| `test_filtro_seguranca.py` | Bloqueio de prompt injection e entradas excessivamente longas; validação SQL read-only, parsing, normalização e `LIMIT` defensivo. |
| `test_nos_grafo.py` | Testes unitários dos nós do grafo: follow-up, escopo, roteamento, geração/validação/execução SQL, recusa, síntese e finalização/auditoria. |
| `test_executor_agente.py` | Fluxos integrados do agente: caminho SQL feliz, retry após erro de consulta, esgotamento de tentativas, bloqueio de entrada maliciosa, recusa por escopo e follow-up. |
| `test_sql_executor.py` | Consultas e agregações sobre os dados sintéticos, joins, limite de linhas, captura de erros e configuração do executor PostgreSQL. |
| `test_postgres_fixtures.py` | Seleção de PostgreSQL/SQLite, isolamento de `DATABASE_URL`, preservação de `TEST_DATABASE_URL` e tratamento de falhas no setup PostgreSQL. |
| `test_avaliacao_golden_set.py` | Avaliação ponta a ponta de 12 casos de `golden_dataset/golden_dataset.json`, incluindo execução SQL, tabelas identificadas via AST, recusas e consumo de tokens. |

Os testes do validador de segurança também existem em
`ai-agent/security/tests/`; eles ficam fora de `ai-agent/tests` e podem ser
executados separadamente ou junto à suíte principal.

## Requisitos e comandos

Instale as dependências declaradas em `ai-agent/requirements.txt` no ambiente
Python do projeto. A suíte usa `pytest`, `psycopg2-binary` para o setup
PostgreSQL e as dependências do agente.

Execute os comandos a partir da raiz do repositório:

```powershell
# Suíte principal
python -m pytest ai-agent/tests -v

# Testes do validador SQL isolados
python -m pytest ai-agent/security/tests -v

# Todas as suítes do agente
python -m pytest ai-agent/tests ai-agent/security/tests -v
```

Para observar o relatório do Golden Dataset e os avisos durante a execução:

```powershell
python -m pytest ai-agent/tests/test_avaliacao_golden_set.py -v -s
```

## Banco usado nos testes

### PostgreSQL local

Para executar consultas contra PostgreSQL real:

1. Inicie uma instalação PostgreSQL local por fora do pytest.
2. Crie um banco dedicado a testes. A fixture precisa poder criar e remover
   schemas nesse banco.
3. Defina `TEST_DATABASE_URL` para essa base e execute os testes.

Exemplo PowerShell (substitua usuário, senha, porta e banco pelos valores da
sua instalação):

```powershell
$env:TEST_DATABASE_URL="postgresql://<usuario>:<senha>@localhost:5432/v_energy_test_db"
$env:TEST_POSTGRES_SCHEMA="venergy_test_gold"
python -m pytest ai-agent/tests -v -s
```

[`../.env.test.example`](../.env.test.example) é apenas um exemplo de valores:
ele **não** é carregado automaticamente. Defina as variáveis no ambiente do
processo que executa o pytest. Não use uma URL de produção ou uma base
compartilhada: o teardown remove o schema de teste criado pela execução.

O fluxo PostgreSQL é:

1. `postgres_test_info` lê somente `TEST_DATABASE_URL`; a variável genérica
   `DATABASE_URL` não seleciona o banco das fixtures.
2. Se a URL não for PostgreSQL ou a conexão inicial não estiver disponível, a
   fixture registra um aviso e seleciona SQLite.
3. Após conectar, cria um schema exclusivo com o prefixo de
   `TEST_POSTGRES_SCHEMA` e um sufixo aleatório. Cria as tabelas Gold e insere
   os dados sintéticos nesse schema.
4. `sql_executor_teste` usa o executor PostgreSQL com esse schema como
   `search_path`. O executor aplica timeout, acesso somente leitura e
   normaliza valores `Decimal`.
5. Ao encerrar a sessão de testes, a fixture remove somente o schema exclusivo
   que criou. Erros ao criar/popular o schema ou removê-lo são reportados; falha
   de setup após conexão bem-sucedida não é convertida em fallback.

Confirme no relatório do Golden Dataset qual motor foi usado. Uma execução
SQLite bem-sucedida não substitui a validação de integração com PostgreSQL.

### SQLite sintético (fallback)

Quando `TEST_DATABASE_URL` estiver ausente ou a conexão inicial falhar, a suíte
usa um arquivo SQLite temporário por teste. Para selecionar explicitamente esse
modo, remova a URL antes de rodar:

```powershell
Remove-Item Env:TEST_DATABASE_URL -ErrorAction SilentlyContinue
python -m pytest ai-agent/tests -v
```

O banco sintético reproduz parte do esquema Gold usado pela suíte:

- `dim_unidade_consumidora`: seis unidades consumidoras;
- `fact_faturamento`: doze registros de faturamento;
- `fact_ocorrencias`: quatro ocorrências de interrupção.

Os mesmos dados permitem validar contagens, agregações, joins e limites sem
serviço externo. SQLite é um fallback rápido, mas seu dialeto e comportamento
não cobrem todas as diferenças do PostgreSQL.

## Isolamento de ambiente e mocks

- Uma fixture `autouse` remove `DATABASE_URL` durante cada teste e restaura o
  ambiente ao final, evitando que uma configuração genérica do desenvolvedor
  conecte o grafo ao banco errado ou provoque gravações de auditoria.
- `TEST_DATABASE_URL` não é removida; ela continua disponível para testes
  PostgreSQL explicitamente configurados.
- Um teste que precise exercitar persistência de auditoria deve configurar ou
  injetar, dentro do próprio teste, um destino controlado e isolado. Os testes
  atuais não fazem gravação real de auditoria em PostgreSQL.
- `FakeClienteLLM` e os mocks específicos simulam respostas e chamadas de LLM;
  os testes comuns não dependem de provedor de IA externo.

## Golden Dataset

O runner avalia as perguntas canônicas em
`golden_dataset/golden_dataset.json`. As metas verificadas são:

| Métrica | Cálculo/critério | Meta |
| --- | --- | --- |
| Execution Rate | Casos SQL executados com dados e selo `gerada_confiavel` | `>= 90%` |
| Component Match | Casos SQL cujo AST contém todas as tabelas obrigatórias | `>= 85%` |
| Honesty Accuracy | Recusas esperadas que terminam com selo de recusa/bloqueio | `100%` |
| FinOps | Média de tokens por pergunta | `< 1.800` |

O parsing de tabelas do Golden Dataset usa SQLGlot no dialeto PostgreSQL,
independentemente de o executor da rodada estar em SQLite fallback.

## Diagnóstico rápido

- **O relatório mostra `SQLite (fallback)` inesperadamente:** verifique se
  `TEST_DATABASE_URL` foi definida no mesmo terminal que iniciou o pytest e se
  o serviço/credenciais locais estão corretos. Uma falha na conexão inicial
  seleciona SQLite e gera aviso.
- **O setup PostgreSQL falha após conectar:** verifique permissões para criar
  schemas e compatibilidade do DDL. A suíte falha intencionalmente em vez de
  esconder esse erro usando SQLite.
- **Erros ou lentidão de auditoria em testes:** confirme que
  `DATABASE_URL` não está sendo configurada deliberadamente dentro do teste;
  auditoria real deve usar um destino isolado e controlado.
- **Comparação de dialetos:** execute a suíte com PostgreSQL local quando a
  mudança depender de operadores, funções ou tipos específicos do PostgreSQL.
