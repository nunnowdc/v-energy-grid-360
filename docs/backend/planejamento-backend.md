# Planejamento do backend FastAPI

## 1. Objetivo e escopo

Consolidar a arquitetura, os requisitos e os contratos planejados da API FastAPI para o Portal Web V-Energy Grid 360. A base da aplicação, configuração local, OpenAPI e uma rota de saúde já existem; a padronização dessa rota como `GET /api/health`, os endpoints de negócio, a autenticação, a persistência PostgreSQL e a integração GenAI dependem de implementação e, onde indicado, da validação de contratos. Este documento não cria contratos físicos da Gold nem afirma que rotas planejadas já estejam disponíveis.

O repositório separa `frontend/`, `backend/`, `data-engineering/` e `ai-agent/`. O backend já contém `app/main.py`, configuração, controller de saúde e testes iniciais; a presença desses arquivos não implica implementação dos demais domínios. O `requirements.txt` da raiz atende à EDA e aos notebooks; as dependências da API ficam no próprio `backend/`.

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
| `REQ-PORTAL-06` (RF-06) | Como gerente de operação, quero acompanhar DEC e FEC por alimentador ao longo do tempo e identificar os piores, para direcionar a manutenção preventiva. | `GET /api/network/continuity` está planejado para DEC/FEC por alimentador e período; a identificação dos piores ainda requer definição de ordenação/recorte no contrato ou tratamento na interface. | `agg_continuidade_alimentador` traz DEC/FEC mensais, `agg_continuidade_alimentador_anual` traz rankings e `dim_alimentador` (singular) traz o cadastro. `fact_ocorrencias.causa` permite identificar causas, mas os agregados não têm recorte exato por causa nem município (seção 13). |
| `REQ-PORTAL-07` (RF-07) | Como usuário do Portal, quero filtrar as informações relevantes para encontrar o que procuro. | `GET /api/filters/options` retorna cinco grupos: `competencias`, `municipios` (com `bairros`), `classes`, `alimentadores` (com `municipios`) e `causas`, no formato acordado com o frontend. Nas rotas de negócio, cada filtro categórico aceita **uma única opção por campo**; sem query parameters repetidos. | As opções vêm da Gold. O filtro de motivo da fila fica fora do MVP até Engenharia de Dados e Perdas definirem seu vocabulário atômico; não criar rota ou lista provisória. |

### 2.2 Requisitos funcionais do Portal — diferenciais

Os identificadores oficiais abaixo correspondem a RF-08 a RF-10 das histórias fornecidas. `REQ-PORTAL-11` permanece na matriz como requisito de testes automatizados e na seção 10 deste planejamento; não foi reclassificado como história funcional.

| ID oficial | História de usuário | API planejada e cobertura | Dependências documentadas e definição pendente |
| --- | --- | --- | --- |
| `REQ-PORTAL-08` (RF-08) | Como gerente de perdas, quero exportar a fila de inspeção para enviar à equipe de campo. | `GET /api/inspections/queue` fornece a fila, mas nenhuma rota ou contrato de exportação foi definido. | Depende da fila e do formato de exportação a acordar com o Portal; o planejamento do Portal menciona CSV para envio ao campo. |
| `REQ-PORTAL-09` (RF-09) | Como gerente de perdas, quero subir pelo portal a planilha que a equipe preenche em campo, para que os resultados sejam registrados sem digitação manual. | `PATCH /api/inspections/{id}` cobre o registro individual de resultado; nenhuma rota ou contrato de importação em lote foi definido. | Depende do formato da planilha, validação, associação às ordens e regras de escrita operacional, ainda a definir. |
| `REQ-PORTAL-10` (RF-10) | Como usuário, quero entrar com meu perfil e ver as telas específicas do meu cargo. | `POST /api/auth/login`, `GET /api/auth/me`, `PATCH /api/auth/password`, `POST /api/auth/logout` e `POST /api/auth/users` estão planejados; a seção 7 registra o RBAC das rotas. | Contas pré-cadastradas por `ADMIN_TI`, JWT de 15 minutos em cookie HttpOnly, modelo mínimo de `usuarios` e controle de telas no Portal; contratos HTTP completos ainda pendentes (seções 7, 9 e 13). |

## 3. Decisões existentes e novas recomendações

**Já documentado:** FastAPI, React + TypeScript + Vite, PostgreSQL local e exportação da Gold constam da visão geral e do Portal. O documento original de Diagnóstico prevê Shapley e períodos comparáveis, mas para o **MVP a decisão atual é utilizar a fórmula da Gold e comparar apenas o primeiro ano com os últimos 12 meses**. As equipes responsáveis deverão estar cientes dessa diferença; não implementar decomposição paralela no FastAPI. A implementação de IA segue sob responsabilidade da equipe de IA, incluindo a conciliação de seus documentos.

**Decisão arquitetural do responsável pelo projeto:** organizar o backend em camadas `controllers/`, `entities/`, `exceptions/`, `repositories/`, `security/`, `services/` e `tests/`, preservando `app/main.py` e `core/`. Usar `schemas/` para contratos HTTP quando necessário, separados dos modelos ORM de `entities/`.

**Decisões atuais de integração:** MVP local com PostgreSQL e Gold estática, prefixo HTTP global `/api`, autenticação/RBAC no FastAPI sem RLS, roles `DIRETORIA`, `ATENDIMENTO`, `PERDAS`, `OPERACAO` e `ADMIN_TI` (sempre em maiúsculas). Somente `ADMIN_TI` cria contas; não há cadastro público e a troca de senha no primeiro acesso não é obrigatória. A equipe do backend autentica e autoriza rotas, e a equipe de IA cuida da autorização interna de suas tools. A Gold é a referência para as métricas analíticas. O Portal adotará filtros de **seleção única por campo**, receita com **períodos fixos** e Visão 360 consultada pelo **ID exato da UC**.

**Diretriz arquitetural aprovada para o MVP:** a Gold é a fonte de verdade dos dados, indicadores e regras analíticas definidos pela Engenharia de Dados. O FastAPI consulta a Gold no PostgreSQL, aplica os filtros solicitados pelo Portal, valida autenticação e RBAC e entrega os resultados ao React por HTTP, preservando unidades e significados. Não duplica, reinterpreta ou recalcula regras analíticas já implementadas na Gold. Qualquer lógica analítica adicional só pode ser considerada quando um requisito não for atendido pela Gold, após identificar e documentar a lacuna e alinhá-la com a equipe responsável; não se planejam tabelas, agregações ou algoritmos analíticos adicionais sem necessidade comprovada. As regras operacionais de usuários, sessões e ordens de inspeção continuam no backend.

**Recomendação de execução, revisada pelo Gemini:** manter uma única aplicação HTTP em `backend/` e materializar cada camada somente ao surgir um caso de uso real. `ai-agent/` permanece responsável pela lógica de IA; o futuro controller das rotas `/api/ai` será o adaptador HTTP no FastAPI, com a integração concreta entre os módulos definida antes de implementá-la. A arquitetura de pastas é uma direção obrigatória, não uma ordem para criar arquivos vazios no bootstrap.

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

│   │   ├── health.py              # base existente; GET /api/health planejado

│   │   ├── auth.py                # futuro: sessão e contas

│   │   ├── filters.py             # futuro: opções centralizadas

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

`app/core/config.py` lê a configuração do ambiente local; a integração futura acrescentará as configurações de PostgreSQL, segredo de assinatura do JWT, parâmetros do cookie, CORS, rate limiting e timeouts de chamadas de API. Segredos ficam fora do Git. Como o Portal enviará cookie com `credentials: "include"`, CORS deve aceitar apenas origens locais configuradas e credenciais, nunca `*` com credenciais. `GET /api/health` é o caminho aprovado para verificar o processo, ainda não refletido na rota de saúde existente; eventual checagem de prontidão do PostgreSQL será separada quando o banco existir. A expiração do JWT é de 15 minutos; valores de rate limiting e timeout permanecem pendentes.

## 7. Organização da aplicação e fluxo Controller → Service → Repository

Para um caso de uso com dados, o **controller** recebe a requisição React, valida parâmetros por schemas Pydantic, aplica as dependências de autorização com FastAPI e chama o **service**. O service orquestra o caso de uso e recebe explicitamente o **repository**, que consulta a Gold no PostgreSQL com os filtros validados ou grava dados operacionais quando cabível. Modelos ORM de `entities/` mapeiam a persistência apenas quando necessários. O controller converte o resultado para o schema de resposta; FastAPI publica o contrato OpenAPI. O retorno não deve trazer objetos de sessão ou linhas cruas do driver à borda.

`security/` define e aplica a política RBAC, com identidade obtida de dados validados da sessão; o acesso necessário ao registro do usuário passa por `repositories/`. `repositories/` é a única camada de SQL e usa a credencial adequada entregue por `core/`. Falhas semânticas de `exceptions/` atravessam as camadas; handlers registrados em `main.py` as traduzem centralmente em status HTTP e envelope JSON consistente. Evitar `try/except` repetidos por controller e evitar `HTTPException` dentro de services, entities, repositories ou security. Erros de validação HTTP próprios do FastAPI permanecem tratados na borda.

Para leitura analítica, o service pode apenas organizar a projeção recebida do repository para a resposta HTTP: não é obrigatório instanciar um modelo ORM para cada linha consultada. Fórmulas, scores, prioridades e indicadores publicados na Gold devem ser consumidos com suas unidades e significados originais. As transições de ordens de inspeção permanecem regras operacionais em `services/`; a decisão do MVP é consumir a decomposição Gold; a diferença em relação à Shapley prevista pelo Diagnóstico deve ser comunicada, sem recalcular outra fórmula no backend. Dependências explícitas permitem substituir services/repositories nos testes sem criar interfaces genéricas antecipadas.

Aplicar o prefixo global `/api` uma única vez a todas as rotas HTTP planejadas, inclusive autenticação, IA, filtros e saúde. A configuração das rotas HTTP geradas pelo FastAPI para documentação e esquema OpenAPI também deve respeitar o prefixo (por exemplo, `/api/docs`, `/api/redoc` e `/api/openapi.json`). Esta é uma decisão documental para a implementação; o código existente ainda requer alinhamento, inclusive para `GET /api/health` e as URLs de documentação.

| Controller futuro | Endpoints documentados para etapas posteriores |
| --- | --- |
| `metrics` | `GET /api/metrics/general`, `GET /api/metrics/revenue-variance` |
| `uc` | `GET /api/uc/{uc_id}/360` |
| `inspections` | `GET /api/inspections/queue`, `POST /api/inspections/order`, `PATCH /api/inspections/{id}`, `DELETE /api/inspections/{id}` |
| `network` | `GET /api/network/continuity` |
| `ai` | `POST /api/ai/ask`, `GET /api/ai/insights/{tela}/{entidade_id}`, `GET /api/ai/audit/{audit_id}`, `POST /api/ai/feedback` (rotas informadas pela equipe de IA; contratos parciais na seção 9) |
| `auth` | `POST /api/auth/login`, `GET /api/auth/me`, `PATCH /api/auth/password`, `POST /api/auth/logout`, `POST /api/auth/users` |
| `filters` | `GET /api/filters/options` |
| `health` | `GET /api/health` (caminho aprovado; ajuste do código existente pendente) |

`DELETE /api/inspections/{id}` está descrito como “cancelar”; a futura implementação deve preservar o registro e definir o status de cancelamento no contrato, sujeito à validação do fluxo operacional. Exportação CSV e upload de inspeções são extensões do domínio `inspections`, sem rotas inventadas agora. O RBAC protege as rotas já planejadas; a identidade informada pelo cliente em payloads de IA não substitui a identidade autenticada.

### 7.1 Autenticação e matriz de autorização das rotas

O RBAC é aplicado exclusivamente no FastAPI, sem Row Level Security (RLS) no PostgreSQL. `DIRETORIA` reúne as histórias de diretor e diretor comercial; os demais cargos são `ATENDIMENTO`, `PERDAS`, `OPERACAO` e `ADMIN_TI`. `ADMIN_TI` tem acesso a todas as rotas. As permissões ficam em um único mapa em `security/`: cada endpoint declara sua permissão, e mudanças nas permissões de uma role alteram apenas esse mapa, sem modificar controllers. `POST /api/auth/login` é a exceção pública necessária para autenticar contas pré-cadastradas. O Portal usa `GET /api/auth/me` para controlar a navegação; a autorização efetiva ocorre no FastAPI. Conta nova só pode ser criada por `ADMIN_TI`; não há cadastro público nem promoção de cargo pelo próprio usuário.

Na matriz, **E** significa acesso explicitamente exigido por requisito ou decisão atual, **P** significa proposta ainda sujeita a aprovação e **—** significa acesso negado até decisão. A matriz trata da **autorização da rota FastAPI**, não da autorização interna das tools da IA. `POST /api/auth/login` é público apenas para autenticar contas já pré-cadastradas; por isso fica fora das colunas de usuários autenticados. A política de acesso a `GET /api/health` e à OpenAPI depende de definição operacional.

| Rotas ou capacidade | `DIRETORIA` | `ATENDIMENTO` | `PERDAS` | `OPERACAO` | `ADMIN_TI` | Fundamento / limite |
| --- | --- | --- | --- | --- | --- | --- |
| `GET /api/metrics/general`, `GET /api/metrics/revenue-variance` | E | — | — | — | E | REQ-PORTAL-01/02; diretor e diretor comercial compartilham `DIRETORIA`. |
| `GET /api/uc/{uc_id}/360` | — | E | E | — | E | REQ-PORTAL-03; `ATENDIMENTO` e `PERDAS` acessam a UC pesquisada por ID completo, sem rota adicional. |
| `GET /api/inspections/queue`, `POST /api/inspections/order`, `PATCH /api/inspections/{id}`, `DELETE /api/inspections/{id}` | — | — | E | — | E | REQ-PORTAL-04/05; exportação e importação seguem sem rota. |
| `GET /api/network/continuity` | E | — | — | E | E | REQ-PORTAL-06; acesso da `DIRETORIA` aprovado, além de `OPERACAO` e `ADMIN_TI`. |
| `GET /api/filters/options` | E | E | E | E | E | REQ-PORTAL-07; resposta comum com cinco grupos (`competencias`, `municipios`, `classes`, `alimentadores`, `causas`), sem `fields` ou `motivos`. |
| `GET /api/auth/me`, `PATCH /api/auth/password`, `POST /api/auth/logout` | E | E | E | E | E | Cada usuário autenticado consulta a própria identidade, pode trocar a própria senha e encerrar a sessão no navegador. |
| `POST /api/auth/users` | — | — | — | — | E | Criação exclusiva de `ADMIN_TI`; não há cadastro público. |
| Rotas `/api/ai` da tabela acima | E | E | E | E | E | Acesso por cargo e visibilidade de auditoria/SQL ainda dependem de contrato; as tools da IA têm autorização própria sob responsabilidade da equipe de IA. |
| Exportação/importação de inspeções (sem rota) | — | — | E | — | E | REQ-PORTAL-08/09 exigem a capacidade para `PERDAS`; contrato HTTP ainda indefinido. |

`E` para `ADMIN_TI` decorre da decisão de acesso a todas as rotas, inclusive as futuras; isso não altera a responsabilidade da equipe de IA pela autorização interna das ferramentas. Nenhum `P` concede acesso antes da decisão. Os `—` expressam a política conservadora atual para os fluxos listados, sem pressupor que os demais cargos nunca possam receber acesso. **Acesso da `DIRETORIA` à Continuidade:** aprovado (`E`), junto a `OPERACAO` e `ADMIN_TI`; as demais permissões da matriz permanecem. **Acesso de `PERDAS` à Visão 360:** já autorizado (`E`) e mantido.

## 8. Preparação para PostgreSQL

PostgreSQL local é o alvo do MVP; a menção alternativa a SQLite no documento de IA não altera essa decisão. A Gold exportada é fonte analítica de leitura e, para o MVP local, suas tabelas serão estáticas, sem rotina de atualização. A tabela operacional `usuarios` e os dados operacionais de inspeção e auditoria ficam separados logicamente da Gold. A futura integração deve usar consultas parametrizadas, filtros e limites explícitos, transações curtas, índices e paginação orientados por consultas medidas. O [dicionário Gold](../../data-engineering/relatorio_tabelas/dicionario_dados_gold.md) documenta 15 entidades; é necessário validar o que será efetivamente exportado ao PostgreSQL e reconciliar regras divergentes antes de codificar consultas.

Com a arquitetura em camadas, `core/` configura e fornece sessões/conexões no ciclo de vida da aplicação; `repositories/` recebe essas sessões e concentra as consultas parametrizadas e operações de persistência. Repositories não criam engines próprias nem leem variáveis de ambiente. Services escolhem o caso de uso, sem conhecer SQL. `security/` aplica políticas na aplicação, sem abrir conexões ou substituir os privilégios do PostgreSQL. Não há RLS no MVP.

A execução do **SQL gerado pela IA** deve usar credencial PostgreSQL com `SELECT` apenas nas tabelas ou visões Gold autorizadas, além de limites de tempo e resultado. O registro de `fact_ai_audit` exigido por REQ-AI-03 usa um repository de **escrita controlada pela aplicação**, nunca a credencial do SQL gerado. A API analítica pode ter sua própria credencial de leitura. São perfis lógicos de permissão; não é necessário criar três pools no bootstrap. A checagem de política em `security/` e a validação SQL do módulo de IA complementam, mas não substituem, os privilégios mínimos no banco.

A extração/exportação inicial da Gold e sua reconciliação pertencem à integração com Engenharia de Dados. O dicionário já foi publicado em `data-engineering/relatorio_tabelas/`; o formato e o mapeamento físico da carga para PostgreSQL ainda devem ser acordados. A decisão de snapshot estático vale para as tabelas Gold do MVP local, sem impedir que a Engenharia mantenha seu próprio pipeline fora dele. Regras de atualização de dados operacionais não se confundem com a Gold estática.

## 9. Endpoints, contratos e integração React/GenAI

Antes de implementar cada endpoint, acordar com o frontend nomes de campos, tipos, unidades, datas e fusos, formato de erro, filtros, ordenação, paginação e casos sem dados. Usar OpenAPI e exemplos revisados como contrato executável. Históricos da UC e a fila de inspeção precisam de paginação; filtros por município, bairro e classe são obrigatórios na análise de receita. O frontend não deve depender de um contrato simplificado provisório.

Para `GET /api/metrics/revenue-variance`, utilizar **somente os períodos fixos disponíveis na Gold (primeiro ano × últimos 12 meses)** e expor diretamente os valores de `agg_receita_preco_volume`: efeito-volume = `(kwh_p1 - kwh_p0) × preco_p0`; efeito-preço = `(preco_p1 - preco_p0) × kwh_p1`. Os campos de receita, volume, preços e efeitos devem preservar nomes, unidades, grão e significado disponíveis na Gold; a definição detalhada da resposta HTTP depende do contrato com o frontend. **Não implementar Shapley nem períodos livres no MVP.** O antigo requisito do Diagnóstico permanece como divergência documental explícita, não como bloqueio para usar a fórmula Gold aprovada para o MVP. Não prometer efeito mix ou recortes que a agregação não forneça.

### 9.1 Autenticação, sessão e contas

**Decisões aprovadas:** contas pré-cadastradas exclusivamente por `ADMIN_TI`, sem cadastro público. O usuário entra com e-mail e senha, pode alterar a própria senha quando quiser e não é obrigado a fazê-lo no primeiro acesso. Senhas têm no mínimo 8 caracteres e são armazenadas com hash seguro. O JWT expira em **15 minutos** e fica em cookie `HttpOnly`; após a expiração, é necessário novo login. Não há refresh token nem revogação do JWT no servidor. O logout remove o cookie do navegador por `POST /api/auth/logout`. O FastAPI aplica proteção CSRF básica e rate limiting; as chamadas de API têm timeout, sem limites numéricos definidos para estes dois últimos. A identidade e o cargo confiáveis vêm da autenticação no backend, nunca de um campo de cargo ou `user_id` enviado pelo cliente.

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
| `POST /api/auth/login` | Autenticar uma conta pré-cadastrada e estabelecer a sessão. | FastAPI; tela de login do Portal. | Entrada: e-mail e senha. Saída: JWT de 15 minutos em cookie `HttpOnly`; corpo e erros específicos ainda indefinidos. | **Decidido** quanto a rota e mecanismo; contrato HTTP detalhado pendente. |
| `GET /api/auth/me` | Fornecer ao Portal a identidade e o cargo autenticados para controle de telas e estado da sessão. | FastAPI; Portal. | Lê o cookie; campos da resposta ainda não definidos. | **Decidido** quanto a rota e objetivo; schema pendente. |
| `PATCH /api/auth/password` | Permitir alteração opcional da própria senha a qualquer momento. | FastAPI; Portal. | A nova senha deve ter no mínimo 8 caracteres; demais dados de entrada/saída, confirmação da senha atual e tratamento de sessões existentes ainda indefinidos. | **Decidido** quanto a rota e objetivo; somente usuário autenticado; contrato pendente. |
| `POST /api/auth/logout` | Remover o cookie de autenticação do navegador, sem revogar o JWT no servidor. | FastAPI; Portal. | Corpo e resposta ainda indefinidos; a operação remove o cookie. | **Decidido** quanto a rota e efeito no cookie; contrato HTTP detalhado pendente. |
| `POST /api/auth/users` | Criar conta pré-cadastrada e atribuir cargo por ação exclusiva de `ADMIN_TI`. | FastAPI; interface administrativa do Portal, se houver. | Campos de cadastro, entrega da senha inicial e resposta ainda indefinidos. | **Decidido** quanto a rota e exclusividade; modelo físico e contrato pendentes. |

O Portal usa Fetch API com TanStack Query, `credentials: "include"`, timeout e tratamento explícito de `401` (sessão ausente/inválida), `403` (acesso negado) e `429` (limite de requisições). O Portal consulta `GET /api/auth/me` para controlar a navegação; o FastAPI autoriza cada rota. O logout limpa o cookie, mas um JWT eventualmente copiado continua válido até seus 15 minutos de expiração, pois não existe revogação no servidor. Permanecem pendentes os contratos HTTP detalhados, o tratamento da sessão após troca de senha, o provisionamento inicial de contas e os valores de rate limiting e timeout.

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
| Continuidade — `GET /api/network/continuity` | Mesmo período de 3/6/12 meses dos Indicadores, com `inicio`/`fim`, mais município, alimentador e causa (seleção única). Sem alimentador escolhido, município restringe ranking, séries/gráficos por alimentador e lista/contagem de ocorrências aos códigos de `alimentadores[].municipios`. | Cada DEC/FEC permanece o valor Gold **do alimentador inteiro**, inclusive UCs fora do município; a interface avisa essa abrangência. Ocorrências usam `fact_ocorrencias.alimentador` para o conjunto selecionado, não o município cadastral da UC. Causa restringe só lista/contagem de ocorrências, sem alterar DEC/FEC. Não publicar DEC/FEC municipal, por causa, ou agregação temporal sem definição Gold válida. |
| Visão 360 — `GET /api/uc/{uc_id}/360` | Sem filtros de tela. O atendente digita o **ID exato da UC** (exemplo: `UC123456`), o frontend navega para `/visao-360/UC123456` e consulta `GET /api/uc/UC123456/360`. | Consultar UC pelo `id_uc` da Gold; se não existir, responder `404`. Não criar endpoint de busca, autocompletar ou listagem para o MVP. Históricos limitados ao que a Gold disponibiliza. |

**Períodos relativos:** Indicadores e Continuidade usam competências disponíveis no snapshot Gold, não a data do servidor. Ambos os parâmetros `inicio` e `fim` omitidos aplicam 12 meses; períodos incompletos, malformados, invertidos ou fora das janelas aprovadas são inválidos (`422`). A Receita mantém P0/P1 fixos independentemente desses seletores. A seleção municipal na Continuidade limita os alimentadores apresentados, mas não elimina as lacunas analíticas de totais, variações e ranking para janelas móveis; componentes sem definição Gold válida permanecem indisponíveis, sem cálculo substituto no FastAPI.

### 9.3 Rotas de IA informadas pela equipe de IA

As quatro rotas abaixo constam da modelagem enviada pela equipe de IA para o roteador `ai_router`; sua publicação HTTP está planejada sob `/api/ai`, aplicando o prefixo `/api` uma só vez quando o roteador for integrado ao FastAPI. **Aprovado pela equipe de IA** identifica a rota e o objetivo informados, não um contrato HTTP integral validado com Portal, segurança e backend. Os exemplos de valores e o SQL da resposta ilustram a modelagem; não confirmam nomes físicos, resultados reais da Gold nem autorização para expor SQL ao usuário.

| Método e rota | Objetivo e responsabilidade | Serviço responsável; consumidor | Entrada informada | Saída informada | Dependências | Situação |
| --- | --- | --- | --- | --- | --- | --- |
| `POST /api/ai/ask` | Receber pergunta contextualizada e devolver resposta do agente Text-to-SQL com referência de auditoria. | FastAPI expõe a rota; lógica do agente em `ai-agent/`; chat do Portal React consome. | Corpo com `user_id`, `session_id`, `message` e `context` contendo `page` e `current_uc_id` no exemplo (este último pode ser `null`). Obrigatoriedade e validações ainda não definidas. `user_id` do corpo não autentica o usuário. | Exemplo `200 OK`: `answer`, `sql`, `audit_id`, `selo_confianca`, `fontes` e `tempo_ms`. Tipos, nulidade e política de exposição ainda precisam de validação. | Identidade autenticada no FastAPI, histórico de sessão, metadados Gold validados, autorização interna das tools pela IA, execução SQL somente leitura e registro de auditoria por escrita controlada. | **Aprovado pela equipe de IA** quanto à rota e ao formato exemplificado; contrato externo e segurança **pendentes de definição**. |
| `GET /api/ai/insights/{tela}/{entidade_id}` | Fornecer insight proativo referente a uma tela e entidade, sem bloquear a carga dos dados principais da tela. | FastAPI expõe a rota; geração e obtenção do insight pertencem ao módulo de IA; telas do Portal React consomem. | Parâmetros de caminho `tela` e `entidade_id`; exemplo `visao_360_uc` e `45892`. Domínio de valores e validações não definidos. | Exemplo `200 OK`: `tela`, `entidade_id`, `insight_texto`, `metricas_destaque` (com chaves exemplificadas `variacao_pct`, `consumo_atual_kwh`, `faturas_aberto`), `selo` e `tempo_ms`. | Dados de origem validados; estratégia de geração/armazenamento dos insights e política de atualização ainda dependem de alinhamento. | **Aprovado pela equipe de IA** quanto à rota e ao formato exemplificado; semântica, disponibilidade e contrato completo **pendentes de definição**. |
| `GET /api/ai/audit/{audit_id}` | Exibir na gaveta “Como a IA chegou nisso?” os passos executados, a query gerada e o tempo em milissegundos. | FastAPI expõe a rota; serviço de auditoria da IA fornece os dados; Portal React consome. | `audit_id` no caminho; formato e regras de acesso não informados. | Passos, query e tempo descritos conceitualmente; não foi fornecido schema de resposta nem exemplo HTTP. | Auditoria registrada por `POST /api/ai/ask`, consulta aos registros operacionais e política de visibilidade do SQL e dos dados. | **Aprovado pela equipe de IA** quanto à rota e ao objetivo; contrato e autorização **pendentes de definição**. |
| `POST /api/ai/feedback` | Receber avaliação positiva ou negativa do analista sobre uma resposta para alimentar o índice de acurácia de REQ-AI-08. | FastAPI expõe a rota; serviço de avaliação da IA processa o feedback; Portal React envia. | Intenção de 👍/👎 informada; corpo, vínculo com resposta/auditoria e identidade não definidos. | Não informada. | Resposta previamente apresentada e mecanismo de avaliação; armazenamento, agregação e autorização ainda não definidos. | **Aprovado pela equipe de IA** quanto à rota e ao objetivo; contratos de entrada/saída e processamento **pendentes de definição**. |

### 9.4 Fluxo Portal → FastAPI → agente de IA

1. O Portal React usa Fetch API com `credentials: "include"` para chamar o FastAPI. Para o chat, envia a pergunta e os campos de contexto informados em `POST /api/ai/ask`; para uma tela com insights, consulta `GET /api/ai/insights/{tela}/{entidade_id}` separadamente da rota de dados da tela. Aplica timeout e trata `401`, `403` e `429`.

2. O controller FastAPI valida o cookie/sessão, aplica o RBAC da rota, valida a requisição e encaminha o caso de uso à integração com `ai-agent/`. A identidade transmitida ao módulo vem da autenticação; eventual `user_id` no corpo exemplificado pela IA não tem autoridade. O módulo de IA cuida do pipeline Text-to-SQL, da geração/obtenção de insights e da autorização interna de suas tools. A forma concreta de chamada entre `backend/` e `ai-agent/` e a propagação da identidade/cargo ainda serão definidas; não pressupor serviço HTTP separado.

3. No fluxo de pergunta, a equipe de IA valida a autorização das tools e o SQL gerado para leitura; a execução usa credencial restrita às fontes Gold autorizadas. A trilha de auditoria é persistida por caminho operacional de escrita distinto. O FastAPI devolve a resposta ao Portal com `audit_id`, conforme o exemplo da equipe de IA.

4. Quando o usuário abre a gaveta de auditoria, o Portal consulta `GET /api/ai/audit/{audit_id}`. Quando avalia a resposta, envia `POST /api/ai/feedback`. A vinculação e as permissões desses fluxos precisam ser acordadas antes da implementação.

**Conciliação documental:** a [revisão Portal/IA](../context/diagnostico_dev_ia.md) tratava contexto de tela e feedback como recomendações; a modelagem posterior da equipe de IA os incluiu nas rotas acima. O [planejamento do agente](../ai/planejamento-ai-agent.md) ainda cita `GET /api/ai/insights/{uc_id}` e `ai-agent/controller.py`, enquanto a nova modelagem informa `GET /api/ai/insights/{tela}/{entidade_id}` e o planejamento deste backend reserva `backend/app/controllers/ai.py` como adaptador HTTP. O roteador `ai_router` já aparece em `ai-agent/src/api/ai_router.py`, mas não está montado no `backend/app/main.py`; resolver a forma de integração e a atualização do documento do agente antes de implementar. O planejamento do agente também situa execução SQL, conexões, auditoria e migrações em `ai-agent/`; acordar a fronteira com `core/` e `repositories/` do backend sem tomar para esta equipe a autorização interna das tools. A estratégia de cache/batch descrita naquele planejamento é uma decisão do módulo de IA a conciliar com a nova rota, sem impor aqui tabela ou contrato físico.

## 10. Testes automatizados

Os testes iniciais de aplicação, saúde e OpenAPI já existem no backend, mas ainda verificam os caminhos anteriores à decisão de prefixo global. Adaptá-los ao planejar `GET /api/health` e as URLs de documentação sob `/api`; sua presença não comprova os novos fluxos. Com cada caso de uso, acrescentar testes no nível adequado:

- **Borda (`controllers/`, `schemas/`, handlers de `exceptions/`):** requisição HTTP com `httpx` e dependências FastAPI substituídas, verificando validação, contratos, filtros, paginação e formato de erro.

- **Regras e políticas (`services/`, `security/`):** testes diretos, sem servidor ou PostgreSQL, cobrindo orquestração, regras operacionais, transições e políticas, sem duplicar testes das fórmulas analíticas da Gold.

- **Persistência (`entities/`, `repositories/`):** testes de integração com PostgreSQL real quando ele for introduzido, verificando mapeamentos ORM, transações e permissões de leitura Gold, escrita operacional e rejeição de escrita pela credencial restrita da IA.

Para receita, testar que `GET /api/metrics/revenue-variance` devolve os **períodos fixos** e os efeitos preço/volume diretamente da `agg_receita_preco_volume`, sem fórmula Shapley paralela ou períodos livres. Para continuidade e fila, testar que DEC/FEC, scores e prioridades expostos coincidem com os valores homologados da Gold nos recortes disponíveis. Para inspeções operacionais, testar transições e cancelamento. Para IA, testar que falhas ou ausência de dados não produzam resposta inventada e que a auditoria seja persistida pelo caminho correto. Não usar SQLite como prova de comportamento específico do PostgreSQL.

Para autenticação, testar que somente contas pré-cadastradas entram, apenas `ADMIN_TI` cria usuários, senhas têm pelo menos 8 caracteres e hash seguro, **a troca no primeiro acesso não é obrigatória**, JWT expira em 15 minutos e logout remove o cookie. Cobrir CSRF, `401`, `403`, `429`, RBAC, timeouts e limites configurados. Para filtros, testar a resposta **com exatamente os cinco campos** acordados, ordenação, bairros por município, alimentadores com todos os municípios atendidos, causas Gold distintas e ausência de `motivos` e `fields`. Testar seleção única, no máximo um query parameter por campo, combinações válidas e `422` para entradas inválidas. Para Visão 360, testar ID exato, consulta à rota existente e `404` quando ausente. Em Continuidade, testar o recorte do conjunto de alimentadores por município sem alterar DEC/FEC publicados, as ocorrências pelo alimentador do fato e a causa apenas sobre ocorrências; não testar indicadores ainda não sustentados pela Gold.

## 11. Passo a passo da implementação futura

1. Especificar os contratos ainda pendentes de autenticação, autorização, filtros e erros com o Portal; aplicar o prefixo `/api` ao código e aos testes existentes, inclusive saúde e OpenAPI; preparar migração e provisionamento da tabela `usuarios` aprovada, detalhar a configuração local de cookie/CSRF e definir valores de rate limiting e timeout. Preservar a arquitetura em camadas existente.

2. Validar a exportação física da Gold e os valores e indicadores de cada endpoint. **Para Receita, usar a fórmula e a comparação de períodos fixos da Gold**, sem implementar Shapley no FastAPI; comunicar às equipes a diferença em relação ao documento antigo de Diagnóstico. Manter a lacuna de DEC/FEC por município e causa como pendência com Engenharia/Operação, sem recomputá-los localmente. Obter amostras homologadas.

3. Em tarefas de código próprias, integrar PostgreSQL em `core/` e `repositories/`, implementar autenticação e RBAC no FastAPI e os consumidores Fetch API/TanStack Query no Portal, com testes de contrato, segurança e integração.

4. Implementar os domínios por prioridade do case, consultando e filtrando a Gold para os recortes homologados e preservando suas unidades e definições. Definir separadamente o ciclo de vida das ordens de inspeção, sem publicar dados fictícios como reais.

5. Acordar com a equipe de IA a fronteira de identidade, a autorização interna das tools, o roteador HTTP e a auditoria; então integrar `ai-agent/` e verificar permissões de banco, latência e respostas honestas.

## 12. Critérios para futuras tarefas de código

- A base FastAPI, `GET /api/health` e as rotas de documentação/OpenAPI sob `/api` funcionam após o ajuste do código existente; `app/main.py` e `core/config.py` permanecem limitados à inicialização e configuração, sem segredos versionados, e CORS permite apenas origens locais configuradas com credenciais.

- Criar somente arquivos necessários aos casos de uso; dependências do backend ficam isoladas das da EDA. Testes pertinentes e lint/formatação passam.

- Autenticação, RBAC e filtros seguem as seções 7 e 9, com roles em maiúsculas, troca de senha opcional, seleção única por filtro e JSON de `/api/filters/options` com **exatamente os cinco grupos** acordados. A rota da Visão 360 usa ID exato e retorna `404` se inexistente; a IA não recebe identidade confiável do corpo HTTP.

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
| Continuidade por causa e município | **Escopo de filtro aprovado:** município seleciona o conjunto de alimentadores pelos pares cadastrais de `dim_unidade_consumidora.municipio` e `.alimentador`, para restringir ranking, séries/gráficos individuais e lista/contagem de ocorrências. `fact_ocorrencias.alimentador` determina a inclusão de cada ocorrência, sem filtrar pelo município cadastral da UC; causa afeta apenas lista/contagem de ocorrências. `agg_continuidade_alimentador` preserva DEC/FEC do alimentador inteiro por competência, inclusive fora do município selecionado; a interface informa essa abrangência. `municipio_principal` não representa todos os municípios atendidos. A Gold não publica DEC/FEC municipal ou por causa; totais, variações e rankings de janelas móveis ainda exigem semântica Gold/Operação validada. A versão anual traz rankings, mas 2022 e 2026 são parciais. Não recalcular DEC/FEC para preencher essas lacunas. |
| Visão 360 e chamados | **Fluxo decidido para o MVP:** usuário informa o ID completo da UC (exemplo `UC123456`), frontend navega para `/visao-360/UC123456`, chama `GET /api/uc/UC123456/360` e recebe `404` caso o ID não exista. **Não criar outra rota de busca de UC.** O endpoint consulta `dim_unidade_consumidora` e, por `id_uc`, as tabelas Gold de medidor, GD, leituras, faturas, ocorrências e atendimentos. O histórico de ações dos chamados não existe na Gold atual; não prometer esse dado, preservar apenas históricos disponíveis e a privacidade da UC. |
| Permissões de Continuidade | **Decisão aprovada:** `DIRETORIA`, `OPERACAO` e `ADMIN_TI` têm acesso a `GET /api/network/continuity` (`E` na seção 7.1); os demais cargos permanecem sem acesso nessa rota. `PERDAS` mantém o acesso à Visão 360 (`E`). Roles continuam em maiúsculas no contrato; a implementação futura do RBAC deve refletir a matriz aprovada. |
| Dados pessoais | O [levantamento LGPD](../../data-engineering/relatorio_tabelas/levantamento_lgpd.md) e o dicionário classificam campos de cadastro de UC, inadimplência e suspeitas/inspeções como dados pessoais de maior risco de exposição. Fechar a exposição de campos por rota, logs e auditoria conforme os cargos aprovados antes de publicar a Visão 360 e a fila. |
| Identidade e sessão | Cinco roles, tabela mínima `usuarios`, contas pré-cadastradas por `ADMIN_TI`, senha mínima de 8 caracteres com hash seguro, JWT de 15 minutos em cookie `HttpOnly`, CSRF básico, novo login após expiração e logout que remove o cookie sem revogação estão decididos. Faltam provisionamento inicial, entrega/recuperação de senha, contratos HTTP detalhados das cinco rotas de autenticação, atributos restantes do cookie, validação CSRF concreta, tratamento da sessão após troca de senha e valores de rate limiting e timeout. As configurações de `Secure`, `SameSite`, CORS e verificação de origem da seção 9.1 são recomendação técnica para o MVP local. |
| Filtros e Portal | **Aprovado com o frontend:** `GET /api/filters/options` contém exatamente `competencias`, `municipios` com `bairros`, `classes`, `alimentadores` como `{codigo, municipios[]}` e `causas` como `string[]`, sem `fields` ou `motivos`. Seleção única por campo; “Todos/Todas” omite o parâmetro, e o backend valida entradas inválidas com `422`. Bairro e alimentador dependem do município; a troca de município limpa seleções incompatíveis. Indicadores e Continuidade usam últimos 3/6/12 meses da Gold (padrão 12), enviados como `inicio`/`fim`; Indicadores compara com X meses imediatamente anteriores. Receita usa P0/P1 fixos. Cache TanStack Query `staleTime: Infinity` para a Gold estática. Permanece pendente o vocabulário atômico de motivos e a cobertura analítica de certos componentes da Continuidade; o [README do frontend](../../frontend/README.md) será alinhado na tarefa própria. |
| Prefixo HTTP | **Decisão aprovada:** todas as rotas HTTP do backend, inclusive saúde, autenticação, filtros, negócio, IA e documentação/OpenAPI, usam `/api` uma única vez. O documento usa os caminhos finais; `backend/app/main.py` e o controller de saúde ainda não implementam essa mudança. Ajustar configuração e testes em tarefa de código. |
| Segurança e IA | O backend autentica e autoriza rotas; a equipe de IA autoriza internamente as tools. Falta contrato de propagação de identidade/cargo verificados, permissões de `/api/ai` por cargo, obrigatoriedade dos campos de `/api/ai/ask`, erros, retenção da auditoria, exposição de SQL e autorização de `GET /api/ai/audit/{audit_id}`. [Decisões de acoplamento da IA](../../ai-agent/arquitetura_e_integracao/decisoes_acoplamento_dev_genai_dados.md) propõem `SET LOCAL ROLE` por perfil no PostgreSQL; isso não equivale a RLS, mas a estratégia interna da IA precisa ser conciliada com o RBAC do FastAPI e com o acesso somente leitura, sem atribuí-la ao backend. |
| Insights | Conciliar `GET /api/ai/insights/{tela}/{entidade_id}` da nova modelagem com `GET /api/ai/insights/{uc_id}` do planejamento de IA; definir telas e entidades aceitas, origem e atualização dos insights e comportamento sem dados. O exemplo `entidade_id = 45892` da equipe de IA não coincide com o padrão `id_uc` da Gold (`UC` + 6 dígitos); confirmar a identificação para Visão 360 sem alterar o contrato da equipe de IA aqui. O cache descrito no planejamento de IA contempla somente UC e texto do insight; validar como atender a nova rota e seus campos, sem presumir mudança de esquema. O planejamento de IA prevê cache/batch, enquanto o documento de contexto descreve geração na abertura da tela; alinhar os documentos antes da implementação. |
| Feedback e auditoria | Definir corpos, schemas de resposta, vínculo entre feedback e resposta/auditoria, persistência, política de acesso e forma de cálculo do índice de acurácia. O registro de auditoria descrito no planejamento de IA não especifica passos executados, `selo_confianca` ou `fontes`, nem armazenamento de feedback; validar a origem desses dados antes de assumir alterações físicas. A equipe de IA informou rota e objetivo, sem esses contratos. |
| Prazo | A base FastAPI já existe. Priorizar contratos, autenticação/RBAC, filtros e fluxos obrigatórios; exportação, upload e avaliação de IA continuam diferenciais, enquanto autenticação de `REQ-PORTAL-10` já tem decisões de base para viabilizar o acesso. |

## 14. Revisões Gemini e consolidação

O Gemini recomendou explicitar a fronteira `backend/`–`ai-agent/`, separar consulta Text-to-SQL da escrita de auditoria, alinhar o contrato de receita ao Diagnóstico, reservar extensões de inspeções/perfis/contexto de IA e isolar dependências da API. Essas decisões permanecem.

O Gemini validou a arquitetura em camadas definida pelo responsável do projeto e recomendou: manter `security/` sem SQL ou conexão; concentrar SQL em `repositories/` com sessões fornecidas por `core/`; separar as camadas `entities/` e `schemas/`; centralizar em `main.py` a tradução das falhas de `exceptions/`; e testar borda, domínio e persistência nos níveis apropriados. Essas recomendações foram incorporadas às seções 4, 7, 8 e 10.

A revisão também reforçou o faseamento: a árvore descreve as responsabilidades futuras; a base com rota de saúde já existe. Não são exigidos modelos ORM da Gold, interfaces genéricas, três pools, schemas HTTP completos ou provedores em memória para preencher camadas.
