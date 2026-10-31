# Planejamento do backend FastAPI

## 1. Objetivo e escopo

Consolidar a arquitetura, os requisitos e os contratos da API FastAPI para o Portal Web V-Energy Grid 360. Na branch `dev` examinada, estão registrados `/api/health`, filtros, Indicadores, Receita, Visão 360, Fila de Inspeção, Continuidade e as quatro rotas de IA. A implementação de Continuidade chegou à `dev` pelo merge do PR #67; as cinco rotas de autenticação continuam planejadas e ainda não estão registradas. A autenticação e o RBAC aqui definidos **ainda não protegem** as rotas registradas. Este documento não cria contratos físicos da Gold nem confunde rotas planejadas com rotas disponíveis.

O repositório separa `frontend/`, `backend/`, `data-engineering/` e `ai-agent/`. O backend contém `app/main.py`, configuração, conexão PostgreSQL, controllers, services, repositories, schemas e testes para os domínios registrados. O `requirements.txt` da raiz atende à EDA e aos notebooks; as dependências da API ficam no próprio `backend/`.

## 2. Requisitos que orientam a estrutura

| Fonte | Requisito e efeito no backend |
| --- | --- |
| [Matriz de rastreabilidade](../context/matriz-rastreabilidade.md) | REQ-PORTAL-01 a 07 exigem indicadores, análise de receita, Visão 360 da UC, fila e ordens de inspeção, continuidade e filtros. REQ-PORTAL-08 a 11 são diferenciais: exportação, upload, perfis e testes. |
| [Portal Web](../context/04-portal-web.md) | FastAPI atende React/TypeScript/Vite; PostgreSQL recebe a Gold exportada e dados operacionais de inspeção. Os caminhos HTTP principais já foram propostos. |
| [Engenharia de Dados](../context/03-engenharia-de-dados.md) e [dicionário Gold](../../data-engineering/relatorio_tabelas/dicionario_dados_gold.md) | A Gold vem do fluxo Databricks Bronze → Silver → Gold → exportação. Há um dicionário recente das tabelas Gold, mas o contrato físico da exportação para o PostgreSQL local e as divergências de regra de negócio da seção 13 ainda exigem validação antes das consultas. |
| [Diagnóstico de Receita](../context/06-diagnostico-receita.md) | REQ-DIAG-01 originalmente prevê decomposição Shapley e períodos comparáveis; **para o MVP, foi aprovada a adoção dos períodos fixos e da fórmula já publicados em `agg_receita_preco_volume` na Gold**. A divergência com o diagnóstico permanece identificada como decisão de escopo do MVP, sem alterar os arquivos de origem de outras equipes. |
| [Inteligência Artificial](../context/05-inteligencia-artificial.md) e [planejamento do agente](../ai/planejamento-ai-agent.md) | REQ-AI-01 a 06 preveem `/api/ai/ask`, Text-to-SQL com acesso de consulta restrito, auditoria, resposta honesta e insights no Portal; REQ-AI-07 prevê contexto de conversa e REQ-AI-08, avaliação automatizada. A modelagem posterior da equipe de IA acrescenta feedback. A infraestrutura de IA fica para outra tarefa. |
| [Revisões cruzadas](../context/diagnostico_dados.md), [IA/Portal](../context/diagnostico_dev_ia.md) e [IA/SQL](../context/diagnostico_IA_sql.md) | Alertam para lacunas da Gold, latência de insights e necessidade de compartilhar semântica de preço médio e períodos. |

### 2.1 Requisitos funcionais do Portal — obrigatórios

Os identificadores oficiais são os da [matriz de rastreabilidade](../context/matriz-rastreabilidade.md); correspondem, na mesma ordem, a RF-01 a RF-07 das histórias fornecidas. A coluna de API aponta apenas para rotas já planejadas na seção 7. Uma rota relacionada não significa que todos os dados, filtros ou comportamentos da história tenham contrato fechado ou estejam implementados. As fontes Gold citadas abaixo constam do [planejamento do Portal](../context/04-portal-web.md) ou do [dicionário Gold](../../data-engineering/relatorio_tabelas/dicionario_dados_gold.md) e dependem da validação da exportação física, conforme a seção 13.

| ID oficial | História de usuário | API planejada e cobertura | Dependências documentadas e definição pendente |
| --- | --- | --- | --- |
| `REQ-PORTAL-01` (RF-01) | Como diretor, quero ver os principais indicadores do negócio e compará-los entre períodos, para saber rapidamente se estamos indo bem ou mal. | `GET /api/metrics/general` está planejado para indicadores gerais; a comparação entre períodos ainda requer contrato de entrada e saída. | `agg_receita_mensal` traz receita, consumo medido e preço médio por mês, município, bairro e classe; `dim_competencia` delimita os meses. A lista de KPIs, seus recortes e sua cobertura ainda precisam de definição. |
| `REQ-PORTAL-02` (RF-02) | Como diretor comercial, quero entender a variação de receita, separando efeito-preço e efeito-volume e investigando município, bairro e classe. | `GET /api/metrics/revenue-variance` expõe os efeitos e os **períodos fixos (primeiro ano × últimos 12 meses)** conforme publicados pela Gold; no MVP o Portal não permite escolher outros períodos. | Utilizar diretamente `agg_receita_preco_volume` e suas definições de efeito-preço/efeito-volume, sem recalcular Shapley no backend. Eventuais recortes que não estejam disponíveis nessa agregação permanecem limitados à cobertura da Gold. |
| `REQ-PORTAL-03` (RF-03) | Como atendente, quero encontrar uma unidade consumidora e consultar seus dados e históricos na Visão 360. | O Portal recebe o ID completo digitado pelo usuário, navega para `/visao-360/{uc_id}` e consulta `GET /api/uc/{uc_id}/360`; retorna `404` se a UC não existir. **Não haverá uma rota adicional de busca de UC no MVP.** | Consultar por `dim_unidade_consumidora.id_uc` e relacionar medidor, GD, leituras, faturas, ocorrências e atendimentos conforme a Gold disponível; históricos sujeitos a paginação. |
| `REQ-PORTAL-04` (RF-04) | Como gerente de perdas, quero ver as unidades suspeitas ordenadas por prioridade, com o motivo da suspeita e a energia estimada a recuperar. | `GET /api/inspections/queue` está planejado para expor a fila Gold na prioridade já calculada; os campos de motivo e energia estimada ainda precisam ser confirmados no contrato HTTP. | `fila_inspecao` traz `prioridade`, `score`, `motivo_suspeita` e `kwh_recuperavel_estimado_ano`, além de município, bairro e classe. `motivo_suspeita` reúne regras separadas por `;` e os pesos do score ainda precisam de calibração pela equipe responsável, sem recálculo no backend (seção 13). |
| `REQ-PORTAL-05` (RF-05) | Como gerente de perdas, quero gerar ordens de inspeção a partir da fila, atualizar o status de cada uma, registrar o resultado encontrado em campo e cancelar as que não forem mais necessárias. | `POST /api/inspections/order`, `PATCH /api/inspections/{id}` e `DELETE /api/inspections/{id}` estão planejados para gerar, atualizar/registrar e cancelar, respectivamente; `GET /api/inspections/queue` fornece a fila de origem. | Dados operacionais de `inspecoes` separados da Gold; definir transições, autoria, persistência e semântica de cancelamento sem apagar o registro (seções 7 e 13). |
| `REQ-PORTAL-06` (RF-06) | Como gerente de operação, quero acompanhar DEC e FEC por alimentador ao longo do tempo e identificar os piores, para direcionar a manutenção preventiva. | `GET /api/network/continuity` está implementado na `dev`, com dois períodos selecionáveis, ranking por DEC do período comparado, série mensal e ocorrências. | `agg_continuidade_alimentador` publica DEC/FEC mensais; `dim_alimentador` traz o cadastro. A rota agrega os indicadores por alimentador, sem produzir DEC/FEC municipal ou por causa; `fact_ocorrencias` fornece as contagens e causas em grão de UC interrompida. A homologação formal da agregação temporal pela Engenharia de Dados permanece pendente. |
| `REQ-PORTAL-07` (RF-07) | Como usuário do Portal, quero filtrar as informações relevantes para encontrar o que procuro. | `GET /api/filters/options` retorna cinco grupos: `competencias`, `municipios` (com `bairros`), `classes`, `alimentadores` (com `municipios`) e `causas`, no formato acordado com o frontend. Nas rotas de negócio, cada filtro categórico aceita **uma única opção por campo**; sem query parameters repetidos. | As opções vêm da Gold. O filtro de motivo da fila fica fora do MVP até Engenharia de Dados e Perdas definirem seu vocabulário atômico; não criar rota ou lista provisória. |

### 2.2 Requisitos funcionais do Portal — diferenciais

Os identificadores oficiais abaixo correspondem a RF-08 a RF-10 das histórias fornecidas. `REQ-PORTAL-11` permanece na matriz como requisito de testes automatizados e na seção 10 deste planejamento; não foi reclassificado como história funcional.

| ID oficial | História de usuário | API planejada e cobertura | Dependências documentadas e definição pendente |
| --- | --- | --- | --- |
| `REQ-PORTAL-08` (RF-08) | Como gerente de perdas, quero exportar a fila de inspeção para enviar à equipe de campo. | `GET /api/inspections/queue` fornece a fila, mas nenhuma rota ou contrato de exportação foi definido. | Depende da fila e do formato de exportação a acordar com o Portal; o planejamento do Portal menciona CSV para envio ao campo. |
| `REQ-PORTAL-09` (RF-09) | Como gerente de perdas, quero subir pelo portal a planilha que a equipe preenche em campo, para que os resultados sejam registrados sem digitação manual. | `PATCH /api/inspections/{id}` cobre o registro individual de resultado; nenhuma rota ou contrato de importação em lote foi definido. | Depende do formato da planilha, validação, associação às ordens e regras de escrita operacional, ainda a definir. |
| `REQ-PORTAL-10` (RF-10) | Como usuário, quero entrar com meu perfil e ver as telas específicas do meu cargo. | `POST /api/auth/login`, `GET /api/auth/me`, `PATCH /api/auth/password`, `POST /api/auth/logout` e `POST /api/auth/users` estão planejados para implementação; seus contratos HTTP foram validados pelo Frontend no [documento técnico](impl_autenticação-backend.md#7-contratos-http-aprovados-com-o-frontend). A seção 7 registra o RBAC das rotas. | Contas pré-cadastradas, JWT de 15 minutos no cookie `vgrid360_access_token` e controle de telas por perfil; faltam a implementação dos endpoints e a integração React, não a definição dos seus requests, responses ou status. |

## 3. Decisões existentes e novas recomendações

**Já documentado:** FastAPI, React + TypeScript + Vite, PostgreSQL local e exportação da Gold constam da visão geral e do Portal. O documento original de Diagnóstico prevê Shapley e períodos comparáveis, mas para o **MVP a decisão atual é utilizar a fórmula da Gold e comparar apenas o primeiro ano com os últimos 12 meses**. As equipes responsáveis deverão estar cientes dessa diferença; não implementar decomposição paralela no FastAPI. A implementação de IA segue sob responsabilidade da equipe de IA, incluindo a conciliação de seus documentos.

**Decisão arquitetural do responsável pelo projeto:** organizar o backend em camadas `controllers/`, `entities/`, `exceptions/`, `repositories/`, `security/`, `services/` e `tests/`, preservando `app/main.py` e `core/`. Usar `schemas/` para contratos HTTP quando necessário, separados dos modelos ORM de `entities/`.

**Decisões atuais de integração:** MVP exclusivamente local com PostgreSQL e Gold estática, prefixo HTTP global `/api`, autenticação/RBAC no FastAPI sem RLS e perfis `DIRETORIA`, `ATENDIMENTO`, `PERDAS`, `OPERACAO` e `ADMIN_TI` (sempre em maiúsculas). Somente `ADMIN_TI` cria contas; não há cadastro público e a troca de senha no primeiro acesso não é obrigatória. A equipe do backend autentica e autoriza rotas, e a equipe de IA cuida da autorização interna de suas tools. A Gold é a referência para as métricas analíticas. O Portal adotará filtros de **seleção única por campo** e Visão 360 consultada pelo **ID exato da UC**.

**Diretriz arquitetural aprovada para o MVP:** a Gold é a fonte de verdade dos dados, indicadores e regras analíticas definidos pela Engenharia de Dados. O FastAPI consulta a Gold no PostgreSQL, aplica os filtros solicitados pelo Portal, valida autenticação e RBAC e entrega os resultados ao React por HTTP, preservando unidades e significados. Não duplica, reinterpreta ou recalcula regras analíticas já implementadas na Gold. Qualquer lógica analítica adicional só pode ser considerada quando um requisito não for atendido pela Gold, após identificar e documentar a lacuna e alinhá-la com a equipe responsável; não se planejam tabelas, agregações ou algoritmos analíticos adicionais sem necessidade comprovada. As regras operacionais de usuários, sessões e ordens de inspeção continuam no backend.

**Recomendação de execução, revisada pelo Gemini:** manter uma única aplicação HTTP em `backend/` e materializar cada camada somente ao surgir um caso de uso real. `ai-agent/` permanece responsável pela lógica de IA; seu `ai_router` já é montado no FastAPI, embora ainda precise receber a autenticação e o RBAC deste planejamento. A arquitetura de pastas é uma direção obrigatória, não uma ordem para criar arquivos vazios.

## 4. Estrutura proposta e responsabilidades

A árvore abaixo representa a **arquitetura de responsabilidades**, não um inventário completo de arquivos. A marcação indica o estado na branch `dev` examinada; não criar diretórios, classes base ou arquivos vazios para completar o desenho.

```text

backend/

├── app/

│   ├── main.py                    # base existente: aplicação e inicialização

│   ├── core/

│   │   ├── config.py              # base existente: configuração do ambiente

│   │   └── database.py            # existente: conexões PostgreSQL

│   ├── controllers/

│   │   ├── health.py              # existente; GET /api/health público no MVP local

│   │   ├── auth.py                # futuro: sessão e contas

│   │   ├── filters.py             # existente: opções centralizadas

│   │   ├── metrics.py             # existente: indicadores e receita

│   │   ├── uc.py                  # existente: Visão 360 e históricos

│   │   ├── inspections.py         # existente: fila e ordens

│   │   ├── network.py             # existente: continuidade

│   │   └── ai.py                  # não existe: ai_router é montado de ai-agent/

│   ├── entities/                  # futuro: modelos ORM SQLAlchemy do PostgreSQL

│   ├── exceptions/               # futuro: falhas semânticas independentes de HTTP

│   ├── repositories/             # existente: consultas e persistência PostgreSQL

│   ├── security/                 # futuro: identidade, autorização e políticas

│   ├── services/                 # existente: casos de uso e regras de negócio

│   └── schemas/                  # existente: contratos HTTP Pydantic

├── tests/                         # testes iniciais existentes; depois, cada camada

└── manifesto de dependências      # próprio do backend

```

| Camada | Responsabilidade | Limite explícito |
| --- | --- | --- |
| `app/main.py` | Montar FastAPI, registrar controllers e handlers de exceção; futuramente gerenciar o ciclo de vida da infraestrutura. | Não conter consultas nem regra de negócio. |
| `core/` | Ler/validar configuração; futuramente criar e fornecer conexões ou sessões PostgreSQL para o ciclo de vida da aplicação. | Não conter consultas de domínio nem regras de autorização. |
| `controllers/` | Definir `APIRouter`, receber e validar parâmetros HTTP, aplicar dependências de autenticação/autorização e traduzir resultados para a resposta; preservar os caminhos acordados com React. | Não executar SQL nem calcular regras de negócio; `health.py` pode responder diretamente por não haver caso de uso de domínio. |
| `schemas/` | DTOs Pydantic de entrada/saída HTTP, paginação e formato de erro quando houver contratos reais. | Permanecer independentes dos modelos ORM de `entities/`; não mapear tabelas PostgreSQL. |
| `services/` | Orquestrar casos de uso e transformar resultados apenas quando necessário para o contrato; manter as regras operacionais próprias do backend. | Não conhecer `Request`, `HTTPException`, engine ou detalhes de SQL; não reproduzir fórmulas, scores ou indicadores já definidos na Gold. Lógica analítica adicional exige lacuna documentada e alinhamento prévio. |
| `entities/` | Conter modelos ORM do SQLAlchemy para mapear tabelas, colunas, chaves e relacionamentos do PostgreSQL, somente após confirmação dos contratos físicos pertinentes. | Não validar HTTP nem concentrar regras de negócio; não definir modelos Gold definitivos antes da validação pela Engenharia de Dados. |
| `repositories/` | Concentrar consultas parametrizadas, filtros e leitura dos dados Gold, além da persistência operacional, recebendo sessão/conexão configurada; devolver projeções necessárias ao serviço. | Não ler ambiente, criar engine global, expor objetos HTTP, decidir políticas de acesso nem reproduzir cálculos analíticos já disponíveis na Gold. Uma consulta analítica simples não precisa passar por uma entidade idêntica à linha e ao schema. |
| `security/` | Manter identidade, autenticação, JWT, CSRF e RBAC das rotas FastAPI; transmitir contexto de identidade validado à integração com `ai-agent/`. | Não abrir conexão nem executar SQL; não duplicar o parser, o pipeline ou a autorização interna das tools da IA. Privilégios PostgreSQL seguem como proteção dos dados, sem RLS no backend. |
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

`app/core/config.py` já lê a configuração local do PostgreSQL e das origens CORS; a implementação da autenticação acrescentará segredo de assinatura do JWT e a configuração de cookie decidida na seção 9.1. Segredos ficam fora do Git. Em chamadas entre origens, CORS deve aceitar apenas as origens locais explícitas do frontend, nunca `*`; usar `allow_credentials=True`. O proxy Vite atual mantém os caminhos relativos `/api` na mesma origem do navegador, com `credentials: "same-origin"` nas chamadas autenticadas. `credentials: "include"` só será necessário se futuramente houver chamadas diretas entre origens, com CORS e cookies configurados para isso. A validação de `Origin` nas escritas é distinta de CORS e inclui a origem local do Swagger, conforme a seção 9.1. `GET /api/health` e as URLs `/api/docs`, `/api/redoc` e `/api/openapi.json` já estão registradas. A expiração do JWT será de 15 minutos; valores de rate limiting e timeout permanecem pendentes.

## 7. Organização da aplicação e fluxo Controller → Service → Repository

Para um caso de uso com dados, o **controller** recebe a requisição React, valida parâmetros por schemas Pydantic, aplica as dependências de autorização com FastAPI e chama o **service**. O service orquestra o caso de uso e recebe explicitamente o **repository**, que consulta a Gold no PostgreSQL com os filtros validados ou grava dados operacionais quando cabível. Modelos ORM de `entities/` mapeiam a persistência apenas quando necessários. O controller converte o resultado para o schema de resposta; FastAPI publica o contrato OpenAPI. O retorno não deve trazer objetos de sessão ou linhas cruas do driver à borda.

`security/` define e aplica a política RBAC, com identidade obtida de dados validados da sessão; o acesso necessário ao registro do usuário passa por `repositories/`. `repositories/` é a única camada de SQL e usa a credencial adequada entregue por `core/`. Falhas semânticas de `exceptions/` atravessam as camadas; handlers registrados em `main.py` as traduzem centralmente em status HTTP e envelope JSON consistente. Evitar `try/except` repetidos por controller e evitar `HTTPException` dentro de services, entities, repositories ou security. Erros de validação HTTP próprios do FastAPI permanecem tratados na borda.

Para leitura analítica, o service pode apenas organizar a projeção recebida do repository para a resposta HTTP: não é obrigatório instanciar um modelo ORM para cada linha consultada. Fórmulas, scores, prioridades e indicadores publicados na Gold devem ser consumidos com suas unidades e significados originais. As transições de ordens de inspeção permanecem regras operacionais em `services/`; a decisão do MVP é consumir a decomposição Gold; a diferença em relação à Shapley prevista pelo Diagnóstico deve ser comunicada, sem recalcular outra fórmula no backend. Dependências explícitas permitem substituir services/repositories nos testes sem criar interfaces genéricas antecipadas.

Aplicar o prefixo global `/api` uma única vez às rotas HTTP, inclusive autenticação, IA, filtros e saúde. As rotas já registradas e as URLs geradas pelo FastAPI para documentação e esquema OpenAPI usam esse prefixo (`/api/docs`, `/api/redoc` e `/api/openapi.json`). As rotas novas de autenticação devem seguir o mesmo padrão.

| Domínio / controller | Estado na branch examinada | Endpoints |
| --- | --- | --- |
| `metrics` | Implementado | `GET /api/metrics/general`, `GET /api/metrics/revenue-variance` |
| `uc` | Implementado | `GET /api/uc/{uc_id}/360` |
| `inspections` | Implementado | `GET /api/inspections/queue`, `GET /api/inspections/orders`, `POST /api/inspections/order`, `PATCH /api/inspections/{id}`, `DELETE /api/inspections/{id}` |
| `network` | Implementado e integrado à `dev` pelo PR #67 | `GET /api/network/continuity` |
| `ai_router` de `ai-agent/src/api/ai_router.py` | Implementado e montado no FastAPI, ainda sem RBAC | `POST /api/ai/ask`, `GET /api/ai/insights/{tela}/{entidade_id}`, `GET /api/ai/audit/{audit_id}`, `POST /api/ai/feedback` |
| `auth` | Planejado | `POST /api/auth/login`, `GET /api/auth/me`, `PATCH /api/auth/password`, `POST /api/auth/logout`, `POST /api/auth/users` |
| `filters` | Implementado | `GET /api/filters/options` |
| `health` | Implementado | `GET /api/health` |

`DELETE /api/inspections/{id}` executa cancelamento lógico e preserva a ordem. Exportação CSV e upload de inspeções são capacidades futuras sem rotas definidas. O RBAC desta seção é **planejado** para as rotas existentes e futuras; a identidade informada pelo cliente em payloads de IA não substitui a identidade autenticada.

### 7.1 Autenticação e matriz de autorização dos endpoints

O RBAC será aplicado no FastAPI, sem Row Level Security (RLS) no PostgreSQL. Há um único mapa central de permissões em `security/`, indexado por **método HTTP e rota**; uma dependência compartilhada consulta esse mapa, em vez de espalhar condicionais pelos controllers. O fluxo é: autenticar as credenciais, emitir JWT com identificador estável do usuário, validar o token e consultar o usuário e seu `perfil` persistido, verificar a permissão da rota e permitir a chamada ou retornar `403`. Token ausente, inválido ou expirado retorna `401`. `ADMIN_TI` acessa todos os endpoints protegidos e tem as rotas administrativas exclusivas. A autorização interna das ferramentas da IA permanece com a equipe de IA.

Na matriz, **✓** = permitido para usuário autenticado, **—** = negado e **público** = não exige login. “Implementado” significa que a rota está registrada na branch `dev`; **não** significa que o RBAC já esteja aplicado. `POST /api/auth/login`, `GET /api/health` e as rotas locais de documentação/OpenAPI são públicos; as demais rotas de autenticação estão planejadas. Os endpoints de IA estão montados pelo roteador `ai_router` em `app/main.py`, mas ainda não têm a proteção de autenticação/RBAC proposta. O controller de Continuidade está registrado em `app/main.py` e foi integrado à `dev` pelo PR #67; suas permissões da matriz permanecem para o RBAC futuro.

| Método e endpoint | Estado na `dev` | `DIRETORIA` | `ATENDIMENTO` | `PERDAS` | `OPERACAO` | `ADMIN_TI` |
| --- | --- | :---: | :---: | :---: | :---: | :---: |
| `GET /api/health` | Implementado; público | público | público | público | público | público |
| `GET /api/docs` | Implementado; público no MVP local | público | público | público | público | público |
| `GET /api/openapi.json` | Implementado; público no MVP local | público | público | público | público | público |
| `GET /api/redoc` | Implementado; público no MVP local | público | público | público | público | público |
| `POST /api/auth/login` | Planejado | público | público | público | público | público |
| `POST /api/auth/logout` | Planejado | ✓ | ✓ | ✓ | ✓ | ✓ |
| `GET /api/auth/me` | Planejado | ✓ | ✓ | ✓ | ✓ | ✓ |
| `PATCH /api/auth/password` | Planejado | ✓ | ✓ | ✓ | ✓ | ✓ |
| `POST /api/auth/users` | Planejado | — | — | — | — | ✓ |
| `GET /api/filters/options` | Implementado | ✓ | ✓ | ✓ | ✓ | ✓ |
| `GET /api/metrics/general` | Implementado | ✓ | — | — | — | ✓ |
| `GET /api/metrics/revenue-variance` | Implementado | ✓ | — | — | — | ✓ |
| `GET /api/uc/{uc_id}/360` | Implementado | — | ✓ | ✓ | — | ✓ |
| `GET /api/network/continuity` | Implementado | ✓ | — | — | ✓ | ✓ |
| `GET /api/inspections/queue` | Implementado | — | — | ✓ | — | ✓ |
| `GET /api/inspections/orders` | Implementado | — | — | ✓ | — | ✓ |
| `POST /api/inspections/order` | Implementado | — | — | ✓ | — | ✓ |
| `PATCH /api/inspections/{id}` | Implementado | — | — | ✓ | — | ✓ |
| `DELETE /api/inspections/{id}` | Implementado | — | — | ✓ | — | ✓ |
| `POST /api/ai/ask` | Implementado | ✓ | ✓ | ✓ | ✓ | ✓ |
| `GET /api/ai/insights/{tela}/{entidade_id}` | Implementado | ✓ | ✓ | ✓ | ✓ | ✓ |
| `POST /api/ai/feedback` | Implementado | ✓ | ✓ | ✓ | ✓ | ✓ |
| `GET /api/ai/audit/{audit_id}` | Implementado | — | — | — | — | ✓ |

Os cinco endpoints operacionais de Fila de Inspeção são exclusivos de `PERDAS` e `ADMIN_TI`; `DIRETORIA` e `OPERACAO` não os acessam. Exportação e importação da fila são capacidades futuras para `PERDAS` e `ADMIN_TI`, **sem método, rota ou contrato HTTP definidos**; não aparecem como endpoints implementados na matriz. Saúde e documentação/OpenAPI permanecem públicos no MVP executado localmente, sem RBAC. Os caminhos conhecidos do FastAPI como `/docs` e `/openapi.json` estão configurados nesta aplicação com o prefixo aprovado: `/api/docs` e `/api/openapi.json`; `/api/redoc` segue a mesma política. Não há aliases sem `/api` registrados na branch examinada.

### 7.2 Matriz definitiva de acesso às telas

| Tela | `DIRETORIA` | `ATENDIMENTO` | `PERDAS` | `OPERACAO` | `ADMIN_TI` |
| --- | :---: | :---: | :---: | :---: | :---: |
| Indicadores | ✓ | — | — | — | ✓ |
| Receita | ✓ | — | — | — | ✓ |
| Visão 360 | — | ✓ | ✓ | — | ✓ |
| Fila de Inspeção | — | — | ✓ | — | ✓ |
| Continuidade | ✓ | — | — | ✓ | ✓ |

O frontend deve obter `perfil` de `GET /api/auth/me` para controlar navegação e ações. Esse controle visual não substitui a autorização do backend. A matriz de telas é coerente com as respectivas rotas de negócio acima; `/api/filters/options` e as rotas comuns de IA têm acesso transversal, enquanto a auditoria detalhada da IA é exclusiva de `ADMIN_TI`. O frontend atual ainda utiliza um usuário de teste em `use-usuario.ts`, não a rota `/api/auth/me`.

## 8. Preparação para PostgreSQL

PostgreSQL local é o alvo do MVP; a menção alternativa a SQLite no documento de IA não altera essa decisão. A Gold exportada é fonte analítica de leitura e, para o MVP local, suas tabelas serão estáticas, sem rotina de atualização. A tabela operacional `usuarios` e os dados operacionais de inspeção e auditoria ficam separados logicamente da Gold. A futura integração deve usar consultas parametrizadas, filtros e limites explícitos, transações curtas, índices e paginação orientados por consultas medidas. O [dicionário Gold](../../data-engineering/relatorio_tabelas/dicionario_dados_gold.md) documenta 15 entidades; é necessário validar o que será efetivamente exportado ao PostgreSQL e reconciliar regras divergentes antes de codificar consultas.

Com a arquitetura em camadas, `core/` configura e fornece sessões/conexões no ciclo de vida da aplicação; `repositories/` recebe essas sessões e concentra as consultas parametrizadas e operações de persistência. Repositories não criam engines próprias nem leem variáveis de ambiente. Services escolhem o caso de uso, sem conhecer SQL. `security/` aplica políticas na aplicação, sem abrir conexões ou substituir os privilégios do PostgreSQL. Não há RLS no MVP.

A execução do **SQL gerado pela IA** deve usar credencial PostgreSQL com `SELECT` apenas nas tabelas ou visões Gold autorizadas, além de limites de tempo e resultado. O registro de `fact_ai_audit` exigido por REQ-AI-03 usa um repository de **escrita controlada pela aplicação**, nunca a credencial do SQL gerado. A API analítica pode ter sua própria credencial de leitura. São perfis lógicos de permissão; não é necessário criar três pools no bootstrap. A checagem de política em `security/` e a validação SQL do módulo de IA complementam, mas não substituem, os privilégios mínimos no banco.

A extração/exportação inicial da Gold e sua reconciliação pertencem à integração com Engenharia de Dados. O dicionário já foi publicado em `data-engineering/relatorio_tabelas/`; o formato e o mapeamento físico da carga para PostgreSQL ainda devem ser acordados. A decisão de snapshot estático vale para as tabelas Gold do MVP local, sem impedir que a Engenharia mantenha seu próprio pipeline fora dele. Regras de atualização de dados operacionais não se confundem com a Gold estática.

## 9. Endpoints, contratos e integração React/GenAI

Antes de implementar cada endpoint, acordar com o frontend nomes de campos, tipos, unidades, datas e fusos, formato de erro, filtros, ordenação, paginação e casos sem dados. Usar OpenAPI e exemplos revisados como contrato executável. Históricos da UC e a fila de inspeção precisam de paginação; filtros por município, bairro e classe são obrigatórios na análise de receita. O frontend não deve depender de um contrato simplificado provisório.

Para `GET /api/metrics/revenue-variance`, utilizar **somente os períodos fixos disponíveis na Gold (primeiro ano × últimos 12 meses)** e expor diretamente os valores de `agg_receita_preco_volume`: efeito-volume = `(kwh_p1 - kwh_p0) × preco_p0`; efeito-preço = `(preco_p1 - preco_p0) × kwh_p1`. Os campos de receita, volume, preços e efeitos devem preservar nomes, unidades, grão e significado disponíveis na Gold; a definição detalhada da resposta HTTP depende do contrato com o frontend. **Não implementar Shapley nem períodos livres no MVP.** O antigo requisito do Diagnóstico permanece como divergência documental explícita, não como bloqueio para usar a fórmula Gold aprovada para o MVP. Não prometer efeito mix ou recortes que a agregação não forneça.

### 9.1 Autenticação, sessão e contas

**Contas e senhas — decisões aprovadas:** não há cadastro público. A primeira conta `ADMIN_TI` será criada por script local manual; as demais, exclusivamente por `ADMIN_TI` em `POST /api/auth/users`. O usuário entra com e-mail e senha, não precisa trocá-la no primeiro acesso e pode alterá-la quando quiser, desde que autenticado e após confirmar a senha atual. Não há recuperação pública de senha neste MVP. Tanto na criação quanto na alteração, a senha tem no mínimo **8 caracteres**, sem exigências adicionais de composição. Armazenar apenas o hash **Argon2id**, nunca texto puro; a nova senha substitui `senha_hash` por um hash novo. Senhas, hashes e tokens não entram em respostas ou logs.

**Modelo mínimo aprovado da única tabela operacional de contas, `usuarios`** (sem SQL ou migração nesta etapa):

| Campo | Tipo | Regra |
| --- | --- | --- |
| `id` | `UUID` | Chave primária, identificador único. |
| `nome` | `VARCHAR(150)` | Obrigatório. |
| `email` | `VARCHAR(255)` | Obrigatório e único. |
| `senha_hash` | `VARCHAR(255)` | Obrigatório; hash seguro da senha. |
| `perfil` | `VARCHAR(30)` | Obrigatório; somente `DIRETORIA`, `ATENDIMENTO`, `PERDAS`, `OPERACAO` ou `ADMIN_TI`. |
| `criado_em` | `TIMESTAMP` | Obrigatório; data e hora de criação da conta. |

As restrições de chave primária, unicidade, obrigatoriedade e domínio do `perfil` devem ser garantidas no PostgreSQL quando a tabela for implementada. O usuário não altera o próprio perfil. Não adicionar `ativo`, `primeiro_acesso`, `ultimo_login`, tabela de sessão ou outros campos sem aprovação. O nome persistido é **`perfil`**, nunca `role`.

**Email na criação e no login:** remover espaços nas extremidades e converter para minúsculas antes de buscar ou persistir. Após a normalização, exigir a presença de `@` e no máximo 255 caracteres, sem dependência adicional apenas para essa validação. Esta decisão aprova a sintaxe mínima que o [documento técnico](impl_autenticação-backend.md#3-tabela-usuarios-entidade-e-persistência) ainda rotula como proposta do Frontend. Preservar a unicidade do valor normalizado no PostgreSQL; não introduzir outras regras de normalização.

**Bootstrap da primeira conta `ADMIN_TI`:** um script futuro, executado manualmente somente no ambiente local, verificará a existência da conta pelo e-mail único `adminti.vgrid360@visagio.com`. Se o e-mail ainda não existir, criará o usuário com `nome = admin_ti`, `perfil = ADMIN_TI`, `id` UUID gerado na criação e `criado_em` preenchido com a data e hora reais da execução. A senha inicial será definida por quem executar o script e deverá ter no mínimo 8 caracteres; não haverá senha fixa ou padrão no código. Preferir recebê-la por variável de ambiente no momento da execução, sem armazená-la em texto puro, deixá-la no código versionado ou registrá-la em logs. Persistir somente o hash Argon2id. Se a conta já existir, o script não alterará senha, perfil ou qualquer outro dado. O bootstrap não criará tabelas, serviços adicionais ou endpoint HTTP público. Esta seção define apenas o comportamento; não implementa o script.
O bootstrap cria apenas essa primeira conta; não há criação automática de usuários demonstrativos.

**Criação das demais contas:** `POST /api/auth/users` será exclusivo de `ADMIN_TI`. O administrador informará nome, email, um dos cinco perfis permitidos e senha inicial com pelo menos 8 caracteres, pelo Swagger ou por formulário administrativo que utilize o mesmo endpoint. O backend validará a unicidade do email normalizado, gerará UUID, preencherá `criado_em` e persistirá somente o hash Argon2id. A resposta `201` conterá apenas `id`, `nome`, `email` e `perfil`, sem `senha_hash`. Email duplicado retorna `409`. Não haverá convite por email, cadastro público, recuperação pública de senha ou troca obrigatória no primeiro login.

**JWT e cookie — MVP exclusivamente local:** o JWT identifica o usuário, expira em **15 minutos** e é transportado exclusivamente pelo cookie `vgrid360_access_token`, com `HttpOnly=True`, `Secure=False`, `SameSite=Lax`, `Path=/` e expiração coerente com a do token. `Secure=False` é uma decisão restrita ao HTTP local; não é configuração adequada para exposição pública. Ao expirar, é necessário novo login. Não haverá refresh token, lista de revogação, sessões persistidas no banco nem serviço externo de autenticação. `POST /api/auth/logout` remove o cookie no navegador. Após `PATCH /api/auth/password`, a sessão atual permanece autenticada e não se emite outro JWT. O token atual mantém a expiração original ou sai do navegador no logout; outros tokens já emitidos podem continuar válidos até expirarem, sem revogação no servidor.

**CORS e CSRF proporcionais ao MVP:** o frontend usa caminhos relativos `/api` pelo proxy Vite e `credentials: "same-origin"` (padrão do `fetch`); assim, o navegador envia o cookie nas chamadas autenticadas da mesma origem. `credentials: "include"` só será necessário se futuramente houver chamadas diretas entre origens, com CORS e cookies adequados. Para esse acesso entre origens, configurar CORS no FastAPI com `allow_credentials=True`, sem `*`, e com as origens do frontend `http://localhost:5173` e `http://127.0.0.1:5173` explicitamente permitidas. Manter `SameSite=Lax` e usar hostname consistente no navegador.

A validação do cabeçalho `Origin` nas operações que alteram estado é distinta de CORS. Sua lista local permitida contém `http://localhost:5173`, `http://127.0.0.1:5173` e `http://127.0.0.1:8000`; a terceira origem atende ao Swagger em `/api/docs`, que chama a própria API na mesma origem e não precisa de CORS. O navegador envia `Origin` em `POST`, `PATCH` e `DELETE` mesmo quando o proxy Vite encaminha a chamada. Se `Origin` estiver presente, validar essa lista e rejeitar divergências; se estiver ausente, permitir a requisição no MVP local após as demais verificações aplicáveis. A ausência de `Origin` não é falha de autenticação: JWT e RBAC continuam obrigatórios nas rotas protegidas, inclusive para operações pelo Swagger. `POST /api/auth/login` permanece público, sem JWT ou RBAC prévio, mas também valida `Origin` quando presente. Aceitar ausência de `Origin` é uma simplificação do MVP local e **não oferece proteção CSRF completa**; CORS e `HttpOnly` isoladamente também não eliminam CSRF. Não adicionar token CSRF, serviço externo, proxy reverso adicional, HTTPS ou infraestrutura de produção por padrão.

**Autenticação e autorização:** o backend valida o JWT, carrega o usuário e o `perfil` persistido e consulta o mapa central da seção 7.1. Responder `401` para token ausente, inválido ou expirado; `403` para usuário autenticado sem permissão. O frontend usará `GET /api/auth/me` para obter o perfil e construir a navegação; o FastAPI decide o acesso efetivo. Dados de identidade ou `user_id` enviados pelo cliente, inclusive ao agente de IA, não substituem a identidade autenticada. O backend responde pela autenticação, contas, senhas e RBAC dos endpoints; a equipe de IA autoriza internamente as ferramentas do agente.

| Método e rota | Objetivo e responsabilidade | Serviço responsável; consumidor | Entrada e saída informadas | Dependências e situação |
| --- | --- | --- | --- | --- |
| `POST /api/auth/login` | Autenticar uma conta existente e emitir o cookie. | FastAPI; tela de login do Portal. | JSON `{ "email", "senha" }`; `200` com `{ "id", "nome", "email", "perfil" }` e `Set-Cookie`; `401` para credenciais inválidas. | **Contrato validado pelo Frontend; rota planejada**, pública e sem cadastro. |
| `GET /api/auth/me` | Informar ao Portal a identidade e o `perfil` autenticados. | FastAPI; Portal. | Cookie `vgrid360_access_token`; `200` com `{ "id", "nome", "email", "perfil" }`; `401` se token ausente, inválido ou expirado. | **Contrato validado pelo Frontend; rota planejada**, autenticada. |
| `PATCH /api/auth/password` | Alterar a própria senha, sem troca obrigatória no primeiro acesso. | FastAPI; Portal. | JSON `{ "senha_atual", "nova_senha" }`; `204` sem corpo, mantendo a sessão; `400` para senha atual incorreta. | **Contrato validado pelo Frontend; rota planejada**, autenticada. |
| `POST /api/auth/logout` | Remover o cookie de autenticação do navegador. | FastAPI; Portal. | Sem corpo; `204` sem corpo e cookie removido; `401` se o cookie já estiver inválido ou expirado. | **Contrato validado pelo Frontend; rota planejada**, autenticada; sem revogação no servidor. |
| `POST /api/auth/users` | Criar contas pré-cadastradas. | FastAPI; administração local. | JSON `{ "nome", "email", "perfil", "senha" }`; `201` com `{ "id", "nome", "email", "perfil" }`; `409` para email duplicado. | **Contrato validado pelo Frontend; rota planejada**, exclusiva de `ADMIN_TI`; sem cadastro público. |

Os cinco contratos HTTP foram validados pela equipe do Frontend no [documento técnico](impl_autenticação-backend.md#7-contratos-http-aprovados-com-o-frontend), incluindo `422` para request inválido, `401` para ausência/invalidade/expiração do JWT, `403` para falta de permissão ou `Origin` rejeitada e respostas seguras `500/503` quando aplicáveis. A especificação técnica futura deve reproduzir esses contratos, sem reabri-los ou criar endpoints adicionais de gerenciamento por suposição. O Frontend espera `/api/auth/me` antes de exibir telas protegidas, distingue `401` inicial (login sem aviso), `401` no formulário de login (credenciais incorretas) e `401` durante o uso (limpa cache e vai a `/login?motivo=sessao-expirada`); `403` mantém a sessão. Depois de logout, limpa o cache e volta a `/login` mesmo se o cookie tiver expirado. A navegação prioriza a URL solicitada quando autorizada; caso contrário, DIRETORIA e ADMIN_TI vão a Indicadores, OPERACAO a Continuidade e ATENDIMENTO e PERDAS à Visão 360. O frontend espelha essas permissões em `config/perfis.ts`, sem substituir o RBAC FastAPI. Rate limiting e timeouts continuam pendentes de dimensionamento.

### 9.2 Opções e aplicação dos filtros

**Contrato aprovado com o frontend para o MVP:** `GET /api/filters/options` retorna **exatamente cinco grupos**: `competencias`, `municipios` (com `bairros` aninhados), `classes`, `alimentadores` (objetos com `codigo` e `municipios`) e `causas` (`string[]`). Os três primeiros preservam a estrutura anterior; os dois últimos são uma extensão aditiva. Não retornar `motivos`, nem aceitar o parâmetro `fields` ou contextos por tela. Os valores abaixo são **ilustrativos**, não o conteúdo literal de uma Gold exportada:

```json
{
  "competencias": ["2022-07", "2022-08", "2026-06"],
  "municipios": [
    {
      "nome": "Recife",
      "bairros": ["Boa Viagem", "Casa Forte"]
    }
  ],
  "classes": ["RESIDENCIAL", "COMERCIAL", "INDUSTRIAL", "RURAL", "PODER_PUBLICO"],
  "alimentadores": [
    {
      "codigo": "ALM-REC-008",
      "municipios": ["Recife"]
    }
  ],
  "causas": ["NAO IDENTIFICADA", "NAO INFORMADA", "VEGETACAO"]
}
```

| Campo JSON | Fonte no dicionário Gold | Regra de apresentação |
| --- | --- | --- |
| `competencias` | `dim_competencia.mes_referencia` (`yyyy-MM`), ordenável por `dim_competencia.competencia`. | Meses da Gold em ordem cronológica. O dicionário cobre 2022-07 a 2026-06; confirmar a exportação física. A presença do mês no seletor não garante dados em toda métrica. |
| `municipios[].nome`, `municipios[].bairros` | Pares distintos de `dim_unidade_consumidora.municipio` e `.bairro`. | Municípios e seus respectivos bairros, sem duplicatas, em ordem alfabética. Preservar a grafia Gold; validar eventuais valores ausentes. |
| `classes` | Valores distintos de `dim_unidade_consumidora.classe`. | Preservar exatamente valores e grafia da Gold, inclusive `RESIDENCIAL`, `COMERCIAL`, `INDUSTRIAL`, `RURAL` e `PODER_PUBLICO` quando presentes no snapshot. |
| `alimentadores[].codigo`, `alimentadores[].municipios` | `dim_alimentador.alimentador` e pares distintos de `dim_unidade_consumidora.alimentador` e `.municipio`, ligados pelo código do alimentador. | Um objeto por código Gold, com todos os municípios atendidos em ordem alfabética. `dim_alimentador.municipio_principal` não representa a lista completa; preservar os códigos Gold e não presumir validade histórica desse vínculo cadastral. |
| `causas` | Valores distintos de `fact_ocorrencias.causa`. | Preservar a grafia e ordenar deterministicamente. `NAO INFORMADA` e `NAO IDENTIFICADA` são categorias Gold distintas; não fundi-las. |

**Aplicação dos filtros:** o Portal usa **seleção única por campo categórico**. Cada rota de negócio recebe no máximo um valor por query parameter de município, bairro, classe, alimentador ou causa, por exemplo `GET /api/network/continuity?municipio=Recife&causa=VEGETACAO`; filtros distintos se combinam com **AND** apenas nos componentes em que a Gold suporta o recorte. “Todos/Todas” omite o parâmetro. O backend valida valores e combinações recebidos diretamente, com `422` para entradas inválidas. Bairros são filtrados localmente a partir de `municipios[].bairros`; alimentadores, a partir de `alimentadores[].municipios`. Trocar o município limpa o bairro e, se incompatível, o alimentador selecionado.

Como a Gold do MVP é estática, o frontend reutiliza a resposta com Fetch API + TanStack Query e `staleTime: Infinity`, sem novas chamadas para filtrar bairros ou alimentadores. As opções globais são idênticas em todas as páginas que as utilizam. O cache de dados autenticados deve ser invalidado/limpo quando a identidade mudar; definir o detalhe dessa integração com o frontend.

**Motivos de inspeção:** `fila_inspecao.motivo_suspeita` reúne regras separadas por `;`, sem vocabulário atômico definido no dicionário. `motivos` não integra o catálogo nem é filtro da Fila no MVP. Engenharia de Dados e Perdas precisam validar os valores e a semântica antes de uma eventual extensão; não publicar as strings concatenadas como opções individuais.

A Gold mantém suas junções lógicas por `id_uc`, `competencia` e `alimentador`; confirmar chaves e tipos na exportação física. A tabela `fila_inspecao` é um snapshot e não uma série de competências. O FastAPI consulta e filtra os dados, sem recriar indicadores homologados pela Engenharia de Dados.

| Tela / rota de negócio | Filtros e períodos do MVP | Limite atual |
| --- | --- | --- |
| Indicadores — `GET /api/metrics/general` | Município e classe (seleção única); seletor “Últimos 3 / 6 / 12 meses”, padrão 12, encerrado no último mês de `dim_competencia`. O frontend envia `inicio` e `fim` (`yyyy-MM`); o backend deriva a comparação com os X meses imediatamente anteriores, de mesma duração, sem segundo seletor. | Consultar os indicadores homologados disponíveis em `agg_receita_mensal`; não somar métricas não aditivas sem semântica aprovada. O contrato dos KPIs continua pendente. |
| Receita — `GET /api/metrics/revenue-variance` | Município, bairro e classe (seleção única); **períodos P0 e P1 fixos** da Gold, exibidos como texto pela tela, sem `inicio`/`fim` nem seleção de outras datas. | Consumir efeitos e períodos de `agg_receita_preco_volume` exatamente como publicados. Somente os recortes disponíveis na Gold podem ser prometidos; sem Shapley, mix calculado no backend ou períodos livres. |
| Fila de inspeções — `GET /api/inspections/queue` | Município, bairro e classe (seleção única por campo); sem filtro de motivo no MVP. | Preservar `prioridade`, `score` e `kwh_recuperavel_estimado_ano` da `fila_inspecao` (`score ≥ 20`). O motivo continua disponível como dado da fila, mas sua filtragem depende de vocabulário validado. |
| Continuidade — `GET /api/network/continuity` | Período comparado em `inicio`/`fim` e base em `inicio_anterior`/`fim_anterior`, de mesma duração entre 1 e 24 meses, sem sobreposição; sem datas, últimos 12 meses Gold contra os 12 anteriores. Município, alimentador e causa têm seleção única. Sem alimentador escolhido, município restringe ranking, série e ocorrências aos códigos de `alimentadores[].municipios`. | Cada DEC/FEC agrega os indicadores mensais Gold **por alimentador inteiro**, inclusive UCs fora do município; a interface avisa essa abrangência. Ocorrências usam `fact_ocorrencias.alimentador`, não o município cadastral da UC. Causa restringe somente ocorrências, sem alterar DEC/FEC. Não publicar DEC/FEC municipal ou por causa; homologação formal da agregação temporal pela Engenharia de Dados ainda pendente. |
| Visão 360 — `GET /api/uc/{uc_id}/360` | Sem filtros de tela. O atendente digita o **ID exato da UC** (exemplo: `UC123456`), o frontend navega para `/visao-360/UC123456` e consulta `GET /api/uc/UC123456/360`. | Consultar UC pelo `id_uc` da Gold; se não existir, responder `404`. Não criar endpoint de busca, autocompletar ou listagem para o MVP. Históricos limitados ao que a Gold disponibiliza. |

**Períodos da Continuidade:** a referência é o calendário Gold, não a data do servidor. Sem parâmetros temporais, o comparado cobre os últimos 12 meses disponíveis e a base cobre os 12 imediatamente anteriores. Se somente `inicio` e `fim` forem informados, a base de mesma duração é derivada imediatamente antes; se os quatro forem informados, os períodos podem ser não consecutivos, desde que tenham a mesma duração de 1 a 24 meses, estejam na Gold e o comparado comece após o fim da base. Entradas inválidas retornam `422`; calendário insuficiente ou inconsistente recebe o `503` previsto no contrato. O ranking por DEC e a série usam o período comparado, enquanto a comparação usa o base, sempre por alimentador inteiro. As regras dos demais módulos devem ser conferidas em seus documentos específicos.

### 9.3 Rotas de IA informadas pela equipe de IA

As quatro rotas abaixo constam da modelagem da equipe de IA e **já estão montadas** pelo roteador `ai_router` sob `/api/ai` na branch examinada. O RBAC da seção 7.1 ainda não foi aplicado. Os exemplos de valores e o SQL da resposta ilustram a modelagem documental; o contrato executável deve ser conferido no roteador e não autoriza expor SQL a qualquer perfil.

| Método e rota | Objetivo e responsabilidade | Serviço responsável; consumidor | Entrada informada | Saída informada | Dependências | Situação |
| --- | --- | --- | --- | --- | --- | --- |
| `POST /api/ai/ask` | Receber pergunta contextualizada e devolver resposta do agente Text-to-SQL com referência de auditoria. | FastAPI expõe a rota; lógica do agente em `ai-agent/`; chat do Portal React consome. | Corpo com `user_id`, `session_id`, `message` e `context` contendo `page` e `current_uc_id` no exemplo (este último pode ser `null`). Obrigatoriedade e validações ainda não definidas. `user_id` do corpo não autentica o usuário. | Exemplo `200 OK`: `answer`, `sql`, `audit_id`, `selo_confianca`, `fontes` e `tempo_ms`. Tipos, nulidade e política de exposição ainda precisam de validação. | Identidade autenticada no FastAPI, histórico de sessão, metadados Gold validados, autorização interna das tools pela IA, execução SQL somente leitura e registro de auditoria por escrita controlada. | **Aprovado pela equipe de IA** quanto à rota e ao formato exemplificado; contrato externo e segurança **pendentes de definição**. |
| `GET /api/ai/insights/{tela}/{entidade_id}` | Fornecer insight proativo referente a uma tela e entidade, sem bloquear a carga dos dados principais da tela. | FastAPI expõe a rota; geração e obtenção do insight pertencem ao módulo de IA; telas do Portal React consomem. | Parâmetros de caminho `tela` e `entidade_id`; exemplo `visao_360_uc` e `45892`. Domínio de valores e validações não definidos. | Exemplo `200 OK`: `tela`, `entidade_id`, `insight_texto`, `metricas_destaque` (com chaves exemplificadas `variacao_pct`, `consumo_atual_kwh`, `faturas_aberto`), `selo` e `tempo_ms`. | Dados de origem validados; estratégia de geração/armazenamento dos insights e política de atualização ainda dependem de alinhamento. | **Aprovado pela equipe de IA** quanto à rota e ao formato exemplificado; semântica, disponibilidade e contrato completo **pendentes de definição**. |
| `GET /api/ai/audit/{audit_id}` | Consultar a trilha detalhada de auditoria. | FastAPI expõe a rota; serviço de auditoria da IA fornece os dados. | `audit_id` no caminho; formato de validação ainda a conferir. | Passos, query e tempo, conforme contrato executável do roteador. | Auditoria registrada pelo agente; proteger SQL e dados retornados. | **Implementado** como rota; acesso futuro **exclusivo de `ADMIN_TI`**. O painel atual de IA oferece a gaveta a outros perfis, exigindo adaptação de interface antes de aplicar o RBAC. |
| `POST /api/ai/feedback` | Receber avaliação positiva ou negativa do analista sobre uma resposta para alimentar o índice de acurácia de REQ-AI-08. | FastAPI expõe a rota; serviço de avaliação da IA processa o feedback; Portal React envia. | Intenção de 👍/👎 informada; corpo, vínculo com resposta/auditoria e identidade não definidos. | Não informada. | Resposta previamente apresentada e mecanismo de avaliação; armazenamento, agregação e autorização ainda não definidos. | **Aprovado pela equipe de IA** quanto à rota e ao objetivo; contratos de entrada/saída e processamento **pendentes de definição**. |

### 9.4 Fluxo Portal → FastAPI → agente de IA

1. O Portal React chama o FastAPI por Fetch API com caminhos relativos `/api`; o proxy Vite mantém a mesma origem do navegador e usa `credentials: "same-origin"`. `credentials: "include"` só será necessário se futuramente houver chamadas autenticadas diretas entre origens locais, com CORS e cookies configurados para isso. Para o chat, envia a pergunta e o contexto em `POST /api/ai/ask`; para insights, consulta `GET /api/ai/insights/{tela}/{entidade_id}` separadamente. Aplica timeout e trata `401`, `403` e `429`.

2. O controller FastAPI valida o cookie/sessão, aplica o RBAC da rota, valida a requisição e encaminha o caso de uso à integração com `ai-agent/`. A identidade transmitida ao módulo vem da autenticação; eventual `user_id` no corpo exemplificado pela IA não tem autoridade. O módulo de IA cuida do pipeline Text-to-SQL, da geração/obtenção de insights e da autorização interna de suas tools. A forma concreta de chamada entre `backend/` e `ai-agent/` e a propagação da identidade/cargo ainda serão definidas; não pressupor serviço HTTP separado.

3. No fluxo de pergunta, a equipe de IA valida a autorização das tools e o SQL gerado para leitura; a execução usa credencial restrita às fontes Gold autorizadas. A trilha de auditoria é persistida por caminho operacional de escrita distinto. O FastAPI devolve a resposta ao Portal com `audit_id`, conforme o exemplo da equipe de IA.

4. O Portal envia avaliações por `POST /api/ai/feedback`. A gaveta de auditoria consulta `GET /api/ai/audit/{audit_id}`, que, após aplicar o RBAC, será exclusiva de `ADMIN_TI`; o frontend deverá ocultar ou desabilitar essa ação para os demais perfis. A vinculação dos registros à identidade autenticada ainda precisa de alinhamento técnico com a equipe de IA.

**Conciliação documental:** a [revisão Portal/IA](../context/diagnostico_dev_ia.md) tratava contexto de tela e feedback como recomendações; a modelagem posterior da equipe de IA os incluiu nas rotas acima. O [planejamento do agente](../ai/planejamento-ai-agent.md) ainda cita `GET /api/ai/insights/{uc_id}` e `ai-agent/controller.py`, enquanto o roteador real implementa `GET /api/ai/insights/{tela}/{entidade_id}` em `ai-agent/src/api/ai_router.py` e está montado em `backend/app/main.py`. Atualizar a documentação de IA em tarefa própria. A equipe de IA mantém a autorização interna das tools; a equipe do backend aplicará autenticação e RBAC nas rotas FastAPI, inclusive auditoria exclusiva de `ADMIN_TI`.

## 10. Testes automatizados

Os testes atuais cobrem as rotas implementadas, incluindo saúde e OpenAPI sob `/api`; ainda não comprovam autenticação ou RBAC. Para esses novos casos de uso, acrescentar testes no nível adequado:

- **Borda (`controllers/`, `schemas/`, handlers de `exceptions/`):** requisição HTTP com `httpx` e dependências FastAPI substituídas, verificando validação, contratos, filtros, paginação e formato de erro.

- **Regras e políticas (`services/`, `security/`):** testes diretos, sem servidor ou PostgreSQL, cobrindo orquestração, regras operacionais, transições e políticas, sem duplicar testes das fórmulas analíticas da Gold.

- **Persistência (`entities/`, `repositories/`):** testes de integração com PostgreSQL real quando ele for introduzido, verificando mapeamentos ORM, transações e permissões de leitura Gold, escrita operacional e rejeição de escrita pela credencial restrita da IA.

Para receita, testar que `GET /api/metrics/revenue-variance` devolve os **períodos fixos** e os efeitos preço/volume diretamente da `agg_receita_preco_volume`, sem fórmula Shapley paralela ou períodos livres. Para continuidade e fila, testar que DEC/FEC, scores e prioridades expostos coincidem com os valores homologados da Gold nos recortes disponíveis. Para inspeções operacionais, testar transições e cancelamento. Para IA, testar que falhas ou ausência de dados não produzam resposta inventada e que a auditoria seja persistida pelo caminho correto. Não usar SQLite como prova de comportamento específico do PostgreSQL.

Para autenticação, testar login apenas de contas existentes; bootstrap manual idempotente, baseado no email único, com senha fornecida na execução e pelo menos 8 caracteres, sem senha padrão, sem sobrescrever conta existente nem criar usuários demonstrativos, com UUID, `criado_em` real e hash Argon2id. Na criação e no login, testar normalização do email, presença de `@`, máximo de 255 caracteres e unicidade do valor persistido, sem dependência nova. Testar criação das demais contas exclusivamente por `ADMIN_TI`, os requests e responses validados dos cinco endpoints, `400` para senha atual incorreta, `409` para email duplicado e `204` sem corpo no logout e na troca de senha. Verificar novo hash, sessão preservada após alteração, ausência de senha/hash/token em corpos e logs e **ausência de troca obrigatória no primeiro acesso**. Cobrir JWT de 15 minutos, expiração com novo login, cookie `vgrid360_access_token` com `HttpOnly`/`Secure=False`/`SameSite=Lax`/`Path=/`, remoção no logout, ausência de refresh e revogação, e comportamentos distintos de `401` e `403`. Verificar login e `GET /api/auth/me` pelo proxy Vite com `credentials: "same-origin"` e envio do cookie; testar separadamente CORS com origens explícitas do frontend e credenciais, sem `*`, e a validação de `Origin` em `POST`, `PATCH` e `DELETE`: as origens `http://localhost:5173`, `http://127.0.0.1:5173` e `http://127.0.0.1:8000` são aceitas, origem desconhecida é rejeitada e ausência de `Origin` é aceita no MVP local sem dispensar JWT/RBAC. Pelo Swagger, `POST /api/auth/users` continua exclusivo de `ADMIN_TI`; outro perfil recebe `403` mesmo com `Origin` permitido. Testar cada combinação perfil × endpoint da seção 7.1, especialmente Fila exclusiva de `PERDAS`/`ADMIN_TI`, auditoria da IA exclusiva de `ADMIN_TI`, rotas públicas de login, saúde e documentação/OpenAPI, telas coerentes com `GET /api/auth/me` e acesso direto negado mesmo quando o frontend oculta a ação. Testar também a separação entre identidade autenticada e `user_id` enviado ao agente. Rate limiting e timeouts entram após definição concreta.

Para filtros, testar a resposta **com exatamente os cinco campos** acordados, ordenação, bairros por município, alimentadores com todos os municípios atendidos, causas Gold distintas e ausência de `motivos` e `fields`. Testar seleção única, no máximo um query parameter por campo, combinações válidas e `422` para entradas inválidas. Para Visão 360, testar ID exato, consulta à rota existente e `404` quando ausente. Em Continuidade, testar o recorte do conjunto de alimentadores por município sem alterar DEC/FEC publicados, as ocorrências pelo alimentador do fato e a causa apenas sobre ocorrências; não testar indicadores ainda não sustentados pela Gold.

## 11. Passo a passo da implementação futura

1. Transformar os cinco contratos HTTP já validados com o Frontend em especificação verificável; preparar a criação controlada da tabela `usuarios` aprovada e o script local manual e idempotente de bootstrap da primeira conta `ADMIN_TI`, sem endpoint público. Preparar segredo JWT, cookie, CORS e validação do cabeçalho `Origin` quando presente, aceitando sua ausência no MVP local conforme a seção 9.1. Definir posteriormente os valores de rate limiting e timeout, se forem incorporados. O prefixo `/api`, saúde e OpenAPI já estão no código da branch examinada.

2. Validar a exportação física da Gold e os valores e indicadores de cada endpoint. **Para Receita, usar a fórmula e a comparação de períodos fixos da Gold**, sem implementar Shapley no FastAPI; comunicar às equipes a diferença em relação ao documento antigo de Diagnóstico. Manter a lacuna de DEC/FEC por município e causa como pendência com Engenharia/Operação, sem recomputá-los localmente. Obter amostras homologadas.

3. Em tarefas de código próprias, reutilizar a infraestrutura PostgreSQL existente em `core/` e `repositories/`, implementar autenticação e RBAC no FastAPI e integrar `GET /api/auth/me` e cookies ao Portal, com testes de contrato, segurança e integração.

4. Implementar os domínios por prioridade do case, consultando e filtrando a Gold para os recortes homologados e preservando suas unidades e definições. Definir separadamente o ciclo de vida das ordens de inspeção, sem publicar dados fictícios como reais.

5. Acordar com a equipe de IA a propagação da identidade autenticada e a autorização interna das tools; aplicar o RBAC ao roteador HTTP de IA já montado, com auditoria acessível apenas a `ADMIN_TI`, e verificar permissões de banco, latência e respostas honestas.

## 12. Critérios para futuras tarefas de código

- A base FastAPI, `GET /api/health` e documentação/OpenAPI já funcionam sob `/api`; `app/main.py` e `core/config.py` permanecem limitados à inicialização e configuração, sem segredos versionados. Ao ativar cookies para chamadas entre origens locais, CORS deve permitir credenciais apenas para origens explícitas.

- Criar somente arquivos necessários aos casos de uso; dependências do backend ficam isoladas das da EDA. Testes pertinentes e lint/formatação passam.

- Autenticação e RBAC seguem as seções 7 e 9, com `perfil` persistido em maiúsculas, matriz de endpoints e matriz de telas separadas, bootstrap local sem HTTP, senha alterável após confirmação da atual e criação das demais contas restrita a `ADMIN_TI`. Login, saúde e documentação/OpenAPI não exigem autenticação no MVP local; as rotas de negócio seguem a matriz. Filtros mantêm seleção única e JSON de `/api/filters/options` com **exatamente os cinco grupos** acordados. A rota da Visão 360 usa ID exato e retorna `404` se inexistente; a IA não recebe identidade confiável do corpo HTTP.

- Os endpoints analíticos preservam valores, unidades, grão e significado da Gold; qualquer lógica analítica adicional tem lacuna e necessidade documentadas e alinhadas com a equipe responsável antes de entrar no FastAPI.

- Nenhuma rota de negócio é publicada com resposta fictícia apresentada como dado real.

- Não há modelo ORM ou schema HTTP definitivo para a Gold, biblioteca de IA ou infraestrutura adicional criados antes das respectivas decisões.

- Alteração segue Git Flow por PR para `dev`; execução, commit e PR dependem de tarefa e autorização próprias.

## 13. Riscos, premissas e decisões pendentes

| Tema | Estado e encaminhamento |
| --- | --- |
| Contrato Gold | **Decisão aprovada:** a Gold é a fonte de verdade dos dados, indicadores e regras analíticas definidos pela Engenharia de Dados; o backend não os duplica nem recalcula. O [dicionário Gold recente](../../data-engineering/relatorio_tabelas/dicionario_dados_gold.md) descreve 15 entidades, enquanto o [contexto antigo de Engenharia](../context/03-engenharia-de-dados.md) lista seis e usa `dim_alimentadores` (plural), em vez de `dim_alimentador` do dicionário. Validar conjunto, nomes, tipos, grãos, chaves, cobertura, versão e mapeamento físico exportados ao PostgreSQL local. Requisitos sem cobertura Gold exigem lacuna documentada e alinhamento antes de considerar lógica adicional no FastAPI; o dicionário não resolve por si só divergências com outras equipes. |
| Contrato de interface | A [visão geral](../context/01-visao-geral.md) aponta `coordenacao/contratos-de-interface.md`, ausente no estado atual do repositório. Confirmar onde ficará o contrato vigente. |
| Frequência de carga | **Decisão para o MVP local:** snapshot Gold estático no PostgreSQL, sem atualização. Os textos antigos de [Engenharia](../context/03-engenharia-de-dados.md) (incremental diário) e [Portal](../context/04-portal-web.md) (carga mensal local) não descrevem a operação deste MVP; o pipeline Databricks externo pode continuar. Registrar data/versão do snapshot e decidir a origem dessa informação quando o contrato de exportação for fechado. |
| Banco da IA | [IA](../context/05-inteligencia-artificial.md) menciona SQLite/PostgreSQL como premissa; as decisões da Visão Geral e do Portal fixam PostgreSQL. Confirmar a correção documental na tarefa apropriada. |
| Modelo e orquestração de IA | O [contexto de IA](../context/05-inteligencia-artificial.md) registra PydanticAI/Gemini 3.1 Flash-Lite; o [planejamento do agente](../ai/planejamento-ai-agent.md) registra Gemini 2.0 Flash Lite; [decisões posteriores de arquitetura](../../ai-agent/arquitetura_e_integracao/decisoes_arquitetura_agente.md) apontam LangGraph e OpenRouter/9router. A equipe de IA deve confirmar o stack vigente e a forma de integração; o backend não o decide aqui. |
| Receita e qualidade | **Decisão vigente para o MVP:** usar diretamente a fórmula, os efeitos e os períodos publicados em `agg_receita_preco_volume` (primeiro ano × últimos 12 meses), sem escolha de períodos ou decomposição Shapley no FastAPI. `efeito_volume = (kwh_p1 - kwh_p0) × preco_p0`; `efeito_preco = (preco_p1 - preco_p0) × kwh_p1`. O documento antigo do Diagnóstico propõe Shapley e períodos livres; essa **divergência documental é conhecida e deve ser comunicada**, mas a implementação do MVP segue a Gold. `agg_receita_mensal` e `fact_faturamento` utilizam definições distintas de preço médio; preservar a origem, as unidades e a cobertura declaradas. Efeito mix, recortes indisponíveis e preços/volumes com semântica distinta não devem ser inventados pelo backend. |
| Indicadores gerais | `agg_receita_mensal` oferece receita, consumo, preço e `ucs_faturadas` mensais por município e classe, mas não define todos os KPIs de `GET /api/metrics/general`. Somar `ucs_faturadas` entre meses produz UC-mês, e combinar diretamente preços médios mensais distorce o período; a fonte Gold e a semântica dos indicadores no recorte solicitado devem ser alinhadas com Engenharia antes de fechar a resposta, sem cálculo paralelo no FastAPI. |
| Inspeções | `fila_inspecao` é um snapshot analítico de UCs com `score ≥ 20`; seus `score`, `prioridade` e `kwh_recuperavel_estimado_ano` são consumidos como publicados, sem recalibração no backend. `fact_inspecoes` registra inspeções históricas, não o ciclo de ordens do Portal. Validar semântica de cancelamento, transições, autoria e migração da tabela operacional separada. O [dicionário](../../data-engineering/relatorio_tabelas/dicionario_dados_gold.md) informa pesos a calibrar e vazamento na calibração atual; a equipe responsável deve tratar essa qualidade, e a prioridade não deve ser apresentada como modelo validado. Exportação e importação continuam sem contrato HTTP. |
| Motivos da fila | **Decidido para o MVP:** a Fila usa município, bairro e classe, sem filtro de motivo; `motivos` não integra `/api/filters/options`. `fila_inspecao.motivo_suspeita` concatena regras com `;`. Engenharia de Dados e Perdas ainda precisam definir vocabulário e correspondência atômica antes de propor esse filtro futuramente. |
| Continuidade por causa e município | **Escopo de filtro aprovado e implementado:** município seleciona o conjunto de alimentadores pelos pares cadastrais de `dim_unidade_consumidora.municipio` e `.alimentador`, para restringir ranking, série e ocorrências. `fact_ocorrencias.alimentador` determina a inclusão de cada ocorrência, sem filtrar pelo município cadastral da UC; causa afeta apenas ocorrências. `agg_continuidade_alimentador` publica DEC/FEC mensais do alimentador inteiro, inclusive fora do município selecionado; a interface informa essa abrangência. `municipio_principal` não representa todos os municípios atendidos. A rota soma os quatro indicadores mensais Gold por alimentador e período, ordena o ranking pelo DEC do comparado e não produz DEC/FEC municipal, por causa ou agregado entre alimentadores. A homologação formal dessa composição temporal pela Engenharia de Dados permanece pendente, sem alterar o contrato já implementado. |
| Visão 360 e chamados | **Fluxo decidido para o MVP:** usuário informa o ID completo da UC (exemplo `UC123456`), frontend navega para `/visao-360/UC123456`, chama `GET /api/uc/UC123456/360` e recebe `404` caso o ID não exista. **Não criar outra rota de busca de UC.** O endpoint consulta `dim_unidade_consumidora` e, por `id_uc`, as tabelas Gold de medidor, GD, leituras, faturas, ocorrências e atendimentos. O histórico de ações dos chamados não existe na Gold atual; não prometer esse dado, preservar apenas históricos disponíveis e a privacidade da UC. |
| Permissões de Continuidade | **Decisão aprovada:** `DIRETORIA`, `OPERACAO` e `ADMIN_TI` terão acesso a `GET /api/network/continuity` (✓ na seção 7.1); os demais perfis não. `PERDAS` mantém acesso à Visão 360. A rota de Continuidade está implementada e foi integrada à `dev` pelo PR #67; o RBAC ainda não está aplicado. |
| Dados pessoais | O [levantamento LGPD](../../data-engineering/relatorio_tabelas/levantamento_lgpd.md) e o dicionário classificam campos de cadastro de UC, inadimplência e suspeitas/inspeções como dados pessoais de maior risco de exposição. Fechar a exposição de campos por rota, logs e auditoria conforme os cargos aprovados antes de publicar a Visão 360 e a fila. |
| Identidade e sessão | **Decidido e validado com o Frontend:** cinco perfis no campo `usuarios.perfil`, sem cadastro público; primeira conta `ADMIN_TI` por script local manual, idempotente e sem endpoint; demais contas por `ADMIN_TI`. Email normalizado nas duas operações, com `@` e até 255 caracteres. Senha mínima de 8 caracteres com hash Argon2id, troca mediante senha atual, JWT de 15 minutos exclusivamente no cookie `vgrid360_access_token` (`HttpOnly=True`, `Secure=False`, `SameSite=Lax`, `Path=/`), sem refresh, revogação ou sessão no banco. Os cinco contratos HTTP e os fluxos de `401`/`403` estão no [documento técnico](impl_autenticação-backend.md#7-contratos-http-aprovados-com-o-frontend); a troca de senha preserva a sessão e não emite novo JWT. Em escritas, `Origin` presente deve ser local e permitido; `Origin` ausente é aceito no MVP local, sem proteção CSRF completa. **Pendente:** implementação, escolha das bibliotecas/variáveis de configuração e eventual dimensionamento de rate limiting e timeout. Recuperação pública de senha está fora do escopo. |
| RBAC e frontend | A matriz de endpoints e a matriz definitiva de telas da seção 7 estão aprovadas; Fila é exclusiva de `PERDAS`/`ADMIN_TI`, e `GET /api/ai/audit/{audit_id}` é exclusivo de `ADMIN_TI`. Login, saúde e documentação/OpenAPI são públicos no MVP local. O backend ainda precisa aplicar autenticação e RBAC às demais rotas existentes. O frontend usa perfil de teste, `credentials: 'same-origin'` pelo proxy Vite e exibe a gaveta de auditoria a outros perfis; a integração futura deverá consultar `/api/auth/me`, tratar o cookie e restringir essa ação. Exportação/importação de inspeções ainda não têm contrato HTTP. |
| Filtros e Portal | **Aprovado com o frontend:** `GET /api/filters/options` contém exatamente `competencias`, `municipios` com `bairros`, `classes`, `alimentadores` como `{codigo, municipios[]}` e `causas` como `string[]`, sem `fields` ou `motivos`. Seleção única por campo; “Todos/Todas” omite o parâmetro, e o backend valida entradas inválidas com `422`. Bairro e alimentador dependem do município; a troca de município limpa seleções incompatíveis. Continuidade utiliza período base e comparado selecionáveis de 1 a 24 meses, conforme [seu planejamento](impl_continuidade.md), com 12 meses × 12 meses como padrão sem datas. Os trechos antigos deste planejamento sobre períodos de Indicadores e Receita requerem revisão documental própria. Cache TanStack Query `staleTime: Infinity` para a Gold estática. Permanece pendente o vocabulário atômico de motivos; o [README do frontend](../../frontend/README.md) será alinhado na tarefa própria. |
| Prefixo HTTP | **Decisão aprovada:** todas as rotas HTTP do backend, inclusive saúde, autenticação, filtros, negócio, IA e documentação/OpenAPI, usam `/api` uma única vez. As rotas registradas em `backend/app/main.py` e o controller de saúde já refletem essa decisão; a autenticação planejada seguirá o mesmo prefixo. |
| Segurança e IA | O backend será responsável por autenticar e autorizar as rotas FastAPI; a equipe de IA autoriza internamente as tools. **Permissões de `/api/ai` estão definidas na seção 7.1**, inclusive auditoria exclusiva de `ADMIN_TI`; sua implementação ainda falta. Permanecem a definir a propagação de identidade verificada, exposição de SQL, retenção e outros detalhes do contrato de IA. [Decisões de acoplamento da IA](../../ai-agent/arquitetura_e_integracao/decisoes_acoplamento_dev_genai_dados.md) propõem `SET LOCAL ROLE` por perfil no PostgreSQL; isso não equivale a RLS nem transfere ao backend a autorização interna das tools. |
| Insights | Conciliar `GET /api/ai/insights/{tela}/{entidade_id}` da nova modelagem com `GET /api/ai/insights/{uc_id}` do planejamento de IA; definir telas e entidades aceitas, origem e atualização dos insights e comportamento sem dados. O exemplo `entidade_id = 45892` da equipe de IA não coincide com o padrão `id_uc` da Gold (`UC` + 6 dígitos); confirmar a identificação para Visão 360 sem alterar o contrato da equipe de IA aqui. O cache descrito no planejamento de IA contempla somente UC e texto do insight; validar como atender a nova rota e seus campos, sem presumir mudança de esquema. O planejamento de IA prevê cache/batch, enquanto o documento de contexto descreve geração na abertura da tela; alinhar os documentos antes da implementação. |
| Feedback e auditoria | As rotas estão montadas no FastAPI. A **política de acesso** está definida: feedback para todos os perfis autenticados e auditoria detalhada apenas para `ADMIN_TI`; o código ainda não a aplica. Conferir schemas efetivos, vínculo entre feedback e resposta/auditoria, persistência, exposição de SQL e índice de acurácia com a equipe de IA antes de mudanças de contrato ou de armazenamento. |
| Prazo | A base FastAPI já existe. Priorizar contratos, autenticação/RBAC, filtros e fluxos obrigatórios; exportação, upload e avaliação de IA continuam diferenciais, enquanto autenticação de `REQ-PORTAL-10` já tem decisões de base para viabilizar o acesso. |

## 14. Revisões Gemini e consolidação

O Gemini recomendou explicitar a fronteira `backend/`–`ai-agent/`, separar consulta Text-to-SQL da escrita de auditoria, alinhar o contrato de receita ao Diagnóstico, reservar extensões de inspeções/perfis/contexto de IA e isolar dependências da API. Essas decisões permanecem.

O Gemini validou a arquitetura em camadas definida pelo responsável do projeto e recomendou: manter `security/` sem SQL ou conexão; concentrar SQL em `repositories/` com sessões fornecidas por `core/`; separar as camadas `entities/` e `schemas/`; centralizar em `main.py` a tradução das falhas de `exceptions/`; e testar borda, domínio e persistência nos níveis apropriados. Essas recomendações foram incorporadas às seções 4, 7, 8 e 10.

A revisão também reforçou o faseamento: a árvore descreve as responsabilidades futuras; a base com rota de saúde já existe. Não são exigidos modelos ORM da Gold, interfaces genéricas, três pools, schemas HTTP completos ou provedores em memória para preencher camadas.
