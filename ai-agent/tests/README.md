# Testes do AI Agent

Este guia descreve a suíte em `ai-agent/tests`, suas fixtures e como executá-la
com PostgreSQL local ou SQLite sintético. Os testes não iniciam nem provisionam
bancos.

## Escopo da suíte

| Arquivo | Responsabilidade |
| --- | --- |
| `test_filtro_seguranca.py` | Bloqueio de prompt injection e entradas excessivamente longas; validação SQL read-only, parsing, normalização e `LIMIT` defensivo. |
| `test_nos_grafo.py` | Testes unitários dos nós do grafo: follow-up, escopo, roteamento, geração/validação/execução SQL, recusa, síntese e finalização/auditoria. |
| `test_executor_agente.py` | Fluxos integrados do agente: caminho SQL feliz, retry após erro de consulta, esgotamento de tentativas, bloqueio de entrada maliciosa, recusa por escopo e follow-up. |
| `test_sql_executor.py` | Consultas e agregações sobre os dados sintéticos, joins, limite de linhas, captura de erros e configuração do executor PostgreSQL. |
| `test_postgres_fixtures.py` | Seleção de PostgreSQL/SQLite, isolamento de `DATABASE_URL`, preservação de `TEST_DATABASE_URL` e tratamento de falhas no setup PostgreSQL. |
| `test_avaliacao_golden_set.py` | Avaliação ponta a ponta de 12 casos de `golden_dataset/golden_dataset.json`, incluindo execução SQL, tabelas identificadas via AST, recusas e consumo de tokens. |
| `test_avaliacao_golden_set_openrouter.py` | Avaliação manual e opt-in com OpenRouter e Gold PostgreSQL real. Executa os seis casos SQL e as três recusas; os três casos RAG ficam explicitamente pendentes até a infraestrutura vetorial estar pronta. |
| `test_real_llm_eval_support.py` | Testes determinísticos das barreiras de OpenRouter, SQL agregado e limite mínimo amostral usadas pela avaliação real. |

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

### Camada Gold local carregada (opcional)

O teste `test_gold_postgres_integration.py` executa o agente contra a tabela
`agg_receita_mensal` já carregada no PostgreSQL. Diferentemente de
`TEST_DATABASE_URL`, esta configuração **não** cria nem remove schemas ou
tabelas: consulta diretamente o schema Gold existente. O LLM continua mockado,
então nenhuma pergunta, resultado ou dado do banco é enviado a um provedor
externo. Não é necessário exportar novamente os CSVs.

Configure as variáveis no mesmo terminal do pytest:

```powershell
$env:AI_AGENT_GOLD_DATABASE_URL="postgresql://<usuario>:<senha>@localhost:5432/v_energy"
$env:AI_AGENT_GOLD_SCHEMA="public"
python -m pytest ai-agent/tests/test_gold_postgres_integration.py -v
```

Use um usuário PostgreSQL dedicado com permissão somente de leitura nas tabelas
Gold necessárias. O executor também abre a conexão em modo read-only e aplica
timeout. Se `AI_AGENT_GOLD_DATABASE_URL` não estiver definida, o teste é
marcado como ignorado; se estiver configurada e houver erro de conexão, schema
ou tabela, o teste falha explicitamente.

**Não configure `TEST_DATABASE_URL` com o banco Gold carregado.** Essa variável
é exclusiva da fixture sintética, que cria e remove um schema temporário no
banco apontado. A execução opcional Gold usa somente `AI_AGENT_GOLD_DATABASE_URL`.

### SQLite sintético (fallback)

Quando `TEST_DATABASE_URL` estiver ausente ou a conexão inicial falhar, a suíte
usa um arquivo SQLite temporário por teste. Para selecionar explicitamente esse
modo, remova a URL antes de rodar:

```powershell
Remove-Item Env:TEST_DATABASE_URL -ErrorAction SilentlyContinue
python -m pytest ai-agent/tests -v
```

O banco sintético reproduz as tabelas e os nomes canônicos mais usados pela suíte:

- `dim_unidade_consumidora`: seis unidades consumidoras, com `id_uc`, `classe`,
  `municipio`, `bairro` e `status`;
- `fact_faturamento`: doze registros com `id_uc`, `ano`, `mes` e
  `receita_faturada`;
- `fact_leituras`: seis leituras com `id_uc`, `ano`, `mes` e `consumo_kwh`;
- `fact_ocorrencias`: quatro ocorrências com `causa`, `competencia` e
  `duracao_h`.

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

## Avaliação real via OpenRouter

O teste padrão do Golden Dataset continua usando LLM fake e dados sintéticos.
Para uma chamada real, há um runner separado e opt-in. Ele usa o modelo
configurado em `MODELO_LLM_PRIMARIO` (padrão
`google/gemini-2.5-flash-lite`) e exige `OPENROUTER_API_KEY`. As chamadas não
fazem fallback para 9router ou mock; uma falha no OpenRouter interrompe a
avaliação. O limite é de 60 chamadas OpenRouter por execução.

No PowerShell, configure as variáveis no mesmo terminal e rode o comando a
partir da raiz do repositório:

```powershell
$env:OPENROUTER_API_KEY="<sua-chave OpenRouter>"
$env:LLM_MOCK_MODE="false"
$env:AI_AGENT_GOLD_DATABASE_URL="postgresql://<usuario_leitura>:<senha>@localhost:5432/<banco>"
$env:AI_AGENT_GOLD_SCHEMA="public"
$env:AI_AGENT_RUN_REAL_LLM="1"
python -m pytest ai-agent/tests/test_avaliacao_golden_set_openrouter.py -v -s
```

Mantenha a chave apenas no ambiente local; não a escreva no código, em arquivo
versionado ou no chat. Configure também um teto de gastos na conta OpenRouter:
o runner informa os tokens reportados pelo provedor, mas não calcula o custo em
dinheiro.

O teste consulta o PostgreSQL existente em modo somente leitura e não cria nem
remove tabelas/schemas, nem grava auditoria. Use um usuário de banco com
permissão somente de leitura. **Não** aponte `TEST_DATABASE_URL` para a Gold:
essa variável é usada pelas fixtures sintéticas que criam e removem um schema.
`AI_AGENT_GOLD_DATABASE_URL` é a conexão separada do runner real.

O runner envia ao OpenRouter a pergunta e os prompts do agente, que incluem o
schema SQL autorizado. Os resultados do banco só são usados na etapa de síntese
depois de passarem por validação: apenas tabelas Gold autorizadas, agregações e
dimensões não identificáveis; sem projeção de identificadores ou registros
individuais; cada grupo precisa retornar `sample_size` de pelo menos 10
UCs/registros. Grupos menores são suprimidos antes de chamar o LLM. Se não for
possível comprovar o limite, o resultado não é compartilhado e o caso falha.
O runner não imprime SQL nem valores retornados pelo banco.

O relatório mostra execução SQL, correspondência de tabelas, cobertura de
termos, recusas, tokens e chamadas. As métricas de qualidade são informativas;
SQL inseguro, erros do provedor/configuração, impossibilidade de validar a
amostra mínima e falhas nas recusas esperadas reprovam a execução. Com
`AI_AGENT_RUN_REAL_LLM` ausente, o teste é ignorado. Depois de uma execução
opt-in, remova as variáveis locais quando terminar:

```powershell
Remove-Item Env:OPENROUTER_API_KEY
Remove-Item Env:AI_AGENT_GOLD_DATABASE_URL
Remove-Item Env:AI_AGENT_GOLD_SCHEMA
Remove-Item Env:AI_AGENT_RUN_REAL_LLM
```

### Avaliação RAG real via OpenRouter

Os casos RAG têm um runner independente para não exigir o banco vetorial ao
executar a avaliação SQL. O runner avalia TC-007 e TC-008 por meio do grafo
existente, usando `AI_AGENT_RAG_DATABASE_URL` para a base pgvector separada.
Antes de chamar o OpenRouter, valida a extensão, a tabela, os embeddings e se
cada pergunta recupera ao menos um trecho. A auditoria é desativada durante a
avaliação. Use uma conta PostgreSQL somente leitura.

TC-009 permanece pendente: o corpus atualmente indexado não contém fonte sobre
os critérios de compensação financeira por violação de continuidade. O runner
não altera o corpus nem contabiliza esse caso como aprovado ou reprovado.

O `sentence-transformers` e o modelo de embeddings precisam estar disponíveis
no mesmo ambiente Python usado para pytest. Ative o ambiente virtual do projeto
antes de instalar o pacote, se aplicável:

```powershell
python -m pip install sentence-transformers
```

Configure as variáveis no mesmo PowerShell e execute da raiz do repositório:

```powershell
$env:OPENROUTER_API_KEY="<sua-chave OpenRouter>"
$env:MODELO_LLM_PRIMARIO="<provedor/modelo>"
$env:LLM_MOCK_MODE="false"
$env:AI_AGENT_RAG_DATABASE_URL="postgresql://<usuario_leitura>:<senha>@localhost:5433/v_energy_rag"
$env:AI_AGENT_RUN_REAL_RAG="1"
python -m pytest ai-agent/tests/test_avaliacao_rag_openrouter.py -v -s
```

O runner não precisa de `AI_AGENT_GOLD_DATABASE_URL`: estes casos consultam
somente a base vetorial. Durante a avaliação, a conexão RAG é aplicada
temporariamente a `DATABASE_URL`, que é o nome usado pelo buscador existente.
Não configure `AI_AGENT_RAG_DATABASE_URL` com a URL da Gold.

A avaliação exige OpenRouter estrito (sem fallback para 9router/mock) e
respeita o limite de chamadas do cliente live. Configure também um teto de
gastos na conta OpenRouter. O relatório mostra apenas contagens, métricas e
tokens; não imprime o conteúdo dos trechos recuperados nem a resposta integral.
As perguntas e os trechos recuperados são enviados ao provedor, portanto
confirme que o corpus pode ser compartilhado antes da execução.

A execução falha se pgvector/tabela/embeddings estiverem indisponíveis ou se
algum caso habilitado não recuperar contexto, não produzir uma resposta RAG com
fonte ou não fizer chamada real ao OpenRouter. Cobertura dos termos esperados e
presença textual da fonte são métricas informativas. Sem
`AI_AGENT_RUN_REAL_RAG=1`, o teste é ignorado. Não execute junto com o runner
SQL sem considerar que são avaliações distintas e podem consumir chamadas
pagas.

Depois da execução, remova as variáveis para evitar chamadas acidentais em
outras execuções de pytest:

```powershell
Remove-Item Env:OPENROUTER_API_KEY
Remove-Item Env:MODELO_LLM_PRIMARIO
Remove-Item Env:LLM_MOCK_MODE
Remove-Item Env:AI_AGENT_RAG_DATABASE_URL
Remove-Item Env:AI_AGENT_RUN_REAL_RAG
```

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
