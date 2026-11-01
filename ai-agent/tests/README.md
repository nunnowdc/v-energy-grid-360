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
| `test_avaliacao_golden_set_openrouter.py` | Runner opt-in da avaliação SQL/recusas com OpenRouter e PostgreSQL Gold real. |
| `real_llm_eval_support.py` / `test_real_llm_eval_support.py` | Cliente OpenRouter estrito, validação de consultas agregadas e proteções de privacidade; os testes exercitam esses controles sem chamadas externas. |
| `test_avaliacao_rag_openrouter.py` | Runner opt-in separado para avaliação RAG real dos casos TC-007 e TC-008. |
| `real_rag_eval_support.py` / `test_real_rag_eval_support.py` | Preflight do PostgreSQL/pgvector, seleção de casos e medição de recuperação/fontes; os testes são determinísticos e não chamam OpenRouter. |
| `golden_dataset/golden_dataset.json` | Fonte dos casos canônicos compartilhados pelas avaliações mock, SQL real e RAG real. |

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

O teste padrão `test_avaliacao_golden_set.py` usa LLM fake e dados sintéticos;
ele é uma avaliação determinística, não uma chamada real. As avaliações live
são opt-in e usam runners separados porque consultam recursos e bases diferentes:
o runner SQL consulta PostgreSQL Gold, enquanto o runner RAG busca documentos em
PostgreSQL com pgvector. Execute somente a seção que deseja avaliar.

Os dois runners usam `ClienteOpenRouterLimitado`, exigem chamadas diretas ao
OpenRouter (sem fallback para 9router ou mock) e cada um limita sua execução a
60 chamadas. Uma falha do provedor/configuração interrompe a avaliação.
As perguntas e os contextos enviados ao modelo saem da máquina; confirme que
podem ser compartilhados com o provedor e configure um teto de gastos na conta.

### O que cada arquivo faz

| Arquivo | Papel na avaliação real |
| --- | --- |
| `test_avaliacao_golden_set_openrouter.py` | Executa os seis casos SQL e as três recusas do Golden pelo grafo existente, usando o banco Gold local. Mede execução, presença das tabelas esperadas, termos e recusas. Não executa casos RAG. |
| `real_llm_eval_support.py` | Implementa cliente OpenRouter estrito e limitado, validador/executor agregado e as regras de privacidade e tamanho mínimo de amostra para a avaliação SQL. |
| `test_real_llm_eval_support.py` | Valida localmente o cliente, os limites e as regras de segurança do runner SQL com testes determinísticos; não consome chamadas OpenRouter. |
| `test_avaliacao_rag_openrouter.py` | Valida infraestrutura e recuperação antes das chamadas; depois executa TC-007 e TC-008 pelo grafo e imprime apenas métricas, não o texto da resposta ou os chunks. |
| `real_rag_eval_support.py` | Verifica conexão, extensão pgvector, tabela e embeddings; separa os casos RAG executados/pendentes e calcula métricas técnicas. |
| `test_real_rag_eval_support.py` | Testa preflight, seleção de casos e critérios de medição com mocks, sem conexão real ou chamadas OpenRouter. |
| `golden_dataset/golden_dataset.json` | Define perguntas, rota esperada, termos e expectativas utilizadas pelos runners. TC-009 permanece cadastrado, mas fora dos casos RAG executados até haver fonte adequada no corpus. |

O fluxo live, em ambos os runners, é: conferir opt-in e configuração, validar os
recursos necessários, executar os casos no grafo com o cliente OpenRouter real e
exibir métricas agregadas. O preflight evita gastar chamadas quando a base não
está pronta. As métricas informativas não são prova independente de correção
factual: no SQL, `Component Match` verifica a presença literal das tabelas
obrigatórias; no RAG, cobertura de termos e presença textual da fonte são
indicadores auxiliares. Os critérios técnicos obrigatórios são descritos em cada
seção abaixo.

Use os comandos a partir da raiz do repositório, no mesmo PowerShell em que
configurar as variáveis. As credenciais abaixo são placeholders: não as grave
no código ou em arquivos versionados e não as compartilhe nos logs.

### Avaliação SQL e recusas

```powershell
$env:OPENROUTER_API_KEY="<sua-chave OpenRouter>"
$env:MODELO_LLM_PRIMARIO="<provedor/modelo OpenRouter>"
$env:LLM_MOCK_MODE="false"
$env:AI_AGENT_GOLD_DATABASE_URL="postgresql://<usuario_leitura>:<senha>@localhost:<porta>/<banco_gold>"
$env:AI_AGENT_GOLD_SCHEMA="public"
$env:AI_AGENT_RUN_REAL_LLM="1"
.\.venv\Scripts\python.exe -m pytest ai-agent\tests\test_avaliacao_golden_set_openrouter.py -v -s
```

O runner consulta as tabelas Gold existentes em modo somente leitura: não cria
nem remove tabelas/schemas e não grava auditoria. Use um usuário PostgreSQL com
permissão de leitura. Não use `TEST_DATABASE_URL` para essa base: essa variável
é destinada às fixtures sintéticas, que criam e removem um schema temporário.

O cliente envia a pergunta e os prompts/schema autorizado ao OpenRouter. As
consultas passam por validação para permitir somente tabelas Gold autorizadas,
agregações e dimensões seguras; identificadores e registros individuais não
podem ser projetados. Cada grupo precisa comprovar amostra mínima de 10
UCs/registros; grupos menores são suprimidos. O runner não imprime SQL nem
valores retornados pelo banco. O relatório informa execução, component match,
termos, recusas, tokens e chamadas; SQL inseguro, falhas técnicas de privacidade
e recusas incorretas reprovam a execução. Não estima o custo monetário.

`AI_AGENT_RUN_REAL_LLM` habilita esse runner; sem ela, pytest o ignora.
`AI_AGENT_GOLD_DATABASE_URL` e `AI_AGENT_GOLD_SCHEMA` apontam para a Gold.
Configure `MODELO_LLM_PRIMARIO` com um identificador de modelo aceito pelo
OpenRouter; o runner imprime qual modelo selecionou.

Depois da execução, remova as variáveis locais:

```powershell
Remove-Item Env:OPENROUTER_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:MODELO_LLM_PRIMARIO -ErrorAction SilentlyContinue
Remove-Item Env:LLM_MOCK_MODE -ErrorAction SilentlyContinue
Remove-Item Env:AI_AGENT_GOLD_DATABASE_URL -ErrorAction SilentlyContinue
Remove-Item Env:AI_AGENT_GOLD_SCHEMA -ErrorAction SilentlyContinue
Remove-Item Env:AI_AGENT_RUN_REAL_LLM -ErrorAction SilentlyContinue
```

### Avaliação RAG real via OpenRouter

O runner avalia TC-007 e TC-008 pelo grafo existente, usando `AI_AGENT_RAG_DATABASE_URL`
para um banco PostgreSQL/pgvector separado. Antes de consumir chamadas, valida
que Gold e RAG não apontam para o mesmo banco, que pgvector e
`tb_conhecimento_vetorial` estão disponíveis, que todos os documentos têm
embeddings de 384 dimensões, que `sentence-transformers` está instalado e que
cada pergunta recupera pelo menos um chunk. A busca real usa as categorias da
rota RAG. A auditoria é desativada; use um usuário PostgreSQL de leitura.

TC-009 permanece pendente: o corpus atualmente indexado não contém fonte sobre
os critérios de compensação financeira por violação de continuidade. O runner
não altera o corpus nem contabiliza esse caso como aprovado ou reprovado.

O preflight de recuperação do runner cria o buscador sem um limiar explícito e,
por isso, usa `0.70` por padrão. O grafo aplica `0.45` à rota RAG. Para que o
preflight use o mesmo limiar do grafo, defina `RAG_LIMIAR_SIMILARIDADE=0.45`
durante a execução. Isso evita que ele descarte, antes da avaliação, chunks que
a própria rota RAG aceitaria.

Se necessário, instale `sentence-transformers` no ambiente virtual do projeto:

```powershell
.\.venv\Scripts\python.exe -m pip install sentence-transformers
```

Na primeira busca, o `sentence-transformers` pode carregar ou baixar os pesos
do modelo de embeddings; isso não é uma chamada OpenRouter.

Configure as variáveis no mesmo PowerShell e execute da raiz do repositório.
Use uma URL de banco RAG diferente da URL Gold:

```powershell
$env:OPENROUTER_API_KEY="<sua-chave OpenRouter>"
$env:MODELO_LLM_PRIMARIO="<provedor/modelo>"
$env:LLM_MOCK_MODE="false"
$env:AI_AGENT_RAG_DATABASE_URL="postgresql://<usuario_leitura>:<senha>@localhost:<porta>/<banco_rag>"
$env:RAG_LIMIAR_SIMILARIDADE="0.45"
$env:AI_AGENT_RUN_REAL_RAG="1"
.\.venv\Scripts\python.exe -m pytest ai-agent\tests\test_avaliacao_rag_openrouter.py -v -s
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

A execução falha se a infraestrutura não estiver pronta, se um caso habilitado
não recuperar contexto ou se não produzir resposta com selo documental, fonte
e chamada real ao OpenRouter. Cobertura de termos e presença textual da fonte
são métricas informativas. Sem `AI_AGENT_RUN_REAL_RAG=1`, o teste é ignorado.
Não rode junto com o runner SQL sem considerar os bancos e chamadas pagas
separados.

Depois da execução, remova as variáveis para evitar chamadas acidentais em
outras execuções de pytest:

```powershell
Remove-Item Env:OPENROUTER_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:MODELO_LLM_PRIMARIO -ErrorAction SilentlyContinue
Remove-Item Env:LLM_MOCK_MODE -ErrorAction SilentlyContinue
Remove-Item Env:AI_AGENT_RAG_DATABASE_URL -ErrorAction SilentlyContinue
Remove-Item Env:RAG_LIMIAR_SIMILARIDADE -ErrorAction SilentlyContinue
Remove-Item Env:AI_AGENT_RUN_REAL_RAG -ErrorAction SilentlyContinue
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
