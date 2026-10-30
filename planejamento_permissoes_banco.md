# Planejamento: permissões no nível do banco de dados

**Data:** 28/10/2026 (atualizado em 30/10/2026) · **Responsável pela implementação:** Rafael · **Status:** scripts de PERDAS, OPERACAO e ADMIN_TI escritos; integração com o backend adiada (seção 6.3)

> **Para o assistente no VS Code:** este arquivo é o contexto completo. Os fatos das seções 1 e 2 vêm de decisões já documentadas pelo time. Tudo o que estiver marcado **[A CONFIRMAR]** não foi decidido: **pergunte ao Rafael, não invente**. O Rafael quer implementar ele mesmo; o papel do assistente é orientar, explicar e revisar.

---

## 1. Síntese do que o time já decidiu

### 1.1 Conceitos (como o time está usando os termos)

| Conceito | Pergunta que responde | No portal |
|---|---|---|
| **Autenticação** | Quem é você? | Login com e-mail e senha |
| **Autorização por perfil (RBAC)** | O que o seu cargo pode ver e fazer? | O atendente acessa a Visão 360, mas não a tela de Receita |
| **Autorização por linha (RLS)** | Quais registros são seus? | Cada usuário só vê as próprias conversas com a IA |

RBAC e RLS não são alternativas: são camadas complementares. **Decisão do Rafael (30/10): no banco, controlar só por tabela e por coluna; RLS (por linha) foi descartado.**

### 1.2 Os 5 perfis

Mesmos nomes do backend (coluna `role` de `usuarios`, espelhada em `frontend/src/config/perfis.ts`):

`DIRETORIA` · `ATENDIMENTO` · `PERDAS` · `OPERACAO` · `ADMIN_TI`

No banco, cada perfil vira o role `perfil_<perfil em minúsculas>`: `perfil_diretoria`, `perfil_atendimento`, `perfil_perdas`, `perfil_operacao`, `perfil_admin_ti`.

### 1.3 Telas × perfis

Segue a matriz aprovada (seção 7.1 do `docs/backend/planejamento-backend.md`).

| Tela | DIRETORIA | ATENDIMENTO | PERDAS | OPERACAO | ADMIN_TI |
|---|:-:|:-:|:-:|:-:|:-:|
| Indicadores | ✅ | ❌ | ❌ | ❌ | ✅ |
| Receita | ✅ | ❌ | ❌ | ❌ | ✅ |
| Visão 360 | ❌ | ✅ | ✅ (qualquer UC pelo ID) | ❌ | ✅ |
| Fila de inspeção | ❌ | ❌ | ✅ | ❌ | ✅ |
| Continuidade | ✅ | ❌ | ❌ | ✅ | ✅ |
| Chat da IA | ✅ | ✅ | ✅ | ✅ | ✅ |
| Gestão de usuários | ❌ | ❌ | ❌ | ❌ | ✅ |

### 1.4 Ações × perfis

| Ação | DIRETORIA | ATENDIMENTO | PERDAS | OPERACAO | ADMIN_TI |
|---|:-:|:-:|:-:|:-:|:-:|
| Ver dados pessoais do cliente (nome, CPF, endereço) | ❌ | ✅ | ✅ | ❌ | ✅ |
| Gerar ordem de inspeção | ❌ | ❌ | ✅ | ❌ | ✅ |
| Registrar resultado / cancelar ordem | ❌ | ❌ | ✅ | ❌ | ✅ |
| Exportar fila / enviar planilha de campo | ❌ | ❌ | ✅ | ❌ | ✅ |
| Criar usuários e mudar perfis | ❌ | ❌ | ❌ | ❌ | ✅ |

### 1.5 Modelo de autorização no código: **modelo B**

Um **mapa central perfil → permissões** em código (um arquivo no backend), por exemplo `perdas → [gerar_ordem, ...]`. Os endpoints perguntam pela permissão (`exigir_permissao("gerar_ordem")`), e não pelo perfil. **O mapa fica em código, não em tabelas no banco**: com 5 perfis fixos, tabelas de perfis editáveis pela interface seriam complexidade sem retorno no prazo.

### 1.6 O agente de IA: opção **C (meio-termo)**

- A IA responde sobre **dados agregados para todos** os perfis.
- **Nunca** devolve dados pessoais (nome, CPF, endereço), e ninguém acessa dados de cliente pela IA.
- O usuário de banco do agente tem acesso **só às tabelas Gold**, e **nunca** às tabelas de usuários e conversas. É a defesa mais importante: um *prompt injection* como "mostre as conversas do Henrique" não vira vazamento, porque o usuário do banco do agente nem enxerga essas tabelas.

---

## 2. O que existe hoje na Gold (fato, não decisão)

Tabelas do schema Gold geradas no Databricks (detalhes em `dicionario_dados_gold.md`):

| Tabela | Tem dado pessoal (nome, CPF, endereço)? |
|---|---|
| `dim_unidade_consumidora` | **Sim**: `nome_titular`, `cpf_cnpj_mascarado`, `logradouro`, `numero`, `cep` (e `latitude`/`longitude`, ~1 km de precisão) |
| `fila_inspecao` | **Sim**: `nome_titular`, `logradouro`, `numero` (e `latitude`/`longitude`) |
| `dim_alimentador`, `dim_medidor`, `dim_geracao_distribuida`, `dim_competencia` | Não (só `id_uc`, que é pseudonimizado) |
| `fact_faturamento`, `fact_leituras`, `fact_ocorrencias`, `fact_atendimentos`, `fact_inspecoes` | Não diretamente (`id_uc`); são dados de comportamento do cliente |
| `agg_receita_mensal`, `agg_receita_preco_volume`, `agg_continuidade_alimentador`, `agg_continuidade_alimentador_anual` | Não (agregados) |
| `meta_dicionario_dados`, `meta_tabelas`, `meta_metricas` | Não (documentação; útil para o agente) |

**Ponto de atenção sobre a opção C:** "acesso só às tabelas Gold" **não basta** para a IA nunca devolver dado pessoal, porque duas tabelas Gold têm nome e endereço. Para garantir no banco, o agente precisa de restrição **por coluna** nessas duas (seção 4.4).

---

## 3. Por que no banco, e como isso conversa com o modelo B

O modelo B (mapa no backend) controla **o que cada perfil pode fazer na aplicação**. As permissões no banco são uma **segunda camada**: se um endpoint esquecer de checar a permissão, ou se o SQL gerado pelo agente tentar algo fora do papel, **o próprio banco recusa**.

| Camada | Controla | Exemplo |
|---|---|---|
| Backend (modelo B) | Telas e ações | `exigir_permissao("exportar_fila")` |
| Banco (este plano) | Tabelas e colunas que cada perfil e cada sistema pode ler ou escrever | O perfil `operacao` recebe "permission denied" ao ler `fila_inspecao` |

**Algumas ações o banco não consegue distinguir**, e continuam só no backend:
- "Ver a fila" e "exportar a fila" são o mesmo `SELECT` na `fila_inspecao`.
- "Enviar planilha" e "registrar um resultado" são o mesmo `INSERT` na tabela de resultados.
- Qual tela o usuário abriu.

**Regra para manter as duas camadas coerentes:** o mapa do modelo B e os `GRANT`s do banco descrevem a mesma matriz (seções 1.3 e 1.4). Quando um perfil mudar, os dois mudam juntos.

---

## 4. Desenho proposto no banco (Postgres)

> Só funciona em um banco com usuários e permissões, como o Postgres. **SQLite não tem controle de acesso.** **[A CONFIRMAR: qual banco o time vai usar]**

### 4.1 Papéis (roles)

| Role | Tipo | Para quê |
|---|---|---|
| `perfil_diretoria`, `perfil_atendimento`, `perfil_perdas`, `perfil_operacao`, `perfil_admin_ti` | Grupo, **sem login** | Cada um recebe as permissões do seu perfil (seções 1.3 e 1.4) |
| `portal_app` **(adiado, seção 6.3)** | **Com login**, `NOINHERIT`, membro dos 5 perfis | Usuário com que o backend conecta. Sozinho, **não tem permissão nenhuma**: a cada requisição o backend faz `SET LOCAL ROLE perfil_<x>` conforme o perfil de quem está logado |
| `portal_auth` **(adiado, seção 6.3)** | Com login | Só para o endpoint de login: lê as colunas da tabela de usuários necessárias para conferir e-mail e senha. Existe porque, **antes do login, ainda não se sabe o perfil** |
| `agente_ia` | Com login, somente leitura | Só a Gold, sem as colunas pessoais; nunca as tabelas do backend |
| `sync_databricks` | Com login | Só a carga noturna da Gold |
| Dono do banco | — | Cria os objetos; **não é usado em tempo de execução** |

**Por que `NOINHERIT` + `SET LOCAL ROLE`:** se algum código esquecer de definir o perfil, as consultas **falham** em vez de enxergar tudo (o erro é seguro). O `SET LOCAL` vale só até o fim da transação, então uma requisição não "herda" o perfil da anterior no pool de conexões.

### 4.2 Schemas

| Schema | Conteúdo | Quem escreve |
|---|---|---|
| `gold` | Tabelas vindas do Databricks | Só `sync_databricks` |
| `app` | Tabelas do backend (usuários, conversas, ordens, resultados) **[A CONFIRMAR: nomes reais]** | O backend, via os perfis |
| `ia` (opcional) | Views sem dado pessoal para o agente | Ninguém (só leitura) |

Primeira linha de todo script: tirar o acesso padrão (`REVOKE ALL ... FROM PUBLIC`) e conceder só o necessário.

### 4.3 Leitura da Gold por perfil (tabela e coluna)

As telas definem o que cada perfil lê. **Quais tabelas cada tela usa ainda não está decidido: a coluna "Tabelas" abaixo é uma proposta derivada do case e precisa ser confirmada com o time de backend e front.**

| Tela | Perfis | Tabelas (proposta) **[A CONFIRMAR]** |
|---|---|---|
| Indicadores | diretoria, admin | **[A CONFIRMAR: quais indicadores a tela mostra]** |
| Receita | diretoria, admin | `agg_receita_mensal`, `agg_receita_preco_volume` |
| Visão 360 | atendimento, perdas, admin | Pelo case: cliente, consumo × ano anterior, faturas em aberto, medidor, painel solar, falta de luz, chamados → `dim_unidade_consumidora`, `fact_leituras`, `fact_faturamento`, `dim_medidor`, `dim_geracao_distribuida`, `fact_ocorrencias`, `fact_atendimentos` |
| Fila de inspeção | perdas, admin | `fila_inspecao`, `fact_inspecoes` |
| Continuidade | diretoria, operacao, admin | `agg_continuidade_alimentador`, `agg_continuidade_alimentador_anual`, `dim_alimentador` |

**Restrição por coluna (dados pessoais):**
- Perfis **sem** "ver dados pessoais" (`diretoria`, `operacao`): pela matriz de telas, eles **não usam** `dim_unidade_consumidora` nem `fila_inspecao`. Se isso se confirmar, basta **não conceder essas tabelas** (restrição por tabela).
- Se algum desses perfis precisar de uma dessas tabelas, a concessão é **por coluna**, sem as pessoais:
  `GRANT SELECT (id_uc, bairro, municipio, classe, ...) ON gold.dim_unidade_consumidora TO perfil_operacao;`

### 4.4 O agente de IA

| Regra | Como implementar |
|---|---|
| Só a Gold | `GRANT USAGE` apenas no schema `gold` (ou `ia`) |
| Nunca usuários e conversas | **Nenhum** `GRANT` no schema `app` |
| Nunca dado pessoal (opção C) | Duas formas, ver abaixo |
| Somente leitura | `ALTER ROLE agente_ia SET default_transaction_read_only = on` + nenhum `INSERT/UPDATE/DELETE` |

**Duas formas de esconder as colunas pessoais do agente:**

| Forma | Como | Prós e contras |
|---|---|---|
| **Concessão por coluna** | `GRANT SELECT (colunas sem PII) ON gold.dim_unidade_consumidora TO agente_ia` | Simples. **Mas um `SELECT *` gerado pelo LLM falha** com "permission denied", porque o `*` inclui colunas negadas |
| **Views sem as colunas** (schema `ia`) | `CREATE VIEW ia.unidades AS SELECT id_uc, bairro, ... FROM gold.dim_unidade_consumidora` | O `SELECT *` funciona, e o agente nem sabe que as colunas existem. Um pouco mais de estrutura |

Recomendação: **views** para o agente (o LLM escreve `SELECT *` com frequência). **[A CONFIRMAR com o Rafael]**

### 4.5 Escrita no schema `app` (ações)

| Ação (seção 1.4) | Permissão no banco | Perfis |
|---|---|---|
| Gerar ordem de inspeção | `INSERT` na tabela de ordens | perdas, admin |
| Registrar resultado | `INSERT` na tabela de resultados | perdas, admin |
| Cancelar ordem | `UPDATE` (do status) na tabela de ordens **[A CONFIRMAR: cancelar é UPDATE ou DELETE?]** | perdas, admin |
| Enviar planilha de campo | `INSERT` na tabela de resultados | perdas, admin |
| Criar usuários e mudar perfis | `INSERT`/`UPDATE` na tabela de usuários | admin |
| Conversar com a IA | `INSERT`/`SELECT` na tabela de conversas | todos |

Dá para restringir o `UPDATE` a colunas: `GRANT UPDATE (status, motivo_cancelamento, atualizada_em) ON app.ordens_inspecao TO perfil_perdas;` (não deixa mudar a UC ou o score de uma ordem já criada).

**Conversas sem RLS:** como o RLS ficou para depois, "cada usuário só vê as próprias conversas" fica garantido **pelo backend** (filtro pelo usuário logado em toda consulta). No banco, todos os perfis leem a tabela inteira. **[A CONFIRMAR: o time aceita isso nesta primeira versão?]**

---

## 5. Armadilhas práticas a resolver antes de implementar

| # | Armadilha | O que fazer |
|---|---|---|
| 1 | **A carga noturna apaga as permissões.** Se a sincronização recriar as tabelas da Gold (`DROP` + `CREATE`), os `GRANT`s somem junto | Carregar com `TRUNCATE` + `INSERT` dentro de uma transação (mantém a tabela, as permissões e as views), **ou** rodar o script de permissões depois de cada carga **[A CONFIRMAR: como a carga vai funcionar]** |
| 2 | **Trocar tabelas por renomeação quebra as views.** Views apontam para a tabela original; depois de um `RENAME`, continuam lendo a tabela antiga | Mesmo remédio: `TRUNCATE` + `INSERT`. *Isto corrige a sugestão de "troca em transação" do `planejamento_input_portal_e_jobs.md`, seção 8, passo 6.* |
| 3 | **`SELECT *` com concessão por coluna falha** | Views para o agente (seção 4.4) |
| 4 | **Tabelas novas nascem sem permissão** | `ALTER DEFAULT PRIVILEGES` no schema, ou rodar o script de permissões a cada mudança de estrutura |
| 5 | **O backend esquece o `SET LOCAL ROLE`** | Fazer numa única dependência de sessão do banco (todas as rotas passam por ela) + `NOINHERIT` no `portal_app` para o erro ser seguro |
| 6 | ~~**"Perdas: Visão 360 só para abrir a UC suspeita"**~~ | **Resolvido (30/10):** PERDAS abre a Visão 360 de qualquer UC pelo ID, como na matriz aprovada. Não há regra por linha nem view filtrada |

---

## 6. Onde colocar cada regra (estrutura sugerida)

> A estrutura real de pastas do repositório **[A CONFIRMAR]**. A sugestão abaixo é só um ponto de partida.

| O quê | Onde | Observação |
|---|---|---|
| Papéis, schemas e `REVOKE` iniciais | `db/permissoes/01_roles_e_schemas.sql` | Roda uma vez por ambiente |
| Concessões de leitura da Gold por perfil | `db/permissoes/02_grants_gold.sql` | Espelha a seção 4.3 |
| Concessões de escrita no `app` | `db/permissoes/03_grants_app.sql` | Espelha a seção 4.5 |
| Views do agente e o papel `agente_ia` | `db/permissoes/04_agente_ia.sql` | Seção 4.4 |
| Teste das permissões | `db/permissoes/99_testes.sql` (ou testes do backend) | Para cada perfil: `SET ROLE` e tentar o que é proibido, esperando "permission denied" |
| Mapa perfil → permissões (modelo B) | Um arquivo no backend | Já decidido pelo time |
| `SET LOCAL ROLE` por requisição | A dependência que abre a sessão do banco no backend | Um lugar só |
| Senhas dos usuários de banco | Variáveis de ambiente / `.env` | **Nunca** no repositório |

**Ordem de implementação sugerida:**
1. Responder as perguntas da seção 7.
2. Criar papéis e schemas (`01`) e conferir que um usuário sem perfil não lê nada.
3. Concessões de **um** perfil só (por exemplo, `operacao`) e testar com `SET ROLE`.
4. Repetir para os outros perfis.
5. Agente de IA (`04`) e testar um *prompt injection* contra as tabelas de conversas.
6. Escrita no `app` (`03`).
7. Ligar o `SET LOCAL ROLE` no backend.
8. Teste automatizado da matriz inteira (`99`). Também conta como "testes automatizados no backend", diferencial do case.

---

## 6.1 Atualização de 28/10: o que já está confirmado

Fontes: `telas-e-tabelas.md` e `visao-360-perdas.md` (levantamento do código na branch `dev`), mais a lista de tabelas do Postgres.

**Respondido:**
- **Banco:** Postgres, rodando localmente.
- **Tabelas Gold no Postgres:** as 15 do Databricks (as `meta_*` ainda não foram exportadas).
- **Tabelas do agente:** `tb_auditoria_agente` (guarda cada pergunta: é o equivalente às "conversas"), `tb_cache_perguntas_certificadas`, `tb_conhecimento_vetorial`, `tb_insights_tela`.
- **Modelo B já existe no código:** cada tela exige uma permissão (`ver_indicadores`, `ver_receita`, `ver_continuidade`, `ver_visao_360`, `ver_fila_inspecao`), e o mapa perfil → permissões está em `frontend/src/config/perfis.ts` e na seção 7.1 do `planejamento-backend.md`.
- **Hoje o backend conecta com um usuário só e não troca de role.** O agente já planeja `SET LOCAL ROLE` com views por perfil, e o validador de SQL dele aceita o prefixo `vw_gold_`.
- **Cancelar ordem não apaga:** o `DELETE /api/inspections/{id}` mantém o registro (é um `UPDATE` de status). Nenhum perfil precisa de `DELETE` no banco.
- **A tabela de ordens ainda não existe.**

**Matriz perfil × tabela Gold**, derivada das telas (`telas-e-tabelas.md`) e da matriz de telas (seção 1.3):

| Tabela | DIRETORIA | ATENDIMENTO | PERDAS | OPERACAO | ADMIN_TI | Usada por |
|---|:-:|:-:|:-:|:-:|:-:|---|
| `agg_receita_mensal` | ✅ | | | | ✅ | Indicadores |
| `agg_receita_preco_volume` | ✅ | | | | ✅ | Receita |
| `agg_continuidade_alimentador` | ✅ | | | ✅ | ✅ | Continuidade |
| `agg_continuidade_alimentador_anual` | ✅ | | | ✅ | ✅ | Continuidade |
| `dim_competencia` | ✅ | ✅ | ✅ | ✅ | ✅ | Indicadores, Visão 360, filtros |
| `dim_alimentador` | ✅ | | ✅ | ✅ | ✅ | Continuidade, filtros |
| `fact_ocorrencias` | ✅ | ✅ | ✅ | ✅ | ✅ | Continuidade, Visão 360, filtros (causas) |
| `dim_unidade_consumidora` | **só colunas sem PII** | ✅ todas | ✅ colunas da Visão 360 (sem CPF) | **só colunas sem PII** | ✅ | Visão 360 (tudo); Indicadores, Receita, Continuidade e filtros (só município, bairro, classe, alimentador) |
| `fact_leituras` | | ✅ | ✅ | | ✅ | Visão 360 |
| `fact_faturamento` | | ✅ | ✅ | | ✅ | Visão 360 |
| `fact_atendimentos` | | ✅ | ✅ | | ✅ | Visão 360 |
| `fila_inspecao` | | | ✅ | | ✅ | Fila |
| `dim_medidor`, `dim_geracao_distribuida`, `fact_inspecoes` | | | | | ✅ | Nenhuma tela (só o agente) |

**É aqui que a restrição por coluna é necessária:** diretoria e operacao não podem ver dado pessoal, mas os filtros e as validações das telas delas leem `dim_unidade_consumidora`. As colunas exatas que os repositories usam **[A CONFIRMAR lendo `metrics.py`, `revenue.py` e `filters.py`]**. Alternativa sem concessão por coluna: uma view `vw_gold_filtros_uc` só com município, bairro, classe e alimentador.

**OPERACAO não tem Indicadores (corrigido em 30/10).** A versão anterior desta seção concedia `agg_receita_mensal` ao `operacao` por causa de Indicadores. A matriz aprovada e o `perfis.ts` dão à OPERACAO só Continuidade, então o `operacao` não lê nenhuma das duas tabelas de receita (`02_grants_operacao.sql`).

**Correção necessária no agente:** a lista de tabelas que o agente pode consultar inclui `dim_unidade_consumidora` inteira, com nome, CPF mascarado e endereço. Isso contradiz a opção C. O agente precisa ler uma view sem essas colunas (o prefixo `vw_gold_` já é aceito pelo validador).

**Separação de papéis do agente:** quem **executa o SQL gerado pelo LLM** não pode ler nenhuma `tb_*`, principalmente a `tb_auditoria_agente` (que guarda as perguntas de todos). Quem **grava a auditoria** é o backend, com outro usuário de banco.

## 6.2 Atualização de 28/10 (parte 2): decisões do time e respostas

**Respostas do Rafael:**
- **Schema:** tudo no `public` (Gold e `tb_*`).
- **Tabela de usuários:** ainda não foi criada.
- **Perdas na Visão 360:** ~~decisão ainda pendente com o time de Perdas.~~ Decidido em 30/10: qualquer UC pelo ID (seção 6.3).

**Decisões do time (mensagem da daily):**
- 5 perfis: **Diretoria** (indicadores gerais e variação de receita), **Atendimento** (Visão 360), **Perdas** (fila, ordens e resultados de campo), **Operação** (continuidade: DEC/FEC), **Admin TI** (todas as telas e cadastro de usuários).
- Senhas com hash; JWT com expiração de 15 minutos em cookie HttpOnly.
- **Permissões centralizadas e verificadas pelo FastAPI, sem RLS no banco por enquanto.** O frontend também esconde as telas por perfil.

**Divergência resolvida (30/10):** a fonte da verdade é a matriz da seção 7.1 do `planejamento-backend.md`, espelhada em `frontend/src/config/perfis.ts`. Ela dá Continuidade à DIRETORIA (aprovado) e **não** dá Indicadores à OPERACAO. As seções 1.3 e 6.1 foram corrigidas.

**Consequência de tudo estar no schema `public`:** não dá para conceder "o schema inteiro" a ninguém. Um `GRANT SELECT ON ALL TABLES IN SCHEMA public TO agente` daria ao agente a `tb_auditoria_agente` (as perguntas de todos os usuários) e, no futuro, a tabela de usuários. **Todas as concessões precisam listar as tabelas uma a uma.** Separar em schemas (`gold`, `app`, `ia`) facilitaria, mas é uma mudança para combinar com o time.

### Como fica o banco dentro da decisão do time

A decisão "permissões verificadas pelo FastAPI, sem RLS" **não impede** permissões no banco: ela descarta o **RLS** (filtro por linha), não os `GRANT`s por tabela e coluna. O plano em fases, sem mexer no fluxo que o time decidiu:

| Fase | O que o banco passa a garantir | Mexe no backend? |
|---|---|---|
| **1. Separar os sistemas** | Usuários de banco diferentes para o portal, o agente (SQL gerado pelo LLM), a gravação da auditoria do agente e a carga da Gold. O agente só lê views Gold sem dado pessoal e nunca as `tb_*`; o portal não escreve na Gold; só a carga escreve na Gold | Só a configuração das conexões |
| **2. Perfis no agente** | O agente executa o SQL com `SET LOCAL ROLE` do perfil de quem perguntou (o que o `decisoes_acoplamento_dev_genai_dados.md` já planeja). Um atendente não consegue ler a receita pelo chat se o perfil não permitir | Só o módulo do agente |
| **3. Perfis no portal (opcional)** | O backend também faz `SET LOCAL ROLE` em toda requisição: se um endpoint esquecer a checagem do FastAPI, o banco recusa | A dependência de sessão do banco. **Precisa de acordo com o time de backend** |

**Recomendação:** fases 1 e 2 agora (é onde o risco é maior: o SQL do agente é escrito por um LLM). A fase 3 fica como reforço, se o time topar.

## 6.3 Atualização de 30/10: decisão do time e estado dos scripts

**Decisão do time (resposta ao parecer técnico sobre `SET LOCAL ROLE`):**
- **Vale hoje:** autenticação e RBAC centralizado no FastAPI, seguindo a matriz aprovada (seção 7.1 do `planejamento-backend.md`).
- **O backend mantém a conexão atual** com o banco: um usuário só, sem troca de role.
- **A fase 3 (`SET LOCAL ROLE` no portal) fica como evolução futura**, sem acoplar ao login. Retomar depois que a autenticação estiver funcionando.
- A mensagem não trata das fases 1 e 2 (usuários separados e perfis no agente) **[A CONFIRMAR]**.

**Outras decisões de 30/10:**
- **RLS descartado.** Por isso o `perfil_admin_ti` não tem mais `BYPASSRLS`.
- **PERDAS abre a Visão 360 de qualquer UC pelo ID**, sem restrição à fila. O `99_testes.sql` confere com uma UC fora da fila.
- **Nomes dos roles seguem o backend:** `perfil_admin` virou `perfil_admin_ti` (e `05_grants_admin.sql` virou `05_grants_admin_ti.sql`).

**Estado dos scripts em `backend/sql/permissoes/`.** Eles são a segunda camada; nada no backend os usa ainda.

| Script | Cobre |
|---|---|
| `01_perfis.sql` | Roles `perfil_operacao`, `perfil_perdas`, `perfil_admin_ti` |
| `02_grants_operacao.sql` | OPERACAO: Continuidade e colunas de filtro sem PII |
| `03_grants_perdas.sql` | PERDAS: Fila, Visão 360 (sem CPF) e ordens |
| `04_regras_ordens.sql` | Trigger: ordem ativa só para UC da fila |
| `05_grants_admin_ti.sql` | ADMIN_TI: leitura da Gold e ordens |
| `99_testes.sql` | Testes com `SET ROLE`; escreve dentro de `ROLLBACK`, rodar só no banco local de desenvolvimento |

**Pendências para ligar a segunda camada** (levantadas no parecer técnico; nenhuma bloqueia o MVP):
1. `perfil_diretoria` e `perfil_atendimento` e seus GRANTs: responsabilidade de outra pessoa do time.
2. Contas com login (`portal_app`, `portal_auth`) e a associação delas aos perfis. `SET ROLE` só funciona se a conta for membro do perfil com a opção `SET`.
3. GRANTs na tabela `usuarios` para login, `GET /api/auth/me`, troca da própria senha e criação de contas pelo ADMIN_TI.
4. GRANTs da `tb_auditoria_agente` (pergunta 7).
5. Uma fronteira de transação só: o `SET LOCAL ROLE` abre uma transação, e hoje o `InspectionOrdersRepository.transaction()` abre a sua com `connection.begin()`. As duas conflitariam.
6. O executor SQL da IA (`ai-agent/src/services/sql_executor.py`) abre conexões próprias em autocommit. Um `SET LOCAL ROLE` só no `core/database.py` não protege essas consultas.
7. Conferir os privilégios efetivos no banco (`PUBLIC`, outras roles, dono das tabelas), e não só os GRANTs diretos que os scripts revogam ou concedem.

---

## 7. Perguntas em aberto (não inventar: perguntar)

**Respondidas em 28/10:** banco (Postgres local) · tabelas Gold · quais tabelas cada tela lê · cancelar = `UPDATE` (seção 6.1).

**Ainda bloqueiam o início:**
1. ~~**Em que schema** estão as tabelas Gold e as `tb_*` no Postgres?~~ Respondido: tudo no `public` (seção 6.2).
2. ~~**Nome da tabela de usuários** do login e suas colunas.~~ Respondido: `usuarios` (`id`, `nome`, `email`, `senha_hash`, `role`), seção 9.1 do `planejamento-backend.md`. Ainda não foi criada.
3. ~~**O portal vai trocar de role por requisição** (`SET LOCAL ROLE`)?~~ Adiado: o portal mantém um usuário só no MVP (seção 6.3). Para o agente, ver a seção 6.3 **[A CONFIRMAR]**.
4. **Colunas de `dim_unidade_consumidora`** que os repositories de Indicadores, Receita, Continuidade e filtros realmente leem.

**Definem regras:**
5. ~~**"Perdas: Visão 360 (abrir a UC suspeita)"**: qualquer UC ou só as da fila?~~ Respondido: qualquer UC pelo ID (seção 6.3).
6. ~~Cancelar ordem é `UPDATE` ou `DELETE`?~~ Respondido: `UPDATE` de status.
7. **Conversas sem RLS** nesta primeira versão: o time aceita que o isolamento entre usuários fique só no backend? O **admin** pode ler as conversas de todos?
8. **Latitude, longitude e CEP** contam como "endereço" para a regra de dados pessoais? (Afeta o agente.)
9. **Opção C do agente:** confirmar que um atendente pode perguntar ao chat sobre **receita agregada**, mesmo sem acesso à tela de Receita (é o que a opção C implica).
10. O agente pode ler as tabelas `meta_*` (dicionário de dados)? Ajudam a IA a entender as colunas.

**Definem a operação:**
11. **Como a carga noturna da Gold** vai gravar: recria as tabelas ou faz `TRUNCATE` + `INSERT`? (Armadilhas 1 e 2.)
12. Quem roda os scripts de permissão, e em que momento (instalação, depois de cada migração)?
13. ~~**Divergência de telas** entre a mensagem da daily e a matriz.~~ Resolvida: vale a matriz aprovada (seção 6.2).
14. ~~O time topa a **fase 3** (perfis também no portal)?~~ Adiada como evolução futura, depois da autenticação (seção 6.3).

---

## 8. Tarefas para o assistente no VS Code

O Rafael vai implementar; o assistente **investiga o código e orienta**. Antes de propor qualquer SQL, levantar os fatos abaixo e mostrar ao Rafael. Se algo não for encontrado, **perguntar, não supor**.

| # | Tarefa | Onde olhar | Por quê |
|---|---|---|---|
| 8.1 | Listar **as colunas de `dim_unidade_consumidora`** que cada query lê | `backend/app/repositories/metrics.py`, `revenue.py`, `filters.py` e, quando existir, o de continuidade | Define a concessão por coluna da Diretoria e da Operação (seção 6.1) |
| 8.2 | Conferir **o mapa perfil → permissões** e os **nomes exatos** dos perfis e permissões | `frontend/src/config/perfis.ts`; `planejamento-backend.md`, seção 7.1 | Resolver a divergência da seção 6.2; os nomes dos roles do banco devem seguir os do código |
| 8.3 | Mostrar **como o backend abre a conexão e a sessão do banco** (string de conexão, usuário, pool, dependência `get_db` ou equivalente) | Backend (configuração e dependências do FastAPI) | É onde entram os usuários separados (fase 1) e, se aprovado, o `SET LOCAL ROLE` (fase 3) |
| 8.4 | Mostrar **como o agente conecta e executa o SQL gerado**, e onde grava a auditoria | `ai-agent/src/` (serviços, `stub_validador_sql.py`) | Separar o usuário que executa o SQL do LLM do usuário que grava `tb_auditoria_agente` |
| 8.5 | Listar **as tabelas que o validador do agente permite** e conferir se inclui `dim_unidade_consumidora` inteira | `ai-agent/src/interfaces/stub_validador_sql.py` e a configuração do agente | Hoje a lista inclui a tabela com nome e endereço, o que contradiz a opção C (seção 6.1) |
| 8.6 | Ler os itens de perfis e o item 11 do documento de acoplamento | `ai-agent/arquitetura_e_integracao/decisoes_acoplamento_dev_genai_dados.md` | Ver o que já foi decidido sobre views por perfil e `SET LOCAL ROLE` no agente |
| 8.7 | Verificar **como as tabelas Gold são carregadas** no Postgres (script, `DROP`/`CREATE`, `TRUNCATE`, `COPY`, `to_sql`…) | Scripts de carga do repositório | Armadilhas 1 e 2 da seção 5: uma carga que recria as tabelas apaga os `GRANT`s |
| 8.8 | Verificar se existe alguma ferramenta de **migração** (Alembic ou similar) | Backend | Decide onde os scripts de permissão entram (seção 6) |
