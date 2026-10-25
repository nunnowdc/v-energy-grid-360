# Planejamento do backend FastAPI

## 1. Objetivo e escopo

Consolidar a arquitetura, os requisitos e os contratos planejados da API FastAPI para o Portal Web V-Energy Grid 360. A base da aplicação, configuração local, OpenAPI e rota de saúde já existem; endpoints de negócio, autenticação, persistência PostgreSQL e integração GenAI dependem de implementação e, onde indicado, da validação de contratos. Este documento não cria contratos físicos da Gold nem afirma que rotas planejadas já estejam disponíveis.

O repositório separa `frontend/`, `backend/`, `data-engineering/` e `ai-agent/`. O backend já contém `app/main.py`, configuração, controller de saúde e testes iniciais; a presença desses arquivos não implica implementação dos demais domínios. O `requirements.txt` da raiz atende à EDA e aos notebooks; as dependências da API ficam no próprio `backend/`.

## 2. Requisitos que orientam a estrutura

| Fonte | Requisito e efeito no backend |
| --- | --- |
| [Matriz de rastreabilidade](../context/matriz-rastreabilidade.md) | REQ-PORTAL-01 a 07 exigem indicadores, análise de receita, Visão 360 da UC, fila e ordens de inspeção, continuidade e filtros. REQ-PORTAL-08 a 11 são diferenciais: exportação, upload, perfis e testes. |
| [Portal Web](../context/04-portal-web.md) | FastAPI atende React/TypeScript/Vite; PostgreSQL recebe a Gold exportada e dados operacionais de inspeção. Os caminhos HTTP principais já foram propostos. |
| [Engenharia de Dados](../context/03-engenharia-de-dados.md) e [dicionário Gold](../../data-engineering/relatorio_tabelas/dicionario_dados_gold.md) | A Gold vem do fluxo Databricks Bronze → Silver → Gold → exportação. Há um dicionário recente das tabelas Gold, mas o contrato físico da exportação para o PostgreSQL local e as divergências de regra de negócio da seção 13 ainda exigem validação antes das consultas. |
| [Diagnóstico de Receita](../context/06-diagnostico-receita.md) | REQ-DIAG-01 requer períodos comparáveis, receita faturada e volume faturado, decomposição Shapley de preço e volume, mix e informação de cobertura/qualidade. O Portal deve exibir os mesmos números do diagnóstico. |
| [Inteligência Artificial](../context/05-inteligencia-artificial.md) e [planejamento do agente](../ai/planejamento-ai-agent.md) | REQ-AI-01 a 06 preveem `/ai/ask`, Text-to-SQL com acesso de consulta restrito, auditoria, resposta honesta e insights no Portal; REQ-AI-07 prevê contexto de conversa e REQ-AI-08, avaliação automatizada. A modelagem posterior da equipe de IA acrescenta feedback. A infraestrutura de IA fica para outra tarefa. |
| [Revisões cruzadas](../context/diagnostico_dados.md), [IA/Portal](../context/diagnostico_dev_ia.md) e [IA/SQL](../context/diagnostico_IA_sql.md) | Alertam para lacunas da Gold, latência de insights e necessidade de compartilhar semântica de preço médio e períodos. |

### 2.1 Requisitos funcionais do Portal — obrigatórios

Os identificadores oficiais são os da [matriz de rastreabilidade](../context/matriz-rastreabilidade.md); correspondem, na mesma ordem, a RF-01 a RF-07 das histórias fornecidas. A coluna de API aponta apenas para rotas já planejadas na seção 7. Uma rota relacionada não significa que todos os dados, filtros ou comportamentos da história tenham contrato fechado ou estejam implementados. As fontes Gold citadas abaixo constam do [planejamento do Portal](../context/04-portal-web.md) ou do [dicionário Gold](../../data-engineering/relatorio_tabelas/dicionario_dados_gold.md) e dependem da validação da exportação física, conforme a seção 13.

| ID oficial | História de usuário | API planejada e cobertura | Dependências documentadas e definição pendente |
| --- | --- | --- | --- |
| `REQ-PORTAL-01` (RF-01) | Como diretor, quero ver os principais indicadores do negócio e compará-los entre períodos, para saber rapidamente se estamos indo bem ou mal. | `GET /metrics/general` atende aos indicadores gerais; a comparação entre períodos ainda requer contrato de entrada e saída. | Gold exportada para PostgreSQL; definir indicadores, períodos comparáveis e cobertura dos dados. |
| `REQ-PORTAL-02` (RF-02) | Como diretor comercial, quero entender a variação de receita entre períodos, separando efeito-preço e efeito-volume, e investigá-la por município, bairro e classe até encontrar onde está a queda. | `GET /metrics/revenue-variance` está planejado para decomposição e filtros por município, bairro e classe. | `fact_faturamento`, `fact_leituras`, `dim_unidade_consumidora` e `agg_receita_preco_volume` constam do dicionário Gold; a fórmula dessa agregação diverge da Shapley aprovada pelo Diagnóstico. Resolver antes de servir a métrica (seção 13). |
| `REQ-PORTAL-03` (RF-03) | Como atendente, quero encontrar uma unidade consumidora e ver numa única tela seu histórico de consumo, faturas, medidor, geração própria, interrupções e chamados, para responder ao cliente na hora, inclusive quando ele reclama de conta alta. | `GET /uc/{uc_id}/360` cobre a visão de uma UC identificada; ainda não há rota definida para localizar a UC. O contrato da visão deve confirmar a cobertura de cada informação da história. | O dicionário Gold documenta `dim_unidade_consumidora`, `dim_medidor`, `dim_geracao_distribuida`, `fact_leituras`, `fact_faturamento`, `fact_ocorrencias` e `fact_atendimentos`; disponibilidade no PostgreSQL local e junções devem ser validadas. O histórico de ações dos chamados não está na Gold; histórico disponível requer paginação (seções 9 e 13). |
| `REQ-PORTAL-04` (RF-04) | Como gerente de perdas, quero ver as unidades suspeitas ordenadas por prioridade, com o motivo da suspeita e a energia estimada a recuperar. | `GET /inspections/queue` está planejado para a fila priorizada; os campos de motivo e energia estimada ainda precisam ser confirmados no contrato HTTP. | O dicionário Gold documenta `fila_inspecao`, motivo, score e kWh recuperável estimado; seus pesos ainda precisam de calibração, conforme a seção 13. |
| `REQ-PORTAL-05` (RF-05) | Como gerente de perdas, quero gerar ordens de inspeção a partir da fila, atualizar o status de cada uma, registrar o resultado encontrado em campo e cancelar as que não forem mais necessárias. | `POST /inspections/order`, `PATCH /inspections/{id}` e `DELETE /inspections/{id}` estão planejados para gerar, atualizar/registrar e cancelar, respectivamente; `GET /inspections/queue` fornece a fila de origem. | Dados operacionais de `inspecoes` separados da Gold; definir transições, autoria, persistência e semântica de cancelamento sem apagar o registro (seções 7 e 13). |
| `REQ-PORTAL-06` (RF-06) | Como gerente de operação, quero acompanhar DEC e FEC por alimentador ao longo do tempo e identificar os piores, para direcionar a manutenção preventiva. | `GET /network/continuity` está planejado para DEC/FEC por alimentador e período; a identificação dos piores ainda requer definição de ordenação/recorte no contrato ou tratamento na interface. | O dicionário Gold documenta `agg_continuidade_alimentador`, sua versão anual, `fact_ocorrencias` e `dim_alimentador` (singular); validar exportação e semântica das variantes. |
| `REQ-PORTAL-07` (RF-07) | Como usuário do portal, quero filtrar e recortar as informações conforme a minha necessidade, para chegar rápido ao que procuro. | `GET /filters/options` fornece opções centralizadas; múltiplas seleções são enviadas como parâmetros de consulta às rotas de negócio da seção 7. Os filtros específicos e contratos ainda abertos constam da seção 9. | Depende dos atributos da Gold, do controle de acesso e dos contratos de filtro, ordenação e paginação de cada caso de uso. |

### 2.2 Requisitos funcionais do Portal — diferenciais

Os identificadores oficiais abaixo correspondem a RF-08 a RF-10 das histórias fornecidas. `REQ-PORTAL-11` permanece na matriz como requisito de testes automatizados e na seção 10 deste planejamento; não foi reclassificado como história funcional.

| ID oficial | História de usuário | API planejada e cobertura | Dependências documentadas e definição pendente |
| --- | --- | --- | --- |
| `REQ-PORTAL-08` (RF-08) | Como gerente de perdas, quero exportar a fila de inspeção para enviar à equipe de campo. | `GET /inspections/queue` fornece a fila, mas nenhuma rota ou contrato de exportação foi definido. | Depende da fila e do formato de exportação a acordar com o Portal; o planejamento do Portal menciona CSV para envio ao campo. |
| `REQ-PORTAL-09` (RF-09) | Como gerente de perdas, quero subir pelo portal a planilha que a equipe preenche em campo, para que os resultados sejam registrados sem digitação manual. | `PATCH /inspections/{id}` cobre o registro individual de resultado; nenhuma rota ou contrato de importação em lote foi definido. | Depende do formato da planilha, validação, associação às ordens e regras de escrita operacional, ainda a definir. |
| `REQ-PORTAL-10` (RF-10) | Como usuário, quero entrar com meu perfil e ver as telas específicas do meu cargo. | `POST /auth/login`, `GET /auth/me`, `PATCH /auth/password`, `POST /auth/logout` e `POST /auth/users` estão planejados; a seção 7 registra o RBAC das rotas. | Contas pré-cadastradas por `ADMIN_TI`, JWT de 15 minutos em cookie HttpOnly, modelo mínimo de `usuarios` e controle de telas no Portal; contratos HTTP completos ainda pendentes (seções 7, 9 e 13). |

## 3. Decisões existentes e novas recomendações

**Já documentado:** FastAPI, React + TypeScript + Vite, PostgreSQL local e fluxo da Gold exportada constam da [visão geral](../context/01-visao-geral.md) e do [Portal](../context/04-portal-web.md). O Portal já nomeia os endpoints principais e a escrita operacional de inspeções. O [contexto de IA](../context/05-inteligencia-artificial.md) registra PydanticAI e Gemini 3.1 Flash-Lite, enquanto documentos posteriores de `ai-agent/` indicam outra orquestração; a escolha final da equipe de IA precisa de conciliação (seção 13). O [Diagnóstico](../context/06-diagnostico-receita.md) definiu a decomposição Shapley e os cortes município, bairro e classe.

**Decisão arquitetural do responsável pelo projeto:** organizar o backend em camadas `controllers/`, `entities/`, `exceptions/`, `repositories/`, `security/`, `services/` e `tests/`, preservando `app/main.py` e `core/`. Usar `schemas/` para contratos HTTP quando necessário, separados dos modelos ORM de `entities/`.

**Decisões atuais de integração:** MVP local com PostgreSQL e tabelas Gold estáticas, sem atualização durante o MVP; autenticação e RBAC no FastAPI, sem RLS; cinco cargos `DIRETORIA`, `ATENDIMENTO`, `PERDAS`, `OPERACAO` e `ADMIN_TI`. Contas são pré-cadastradas, sem cadastro público, e somente `ADMIN_TI` cria contas. A equipe do backend responde por autenticação, autorização das rotas e controle de acesso no Portal; o agente de IA e a autorização interna das suas tools pertencem à equipe de IA. A fronteira de identidade e autorização entre as equipes ainda precisa de contrato. Estas decisões prevalecem, para o MVP, sobre premissas antigas de carga periódica e de cadastro em aberto.

**Recomendação de execução, revisada pelo Gemini:** manter uma única aplicação HTTP em `backend/` e materializar cada camada somente ao surgir um caso de uso real. `ai-agent/` permanece responsável pela lógica de IA; o futuro controller das rotas `/ai` será o adaptador HTTP no FastAPI, com a integração concreta entre os módulos definida antes de implementá-la. A arquitetura de pastas é uma direção obrigatória, não uma ordem para criar arquivos vazios no bootstrap.

## 4. Estrutura proposta e responsabilidades

A árvore abaixo representa a **arquitetura de responsabilidades**, não o inventário de arquivos. Os itens marcados `base existente` já constam do backend; os demais são destinos para casos de uso posteriores. Não criar diretórios, classes base ou arquivos vazios para completar o desenho.

```text
backend/
├── app/
│   ├── main.py                    # base existente: aplicação e inicialização
│   ├── core/
│   │   ├── config.py              # base existente: configuração do ambiente
│   │   └── database.py            # futuro: conexões e ciclo de vida PostgreSQL
│   ├── controllers/
│   │   ├── health.py              # base existente: GET /health
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
├── tests/                         # testes iniciais existentes; depois, cada camada
└── manifesto de dependências      # próprio do backend
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
| `security/` | Definir identidade, autenticação, CSRF e RBAC das rotas FastAPI; transmitir contexto de identidade validado à integração com `ai-agent/`. | Não abrir conexão nem executar SQL; não duplicar o parser, o pipeline ou a autorização interna das tools da IA. Privilégios PostgreSQL seguem como proteção dos dados, sem RLS no backend. |
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

`app/core/config.py` lê a configuração do ambiente local; a integração futura acrescentará as configurações de PostgreSQL, segredo de assinatura do JWT, parâmetros do cookie, CORS, rate limiting e timeouts de chamadas de API. Segredos ficam fora do Git. Como o Portal enviará cookie com `credentials: "include"`, CORS deve aceitar apenas origens locais configuradas e credenciais, nunca `*` com credenciais. A rota `GET /health` verifica o processo; eventual checagem de prontidão do PostgreSQL será separada quando o banco existir. A expiração do JWT é de 15 minutos; valores de rate limiting e timeout permanecem pendentes.

## 7. Organização da aplicação e fluxo Controller → Service → Repository

Para um caso de uso com dados, o **controller** recebe a requisição React, valida parâmetros por schemas Pydantic, resolve identidade/dependências com FastAPI e chama o **service**. O service aplica as regras de negócio, consulta ou grava por meio de um **repository** recebido explicitamente, e devolve um resultado sem formato HTTP. O repository usa os modelos ORM de `entities/` para mapear a persistência PostgreSQL quando ela existir. O controller converte o resultado para o schema de resposta; FastAPI publica o contrato OpenAPI. O retorno não deve trazer objetos de sessão ou linhas cruas do driver à borda.

`security/` define e aplica a política RBAC, com identidade obtida de dados validados da sessão; o acesso necessário ao registro do usuário passa por `repositories/`. `repositories/` é a única camada de SQL e usa a credencial adequada entregue por `core/`. Falhas semânticas de `exceptions/` atravessam as camadas; handlers registrados em `main.py` as traduzem centralmente em status HTTP e envelope JSON consistente. Evitar `try/except` repetidos por controller e evitar `HTTPException` dentro de services, entities, repositories ou security. Erros de validação HTTP próprios do FastAPI permanecem tratados na borda.

Para leitura analítica, o service pode transformar diretamente o resultado do repository para uma projeção de resposta: não é obrigatório instanciar um modelo ORM para cada linha consultada. As transições de inspeção e a reconciliação matemática da receita permanecem regras de negócio em `services/`, não em `entities/`. Dependências explícitas permitem substituir services/repositories nos testes sem criar interfaces genéricas antecipadas.

Manter os caminhos já documentados, sem prefixo novo que quebre os consumidores:

| Controller futuro | Endpoints documentados para etapas posteriores |
| --- | --- |
| `metrics` | `GET /metrics/general`, `GET /metrics/revenue-variance` |
| `uc` | `GET /uc/{uc_id}/360` |
| `inspections` | `GET /inspections/queue`, `POST /inspections/order`, `PATCH /inspections/{id}`, `DELETE /inspections/{id}` |
| `network` | `GET /network/continuity` |
| `ai` | `POST /ai/ask`, `GET /ai/insights/{tela}/{entidade_id}`, `GET /ai/audit/{audit_id}`, `POST /ai/feedback` (rotas informadas pela equipe de IA; contratos parciais na seção 9) |
| `auth` | `POST /auth/login`, `GET /auth/me`, `PATCH /auth/password`, `POST /auth/logout`, `POST /auth/users` |
| `filters` | `GET /filters/options` |

`DELETE /inspections/{id}` está descrito como “cancelar”; a futura implementação deve preservar o registro e definir o status de cancelamento no contrato, sujeito à validação do fluxo operacional. Exportação CSV e upload de inspeções são extensões do domínio `inspections`, sem rotas inventadas agora. O RBAC protege as rotas já planejadas; a identidade informada pelo cliente em payloads de IA não substitui a identidade autenticada.

### 7.1 Autenticação e matriz de autorização das rotas

O RBAC é aplicado exclusivamente no FastAPI, sem Row Level Security (RLS) no PostgreSQL. `DIRETORIA` reúne as histórias de diretor e diretor comercial; os demais cargos são `ATENDIMENTO`, `PERDAS`, `OPERACAO` e `ADMIN_TI`. `ADMIN_TI` tem acesso a todas as rotas. As permissões ficam em um único mapa em `security/`: cada endpoint declara sua permissão, e mudanças nas permissões de uma role alteram apenas esse mapa, sem modificar controllers. `POST /auth/login` é a exceção pública necessária para autenticar contas pré-cadastradas. O Portal usa `GET /auth/me` para controlar a navegação; a autorização efetiva ocorre no FastAPI. Conta nova só pode ser criada por `ADMIN_TI`; não há cadastro público nem promoção de cargo pelo próprio usuário.

Na matriz, **E** significa acesso explicitamente exigido por requisito ou decisão atual, **P** significa proposta ainda sujeita a aprovação e **—** significa acesso negado até decisão. A matriz trata da **autorização da rota FastAPI**, não da autorização interna das tools da IA. `POST /auth/login` é público apenas para autenticar contas já pré-cadastradas; por isso fica fora das colunas de usuários autenticados. `GET /health` e a política de acesso à OpenAPI dependem de definição operacional.

| Rotas ou capacidade | `DIRETORIA` | `ATENDIMENTO` | `PERDAS` | `OPERACAO` | `ADMIN_TI` | Fundamento / limite |
| --- | --- | --- | --- | --- | --- | --- |
| `GET /metrics/general`, `GET /metrics/revenue-variance` | E | — | — | — | E | REQ-PORTAL-01/02; diretor e diretor comercial compartilham `DIRETORIA`. |
| `GET /uc/{uc_id}/360` | — | E | P | — | E | REQ-PORTAL-03. A busca da UC não tem rota definida. |
| `GET /inspections/queue`, `POST /inspections/order`, `PATCH /inspections/{id}`, `DELETE /inspections/{id}` | — | — | E | — | E | REQ-PORTAL-04/05; exportação e importação seguem sem rota. |
| `GET /network/continuity` | — | — | — | E | E | REQ-PORTAL-06. |
| `GET /filters/options` | E | E | E | E | E | REQ-PORTAL-07 e decisão de opções centralizadas; o subconjunto de campos autorizado por cargo/tela ainda é P. |
| `GET /auth/me`, `PATCH /auth/password`, `POST /auth/logout` | E | E | E | E | E | Cada usuário autenticado consulta a própria identidade, pode trocar a própria senha e encerrar a sessão no navegador. |
| `POST /auth/users` | — | — | — | — | E | Criação exclusiva de `ADMIN_TI`; não há cadastro público. |
| Rotas `/ai` da tabela acima | P | P | P | P | E | Acesso por cargo e visibilidade de auditoria/SQL ainda dependem de contrato; as tools da IA têm autorização própria sob responsabilidade da equipe de IA. |
| Exportação/importação de inspeções (sem rota) | — | — | E | — | E | REQ-PORTAL-08/09 exigem a capacidade para `PERDAS`; contrato HTTP ainda indefinido. |

`E` para `ADMIN_TI` decorre da decisão de acesso a todas as rotas, inclusive as futuras; isso não altera a responsabilidade da equipe de IA pela autorização interna das ferramentas. Nenhum `P` concede acesso antes da decisão. Os `—` expressam a política conservadora atual para os fluxos listados, sem pressupor que os demais cargos nunca possam receber acesso.

## 8. Preparação para PostgreSQL

PostgreSQL local é o alvo do MVP; a menção alternativa a SQLite no documento de IA não altera essa decisão. A Gold exportada é fonte analítica de leitura e, para o MVP local, suas tabelas serão estáticas, sem rotina de atualização. A tabela operacional `usuarios` e os dados operacionais de inspeção e auditoria ficam separados logicamente da Gold. A futura integração deve usar consultas parametrizadas, filtros e limites explícitos, transações curtas, índices e paginação orientados por consultas medidas. O [dicionário Gold](../../data-engineering/relatorio_tabelas/dicionario_dados_gold.md) documenta 15 entidades; é necessário validar o que será efetivamente exportado ao PostgreSQL e reconciliar regras divergentes antes de codificar consultas.

Com a arquitetura em camadas, `core/` configura e fornece sessões/conexões no ciclo de vida da aplicação; `repositories/` recebe essas sessões e concentra as consultas parametrizadas e operações de persistência. Repositories não criam engines próprias nem leem variáveis de ambiente. Services escolhem o caso de uso, sem conhecer SQL. `security/` aplica políticas na aplicação, sem abrir conexões ou substituir os privilégios do PostgreSQL. Não há RLS no MVP.

A execução do **SQL gerado pela IA** deve usar credencial PostgreSQL com `SELECT` apenas nas tabelas ou visões Gold autorizadas, além de limites de tempo e resultado. O registro de `fact_ai_audit` exigido por REQ-AI-03 usa um repository de **escrita controlada pela aplicação**, nunca a credencial do SQL gerado. A API analítica pode ter sua própria credencial de leitura. São perfis lógicos de permissão; não é necessário criar três pools no bootstrap. A checagem de política em `security/` e a validação SQL do módulo de IA complementam, mas não substituem, os privilégios mínimos no banco.

A extração/exportação inicial da Gold e sua reconciliação pertencem à integração com Engenharia de Dados. O dicionário já foi publicado em `data-engineering/relatorio_tabelas/`; o formato e o mapeamento físico da carga para PostgreSQL ainda devem ser acordados. A decisão de snapshot estático vale para as tabelas Gold do MVP local, sem impedir que a Engenharia mantenha seu próprio pipeline fora dele. Regras de atualização de dados operacionais não se confundem com a Gold estática.

## 9. Endpoints, contratos e integração React/GenAI

Antes de implementar cada endpoint, acordar com o frontend nomes de campos, tipos, unidades, datas e fusos, formato de erro, filtros, ordenação, paginação e casos sem dados. Usar OpenAPI e exemplos revisados como contrato executável. Históricos da UC e a fila de inspeção precisam de paginação; filtros por município, bairro e classe são obrigatórios na análise de receita. O frontend não deve depender de um contrato simplificado provisório.

Para `GET /metrics/revenue-variance`, reservar no contrato lógico os períodos inicial/final, receita, volume e preço médio de cada período, efeitos preço e volume pela fórmula oficial, efeito mix **quando disponível**, contribuição absoluta e percentual, filtros aplicados e informação de cobertura/qualidade. O serviço deve consumir a definição versionada do Diagnóstico, sem refazer silenciosamente a fórmula. O schema HTTP será fechado quando a métrica e a Gold estiverem validadas; valores simulados não devem ser publicados como resposta analítica real.

### 9.1 Autenticação, sessão e contas

**Decisões aprovadas:** contas pré-cadastradas exclusivamente por `ADMIN_TI`, sem cadastro público. O usuário entra com e-mail e senha, pode alterar a própria senha quando quiser e não é obrigado a fazê-lo no primeiro acesso. Senhas têm no mínimo 8 caracteres e são armazenadas com hash seguro. O JWT expira em **15 minutos** e fica em cookie `HttpOnly`; após a expiração, é necessário novo login. Não há refresh token nem revogação do JWT no servidor. O logout remove o cookie do navegador por `POST /auth/logout`. O FastAPI aplica proteção CSRF básica e rate limiting; as chamadas de API têm timeout, sem limites numéricos definidos para estes dois últimos. A identidade e o cargo confiáveis vêm da autenticação no backend, nunca de um campo de cargo ou `user_id` enviado pelo cliente.

**Modelo mínimo aprovado da tabela operacional `usuarios`:**

| Campo | Tipo |
| --- | --- |
| `id` | UUID PRIMARY KEY |
| `nome` | VARCHAR(150) |
| `email` | VARCHAR(255) UNIQUE |
| `senha_hash` | TEXT |
| `role` | VARCHAR(30) |

`role` representa uma das cinco roles da seção 7.1. O backend atribui a role na criação exclusiva por `ADMIN_TI` e não permite que o usuário altere a própria role. Não há outros campos ou tabelas auxiliares no modelo mínimo aprovado.

**Configuração mínima recomendada para o MVP local:** explicitar `SameSite=Lax` no cookie; usar `Secure` quando a aplicação estiver sob HTTPS e configurar o ambiente HTTP local de modo compatível; permitir no CORS somente a origem configurada do Portal com credenciais; validar a origem das requisições que alteram estado como proteção CSRF adicional ao `SameSite`. A configuração local deve usar o mesmo hostname para Portal e API para manter a semântica do cookie. Atributos restantes do cookie, mecanismo exato de validação CSRF, algoritmo/parâmetros do hash e detalhes de implantação ainda precisam de contrato; esta recomendação não acrescenta campos à tabela.

| Método e rota | Objetivo e responsabilidade | Serviço responsável; consumidor | Entrada e saída informadas | Dependências e situação |
| --- | --- | --- | --- | --- |
| `POST /auth/login` | Autenticar uma conta pré-cadastrada e estabelecer a sessão. | FastAPI; tela de login do Portal. | Entrada: e-mail e senha. Saída: JWT de 15 minutos em cookie `HttpOnly`; corpo e erros específicos ainda indefinidos. | **Decidido** quanto a rota e mecanismo; contrato HTTP detalhado pendente. |
| `GET /auth/me` | Fornecer ao Portal a identidade e o cargo autenticados para controle de telas e estado da sessão. | FastAPI; Portal. | Lê o cookie; campos da resposta ainda não definidos. | **Decidido** quanto a rota e objetivo; schema pendente. |
| `PATCH /auth/password` | Permitir alteração opcional da própria senha a qualquer momento. | FastAPI; Portal. | A nova senha deve ter no mínimo 8 caracteres; demais dados de entrada/saída, confirmação da senha atual e tratamento de sessões existentes ainda indefinidos. | **Decidido** quanto a rota e objetivo; somente usuário autenticado; contrato pendente. |
| `POST /auth/logout` | Remover o cookie de autenticação do navegador, sem revogar o JWT no servidor. | FastAPI; Portal. | Corpo e resposta ainda indefinidos; a operação remove o cookie. | **Decidido** quanto a rota e efeito no cookie; contrato HTTP detalhado pendente. |
| `POST /auth/users` | Criar conta pré-cadastrada e atribuir cargo por ação exclusiva de `ADMIN_TI`. | FastAPI; interface administrativa do Portal, se houver. | Campos de cadastro, entrega da senha inicial e resposta ainda indefinidos. | **Decidido** quanto a rota e exclusividade; modelo físico e contrato pendentes. |

O Portal usa Fetch API com TanStack Query, `credentials: "include"`, timeout e tratamento explícito de `401` (sessão ausente/inválida), `403` (acesso negado) e `429` (limite de requisições). O Portal consulta `GET /auth/me` para controlar a navegação; o FastAPI autoriza cada rota. O logout limpa o cookie, mas um JWT eventualmente copiado continua válido até seus 15 minutos de expiração, pois não existe revogação no servidor. Permanecem pendentes os contratos HTTP detalhados, o tratamento da sessão após troca de senha, o provisionamento inicial de contas e os valores de rate limiting e timeout.

### 9.2 Opções e aplicação dos filtros

**Decisões aprovadas:** `GET /filters/options` centraliza as opções dos filtros, com `fields` opcional. Município, bairro e classe são compartilhados entre as telas onde se aplicam; o React filtra localmente os bairros pelo município selecionado. A seleção múltipla usa checkboxes e é enviada aos endpoints de negócio como query parameters repetidos: **OR** entre valores do mesmo filtro e **AND** entre filtros diferentes. Os períodos são selecionados no React e validados pelo FastAPI. Como as tabelas Gold do MVP são estáticas, o Portal reutiliza as opções com TanStack Query e `staleTime: Infinity`. Nomes aceitos em `fields`, formato da resposta, nomes dos query parameters, formatos dos valores e política de acesso às opções por cargo continuam pendentes; não há schema HTTP inventado aqui.

| Tela / rota de negócio | Filtros definitivos | Limite atual |
| --- | --- | --- |
| Indicadores — `GET /metrics/general` | Município, classe, período e comparar com. | Indicadores e parâmetros de período ainda sem contrato. |
| Receita — `GET /metrics/revenue-variance` | Município, bairro, classe, período base e comparar com. | Definir parâmetros, granularidade e compatibilidade com a Gold e com Shapley. |
| Fila de inspeções — `GET /inspections/queue` | Motivo, classe, município e bairro. | Definir parâmetros, múltipla seleção e paginação. |
| Continuidade — `GET /network/continuity` | Alimentador, causa, município e período. | Definir parâmetros e tratamento da variante com/sem dias críticos da Gold. |
| Visão 360 — `GET /uc/{uc_id}/360` | Nenhum filtro de tela; a UC vem da rota. | A busca prévia da UC continua sem endpoint. |

Município, bairro e classe são vocabulário comum de opções, sem presumir que cada tela terá os três filtros. O dicionário Gold documenta esses atributos em `dim_unidade_consumidora` e a correção de encoding dos bairros; é preciso verificar sua preservação na exportação ao PostgreSQL local. Se as opções forem sensíveis ao cargo, o cache do Portal deverá respeitar a sessão autenticada; a forma de invalidá-lo é uma **sugestão técnica pendente**, não contrato aprovado.

### 9.3 Rotas de IA informadas pela equipe de IA

As quatro rotas abaixo constam da modelagem enviada pela equipe de IA para o roteador `ai_router`, montado em `/ai` no FastAPI. **Aprovado pela equipe de IA** identifica a rota e o objetivo informados, não um contrato HTTP integral validado com Portal, segurança e backend. Os exemplos de valores e o SQL da resposta ilustram a modelagem; não confirmam nomes físicos, resultados reais da Gold nem autorização para expor SQL ao usuário.

| Método e rota | Objetivo e responsabilidade | Serviço responsável; consumidor | Entrada informada | Saída informada | Dependências | Situação |
| --- | --- | --- | --- | --- | --- | --- |
| `POST /ai/ask` | Receber pergunta contextualizada e devolver resposta do agente Text-to-SQL com referência de auditoria. | FastAPI expõe a rota; lógica do agente em `ai-agent/`; chat do Portal React consome. | Corpo com `user_id`, `session_id`, `message` e `context` contendo `page` e `current_uc_id` no exemplo (este último pode ser `null`). Obrigatoriedade e validações ainda não definidas. `user_id` do corpo não autentica o usuário. | Exemplo `200 OK`: `answer`, `sql`, `audit_id`, `selo_confianca`, `fontes` e `tempo_ms`. Tipos, nulidade e política de exposição ainda precisam de validação. | Identidade autenticada no FastAPI, histórico de sessão, metadados Gold validados, autorização interna das tools pela IA, execução SQL somente leitura e registro de auditoria por escrita controlada. | **Aprovado pela equipe de IA** quanto à rota e ao formato exemplificado; contrato externo e segurança **pendentes de definição**. |
| `GET /ai/insights/{tela}/{entidade_id}` | Fornecer insight proativo referente a uma tela e entidade, sem bloquear a carga dos dados principais da tela. | FastAPI expõe a rota; geração e obtenção do insight pertencem ao módulo de IA; telas do Portal React consomem. | Parâmetros de caminho `tela` e `entidade_id`; exemplo `visao_360_uc` e `45892`. Domínio de valores e validações não definidos. | Exemplo `200 OK`: `tela`, `entidade_id`, `insight_texto`, `metricas_destaque` (com chaves exemplificadas `variacao_pct`, `consumo_atual_kwh`, `faturas_aberto`), `selo` e `tempo_ms`. | Dados de origem validados; estratégia de geração/armazenamento dos insights e política de atualização ainda dependem de alinhamento. | **Aprovado pela equipe de IA** quanto à rota e ao formato exemplificado; semântica, disponibilidade e contrato completo **pendentes de definição**. |
| `GET /ai/audit/{audit_id}` | Exibir na gaveta “Como a IA chegou nisso?” os passos executados, a query gerada e o tempo em milissegundos. | FastAPI expõe a rota; serviço de auditoria da IA fornece os dados; Portal React consome. | `audit_id` no caminho; formato e regras de acesso não informados. | Passos, query e tempo descritos conceitualmente; não foi fornecido schema de resposta nem exemplo HTTP. | Auditoria registrada por `POST /ai/ask`, consulta aos registros operacionais e política de visibilidade do SQL e dos dados. | **Aprovado pela equipe de IA** quanto à rota e ao objetivo; contrato e autorização **pendentes de definição**. |
| `POST /ai/feedback` | Receber avaliação positiva ou negativa do analista sobre uma resposta para alimentar o índice de acurácia de REQ-AI-08. | FastAPI expõe a rota; serviço de avaliação da IA processa o feedback; Portal React envia. | Intenção de 👍/👎 informada; corpo, vínculo com resposta/auditoria e identidade não definidos. | Não informada. | Resposta previamente apresentada e mecanismo de avaliação; armazenamento, agregação e autorização ainda não definidos. | **Aprovado pela equipe de IA** quanto à rota e ao objetivo; contratos de entrada/saída e processamento **pendentes de definição**. |

### 9.4 Fluxo Portal → FastAPI → agente de IA

1. O Portal React usa Fetch API com `credentials: "include"` para chamar o FastAPI. Para o chat, envia a pergunta e os campos de contexto informados em `POST /ai/ask`; para uma tela com insights, consulta `GET /ai/insights/{tela}/{entidade_id}` separadamente da rota de dados da tela. Aplica timeout e trata `401`, `403` e `429`.
2. O controller FastAPI valida o cookie/sessão, aplica o RBAC da rota, valida a requisição e encaminha o caso de uso à integração com `ai-agent/`. A identidade transmitida ao módulo vem da autenticação; eventual `user_id` no corpo exemplificado pela IA não tem autoridade. O módulo de IA cuida do pipeline Text-to-SQL, da geração/obtenção de insights e da autorização interna de suas tools. A forma concreta de chamada entre `backend/` e `ai-agent/` e a propagação da identidade/cargo ainda serão definidas; não pressupor serviço HTTP separado.
3. No fluxo de pergunta, a equipe de IA valida a autorização das tools e o SQL gerado para leitura; a execução usa credencial restrita às fontes Gold autorizadas. A trilha de auditoria é persistida por caminho operacional de escrita distinto. O FastAPI devolve a resposta ao Portal com `audit_id`, conforme o exemplo da equipe de IA.
4. Quando o usuário abre a gaveta de auditoria, o Portal consulta `GET /ai/audit/{audit_id}`. Quando avalia a resposta, envia `POST /ai/feedback`. A vinculação e as permissões desses fluxos precisam ser acordadas antes da implementação.

**Conciliação documental:** a [revisão Portal/IA](../context/diagnostico_dev_ia.md) tratava contexto de tela e feedback como recomendações; a modelagem posterior da equipe de IA os incluiu nas rotas acima. O [planejamento do agente](../ai/planejamento-ai-agent.md) ainda cita `GET /ai/insights/{uc_id}` e `ai-agent/controller.py`, enquanto a nova modelagem informa `GET /ai/insights/{tela}/{entidade_id}` e o planejamento deste backend reserva `backend/app/controllers/ai.py` como adaptador HTTP. O roteador `ai_router` já aparece em `ai-agent/src/api/ai_router.py`, mas não está montado no `backend/app/main.py`; resolver a forma de integração e a atualização do documento do agente antes de implementar. O planejamento do agente também situa execução SQL, conexões, auditoria e migrações em `ai-agent/`; acordar a fronteira com `core/` e `repositories/` do backend sem tomar para esta equipe a autorização interna das tools. A estratégia de cache/batch descrita naquele planejamento é uma decisão do módulo de IA a conciliar com a nova rota, sem impor aqui tabela ou contrato físico.

## 10. Testes automatizados

Os testes iniciais de aplicação, `GET /health` e OpenAPI já existem no backend; sua presença não comprova os novos fluxos. Com cada caso de uso, acrescentar testes no nível adequado:

- **Borda (`controllers/`, `schemas/`, handlers de `exceptions/`):** requisição HTTP com `httpx` e dependências FastAPI substituídas, verificando validação, contratos, filtros, paginação e formato de erro.
- **Regras e políticas (`services/`, `security/`):** testes diretos, sem servidor ou PostgreSQL, cobrindo regras, transições, reconciliação da receita e políticas.
- **Persistência (`entities/`, `repositories/`):** testes de integração com PostgreSQL real quando ele for introduzido, verificando mapeamentos ORM, transações e permissões de leitura Gold, escrita operacional e rejeição de escrita pela credencial restrita da IA.

Para receita, comparar resultado do endpoint com casos de referência fornecidos pelo Diagnóstico, inclusive reconciliação `efeito_preco + efeito_volume` e tratamento explícito de mix/cobertura. Para inspeções, testar transições de status e cancelamento. Para IA, testar que falha ou ausência de dados não produz resposta inventada e que a auditoria é persistida pelo caminho correto. Não usar SQLite como prova de comportamento específico do PostgreSQL.

Para autenticação, testar que apenas contas pré-cadastradas entram, `ADMIN_TI` cria usuários, senhas de criação/troca têm no mínimo 8 caracteres e hash seguro, o próprio usuário pode trocar senha sem alterar role, o JWT expira em 15 minutos e o logout remove o cookie sem revogação no servidor. Exercitar proteção CSRF, `401`, `403`, `429`, rate limiting e timeout; verificar no FastAPI a matriz E/P/— e a propagação de identidade validada à IA. Para filtros, testar query parameters repetidos, OR dentro de um filtro, AND entre filtros, validação de períodos, relação município–bairro, autorização das opções e consistência entre filtros e agregações, conforme os contratos fechados.

## 11. Passo a passo da implementação futura

1. Especificar os contratos ainda pendentes de autenticação, autorização, filtros e erros com o Portal; preparar migração e provisionamento da tabela `usuarios` aprovada, detalhar a configuração local de cookie/CSRF e definir valores de rate limiting e timeout. Preservar a arquitetura em camadas existente.
2. Reconciliar o dicionário Gold com o contrato físico da exportação local e com a fórmula de receita aprovada pelo Diagnóstico; obter amostra reconciliada antes das consultas analíticas.
3. Em tarefas de código próprias, integrar PostgreSQL em `core/` e `repositories/`, implementar autenticação e RBAC no FastAPI e os consumidores Fetch API/TanStack Query no Portal, com testes de contrato, segurança e integração.
4. Implementar os domínios por prioridade do case, definindo o ciclo de vida de inspeções e sem publicar dados fictícios como reais.
5. Acordar com a equipe de IA a fronteira de identidade, a autorização interna das tools, o roteador HTTP e a auditoria; então integrar `ai-agent/` e verificar permissões de banco, latência e respostas honestas.

## 12. Critérios para futuras tarefas de código

- A base FastAPI, `GET /health` e OpenAPI continuam funcionais; `app/main.py` e `core/config.py` permanecem limitados à inicialização e configuração, sem segredos versionados, e CORS permite apenas origens locais configuradas com credenciais.
- Criar somente arquivos necessários aos casos de uso; dependências do backend ficam isoladas das da EDA. Testes pertinentes e lint/formatação passam.
- Autenticação, RBAC e filtros respeitam as decisões das seções 7 e 9 e os contratos fechados antes da implementação; as rotas da IA não recebem identidade confiável do corpo da requisição.
- Nenhuma rota de negócio é publicada com resposta fictícia apresentada como dado real.
- Não há modelo ORM ou schema HTTP definitivo para a Gold, biblioteca de IA ou infraestrutura adicional criados antes das respectivas decisões.
- Alteração segue Git Flow por PR para `dev`; execução, commit e PR dependem de tarefa e autorização próprias.

## 13. Riscos, premissas e decisões pendentes

| Tema | Estado e encaminhamento |
| --- | --- |
| Contrato Gold | O [dicionário Gold recente](../../data-engineering/relatorio_tabelas/dicionario_dados_gold.md) descreve 15 entidades, incluindo GD, inspeções, fila, receita e continuidade, enquanto o [contexto antigo de Engenharia](../context/03-engenharia-de-dados.md) lista seis tabelas. Validar conjunto, grão, chaves, cobertura, versão e mapeamento físico efetivamente exportados ao PostgreSQL local. O dicionário não aprova por si só os contratos HTTP nem resolve divergências de cálculo. |
| Contrato de interface | A [visão geral](../context/01-visao-geral.md) aponta `coordenacao/contratos-de-interface.md`, ausente no estado atual do repositório. Confirmar onde ficará o contrato vigente. |
| Frequência de carga | **Decisão para o MVP local:** snapshot Gold estático no PostgreSQL, sem atualização. Os textos antigos de [Engenharia](../context/03-engenharia-de-dados.md) (incremental diário) e [Portal](../context/04-portal-web.md) (carga mensal local) não descrevem a operação deste MVP; o pipeline Databricks externo pode continuar. Registrar data/versão do snapshot e decidir a origem dessa informação quando o contrato de exportação for fechado. |
| Banco da IA | [IA](../context/05-inteligencia-artificial.md) menciona SQLite/PostgreSQL como premissa; as decisões da Visão Geral e do Portal fixam PostgreSQL. Confirmar a correção documental na tarefa apropriada. |
| Modelo e orquestração de IA | O [contexto de IA](../context/05-inteligencia-artificial.md) registra PydanticAI/Gemini 3.1 Flash-Lite; o [planejamento do agente](../ai/planejamento-ai-agent.md) registra Gemini 2.0 Flash Lite; [decisões posteriores de arquitetura](../../ai-agent/arquitetura_e_integracao/decisoes_arquitetura_agente.md) apontam LangGraph e OpenRouter/9router. A equipe de IA deve confirmar o stack vigente e a forma de integração; o backend não o decide aqui. |
| Receita e qualidade | O [Diagnóstico aprovado](../context/06-diagnostico-receita.md) requer decomposição Shapley; o [dicionário Gold](../../data-engineering/relatorio_tabelas/dicionario_dados_gold.md) descreve `agg_receita_preco_volume` com efeito-volume ao preço inicial e efeito-preço aplicado ao volume final, fórmula diferente. Além disso, `fact_faturamento` não contém kWh faturado e o volume Gold vem de `fact_leituras` (consumo medido). Diagnóstico, Engenharia e Portal precisam reconciliar fórmula, definição de volume, períodos, cobertura e qualidade antes do endpoint de receita. Não trocar a fórmula aprovada implicitamente. |
| Inspeções | Validar semântica de cancelamento, transições, autoria e migração da tabela operacional. A `fila_inspecao` Gold já documenta score e energia estimada, mas o [dicionário](../../data-engineering/relatorio_tabelas/dicionario_dados_gold.md) informa pesos a calibrar e vazamento na calibração atual; não tratar prioridade como modelo validado. Exportação e importação continuam sem contrato HTTP. |
| Visão 360 e chamados | `fact_atendimentos` traz chamados, mas o histórico de tratativas não foi publicado na Gold porque os rótulos da fonte não são confiáveis ([pendência de atendimentos](../../data-engineering/relatorio_tabelas/pendencia_historico_atendimentos.md)). Definir com Portal e Engenharia o alcance de “histórico de chamados” para a tela, sem presumir eventos inexistentes. |
| Dados pessoais | O [levantamento LGPD](../../data-engineering/relatorio_tabelas/levantamento_lgpd.md) e o dicionário classificam campos de cadastro de UC, inadimplência e suspeitas/inspeções como dados pessoais de maior risco de exposição. Fechar a exposição de campos por rota, logs e auditoria conforme os cargos aprovados antes de publicar a Visão 360 e a fila. |
| Identidade e sessão | Cinco roles, tabela mínima `usuarios`, contas pré-cadastradas por `ADMIN_TI`, senha mínima de 8 caracteres com hash seguro, JWT de 15 minutos em cookie `HttpOnly`, CSRF básico, novo login após expiração e logout que remove o cookie sem revogação estão decididos. Faltam provisionamento inicial, entrega/recuperação de senha, contratos HTTP detalhados das cinco rotas de autenticação, atributos restantes do cookie, validação CSRF concreta, tratamento da sessão após troca de senha e valores de rate limiting e timeout. As configurações de `Secure`, `SameSite`, CORS e verificação de origem da seção 9.1 são recomendação técnica para o MVP local. |
| Filtros e Portal | `GET /filters/options`, `fields` opcional, checkboxes, query parameters repetidos, OR dentro de cada filtro, AND entre filtros, períodos validados pelo FastAPI, `staleTime: Infinity` e filtros por tela estão decididos nos limites da seção 9. Ainda faltam nomes dos parâmetros, formatos dos valores, schema de opções, autorização por campo, paginação/ordenação e a política de cache por sessão; conferir a preservação da normalização de bairros na exportação Gold. O [README do frontend](../../frontend/README.md) ainda apresenta a biblioteca de API como aberta e deverá ser alinhado à decisão Fetch API + TanStack Query em tarefa própria. |
| Segurança e IA | O backend autentica e autoriza rotas; a equipe de IA autoriza internamente as tools. Falta contrato de propagação de identidade/cargo verificados, permissões de `/ai` por cargo, obrigatoriedade dos campos de `/ai/ask`, erros, retenção da auditoria, exposição de SQL e autorização de `GET /ai/audit/{audit_id}`. [Decisões de acoplamento da IA](../../ai-agent/arquitetura_e_integracao/decisoes_acoplamento_dev_genai_dados.md) propõem `SET LOCAL ROLE` por perfil no PostgreSQL; isso não equivale a RLS, mas a estratégia interna da IA precisa ser conciliada com o RBAC do FastAPI e com o acesso somente leitura, sem atribuí-la ao backend. |
| Insights | Conciliar `GET /ai/insights/{tela}/{entidade_id}` da nova modelagem com `GET /ai/insights/{uc_id}` do planejamento de IA; definir telas e entidades aceitas, origem e atualização dos insights e comportamento sem dados. O cache descrito no planejamento de IA contempla somente UC e texto do insight; validar como atender a nova rota e seus campos, sem presumir mudança de esquema. O planejamento de IA prevê cache/batch, enquanto o documento de contexto descreve geração na abertura da tela; alinhar os documentos antes da implementação. |
| Feedback e auditoria | Definir corpos, schemas de resposta, vínculo entre feedback e resposta/auditoria, persistência, política de acesso e forma de cálculo do índice de acurácia. O registro de auditoria descrito no planejamento de IA não especifica passos executados, `selo_confianca` ou `fontes`, nem armazenamento de feedback; validar a origem desses dados antes de assumir alterações físicas. A equipe de IA informou rota e objetivo, sem esses contratos. |
| Prazo | A base FastAPI já existe. Priorizar contratos, autenticação/RBAC, filtros e fluxos obrigatórios; exportação, upload e avaliação de IA continuam diferenciais, enquanto autenticação de `REQ-PORTAL-10` já tem decisões de base para viabilizar o acesso. |

## 14. Revisões Gemini e consolidação

O Gemini recomendou explicitar a fronteira `backend/`–`ai-agent/`, separar consulta Text-to-SQL da escrita de auditoria, alinhar o contrato de receita ao Diagnóstico, reservar extensões de inspeções/perfis/contexto de IA e isolar dependências da API. Essas decisões permanecem.

O Gemini validou a arquitetura em camadas definida pelo responsável do projeto e recomendou: manter `security/` sem SQL ou conexão; concentrar SQL em `repositories/` com sessões fornecidas por `core/`; separar as camadas `entities/` e `schemas/`; centralizar em `main.py` a tradução das falhas de `exceptions/`; e testar borda, domínio e persistência nos níveis apropriados. Essas recomendações foram incorporadas às seções 4, 7, 8 e 10.

A revisão também reforçou o faseamento: a árvore descreve as responsabilidades futuras; a base com rota de saúde já existe. Não são exigidos modelos ORM da Gold, interfaces genéricas, três pools, schemas HTTP completos ou provedores em memória para preencher camadas.
