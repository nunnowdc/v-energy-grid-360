# Planejamento da estrutura inicial do backend FastAPI

**Estado:** proposta para revisão; nenhuma implementação autorizada nesta tarefa.  
**Branch de documentação:** `docs/planejamento-backend-fastapi`, derivada de `dev`.

## 1. Objetivo e escopo

Planejar a inicialização de uma API FastAPI simples e testável para o Portal Web V-Energy Grid 360. A futura tarefa de implementação deve criar apenas a base da aplicação, configuração local, documentação OpenAPI, rota de saúde e testes essenciais. Endpoints de negócio, persistência PostgreSQL e integração GenAI entram em etapas posteriores, após os respectivos contratos serem validados. Este documento não define tabelas ou colunas físicas da Gold.

O estado atual do repositório sustenta essa separação: `backend/` contém apenas `README.md`; `frontend/`, `data-engineering/` e `ai-agent/` também existem como módulos separados. O `requirements.txt` da raiz atende à EDA e aos notebooks; as dependências da futura API devem ficar em manifesto próprio dentro de `backend/`.

## 2. Requisitos que orientam a estrutura

| Fonte | Requisito e efeito no backend |
| --- | --- |
| [Matriz de rastreabilidade](../context/matriz-rastreabilidade.md) | REQ-PORTAL-01 a 07 exigem indicadores, análise de receita, Visão 360 da UC, fila e ordens de inspeção, continuidade e filtros. REQ-PORTAL-08 a 11 são diferenciais: exportação, upload, perfis e testes. |
| [Portal Web](../context/04-portal-web.md) | FastAPI atende React/TypeScript/Vite; PostgreSQL recebe a Gold exportada e dados operacionais de inspeção. Os caminhos HTTP principais já foram propostos. |
| [Engenharia de Dados](../context/03-engenharia-de-dados.md) | A Gold vem do fluxo Databricks Bronze → Silver → Gold → exportação; o dicionário e o contrato físico ainda precisam ser confirmados antes de escrever consultas. |
| [Diagnóstico de Receita](../context/06-diagnostico-receita.md) | REQ-DIAG-01 requer períodos comparáveis, receita faturada e volume faturado, decomposição Shapley de preço e volume, mix e informação de cobertura/qualidade. O Portal deve exibir os mesmos números do diagnóstico. |
| [Inteligência Artificial](../context/05-inteligencia-artificial.md) | REQ-AI-01 a 06 preveem `/ai/ask`, Text-to-SQL com acesso de consulta restrito, auditoria, resposta honesta e insights no Portal. A infraestrutura de IA fica para outra tarefa. |
| [Revisões cruzadas](../context/diagnostico_dados.md), [IA/Portal](../context/diagnostico_dev_ia.md) e [IA/SQL](../context/diagnostico_IA_sql.md) | Alertam para lacunas da Gold, latência de insights e necessidade de compartilhar semântica de preço médio e períodos. |

## 3. Decisões existentes e novas recomendações

**Já documentado:** FastAPI, React + TypeScript + Vite, PostgreSQL local e fluxo da Gold exportada constam da [visão geral](../context/01-visao-geral.md) e do [Portal](../context/04-portal-web.md). O Portal já nomeia os endpoints principais e a escrita operacional de inspeções. O [módulo IA](../context/05-inteligencia-artificial.md) escolheu PydanticAI e Gemini 3.1 Flash-Lite para sua etapa, além de exigir usuário de consulta somente leitura para o SQL gerado. O [Diagnóstico](../context/06-diagnostico-receita.md) definiu a decomposição Shapley e os cortes município, bairro e classe.

**Decisão arquitetural do responsável pelo projeto:** organizar o backend em camadas `controllers/`, `entities/`, `exceptions/`, `repositories/`, `security/`, `services/` e `tests/`, preservando `app/main.py` e `core/`. Usar `schemas/` para contratos HTTP quando necessário, separados dos modelos ORM de `entities/`. Essa organização substitui a proposta anterior de `api/routers/` e `db/`.

**Recomendação de execução, revisada pelo Gemini:** manter uma única aplicação HTTP em `backend/` e materializar cada camada somente ao surgir um caso de uso real. `ai-agent/` permanece responsável pela lógica de IA; o futuro controller de `/ai/ask` será o adaptador HTTP no FastAPI, com a integração concreta entre os módulos definida antes de implementá-la. A arquitetura de pastas é uma direção obrigatória, não uma ordem para criar arquivos vazios no bootstrap.

## 4. Estrutura proposta e responsabilidades

A árvore abaixo representa a **arquitetura planejada**, não arquivos existentes. No bootstrap, criar fisicamente apenas os itens marcados `inicial`. Os demais são destinos para casos de uso posteriores; não criar diretórios, classes base ou arquivos vazios para completar o desenho.

```text
backend/
├── app/
│   ├── main.py                    # inicial: aplicação, registro do controller e inicialização
│   ├── core/
│   │   ├── config.py              # inicial: configuração do ambiente
│   │   └── database.py            # futuro: conexões e ciclo de vida PostgreSQL
│   ├── controllers/
│   │   ├── health.py              # inicial: GET /health
│   │   ├── metrics.py             # futuro: indicadores e receita
│   │   ├── uc.py                  # futuro: Visão 360 e históricos
│   │   ├── inspections.py         # futuro: fila e ordens
│   │   ├── network.py             # futuro: continuidade
│   │   └── ai.py                  # futuro: adaptador HTTP de ai-agent/
│   ├── entities/                  # futuro: modelos ORM SQLAlchemy do PostgreSQL
│   ├── exceptions/               # futuro: falhas semânticas independentes de HTTP
│   ├── repositories/             # futuro: consultas e persistência PostgreSQL
│   ├── security/                 # futuro: identidade, autorização e políticas
│   ├── services/                 # futuro: casos de uso e regras de negócio
│   └── schemas/                  # futuro: contratos HTTP Pydantic quando necessários
├── tests/                         # inicial: saúde, OpenAPI e configuração; depois, cada camada
└── manifesto de dependências      # futuro arquivo próprio do backend
```

| Camada | Responsabilidade | Limite explícito |
| --- | --- | --- |
| `app/main.py` | Montar FastAPI, registrar controllers e handlers de exceção; futuramente gerenciar o ciclo de vida da infraestrutura. | Não conter consultas nem regra de negócio. |
| `core/` | Ler/validar configuração; futuramente criar e fornecer conexões ou sessões PostgreSQL para o ciclo de vida da aplicação. | Não conter consultas de domínio nem regras de autorização. |
| `controllers/` | Definir `APIRouter`, parâmetros, `Depends`, validação e tradução entre HTTP e casos de uso; preservar os caminhos acordados com React. | Não executar SQL nem calcular regras de negócio; `health.py` pode responder diretamente por não haver caso de uso de domínio. |
| `schemas/` | DTOs Pydantic de entrada/saída HTTP, paginação e formato de erro quando houver contratos reais. | Permanecer independentes dos modelos ORM de `entities/`; não mapear tabelas PostgreSQL. |
| `services/` | Orquestrar casos de uso, regras e cálculos; receber dependências explícitas e retornar resultados independentes de FastAPI. | Não conhecer `Request`, `HTTPException`, engine ou detalhes de SQL. |
| `entities/` | Conter modelos ORM do SQLAlchemy para mapear tabelas, colunas, chaves e relacionamentos do PostgreSQL, somente após confirmação dos contratos físicos pertinentes. | Não validar HTTP nem concentrar regras de negócio; não definir modelos Gold definitivos antes da validação pela Engenharia de Dados. |
| `repositories/` | Concentrar toda consulta SQL e persistência, recebendo sessão/conexão configurada; mapear resultados para a forma necessária ao serviço. | Não ler ambiente, criar engine global, expor objetos HTTP nem decidir políticas de acesso. Uma consulta analítica simples não precisa passar por uma entidade idêntica à linha e ao schema. |
| `security/` | Definir políticas de identidade, perfil/autorização e limites de aplicação para o fluxo Text-to-SQL, coordenados com `ai-agent/`. | Não abrir conexão nem executar SQL; não duplicar o parser ou o pipeline de IA. Permissões PostgreSQL continuam sendo a barreira efetiva. |
| `exceptions/` | Definir falhas semânticas, como recurso ausente, transição inválida, violação de política e fonte indisponível. | Não importar FastAPI; a tradução centralizada para status e JSON ocorre em `main.py` quando essas falhas existirem. |
| `tests/` | Verificar contrato HTTP, regras de domínio e integração com banco conforme cada camada for criada. | Não exigir PostgreSQL para testes unitários nem usar mocks para afirmar permissões reais do banco. |

## 5. Dependências e ferramentas de qualidade

| Momento | Recomendação | Motivo |
| --- | --- | --- |
| Estrutura inicial | `fastapi`, `uvicorn` | API HTTP, validação/OpenAPI e execução local. O Pydantic vem pela dependência do FastAPI. |
| Testes iniciais | `pytest`, `httpx` | Exercitar a aplicação e seus contratos sem iniciar um servidor externo. |
| Qualidade inicial | `ruff` como dependência de desenvolvimento | Formatação e lint em uma ferramenta, com configuração mínima. |
| Integração PostgreSQL | `sqlalchemy` 2.x e driver PostgreSQL compatível, por exemplo `psycopg` | Consultas parametrizadas e gestão de conexão após confirmação dos contratos. Escolher modo síncrono ou assíncrono de ponta a ponta nessa tarefa; a mera adoção de FastAPI não exige driver assíncrono. |
| Só se necessário | `pydantic-settings`, `python-multipart`, biblioteca de IA | Configuração mais complexa, upload do REQ-PORTAL-09 e integração GenAI, respectivamente. |

Não incluir no bootstrap Redis, Celery, filas, microserviços, cache distribuído ou Alembic por antecipação. A evolução das tabelas **operacionais** precisará de uma política de migração antes da persistência; não se deve descartar Alembic definitivamente. Bibliotecas da EDA no `requirements.txt` da raiz não entram automaticamente no ambiente da API. Versões exatas devem ser fixadas e verificadas na tarefa de implementação, sem instalação nesta etapa.

## 6. Configuração do ambiente local

Na futura implementação, `app/core/config.py` deve ler variáveis de ambiente com valores locais seguros e validação simples, sem exigir `pydantic-settings` inicialmente. Configurações previstas: ambiente, host/porta, origens CORS explícitas do Vite e, **quando houver banco**, URLs separadas para leitura analítica, escrita operacional e leitura restrita da IA. Segredos ficam fora do Git; um exemplo sem credenciais pode ser documentado na tarefa de código. CORS deve aceitar apenas origens locais configuradas, não `*` com credenciais. A rota `GET /health` verifica o processo; eventual checagem de prontidão do PostgreSQL será separada quando o banco existir.

## 7. Organização da aplicação e fluxo Controller → Service → Repository

Para um caso de uso com dados, o **controller** recebe a requisição React, valida parâmetros por schemas Pydantic, resolve identidade/dependências com FastAPI e chama o **service**. O service aplica as regras de negócio, consulta ou grava por meio de um **repository** recebido explicitamente, e devolve um resultado sem formato HTTP. O repository usa os modelos ORM de `entities/` para mapear a persistência PostgreSQL quando ela existir. O controller converte o resultado para o schema de resposta; FastAPI publica o contrato OpenAPI. O retorno não deve trazer objetos de sessão ou linhas cruas do driver à borda.

`security/` atua antes ou durante o caso de uso para aplicar política de identidade/autorização, sem I/O de banco. `repositories/` é a única camada de SQL e usa a credencial adequada entregue por `core/`. Falhas semânticas de `exceptions/` atravessam as camadas; handlers registrados em `main.py` as traduzem centralmente em status HTTP e envelope JSON consistente. Evitar `try/except` repetidos por controller e evitar `HTTPException` dentro de services, entities, repositories ou security. Erros de validação HTTP próprios do FastAPI permanecem tratados na borda.

Para leitura analítica, o service pode transformar diretamente o resultado do repository para uma projeção de resposta: não é obrigatório instanciar um modelo ORM para cada linha consultada. As transições de inspeção e a reconciliação matemática da receita permanecem regras de negócio em `services/`, não em `entities/`. Dependências explícitas permitem substituir services/repositories nos testes sem criar interfaces genéricas antecipadas.

Manter os caminhos já documentados, sem prefixo novo que quebre os consumidores:

| Controller futuro | Endpoints documentados para etapas posteriores |
| --- | --- |
| `metrics` | `GET /metrics/general`, `GET /metrics/revenue-variance` |
| `uc` | `GET /uc/{uc_id}/360` |
| `inspections` | `GET /inspections/queue`, `POST /inspections/order`, `PATCH /inspections/{id}`, `DELETE /inspections/{id}` |
| `network` | `GET /network/continuity` |
| `ai` | `POST /ai/ask` |

`DELETE /inspections/{id}` está descrito como “cancelar”; a futura implementação deve preservar o registro e definir o status de cancelamento no contrato, sujeito à validação do fluxo operacional. Exportação CSV e upload de inspeções são extensões do domínio `inspections`, sem rotas inventadas agora. Perfis por cargo são um diferencial; identidade, autenticação e autorização precisam de decisão própria antes de proteger dados ou usar `user_id` na auditoria.

## 8. Preparação para PostgreSQL

PostgreSQL é o alvo oficial; a menção alternativa a SQLite no documento de IA não altera essa decisão. A Gold exportada é fonte analítica de leitura. Tabelas de inspeção e auditoria são dados operacionais de escrita, separados logicamente da Gold. A futura integração deve usar consultas parametrizadas, filtros e limites explícitos, transações curtas, índices e paginação orientados por consultas medidas. Nenhum nome de coluna ou relacionamento Gold além do contrato aprovado deve ser codificado agora.

Com a arquitetura em camadas, `core/` configura e fornece sessões/conexões no ciclo de vida da aplicação; `repositories/` recebe essas sessões e concentra as consultas parametrizadas e operações de persistência. Repositories não criam engines próprias nem leem variáveis de ambiente. Services escolhem o caso de uso, sem conhecer SQL. `security/` aplica políticas na aplicação, sem abrir conexões ou substituir os privilégios do PostgreSQL.

A execução do **SQL gerado pela IA** deve usar credencial PostgreSQL com `SELECT` apenas nas tabelas ou visões Gold autorizadas, além de limites de tempo e resultado. O registro de `fact_ai_audit` exigido por REQ-AI-03 usa um repository de **escrita controlada pela aplicação**, nunca a credencial do SQL gerado. A API analítica pode ter sua própria credencial de leitura. São perfis lógicos de permissão; não é necessário criar três pools no bootstrap. A checagem de política em `security/` e a validação SQL do módulo de IA complementam, mas não substituem, os privilégios mínimos no banco.

A estratégia de carga Gold (CSV → PostgreSQL), reconciliação, atualização e publicação de dicionário pertence à integração com Engenharia de Dados. Regras para atualizar tabelas operacionais não devem ser misturadas com a recarga da Gold.

## 9. Endpoints, contratos e integração React/GenAI

Antes de implementar cada endpoint, acordar com o frontend nomes de campos, tipos, unidades, datas e fusos, formato de erro, filtros, ordenação, paginação e casos sem dados. Usar OpenAPI e exemplos revisados como contrato executável. Históricos da UC e a fila de inspeção precisam de paginação; filtros por município, bairro e classe são obrigatórios na análise de receita. O frontend não deve depender de um contrato simplificado provisório.

Para `GET /metrics/revenue-variance`, reservar no contrato lógico os períodos inicial/final, receita, volume e preço médio de cada período, efeitos preço e volume pela fórmula oficial, efeito mix **quando disponível**, contribuição absoluta e percentual, filtros aplicados e informação de cobertura/qualidade. O serviço deve consumir a definição versionada do Diagnóstico, sem refazer silenciosamente a fórmula. O schema HTTP será fechado quando a métrica e a Gold estiverem validadas; valores simulados não devem ser publicados como resposta analítica real.

Para `/ai/ask`, respeitar o contrato já proposto de pergunta/resposta e `audit_id`, mas validar identidade e exposição de SQL antes de fechar o formato externo. Contexto da tela e feedback são recomendações da [revisão Portal/IA](../context/diagnostico_dev_ia.md), ainda não decisões. Insights proativos não devem bloquear a resposta da Visão 360; cache, pré-cálculo ou endpoint separado serão avaliados junto ao módulo de IA. PydanticAI e Gemini são escolhas documentadas para a etapa IA, não dependências da inicialização FastAPI.

## 10. Testes automatizados

Na primeira implementação, testar criação da aplicação, `GET /health`, OpenAPI e configuração CORS local. Com cada caso de uso, acrescentar testes no nível adequado:

- **Borda (`controllers/`, `schemas/`, handlers de `exceptions/`):** requisição HTTP com `httpx` e dependências FastAPI substituídas, verificando validação, contratos, filtros, paginação e formato de erro.
- **Regras e políticas (`services/`, `security/`):** testes diretos, sem servidor ou PostgreSQL, cobrindo regras, transições, reconciliação da receita e políticas.
- **Persistência (`entities/`, `repositories/`):** testes de integração com PostgreSQL real quando ele for introduzido, verificando mapeamentos ORM, transações e permissões de leitura Gold, escrita operacional e rejeição de escrita pela credencial restrita da IA.

Para receita, comparar resultado do endpoint com casos de referência fornecidos pelo Diagnóstico, inclusive reconciliação `efeito_preco + efeito_volume` e tratamento explícito de mix/cobertura. Para inspeções, testar transições de status e cancelamento. Para IA, testar que falha ou ausência de dados não produz resposta inventada e que a auditoria é persistida pelo caminho correto. Não usar SQLite como prova de comportamento específico do PostgreSQL.

## 11. Passo a passo da implementação futura

1. Confirmar a branch de tarefa a partir de `dev` e preservar alterações locais; integrar por Pull Request, sem mexer em `main` diretamente.
2. Criar manifesto de dependências isolado em `backend/` e o bootstrap mínimo: `app/main.py`, `app/core/config.py`, `app/controllers/health.py` e `tests/`, com CORS restrito, `GET /health` e OpenAPI. Não criar as demais camadas vazias.
3. Adicionar testes iniciais e Ruff; executar verificações e registrar instruções de execução local no README do backend.
4. Fechar com Portal e Diagnóstico os contratos HTTP dos primeiros endpoints, especialmente `/metrics/revenue-variance`, antes de anunciar rotas de negócio. Criar `schemas/`, `services/` e `exceptions/` conforme a necessidade concreta de cada fluxo; criar modelos ORM em `entities/` apenas na etapa de persistência, após validar os contratos físicos pertinentes.
5. Receber da Engenharia de Dados dicionário, grão, chaves, cobertura, regras de carga e amostra reconciliada da Gold; só então escolher driver, configurar PostgreSQL em `core/` e implementar consultas em `repositories/`.
6. Implementar os domínios por prioridade do case, com testes de contrato e integração; definir o ciclo de vida de `inspecoes`, políticas em `security/` e migração operacional quando forem necessárias.
7. Integrar `ai-agent/` pelo controller HTTP, fechar identidade/auditoria e validar permissões de banco, latência e respostas honestas.

## 12. Critérios de aceitação da próxima tarefa de código

- Aplicação FastAPI inicia localmente, expõe `GET /health` em `controllers/health.py` e OpenAPI e possui instruções de execução reproduzíveis.
- `app/main.py` e `core/config.py` têm responsabilidades limitadas à inicialização e configuração; configuração vem do ambiente, sem segredos versionados, e CORS permite apenas origens locais configuradas.
- Apenas arquivos necessários ao bootstrap são criados; `entities/`, `exceptions/`, `repositories/`, `security/`, `services/` e `schemas/` não precisam existir fisicamente antes de haver um caso real.
- Dependências do backend ficam isoladas das da EDA. Testes cobrem saúde, OpenAPI e configuração; lint/formatação passam.
- Nenhuma rota de negócio é publicada com resposta fictícia apresentada como dado real.
- Não há modelo ORM ou schema HTTP definitivo para a Gold, conexão PostgreSQL, biblioteca de IA ou infraestrutura adicional criados antes das respectivas decisões.
- Alteração segue Git Flow por PR para `dev`; execução, commit e PR dependem de tarefa e autorização próprias.

## 13. Riscos, premissas e decisões pendentes

| Tema | Estado e encaminhamento |
| --- | --- |
| Contrato Gold | A [engenharia](../context/03-engenharia-de-dados.md) lista seis tabelas como “implementadas”, mas a [revisão de dados](../context/diagnostico_dados.md) aponta lacunas de GD, perdas, grão, chaves e cobertura. Tratar a lista como proposta até a Engenharia publicar contrato e dicionário aprovados. Não definir schemas Gold aqui. |
| Contrato de interface | A [visão geral](../context/01-visao-geral.md) aponta `coordenacao/contratos-de-interface.md`, ausente no estado atual do repositório. Confirmar onde ficará o contrato vigente. |
| Frequência de carga | [Engenharia](../context/03-engenharia-de-dados.md) prevê workflow incremental diário; [Portal](../context/04-portal-web.md) presume carga mensal do banco local. Decidir cadência, janela de atualização e sinalização de frescor da API. |
| Banco da IA | [IA](../context/05-inteligencia-artificial.md) menciona SQLite/PostgreSQL como premissa; as decisões da Visão Geral e do Portal fixam PostgreSQL. Confirmar a correção documental na tarefa apropriada. |
| Receita e qualidade | Confirmar grão e composição de receita faturada, volume, histórico cadastral, períodos e tratamento de nulos/estornos. [Diagnóstico](../context/06-diagnostico-receita.md) e [revisão da Gold](../context/diagnostico_dados.md) condicionam a decomposição a isso. |
| Inspeções | Validar semântica de cancelamento, transições, priorização e autoria; decidir política de migração da tabela operacional. |
| Segurança e IA | Definir identidade real do usuário, perfis, formato externo de `/ai/ask`, retenção da auditoria, política de exposição de SQL e integração concreta com `ai-agent/`. |
| Insights | Resolver divergência entre disparar LLM a cada abertura de tela e recomendar cache/pré-cálculo; medir latência antes de escolher. |
| Prazo | Priorizar bootstrap, contratos e fluxos obrigatórios; diferenciais de exportação, upload, perfis avançados e avaliação de IA só após os requisitos essenciais. |

## 14. Revisões Gemini e consolidação

Na primeira revisão, o Gemini recomendou explicitar a fronteira `backend/`–`ai-agent/`, separar consulta Text-to-SQL da escrita de auditoria, alinhar o contrato de receita ao Diagnóstico, reservar extensões de inspeções/perfis/contexto de IA e isolar dependências da API. Essas decisões permanecem.

Nesta segunda revisão, o Gemini validou a arquitetura em camadas definida pelo responsável do projeto e recomendou: manter `security/` sem SQL ou conexão; concentrar SQL em `repositories/` com sessões fornecidas por `core/`; separar as camadas `entities/` e `schemas/`; centralizar em `main.py` a tradução das falhas de `exceptions/`; e testar borda, domínio e persistência nos níveis apropriados. Essas recomendações foram incorporadas às seções 4, 7, 8 e 10.

A revisão também reforçou o faseamento: a árvore descreve a arquitetura futura, mas o bootstrap cria somente os arquivos necessários à aplicação e à rota de saúde. Não são exigidos modelos ORM da Gold, interfaces genéricas, três pools, schemas HTTP completos ou provedores em memória para preencher camadas.

