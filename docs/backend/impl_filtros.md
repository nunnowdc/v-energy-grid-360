# Planejamento de implementação — filtros compartilhados do Portal

## 1. Objetivo e requisitos das telas

Planejar exclusivamente `GET /api/filters/options` para fornecer opções reutilizáveis às telas do V-Energy Grid 360. Este documento separa **contrato já aprovado**, **comportamento presente no frontend**, **dados confirmados pelo [dicionário Gold](../../data-engineering/relatorio_tabelas/dicionario_dados_gold.md)** e **extensões propostas que dependem de alinhamento**. A Gold é a fonte de verdade para valores, relações e indicadores; a rota de opções não calcula métricas nem aplica filtros aos dashboards.

| Tela e rota de negócio planejada | Filtros solicitados para a tela | Situação observada no frontend |
| --- | --- | --- |
| Indicadores — `GET /api/metrics/general` | Município, classe, últimos X meses e comparação com os X meses anteriores. | `IndicadoresPage` usa município, classe e dois seletores de competência (`De`/`Até`). Não há seletor de X nem de comparação implementado. |
| Receita — `GET /api/metrics/revenue-variance` | Município, bairro, classe, intervalo base mês/ano inicial–final e intervalo de comparação inicial–final. | `ReceitaPage` usa apenas município, bairro e classe. O [planejamento geral](planejamento-backend.md) e o [README da raiz](../../README.md) mantêm períodos **fixos** para o MVP; intervalos livres são requisito proposto, ainda não aprovado. |
| Fila de Inspeção — `GET /api/inspections/queue` | Município, bairro, motivo e classe. | `InspecoesPage` ainda não monta a barra de filtros. A origem e a semântica das opções de motivo precisam de validação. |
| Continuidade — `GET /api/network/continuity` | Últimos X meses, município, alimentador e causa. | `ContinuidadePage` usa apenas competência (`De`/`Até`) e município; o [planejamento da tela](impl_continuidade.md) propõe alimentador e causa, sem implementação. |
| Visão 360 — `GET /api/uc/{uc_id}/360` | Nenhum filtro compartilhado de tela: recebe o ID completo da UC. | Endpoint da UC já existe; seus parâmetros de paginação não são opções deste serviço. |

As opções de município, bairro e classe são globais e iguais onde reaparecem. A seleção visual atual é **única** por campo (`FiltroSelect`); “Todos/Todas” é estado sem seleção, não uma categoria da Gold. A aplicação efetiva dos filtros permanece responsabilidade de cada rota de negócio, respeitando o grão dos seus dados.

## 2. Escopo do endpoint e integração existente

- **Rota única deste planejamento:** `GET /api/filters/options`, sem corpo, sem `fields` e sem contexto de página no contrato aprovado. Retorna o catálogo de opções do snapshot Gold, não resultados filtrados. Não criar rota adicional nesta etapa.
- **Aprovado hoje:** o JSON contém **exatamente** `competencias`, `municipios` (objetos `{nome, bairros}`) e `classes`, conforme a seção 9.2 do planejamento geral e o tipo `OpcoesFiltros` em `frontend/src/hooks/use-opcoes-filtros.ts`. `motivos`, `alimentadores` e `causas` **não fazem parte desse contrato aprovado**. A seção 5 propõe acrescentá-los somente após validação com o frontend; documentá-los aqui não autoriza sua publicação.
- **Estado do código:** `backend/app/main.py` registra `/api/health` e `/api/uc/{uc_id}/360`, além de documentação/OpenAPI sob `/api`. Ainda não há controller, service, repository ou schema de filtros. `frontend/src/mocks/` simula a resposta das três listas no desenvolvimento; o mock não comprova valores do PostgreSQL.
- **Responsabilidades:** o backend consulta e organiza opções Gold; o React mostra seletores, guarda escolhas na URL, filtra listas dependentes localmente quando o contrato fornece os vínculos e chama cada endpoint de negócio com seus parâmetros. A Gold do MVP é estática; não se planeja cache adicional no FastAPI.
- **Fora do escopo:** implementar endpoints de dashboards, regras analíticas, autenticação/RBAC, IA, tabelas, índices ou alterações no frontend. As decisões gerais de segurança permanecem preservadas para outra etapa.

## 3. Mapeamento das opções e dos períodos para a Gold

Os nomes JSON desta seção são **campos HTTP**. As fontes e colunas abaixo estão documentadas na Gold; formatos de seleção relativa e rótulos de interface pertencem ao frontend. Uma competência disponível no calendário não garante registros de todas as métricas naquela competência.

| Opção | Tabela e colunas Gold exatas; tipo e grão | Domínio/ordem e dependência | Limite |
| --- | --- | --- | --- |
| `competencias` | `dim_competencia.mes_referencia` (`string`, `yyyy-MM`) e `dim_competencia.competencia` (`date`, primeiro dia do mês); uma linha por competência. | Meses distintos em ordem de `competencia` crescente; o dicionário documenta 48 meses, de `2022-07` a `2026-06`. Independe dos demais seletores. | Calendário do snapshot, não disponibilidade de cada indicador. X meses e comparação não são colunas Gold. |
| `municipios[].nome` e `municipios[].bairros` | Pares distintos `dim_unidade_consumidora.municipio` e `.bairro` (`string`); uma linha de cadastro por `id_uc`. | Municípios em ordem alfabética; bairros únicos e em ordem alfabética **dentro** do município. Gold documenta 14 municípios e bairros com encoding corrigido. `bairro` exige município para desambiguar. | Não deduzir vínculo bairro–município de texto ou de `municipio_principal`. Valores nulos, se houver no snapshot, não viram a opção literal `null`. |
| `classes` | `dim_unidade_consumidora.classe` (`string`); uma linha por `id_uc`, consultar valores distintos. | Preservar códigos Gold: `RESIDENCIAL`, `COMERCIAL`, `INDUSTRIAL`, `RURAL`, `PODER_PUBLICO`, quando presentes no snapshot. Ordenação determinística; rótulos amigáveis vêm de `frontend/src/config/classes.ts`. | Não trocar códigos pelos rótulos. O frontend tipa os cinco códigos; um domínio novo exigirá alinhamento. |
| `alimentadores` **proposto** | `dim_alimentador.alimentador` (`string`, um registro por circuito; 122 no dicionário). Para a dependência municipal: pares distintos `dim_unidade_consumidora.municipio` e `.alimentador`, ligados por igualdade do código `alimentador`. | Códigos Gold, por exemplo `ALM-REC-008`, em ordem alfabética. Um alimentador pode servir mais de um município; o vínculo cadastral atual permite lista local por município. | `dim_alimentador.municipio_principal` indica apenas o município com mais UCs, não todos os atendidos. O cadastro não documenta validade histórica desse vínculo. |
| `causas` **proposto** | `fact_ocorrencias.causa` (`string`; fato com uma linha por UC interrompida), consultar valores distintos. | A Gold documenta `CLIMATICA`, `VEGETACAO`, `TERCEIROS`, `SOBRECARGA`, `FALHA DE EQUIPAMENTO`, `NAO IDENTIFICADA` e `NAO INFORMADA`; ordenar alfabeticamente e preservar grafia. Não depende de município no catálogo global. | `NAO INFORMADA` já reúne nulos/sentinelas; `NAO IDENTIFICADA` é categoria válida diferente. Selecionar causa **não** torna DEC/FEC por causa disponíveis. |
| `motivos` **proposto** | `fila_inspecao.motivo_suspeita` (`string`; uma linha por UC com `score >= 20`), além de `municipio`, `bairro` e `classe` da própria fila quando a rota de negócio for filtrada. | A coluna contém **múltiplas regras concatenadas por `;`**. Uma opção de motivo atômico exigiria vocabulário e regra de separação/igualdade validados pela Engenharia de Dados e Perdas. | O dicionário não enumera valores atômicos nem uma dimensão de motivos. Não oferecer os textos concatenados como se fossem motivos individuais e não inventar uma lista. O campo está classificado como dado pessoal ALTO; a resposta de opções não deve expor linhas, UCs, scores ou contagens por motivo. |

### 3.1 Indicadores: período relativo e comparação

O requisito solicitado é “últimos X meses” e “X meses anteriores”. **Proposta a validar:** X é uma quantidade inteira positiva de competências consecutivas, escolhida pelo frontend; a janela principal termina em `max(dim_competencia.competencia)` e a comparação ocupa os X meses imediatamente anteriores, com a **mesma duração**. O padrão de ausência de período no frontend atual é X = 12; no snapshot documentado, a janela base seria `2025-07`–`2026-06` e a anterior contígua `2024-07`–`2025-06`. Os X permitidos pela interface, comportamento quando não houver 2X competências e eventual comparação não contígua precisam de decisão. Não assumir controle independente de duração para “Comparar com” sem confirmação do Portal.

Hoje o componente real apresenta `inicio` e `fim` como escolhas absolutas de competência, sem controle de comparação. Esta proposta exige atualização explícita do frontend e do contrato de `GET /api/metrics/general`; o endpoint de opções precisa apenas de `competencias`. Indicadores derivados de `agg_receita_mensal` devem respeitar seu grão `competencia × municipio × bairro × classe × possui_gd`: `ucs_faturadas` não é contagem distinta aditiva entre meses e `preco_medio_kwh` não deve ser somado. Este documento não define cálculos de KPI.

### 3.2 Receita: intervalos absolutos propostos versus períodos fixos

A solicitação atual descreve **dois intervalos inclusivos** por mês/ano (`yyyy-MM`): `base_inicio`–`base_fim` e `comparar_inicio`–`comparar_fim` como nomes HTTP **propostos**, não aprovados. Cada extremo deve existir em `competencias`, e início deve ser menor ou igual ao fim. Padrões coerentes com a decisão vigente seriam base `2022-07`–`2023-06` e comparação `2025-07`–`2026-06`; se a escolha livre for aprovada, validar com o Portal duração, sobreposição, relação temporal e nomes finais dos quatro parâmetros.

**Decisão vigente do MVP:** `agg_receita_preco_volume` publica a decomposição apenas para `periodo_p0` (primeiro ano) e `periodo_p1` (últimos 12 meses), com os períodos acima; a página atual não apresenta seletores de intervalo. `agg_receita_mensal` fornece dados mensais nos recortes de município, bairro e classe, mas **não publica efeitos preço/volume de intervalos arbitrários**. Assim, aceitar intervalos livres na tela de decomposição depende de uma definição analítica e contratual com Engenharia/Diagnóstico e frontend; até essa aprovação, o endpoint de opções não muda os períodos fixos da Receita e não se implementam efeitos alternativos no FastAPI.

### 3.3 Fila de Inspeção

Município, bairro e classe podem usar o catálogo global, mas a fila tem apenas UCs com `score >= 20`; uma opção global pode gerar resultado vazio na fila. `fila_inspecao` já contém `municipio`, `bairro`, `classe` e `motivo_suspeita`, sem JOIN cadastral necessário para esses filtros. Um motivo selecionado só poderá filtrar regras atômicas após definição de vocabulário e correspondência; igualdade com a coluna concatenada inteira mudaria o significado do filtro. O frontend ainda não implementa a barra dessa tela.

### 3.4 Continuidade

A janela relativa proposta termina na última competência Gold e usa X meses, com padrão X = 12, mas o frontend atual mostra `De`/`Até` absolutos. `dim_alimentador.alimentador` fornece circuitos; pares cadastrais `(municipio, alimentador)` permitem restringir **opções** de circuito após selecionar município. `fact_ocorrencias.causa` fornece causas. Para filtrar o fato por município, é necessário `fact_ocorrencias.id_uc = dim_unidade_consumidora.id_uc`; para circuito e tempo, usar `fact_ocorrencias.alimentador` e `.competencia` do evento, não substituir pelo alimentador atual da UC.

A Gold publica `agg_continuidade_alimentador` no grão `alimentador × competencia`, com DEC/FEC já calculados. Ela não publica DEC/FEC por causa nem a fração municipal do circuito; `municipio_principal` é descritivo. Portanto, as opções e a possibilidade de selecionar causa ou município **não garantem** que esses recortes se apliquem aos cards/séries DEC/FEC. A rota de continuidade deve explicitar seus componentes indisponíveis conforme [seu planejamento](impl_continuidade.md), sem recalcular indicadores.

## 4. Dependências e consultas necessárias

1. **Opções básicas:** consultar `dim_competencia` separadamente, obter pares distintos de município/bairro e classes distintas de `dim_unidade_consumidora`. Montar objetos municipais sem multiplicar bairros por JOIN com fatos. Preservar grafia Gold, remover duplicações e ordenar deterministicamente; não retornar dados pessoais da UC.
2. **Circuitos propostos:** consultar a lista distinta de `dim_alimentador.alimentador` e a associação distinta `(dim_unidade_consumidora.municipio, dim_unidade_consumidora.alimentador)`. Relacionar pelo código do alimentador, agrupando os municípios atendidos; não usar apenas `municipio_principal`. Com 122 circuitos documentados, a associação pode ser carregada uma vez e filtrada localmente, após medir o tamanho real da resposta. O vínculo é cadastral atual, não uma afirmação sobre cada ocorrência histórica.
3. **Causas propostas:** consultar `DISTINCT fact_ocorrencias.causa` sem juntar a dimensão de UC, pois a lista global não depende de município. Preservar `NAO INFORMADA` e `NAO IDENTIFICADA` separadas.
4. **Motivos propostos:** não fixar uma consulta de separação como contrato antes da confirmação das regras atômicas e de sua forma canônica. Consultar textos brutos distintos não resolve a opção “motivo” desejada. Após validação, selecionar apenas o vocabulário necessário, sem linhas identificáveis da fila.
5. **Períodos:** o frontend deriva janelas relativas do calendário ordenado; datas de comparação são seleção de interface/contrato de cada dashboard, não novas colunas em `/api/filters/options`. Períodos absolutos usam os códigos `yyyy-MM` já fornecidos. Não usar relógio do servidor como âncora.
6. **Aplicação em endpoints de negócio:** um valor por campo; filtros diferentes combinam com AND, dentro dos limites analíticos da tabela consultada. O backend valida entradas diretas mesmo quando a UI remove escolhas inválidas. Nunca aplicar uma combinação incompatível a um agregado Gold para fingir que possui o recorte.

**Dependentes no Portal:** `bairro` é filtrado pelos `municipios[].bairros` do município escolhido. Trocar ou limpar município remove bairro — comportamento já presente em `frontend/src/lib/filtros-url.ts`. Para alimentador, se aprovada a relação proposta, o React mostrará apenas circuitos cujo `municipios` inclua o município escolhido; ao trocar município, limpar o alimentador somente se ele não atender o novo município. Sem município, mostrar todos os circuitos. A causa continua global; uma combinação sem ocorrências pode produzir resultado vazio. Antes de executar um dashboard, validar no backend município/bairro e município/alimentador; a ausência de uma associação cadastral não deve ser confundida com inexistência histórica de evento sem decisão específica.

## 5. Contrato HTTP: vigente e extensão proposta

### 5.1 Contrato aprovado, sem mudança nesta etapa

**Requisição:** `GET /api/filters/options HTTP/1.1`, sem body e sem query parameters de seleção. No código do frontend, `apiFetch('/filters/options')` aplica `/api` uma vez. O retorno aprovado é `200 OK` com **somente** os três campos abaixo; os valores do exemplo são ilustrativos:

```json
{
  "competencias": ["2022-07", "2022-08", "2026-06"],
  "municipios": [
    {"nome": "Recife", "bairros": ["Boa Viagem", "Casa Forte"]}
  ],
  "classes": ["RESIDENCIAL", "COMERCIAL", "INDUSTRIAL", "RURAL", "PODER_PUBLICO"]
}
```

Não existe parâmetro `fields`, resposta por cargo ou subconjunto por tela. Retornar todos os meses, municípios/bairros e classes do snapshot em uma chamada é compatível com o `useOpcoesFiltros` existente.

### 5.2 Menor extensão recomendada, **ainda não aprovada**

Se frontend, backend e responsáveis pelos dados aprovarem a expansão, manter intactos os três campos anteriores e acrescentar **somente** `alimentadores`, `causas` e `motivos`. Para permitir dependência municipal sem outra requisição nem um segundo campo de mapeamento, propõe-se `alimentadores` como lista de objetos `{codigo, municipios}`. A lista simples de códigos sugerida em `impl_continuidade.md` é uma **proposta anterior incompatível com esta forma**; escolher uma das duas formas com o Portal antes de implementar. `causas` e `motivos` são listas de strings. `motivos` depende primeiro da validação do vocabulário atômico; não publicar lista vazia para disfarçar uma definição pendente.

**Exemplo apenas de formato da extensão; nomes e associações ilustrativos, e `motivos: []` não afirma que a Gold não contenha motivos:**

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
  "causas": ["VEGETACAO"],
  "motivos": []
}
```

Uma resposta compartilhada é recomendada para o MVP: catálogo pequeno e estático, uma consulta de opções já usada pelo Portal, reuso entre telas e nenhuma necessidade comprovada de `contexto`, `fields` ou endpoints por página. A extensão exige atualizar tipo TypeScript, mock, testes e componentes da interface **em outra tarefa**. Se o volume real de motivos ou associações tornar o payload relevante, medir antes de propor contextos. Não adicionar metadados de períodos: `competencias` basta para derivar última competência, intervalos e opções de X; os X oferecidos e as regras de comparação pertencem à UI e aos contratos dos dashboards.

### 5.3 Escolhas do Portal e parâmetros dos dashboards

O frontend atual guarda escolhas compartilhadas na URL com `inicio`, `fim`, `municipio`, `bairro` e `classe`. `municipio`/`bairro` são nomes Gold, `classe` é o código Gold e meses são `yyyy-MM`; a opção geral remove o parâmetro (nunca enviar a palavra `Todos`). `URLSearchParams` faz a codificação. Um campo categórico envia no máximo **um** valor; não usar parâmetros repetidos. `useFiltros` descarta escolhas inválidas após carregar opções, troca os extremos se a URL trouxer `inicio > fim` e limpa bairro ao trocar município. O backend deverá validar seus próprios parâmetros de negócio; não depender dessa sanitização do navegador.

| Tela | Representação vigente / proposta para requisição de negócio | Decisão necessária |
| --- | --- | --- |
| Indicadores | URL atual: `inicio`, `fim`, `municipio`, `classe`. **Proposta de API:** `inicio`, `fim` para a janela base; comparação derivada dos mesmos X meses, com extremos `comparar_inicio`, `comparar_fim` se forem necessários ao contrato. Sem escolha: últimas 12 competências Gold. | Acordar controles de X, formato final dos parâmetros e se comparação é automática ou selecionável; não presumir duração independente. |
| Receita | URL atual e requisição exemplificada no README: `municipio`, `bairro`, `classe`; períodos fixos da Gold sem parâmetros. **Requisito novo proposto:** `base_inicio`, `base_fim`, `comparar_inicio`, `comparar_fim` (`yyyy-MM`). | Aprovar substituição da decisão de períodos fixos, capacidade analítica para decomposição em intervalos livres, controles da tela e nomes HTTP. |
| Fila | **Proposta:** `municipio`, `bairro`, `classe`, `motivo`, um valor de cada vez; omissão equivale a todos. | Definir vocabulário e igualdade de motivo atômico, além da barra ainda inexistente. |
| Continuidade | URL atual: `inicio`, `fim`, `municipio`. `impl_continuidade.md` **propõe** à rota de negócio `periodo_inicio`, `periodo_fim`, `municipio`, `alimentador`, `causa`, ambos os extremos de período ou nenhum. | Alinhar tradução entre URL e API, controle de X relativo e forma da opção de alimentador. Causa/município não podem recortar DEC/FEC agregados como se fossem fatos. |

Exemplos de filtros categóricos **dependentes de aprovação da rota de negócio**: `GET /api/inspections/queue?municipio=Recife&bairro=Boa%20Viagem&classe=RESIDENCIAL`; `GET /api/network/continuity?municipio=Recife&alimentador=ALM-REC-008&causa=VEGETACAO`. Esses exemplos mostram codificação e seleção única, **não** prometem todos os indicadores sob tais recortes. `GET /api/filters/options` não recebe esses parâmetros.

## 6. Erros, ausências e limpeza de seleção

| Situação | Comportamento proposto |
| --- | --- |
| Gold acessível, conjunto de uma categoria realmente vazio | `200` com `[]` no grupo correspondente; o Portal mostra seletor vazio/desabilitado. Uma competência ausente não é inventada. Não usar `[]` para esconder um contrato de motivos ainda indefinido. |
| Município sem bairros válidos ou sem alimentadores associados | Mostrar lista dependente vazia e impedir seleção incompatível; remover valor dependente obsoleto da URL. A ausência de opções não equivale a erro da API. |
| Usuário seleciona “Todos/Todas” ou limpa filtros | Remover parâmetro da URL; para período relativo, voltar à janela padrão derivada da Gold. `removerFiltros` atual preserva parâmetros de URL não pertencentes aos filtros. A limpeza de novos campos precisará ser incorporada pelo frontend quando aprovados. |
| Valor desconhecido, duplicado ou combinação inválida enviada diretamente ao endpoint de negócio | Validar os parâmetros no controller/service do respectivo dashboard e responder erro de validação (`422` proposto), sem aplicar silenciosamente uma categoria diferente. Para `GET /api/filters/options`, não há parâmetros de filtro aprovados. |
| Período malformado, fora do calendário, invertido ou incompleto | A interface usa `yyyy-MM` e pode normalizar sua própria URL; o backend valida requisições diretas. Para Receita proposta, exigir extremos de cada intervalo, se a seleção livre vier a ser aprovada. Para Continuidade, seguir a proposta de ambos os extremos ou nenhum. Regras finais por rota exigem alinhamento. |
| PostgreSQL indisponível ou configuração Gold ausente | `503`, erro genérico no formato FastAPI `{"detail":"Gold indisponível"}`, sem URL, credencial ou SQL na resposta. |
| Falha inesperada de programação ou schema incompatível | Erro interno, sem converter em lista vazia. Registrar a causa sem expor segredo ao cliente. |

A lista global não é reduzida pela seleção ativa; combinações com resultado vazio são possíveis. Se houver troca futura de snapshot, `staleTime: Infinity` exigirá invalidação explícita do cache das opções. No MVP local, o snapshot é estático. Após implementação de identidade, limpar dados de consulta na troca de usuário conforme a política do Portal, sem antecipar autenticação neste endpoint.

## 7. Responsabilidades de Controller, Service e Repository

| Camada / arquivos previstos para tarefa futura | Responsabilidade |
| --- | --- |
| `backend/app/controllers/filters.py` e registro em `backend/app/main.py` | Publicar **somente** `GET /api/filters/options`, aplicando `/api` uma vez, sem `fields`; adquirir e liberar a conexão na requisição, traduzir indisponibilidade da Gold para `503` e declarar schema OpenAPI. Não executar SQL. |
| `backend/app/services/filters.py` | Compor e ordenar os grupos do catálogo e relações município–bairro; adicionar grupos extras apenas após aprovação. Não calcular métricas de dashboard nem criar regra analítica para motivo. |
| `backend/app/repositories/filters.py` | Usar a conexão de `backend/app/core/database.py` com SQLAlchemy 2 Core + psycopg, consultas síncronas e parametrizadas. Consultar projeções/distintos nas tabelas Gold e devolver dados sem joins entre fatos que multipliquem registros. Sem ORM da Gold. |
| `backend/app/schemas/filters.py` | Definir DTO da resposta **vigente** e, se aprovada, tipar a extensão; tipos HTTP não representam tabelas físicas. |
| `backend/tests/` | Testes de repository com PostgreSQL local quando disponível, testes unitários de organização e testes HTTP de contrato/erros. Reutilizar padrões existentes; criar apenas arquivos necessários na implementação futura. |

O engine existente é criado sob demanda, com timeout de conexão/consulta e encerramento da conexão por contexto. Não adicionar cache, novas dependências, migrações ou infraestrutura para este endpoint. As consultas de opções não alteram a Gold.

## 8. Testes e critérios de aceitação

1. **Contrato aprovado:** teste HTTP de `GET /api/filters/options` confirma `200`, exatamente `competencias`, `municipios` e `classes`, ausência de `fields` no OpenAPI e prefixo `/api` único. Antes da aprovação da extensão, grupos extras não devem aparecer.
2. **Gold e ordenação:** teste PostgreSQL verifica meses ordenados por `dim_competencia.competencia`, pares município–bairro distintos e ordenados, classes preservadas exatamente como publicadas, sem nomes/endereços/IDs de UC na resposta. Mock do frontend não é evidência dos dados reais.
3. **Dependências aprovadas:** bairro só aparece dentro do município correto; em tarefa posterior, se aprovado o grupo de alimentadores com vínculos, validar circuitos que atendem vários municípios e não reduzi-los a `municipio_principal`. Causas devem manter `NAO INFORMADA` e `NAO IDENTIFICADA` diferentes.
4. **Motivos:** antes de expor `motivos`, obter exemplos Gold e regra de separação/igualdade validada; testar que o valor selecionado corresponde a uma regra inteira, não à string concatenada nem a substring casual. Não reproduzir cálculo do score da fila.
5. **Períodos e Portal:** testar default baseado na última competência Gold, não no relógio; `inicio`/`fim` e seleção única atuais; limpeza do bairro ao trocar município; novos controles e tradução de parâmetros apenas depois do acordo com frontend. Para Receita, testar que a decisão vigente de períodos fixos não mudou por publicar mais opções.
6. **Falhas e ausência:** testes HTTP para grupos genuinamente vazios e `503` em indisponibilidade, sem vazamento de conexão; teste de erro inesperado não convertido em `200` vazio. Validar que o endpoint de opções não dispara consultas de indicadores nem altera o comportamento de `/api/health` e `/api/uc/{uc_id}/360`.
7. **Aceitação funcional:** todas as telas reutilizam as mesmas opções de município/bairro/classe; o frontend não precisa refazer a chamada ao mudar de página; os dashboards recebem somente os filtros que seus próprios contratos suportam. Filtros de causa e município não passam a alterar DEC/FEC por mera presença no catálogo.

Esta etapa é apenas documental; nenhum teste de código foi executado nem contrato adicional foi publicado.

## 9. Limitações e decisões pendentes para validação

| Tema | Estado e decisão necessária |
| --- | --- |
| Extensão do JSON central | **Aprovado:** três grupos. **Proposto:** adicionar `alimentadores`, `causas`, `motivos` na mesma resposta. O frontend precisa aprovar tipo, presença dos grupos e atualização do mock/componentes antes de alterar a API. `impl_continuidade.md` sugere `alimentadores` como `string[]`; esta proposta usa `{codigo, municipios}[]` para filtragem local — escolher uma forma única. |
| Motivos de inspeção | `fila_inspecao.motivo_suspeita` não é uma dimensão atômica e a Gold não lista as strings de cada regra. Engenharia de Dados/Perdas devem validar vocabulário, separador, igualdade e rótulo; até lá, não há opção de motivo confiável. |
| Receita em intervalos livres | O requisito pedido contradiz os períodos fixos aprovados para a decomposição em `agg_receita_preco_volume` e a UI atual. Frontend, Engenharia/Diagnóstico e backend precisam decidir se mantêm a comparação fixa no MVP ou aprovam outra entrega analítica/contrato. `agg_receita_mensal` mensal, por si só, não resolve a decomposição. |
| Indicadores e comparação | Frontend atual tem `De`/`Até`, não X nem “Comparar com”. Definir X permitidos, relação entre janelas, padrão, nomes de parâmetros e indicadores válidos para cada grão. Comparação de mesma duração é proposta, não decisão já implementada. |
| Continuidade e causa/município | A Gold fornece opções e contagens de `fact_ocorrencias`, mas DEC/FEC em `agg_continuidade_alimentador` não aceita recorte fiel por causa ou município. Alinhar apresentação parcial/indisponível com Operação e frontend; não recalcular DEC/FEC. |
| Dependência de alimentador | Pares de `dim_unidade_consumidora` descrevem o cadastro atual; confirmar se a UI deve restringir só opções ou também impedir combinações que tenham fatos históricos com outro vínculo. Não usar `municipio_principal` como vínculo exclusivo. |
| URL e API de períodos | URL atual usa `inicio`/`fim`; o plano de Continuidade sugere `periodo_inicio`/`periodo_fim`; Receita livre sugere quatro parâmetros próprios. Acordar a tradução e validação por dashboard, sem alterar silenciosamente caminhos existentes. |
| Cache e troca de identidade/snapshot | `useOpcoesFiltros` já usa `staleTime: Infinity`. Definir quando limpar o cache após login/logout/troca de usuário ou eventual recarga do snapshot; não criar cache no backend para o MVP estático. |

**Próximo passo após validação deste documento:** alinhar as decisões de contrato com o frontend e responsáveis pelos dados antes de iniciar GRILL ME, especificação técnica, tickets ou código. Nenhuma dessas etapas é iniciada aqui.
