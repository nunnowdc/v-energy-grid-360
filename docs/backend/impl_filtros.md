# Planejamento de implementação — filtros compartilhados do Portal

## 1. Objetivo e requisitos das telas

Planejar exclusivamente `GET /api/filters/options` para fornecer opções reutilizáveis às telas do V-Energy Grid 360. Este documento separa **decisões aprovadas com o frontend**, **comportamento já implementado**, **dados confirmados pelo [dicionário Gold](../../data-engineering/relatorio_tabelas/dicionario_dados_gold.md)** e **pendências futuras**. A Gold é a fonte de verdade para valores, relações e indicadores; a rota de opções não calcula métricas nem aplica filtros aos dashboards.

| Tela e rota de negócio planejada | Filtros solicitados para a tela | Situação observada no frontend |
| --- | --- | --- |
| Indicadores — `GET /api/metrics/general` | Município, classe e “Últimos 3 / 6 / 12 meses” (padrão 12), sempre comparados aos X meses imediatamente anteriores. | `IndicadoresPage` ainda usa os seletores absolutos `De`/`Até`; o novo seletor aprovado e a comparação não foram implementados. |
| Receita — `GET /api/metrics/revenue-variance` | Município, bairro e classe; P0 e P1 fixos no MVP, exibidos como texto, sem seletores de data. | `ReceitaPage` usa município, bairro e classe. A decisão conjunta com o frontend confirma os períodos fixos do [planejamento geral](planejamento-backend.md) e do [README da raiz](../../README.md). |
| Fila de Inspeção — `GET /api/inspections/queue` | Município, bairro e classe. Motivo fica fora do filtro do MVP. | `InspecoesPage` ainda não monta a barra; o vocabulário de motivos depende da Engenharia de Dados e de Perdas. |
| Continuidade — `GET /api/network/continuity` | “Últimos 3 / 6 / 12 meses” (padrão 12), município, alimentador e causa, com escopos distintos para cada componente. | `ContinuidadePage` ainda usa `De`/`Até` e município; faltam os seletores aprovados de alimentador, causa e período relativo. O [planejamento da tela](impl_continuidade.md) contém propostas anteriores a alinhar depois. |
| Visão 360 — `GET /api/uc/{uc_id}/360` | Nenhum filtro compartilhado de tela: recebe o ID completo da UC. | Endpoint da UC já existe; seus parâmetros de paginação não são opções deste serviço. |

As opções de município, bairro e classe são globais e iguais onde reaparecem. A seleção visual atual é **única** por campo (`FiltroSelect`); “Todos/Todas” é estado sem seleção, não uma categoria da Gold. A aplicação efetiva dos filtros permanece responsabilidade de cada rota de negócio, respeitando o grão dos seus dados.

## 2. Escopo do endpoint e integração existente

- **Rota única deste planejamento:** `GET /api/filters/options`, sem corpo, sem `fields` e sem contexto de página no contrato aprovado. Retorna o catálogo de opções do snapshot Gold, não resultados filtrados. Não criar rota adicional nesta etapa.
- **Contrato agora aprovado com o frontend:** o JSON contém **exatamente cinco grupos**: `competencias`, `municipios` (objetos `{nome, bairros}`), `classes`, `alimentadores` (objetos `{codigo, municipios}`) e `causas` (`string[]`). Os três primeiros preservam o formato anterior. `motivos` fica fora até existir vocabulário atômico validado pela Engenharia de Dados/Perdas. A seção 9.2 do planejamento geral e o tipo `OpcoesFiltros` atual ainda registram apenas três grupos; deverão ser alinhados em tarefas próprias. Esta decisão documental não significa que a rota já exista.
- **Estado do código:** `backend/app/main.py` registra `/api/health` e `/api/uc/{uc_id}/360`, além de documentação/OpenAPI sob `/api`. Ainda não há controller, service, repository ou schema de filtros. O hook, o tipo TypeScript e o mock atuais do frontend abrangem apenas os três grupos antigos; precisam de atualização posterior. O mock não comprova valores do PostgreSQL.
- **Responsabilidades:** o backend consulta e organiza opções Gold; o React mostra seletores, guarda escolhas na URL, filtra listas dependentes localmente quando o contrato fornece os vínculos e chama cada endpoint de negócio com seus parâmetros. A Gold do MVP é estática; não se planeja cache adicional no FastAPI.
- **Fora do escopo:** implementar endpoints de dashboards, regras analíticas, autenticação/RBAC, IA, tabelas, índices ou alterações no frontend. As decisões gerais de segurança permanecem preservadas para outra etapa.

## 3. Mapeamento das opções e dos períodos para a Gold

Os nomes JSON desta seção são **campos HTTP**. As fontes e colunas abaixo estão documentadas na Gold; formatos de seleção relativa e rótulos de interface pertencem ao frontend. Uma competência disponível no calendário não garante registros de todas as métricas naquela competência.

| Opção | Tabela e colunas Gold exatas; tipo e grão | Domínio/ordem e dependência | Limite |
| --- | --- | --- | --- |
| `competencias` | `dim_competencia.mes_referencia` (`string`, `yyyy-MM`) e `dim_competencia.competencia` (`date`, primeiro dia do mês); uma linha por competência. | Meses distintos em ordem de `competencia` crescente; o dicionário documenta 48 meses, de `2022-07` a `2026-06`. Independe dos demais seletores. | Calendário do snapshot, não disponibilidade de cada indicador. X meses e comparação não são colunas Gold. |
| `municipios[].nome` e `municipios[].bairros` | Pares distintos `dim_unidade_consumidora.municipio` e `.bairro` (`string`); uma linha de cadastro por `id_uc`. | Municípios em ordem alfabética; bairros únicos e em ordem alfabética **dentro** do município. Gold documenta 14 municípios e bairros com encoding corrigido. `bairro` exige município para desambiguar. | Não deduzir vínculo bairro–município de texto ou de `municipio_principal`. Valores nulos, se houver no snapshot, não viram a opção literal `null`. |
| `classes` | `dim_unidade_consumidora.classe` (`string`); uma linha por `id_uc`, consultar valores distintos. | Preservar códigos Gold: `RESIDENCIAL`, `COMERCIAL`, `INDUSTRIAL`, `RURAL`, `PODER_PUBLICO`, quando presentes no snapshot. Ordenação determinística; rótulos amigáveis vêm de `frontend/src/config/classes.ts`. | Não trocar códigos pelos rótulos. O frontend tipa os cinco códigos; um domínio novo exigirá alinhamento. |
| `alimentadores` **aprovado** | `dim_alimentador.alimentador` (`string`, um registro por circuito; 122 no dicionário). Para a dependência municipal: pares distintos `dim_unidade_consumidora.municipio` e `.alimentador`, ligados por igualdade do código `alimentador`. | Códigos Gold, por exemplo `ALM-REC-008`, em ordem alfabética. Um alimentador pode servir mais de um município; o vínculo cadastral atual permite lista local por município. | `dim_alimentador.municipio_principal` indica apenas o município com mais UCs, não todos os atendidos. O cadastro não documenta validade histórica desse vínculo. |
| `causas` **aprovado** | `fact_ocorrencias.causa` (`string`; fato com uma linha por UC interrompida), consultar valores distintos. | A Gold documenta `CLIMATICA`, `VEGETACAO`, `TERCEIROS`, `SOBRECARGA`, `FALHA DE EQUIPAMENTO`, `NAO IDENTIFICADA` e `NAO INFORMADA`; ordenar alfabeticamente e preservar grafia. Não depende de município no catálogo global. | `NAO INFORMADA` já reúne nulos/sentinelas; `NAO IDENTIFICADA` é categoria válida diferente. Selecionar causa **não** torna DEC/FEC por causa disponíveis. |
| `motivos` **adiado; não integra a resposta** | `fila_inspecao.motivo_suspeita` (`string`; uma linha por UC com `score >= 20`), além de `municipio`, `bairro` e `classe` da própria fila quando a rota de negócio for filtrada. | A coluna contém **múltiplas regras concatenadas por `;`**. Uma opção de motivo atômico exigiria vocabulário e regra de separação/igualdade validados pela Engenharia de Dados e Perdas. | O dicionário não enumera valores atômicos nem uma dimensão de motivos. Não oferecer os textos concatenados como se fossem motivos individuais e não inventar uma lista. O campo está classificado como dado pessoal ALTO; a resposta de opções não deve expor linhas, UCs, scores ou contagens por motivo. |

### 3.1 Indicadores: período relativo e comparação

**Aprovado com o frontend:** um único seletor “Últimos 3 / 6 / 12 meses”, com 12 como padrão. Para X escolhido, a janela-base contém as X competências consecutivas mais recentes e termina em `max(dim_competencia.competencia)`, sem usar a data do servidor. O frontend envia somente `inicio` e `fim` (`yyyy-MM`); o backend identifica X pelo intervalo e deriva **os X meses imediatamente anteriores**, de igual duração, sem segundo seletor nem parâmetros adicionais de comparação. No snapshot documentado, X = 12 corresponde à base `2025-07`–`2026-06` e à comparação `2024-07`–`2025-06`. A derivação das competências não recalcula métricas Gold.

O componente atual ainda apresenta `De`/`Até` absolutos. Sua substituição e as chamadas de `GET /api/metrics/general` pertencem a tarefas futuras; o endpoint de opções fornece apenas `competencias`, não presets ou metadados adicionais. Se houver meses comparativos sem dados da métrica, a rota de negócio deve representar a ausência sem inventar zero; o formato final dos indicadores permanece no contrato dessa rota. `agg_receita_mensal` tem grão `competencia × municipio × bairro × classe × possui_gd`: `ucs_faturadas` não é aditivo entre meses e `preco_medio_kwh` não deve ser somado. Este documento não define cálculos de KPI.

### 3.2 Receita: períodos fixos aprovados para o MVP

**Decisão conjunta com o frontend:** a tela de Receita mantém os dois períodos já publicados em `agg_receita_preco_volume`: `periodo_p0` = `2022-07`–`2023-06` (primeiro ano) e `periodo_p1` = `2025-07`–`2026-06` (últimos 12 meses do snapshot documentado). Na implementação da tela, os períodos devem aparecer apenas como texto, por exemplo **“jul/22–jun/23 × jul/25–jun/26”**. Não há seletores de intervalo nem parâmetros de período em `GET /api/metrics/revenue-variance` no MVP; a rota recebe apenas os filtros categóricos aplicáveis.

`agg_receita_mensal` fornece dados mensais nos recortes de município, bairro e classe, mas **não publica efeitos preço/volume de intervalos arbitrários**. Portanto, a disponibilidade de competências no catálogo compartilhado não libera escolha de datas em Receita. Preservar os efeitos P0/P1 homologados pela Gold, sem cálculo alternativo no FastAPI. Uma futura seleção livre seria outra decisão de produto e contrato, fora deste planejamento do MVP.

### 3.3 Fila de Inspeção

**Filtros do MVP:** município, bairro e classe, usando o catálogo compartilhado. A fila contém apenas UCs com `score >= 20`; uma opção global pode produzir resultado vazio nessa tela. `fila_inspecao` já possui `municipio`, `bairro` e `classe`, sem JOIN cadastral necessário para esses filtros. `motivo_suspeita` continua sendo dado Gold da fila, mas **não é filtro nem opção de `/api/filters/options` nesta etapa**: a coluna concatena regras com `;`, sem vocabulário atômico documentado. O frontend ainda não implementa a barra dessa tela.

### 3.4 Continuidade

O período usa o mesmo seletor aprovado de 3/6/12 meses dos Indicadores, padrão 12, encerrado na última competência Gold; o frontend atual ainda usa `De`/`Até`. Para um município selecionado, obter o **conjunto de códigos dos alimentadores que o atendem** a partir de `alimentadores[].municipios`, formado pelos pares distintos `(dim_unidade_consumidora.municipio, dim_unidade_consumidora.alimentador)`. `dim_alimentador.municipio_principal` não substitui essa associação. Sem alimentador escolhido, esse conjunto restringe **o ranking, os gráficos e a lista/contagem de ocorrências**, além das opções do seletor. Com alimentador escolhido, usar apenas seu código, que deve pertencer ao conjunto do município. Sem município, usar os alimentadores do escopo geral ou o alimentador selecionado.

Nos gráficos DEC/FEC e no ranking, cada linha ou série mantém o `dec` e o `fec` **do alimentador inteiro**, exatamente como publicados em `agg_continuidade_alimentador` para cada competência; não produzir um DEC/FEC municipal nem uma curva agregada do município. Nos componentes de ocorrências, filtrar `fact_ocorrencias.alimentador` pelos códigos desse conjunto, **não** por `dim_unidade_consumidora.municipio` da UC; isso também vale para o gráfico de causas derivado das ocorrências. A causa selecionada restringe somente a lista e a contagem de ocorrências, sem alterar DEC/FEC por alimentador. Se o município mudar, o frontend limpa um alimentador selecionado que não pertença ao novo conjunto e mostra aviso de que os indicadores abrangem o **alimentador inteiro**, inclusive UCs fora do município escolhido. A seleção municipal limita quais alimentadores são apresentados; não resolve a lacuna analítica de totais, variações ou ranking de DEC/FEC para uma janela móvel, registrada em [impl_continuidade.md](impl_continuidade.md).

## 4. Dependências e consultas necessárias

1. **Opções básicas:** consultar `dim_competencia` separadamente, obter pares distintos de município/bairro e classes distintas de `dim_unidade_consumidora`. Montar objetos municipais sem multiplicar bairros por JOIN com fatos. Preservar grafia Gold, remover duplicações e ordenar deterministicamente; não retornar dados pessoais da UC.
2. **Alimentadores aprovados:** consultar `dim_alimentador.alimentador` e a associação distinta `(dim_unidade_consumidora.municipio, dim_unidade_consumidora.alimentador)`. Relacionar pelo código, agrupando todos os municípios atendidos; não usar apenas `municipio_principal`. Com 122 circuitos documentados, o frontend pode carregar a relação uma vez e filtrar localmente. O vínculo cadastral é atual e não descreve a posição histórica de cada UC.
3. **Causas aprovadas:** consultar valores distintos de `fact_ocorrencias.causa`, sem JOIN ao cadastro para montar a lista global. Preservar `NAO INFORMADA` e `NAO IDENTIFICADA` separadas.
4. **Motivos adiados:** não consultar textos distintos de `fila_inspecao.motivo_suspeita` para a resposta de opções; isso produziria combinações de regras, não motivos individuais. Sua futura inclusão dependerá de vocabulário validado pela Engenharia de Dados/Perdas.
5. **Períodos:** o frontend deriva `inicio`/`fim` para os presets de 3, 6 ou 12 competências do calendário ordenado; o backend de Indicadores deriva a janela comparativa de mesmo X imediatamente anterior. Receita usa P0/P1 fixos, sem parâmetros de período. Não ancorar períodos no relógio do servidor nem acrescentar metadados de período ao catálogo.
6. **Aplicação nas rotas de negócio:** cada controller/service valida seus parâmetros e aplica apenas os filtros que seu componente Gold suporta. Município e bairro, ou município e alimentador, precisam formar combinações válidas no cadastro. Em Continuidade, resolver primeiro os códigos distintos dos alimentadores do município; usá-los para restringir ranking, séries individuais por alimentador e ocorrências. Para ocorrências, aplicar esses códigos em `fact_ocorrencias.alimentador` (mais `causa`, se selecionada), sem JOIN ao município cadastral da UC. DEC/FEC mantêm o grão e os valores Gold por alimentador e competência. Não cruzar fatos brutos com agregados de modo a multiplicar linhas ou alterar indicadores publicados.

**Dependentes no Portal:** `bairro` vem de `municipios[].bairros` do município escolhido. Trocar ou limpar município remove bairro, como já faz `frontend/src/lib/filtros-url.ts`. `alimentadores[].municipios` permite a filtragem local dos circuitos; se o novo município não constar da associação do alimentador selecionado, limpá-lo também. Sem município selecionado, mostrar todos os alimentadores. Causas são globais; uma combinação válida sem ocorrências retorna lista vazia e contagem zero, não erro. “Todos/Todas” remove o parâmetro, e cada categoria aceita apenas um valor.

## 5. Contrato HTTP aprovado e uso pelos dashboards

### 5.1 Resposta única de `GET /api/filters/options`

**Requisição:** `GET /api/filters/options HTTP/1.1`, sem corpo, `fields` ou parâmetros de seleção. `apiFetch('/filters/options')` aplica `/api` uma única vez. **Contrato aprovado com o frontend:** `200 OK` com exatamente os cinco campos abaixo. O exemplo ilustra a estrutura e não pretende reproduzir o snapshot completo; os códigos de causas são categorias documentadas na Gold.

```json
{
  "competencias": ["2022-07", "2022-08", "2026-06"],
  "municipios": [
    {"nome": "Recife", "bairros": ["Boa Viagem", "Casa Forte"]}
  ],
  "classes": ["RESIDENCIAL", "COMERCIAL", "INDUSTRIAL", "RURAL", "PODER_PUBLICO"],
  "alimentadores": [
    {"codigo": "ALM-REC-008", "municipios": ["Recife"]}
  ],
  "causas": ["NAO IDENTIFICADA", "NAO INFORMADA", "VEGETACAO"]
}
```

`competencias` é crescente; municípios, bairros, alimentadores, associações municipais, classes e causas têm ordem determinística. Preservar códigos e grafia Gold. `alimentadores[].codigo` é enviado como valor de `alimentador` nos dashboards; `alimentadores[].municipios` serve para filtrar o seletor localmente. `causas` é `string[]`, com `NAO INFORMADA` e `NAO IDENTIFICADA` como categorias distintas. **Não retornar `motivos`**, nem vazio, pois sua semântica segue indefinida.

A decisão é uma **extensão aditiva** do contrato anterior de três grupos: os três campos e suas formas permanecem; entram somente `alimentadores` e `causas`. A seção 9.2 de `planejamento-backend.md`, a proposta `string[]` em `impl_continuidade.md` e o tipo/mock atuais do frontend ficaram desatualizados e deverão ser sincronizados nas tarefas correspondentes. Não haverá resposta por cargo, subconjunto por tela ou endpoint adicional. Uma resposta compartilhada aproveita a Gold estática e evita chamadas repetidas; medir o tamanho real antes de propor outra arquitetura. Os presets de período são regra de interface derivável de `competencias`, sem campo extra no JSON.

### 5.2 Seleção e parâmetros dos endpoints de negócio

O frontend usa seleção única. Para município, bairro, classe, alimentador e causa, enviar no máximo um query parameter por campo com o valor Gold exato, codificado via `URLSearchParams`; “Todos/Todas” significa **omitir** o parâmetro. `inicio` e `fim` usam `yyyy-MM`, em todas as rotas que aceitam período; Receita tem P0/P1 fixos e não recebe data. A API valida entrada direta mesmo que o frontend descarte escolhas inválidas da URL. `GET /api/filters/options` não recebe os filtros ativos.

| Tela | Parâmetros e comportamento aprovado | Situação da implementação |
| --- | --- | --- |
| Indicadores | `municipio`, `classe`, `inicio`, `fim`. O Portal envia uma janela de 3, 6 ou 12 meses encerrada no último mês Gold; ambos omitidos significam 12 meses. O backend deriva os X meses anteriores para comparação, sem parâmetros extras. | A página ainda usa `De`/`Até` absolutos e precisa adotar o seletor aprovado. O contrato dos KPIs continua próprio da rota. |
| Receita | `municipio`, `bairro`, `classe`; P0/P1 da Gold apenas como texto. Sem `inicio`/`fim`. | A página já mostra os três seletores categóricos, mas a apresentação textual dos períodos ainda será integrada. |
| Fila de Inspeção | `municipio`, `bairro`, `classe`; sem `motivo` no MVP. | Barra ainda não implementada. |
| Continuidade | `inicio`, `fim`, `municipio`, `alimentador`, `causa`. Mesmo seletor 3/6/12. Sem alimentador escolhido, município limita ranking, gráficos e lista/contagem de ocorrências aos circuitos presentes em `alimentadores[].municipios`; ocorrências usam `fact_ocorrencias.alimentador`. Cada DEC/FEC continua sendo do circuito inteiro. Causa restringe só lista/contagem de ocorrências. | A página atual só mostra `De`/`Até` e município. O contrato antigo de `impl_continuidade.md` precisa ser alinhado; o Portal exibirá aviso sobre o alcance integral do alimentador. |

Exemplos ilustrativos: `GET /api/metrics/general?inicio=2026-04&fim=2026-06&municipio=Recife`; `GET /api/inspections/queue?municipio=Recife&bairro=Boa%20Viagem&classe=RESIDENCIAL`; `GET /api/network/continuity?inicio=2025-07&fim=2026-06&municipio=Recife`. Neste último caso, **sem alimentador escolhido**, ranking, gráficos e ocorrências consideram somente os códigos de alimentadores associados a Recife; as ocorrências são selecionadas por `fact_ocorrencias.alimentador`, e cada DEC/FEC exibido continua sendo do alimentador inteiro. Uma causa adicional afetaria apenas lista/contagem de ocorrências. Quando o usuário troca município, o frontend remove bairro e alimentador incompatível; o backend verifica combinações recebidas diretamente.

## 6. Erros, ausências e limpeza de seleção

| Situação | Comportamento planejado |
| --- | --- |
| Gold acessível e uma categoria realmente vazia | `200` com `[]` no grupo correspondente; seletor sem opções. Não usar `[]` para mascarar a indefinição de motivos: esse campo não integra o contrato. |
| Município sem bairro ou alimentador associado | Lista dependente vazia, sem inventar uma opção. Trocar/limpar município limpa bairro; alimentador é limpo se deixar de atender o município escolhido. |
| “Todos/Todas” ou limpar filtros | Remover os parâmetros categóricos. Limpar período retorna aos últimos 12 meses da Gold em Indicadores/Continuidade; Receita permanece com P0/P1. O `removerFiltros` atual preserva parâmetros da URL que não são filtros; novos campos devem ser incluídos em tarefa do frontend. |
| Categoria Gold desconhecida, valor repetido, bairro/município ou alimentador/município incompatíveis em requisição direta | Responder `422`, sem corrigir silenciosamente a entrada. Uma combinação válida que apenas não possua fatos retorna resposta vazia do endpoint de negócio, não `422`. |
| `inicio`/`fim` malformados, invertidos, fora de `dim_competencia`, incompletos ou incompatíveis com as janelas aprovadas de 3/6/12 meses até o último mês Gold | Responder `422`. Ambos omitidos usam 12 meses. O frontend atual aceita extremos parciais na URL e precisará adequar a chamada aos dashboards; o backend não depende dessa normalização. |
| Janela válida com ausência de algum dado comparativo ou analítico | Não converter ausência em zero. O contrato do dashboard define `null`/indisponibilidade do componente; não é erro do catálogo de opções. |
| PostgreSQL indisponível ou configuração Gold ausente | `503`, com erro genérico no formato FastAPI `{"detail":"Gold indisponível"}`, sem URL, credencial ou SQL na resposta. |
| Falha inesperada de programação ou schema incompatível | Erro interno, sem converter em `200` vazio. Registrar a causa sem expor segredos ao cliente. |

A lista global de opções não é reduzida pela seleção ativa. Na Continuidade, município define o conjunto de alimentadores usado no ranking, nos gráficos e nas ocorrências; isso não cria DEC/FEC municipal. A ocorrência é filtrada pelo alimentador registrado no fato, nunca pelo município cadastral da UC. Causa afeta apenas lista/contagem de ocorrências. Como o snapshot Gold do MVP é estático, `staleTime: Infinity` evita novas chamadas de opções; uma eventual troca de snapshot ou de identidade exigirá invalidação explícita do cache.

## 7. Responsabilidades de Controller, Service e Repository

| Camada / arquivos previstos para tarefa futura | Responsabilidade |
| --- | --- |
| `backend/app/controllers/filters.py` e registro em `backend/app/main.py` | Publicar **somente** `GET /api/filters/options`, aplicando `/api` uma vez, sem `fields`; adquirir e liberar a conexão na requisição, traduzir indisponibilidade da Gold para `503` e declarar schema OpenAPI. Não executar SQL. |
| `backend/app/services/filters.py` | Compor e ordenar os cinco grupos aprovados, inclusive as relações município–bairro e alimentador–municípios. Não calcular métricas de dashboard nem derivar motivos de strings concatenadas. |
| `backend/app/repositories/filters.py` | Usar a conexão de `backend/app/core/database.py` com SQLAlchemy 2 Core + psycopg, consultas síncronas e parametrizadas. Consultar projeções/distintos nas tabelas Gold e devolver dados sem joins entre fatos que multipliquem registros. Sem ORM da Gold. |
| `backend/app/schemas/filters.py` | Definir DTO dos cinco campos aprovados; tipos HTTP não representam tabelas físicas. |
| `backend/tests/` | Testes de repository com PostgreSQL local quando disponível, testes unitários de organização e testes HTTP de contrato/erros. Reutilizar padrões existentes; criar apenas arquivos necessários na implementação futura. |

O engine existente é criado sob demanda, com timeout de conexão/consulta e encerramento da conexão por contexto. Não adicionar cache, novas dependências, migrações ou infraestrutura para este endpoint. As consultas de opções não alteram a Gold.

## 8. Testes e critérios de aceitação

1. **Contrato aprovado:** teste HTTP de `GET /api/filters/options` confirma `200`, exatamente `competencias`, `municipios`, `classes`, `alimentadores` e `causas`; ausência de `motivos` e `fields` no OpenAPI; prefixo `/api` único.
2. **Gold e ordenação:** teste PostgreSQL confirma meses em ordem de `dim_competencia.competencia`, pares município–bairro distintos, códigos de classe preservados, circuitos distintos com **todos** os municípios atendidos e causas Gold distintas, inclusive `NAO INFORMADA` e `NAO IDENTIFICADA`. A resposta não inclui UC, nome de titular, endereço, score ou motivo concatenado. Mock do frontend não é evidência do snapshot real.
3. **Dependências:** teste de frontend futuro valida bairro e alimentador filtrados localmente por município, limpeza de bairro ao trocar município e de alimentador incompatível; teste de API rejeita pares inválidos com `422`. Alimentador que serve dois municípios deve aparecer em ambos, sem usar apenas `municipio_principal`.
4. **Períodos:** testar presets 3/6/12 ancorados no último mês Gold, padrão 12, `inicio`/`fim` nas rotas temporais e comparação de Indicadores com os X meses imediatamente anteriores derivada no backend. Verificar `422` para formato, ordem, competência, janela ou combinação inválida; histórico comparativo ausente não vira zero. Receita mantém P0/P1 fixos e nenhum parâmetro de período.
5. **Escopo da Continuidade:** sem alimentador escolhido, testar que município restringe ranking, séries/gráficos e lista/contagem de ocorrências ao conjunto de alimentadores associado; alimentar as ocorrências por `fact_ocorrencias.alimentador`, inclusive quando a UC do evento tiver outro município cadastral. Conferir DEC/FEC Gold de cada alimentador sem alteração ou agregado municipal, e o aviso de alcance do circuito inteiro na interface. Causa altera somente lista/contagem de ocorrências, sem modificar DEC/FEC. Um ranking ou total sem definição Gold válida permanece indisponível, mesmo com o filtro municipal.
6. **Falhas e ausência:** testar `200` com lista genuinamente vazia, `503` por indisponibilidade e falhas inesperadas sem falso sucesso; o catálogo não consulta indicadores nem altera `/api/health` ou `/api/uc/{uc_id}/360`.
7. **Integração do Portal:** uma resposta compartilhada reutilizada com TanStack Query `staleTime: Infinity`, sem novas chamadas ao trocar de tela ou município; atualização do tipo/mock/componentes em tarefa própria. Todos os critérios de negócio só podem ser declarados atendidos depois de implementados e testados em suas rotas.

Esta etapa é apenas documental; nenhum teste de código foi executado nem rota adicional foi publicada.

## 9. Limitações e pendências para validação

| Tema | Estado e encaminhamento |
| --- | --- |
| Motivos da Fila | **Decidido para o MVP:** não filtrar por motivo nem incluir `motivos` no catálogo. `fila_inspecao.motivo_suspeita` concatena regras com `;`; Engenharia de Dados e Perdas ainda precisam publicar/validar vocabulário e correspondência atômica antes de uma extensão futura. Isso não bloqueia município, bairro e classe. |
| Cobertura analítica da Continuidade | **Decidido na interface:** município limita os alimentadores do ranking, dos gráficos e das ocorrências; causa só filtra lista/contagem de ocorrências. DEC/FEC de cada alimentador permanecem integrais, com aviso na tela, sem indicador municipal ou por causa. A Gold ainda não fornece DEC/FEC pronto para toda a rede, janelas móveis completas ou variações/ranking nos grãos desejados. Restringir o conjunto de circuitos não resolve essa lacuna; apresentar componentes indisponíveis quando necessário, sem cálculo substituto no FastAPI. |
| Relação município–alimentador | O conjunto de circuitos usa a associação do cadastro atual da UC, não vínculo histórico. Uma ocorrência antiga pode trazer circuito diferente do atual daquela UC; filtrar pelo `fact_ocorrencias.alimentador` do evento, se ele estiver no conjunto associado ao município escolhido. O Portal avisará que DEC/FEC são do alimentador inteiro. Não filtrar fatos pelo município da UC. |
| Dados insuficientes na comparação de Indicadores | **Decidido:** janela anterior tem o mesmo X e é derivada no backend. Se um snapshot futuro não oferecer 2X competências ou uma métrica faltar em parte da comparação, o contrato de `GET /api/metrics/general` ainda precisa definir a forma exata de `null`/componente indisponível; nunca inventar zero. |
| Documentos e frontend ainda desatualizados | `planejamento-backend.md` e `frontend/src/hooks/use-opcoes-filtros.ts` ainda descrevem três grupos; `impl_continuidade.md` ainda usa alimentadores `string[]`, `periodo_inicio`/`periodo_fim`, filtro pelo município cadastral da ocorrência e trata o gráfico sem alimentador como indisponível. Sincronizar esses contratos em tarefas próprias com o recorte por conjunto de alimentadores e séries individuais, sem inventar DEC/FEC agregado. A UI atual ainda mostra `De`/`Até`, não os presets 3/6/12. |
| Cache e troca de identidade/snapshot | `useOpcoesFiltros` já usa `staleTime: Infinity`. Definir o momento de limpeza do cache após login/logout/troca de usuário ou eventual nova carga da Gold; não criar cache no backend para o MVP estático. |

**Próximo passo após validação deste documento:** sincronizar o planejamento geral, o contrato da Continuidade e o tipo/mock do frontend com as decisões já tomadas; tratar as lacunas analíticas e o vocabulário de motivos com as equipes responsáveis. GRILL ME, especificação técnica, tickets e código não são iniciados aqui.
