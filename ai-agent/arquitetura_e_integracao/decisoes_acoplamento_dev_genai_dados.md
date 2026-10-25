# Ordem de prioridade: ajustes finais do agente (V-Energy Grid 360)

**Critério da ordem**
1. Primeiro o que destrava os outros itens.
2. Depois o que o case cobra como obrigatório (histórias 1 a 6 de GenAI, insights em pelo menos uma tela e o README).
3. Diferenciais por último (histórias 7 e 8).
4. Básico bem feito antes de perfeito.

---

## Visão geral

| #   | Item                                                                        | Responsável | Depende de |
| --- | --------------------------------------------------------------------------- | ----------- | ---------- |
| 1   | Configuração e ambiente                                                     | Eu          | nada       |
| 2   | Propagar `user_id`, contexto da tela e perfil                               | Eu          | nada       |
| 3   | Alinhamento rápido com Segurança (contrato, política, whitelist, retry)     | Eu + Seg    | nada       |
| 4   | Decisões de perfis com a equipe                                             | Todos       | nada       |
| 5   | Confirmar o schema Gold                                                     | Banco → Eu  | Banco      |
| 6   | Atualizar a whitelist de tabelas nos 4 lugares                              | Eu          | 3 e 5      |
| 7   | Ajustar o executor PostgreSQL                                               | Eu          | 5          |
| 8   | Permissões do usuário do agente                                             | Banco       | 4          |
| 9   | Tabelas de controle (JSONB, pgvector, índices)                              | Banco + Eu  | 5          |
| 10  | Confirmar o modelo de embeddings                                            | Banco + Eu  | 9          |
| 11  | Contexto de schema por perfil e views para dados restritos                  | Eu + Banco  | 4, 5 e 8   |
| 12  | Trocar o stub pelo validador oficial                                        | Eu          | Seg        |
| 13  | Indexar o conhecimento real                                                 | Eu          | 5, 6 e 10  |
| 14  | Completar o cache parametrizado                                             | Eu          | 5 e 6      |
| 15  | Validar a auditoria no banco real                                           | Eu + Banco  | 9          |
| 16  | Completar os insights (pelo menos 1 tela)                                   | Eu          | 5          |
| 17  | Executar o Golden Set e os testes por nó                                    | Test + Eu   | 12         |
| 18  | Corrigir problemas dos testes e ajustar retries, selos, auditoria e limites | Eu          | 17         |
| 19  | Documentação e README                                                       | Eu          | todos      |
| 20  | Memória persistente (PostgresSaver), diferencial                            | Eu          | 9          |
| 21  | Extras de perfis, só se sobrar tempo                                        | Eu + Banco  | 11         |

---

## Prioridade 1: destrava tudo (fazer primeiro)

Não dependem de ninguém, ou são só conversa.

### 1. Configuração e ambiente
- [ ] `DATABASE_URL`, `SQLITE_PATH`
- [ ] Chaves dos provedores LLM
- [ ] Modelo primário e fallback
- [ ] Modo mock
- [ ] Timeout, limites de concorrência, configuração de logs, pool de conexões

**Pronto quando:** o agente sobe em modo mock e em modo real só trocando variáveis de ambiente.

### 2. Propagar `user_id`, contexto da tela e perfil
Hoje o request em `ai_router.py` recebe `user_id` e `context`, mas não encaminha para `executar_agente`.
- [ ] Adicionar `contexto_tela` e `user_id` ao estado inicial
- [ ] Usar o contexto no follow-up, no roteamento, no SQL e nos insights
- [ ] Registrar esses dados de forma compatível com LGPD
- [ ] **[perfis]** Adicionar o **perfil** (`role`) ao estado. Ele vem do login (token validado pelo backend), nunca do texto da pergunta.

**Pronto quando:** `user_id`, contexto e perfil aparecem no estado do grafo e no registro de auditoria.

### 3. Alinhamento rápido com Segurança
Uma conversa curta. Levar estas perguntas:
- [ ] `ResultadoValidacaoSQL` terá os campos `aprovado`, `motivo_rejeicao`, `malicioso`, `tabelas_detectadas`? Serão necessários campos  s (colunas detectadas, comandos encontrados, motivo técnico, classificação de risco)?
- [ ] Retry: quantas tentativas, o que é erro corrigível, quando é malicioso, se ataque gera `recusa_honesta` imediata, se erro de sintaxe volta ao `no_escreve_sql`
- [ ] Política de execução: CTEs, `WITH`, subqueries, `EXTRACT`, funções específicas do PostgreSQL, comentários SQL, múltiplas instruções com `;` no final
- [ ] Whitelist final: `agg_continuidade_alimentador`, `agg_continuidade_alimentador_anual`, `agg_receita_mensal`, `agg_receita_preco_volume`, dimensões e fatos Gold, `fila_inspecao` e tabelas de controle (auditoria, cache, insights)
- [ ] **[perfis]** O validador deve bloquear `SET` e `RESET` dentro do SQL gerado pelo LLM (para ninguém trocar de perfil no meio da consulta)

**Pronto quando:** o contrato e a política estão escritos e os dois lados concordam.

### 4. Decisões de perfis com a equipe
- [ ] Quais perfis existem e quantos (diretor, atendente, perdas, operação, comum)
- [ ] Quais dados são restritos a qual perfil
- [ ] Nível de redução que cada perfil recebe de um dado restrito: flag (sim/não), faixa, agregado, mascarado ou nada (recusa)
- [ ] Views separadas por perfil, ou uma view única com colunas mascaradas

**Pronto quando:** existe uma tabelinha "dado restrito → perfil → nível de redução" aprovada pelo time.

---

## Prioridade 2: assim que o Banco entregar o schema Gold

### 5. Confirmar o schema Gold
Comparar o schema real com o `guia_banco_e_portal.md`:
- [ ] Nomes de tabelas e colunas, tipos, chaves estrangeiras
- [ ] Granularidade e valores possíveis de status
- [ ] Municípios válidos, classes tarifárias, períodos disponíveis

Isso impacta `no_escreve_sql.py`, `indexador_conhecimento.py`, os templates de cache, as consultas de insights e a documentação.

### 6. Atualizar a whitelist de tabelas nos 4 lugares
- [ ] Prompt de Text-to-SQL em `no_escreve_sql.py`
- [ ] Stub, caso ainda seja usado localmente
- [ ] Templates do cache em `no_cache_parametrizado.py`
- [ ] Templates indexados em `indexador_conhecimento.py`

### 7. Ajustar o executor PostgreSQL
- [ ] Driver (`psycopg2` ou `psycopg`)
- [ ] `statement_timeout` efetivo, modo `READ ONLY`, limite de linhas
- [ ] Tipos PostgreSQL (`Decimal`, datas, UUID)
- [ ] Conexão e pool, para não abrir uma conexão nova a cada consulta
- [ ] **[perfis]** Executar cada consulta numa transação `READ ONLY` com `SET LOCAL ROLE <perfil do usuário>` antes do SQL. O `SET LOCAL` vale só dentro da transação, então é seguro com pool.

Arquivos: `sql_executor.py`, `no_executa_sql.py`.

### 8. Permissões do usuário do agente
Feito pelo Banco, fora do código do agente. Eu só testo o agente com esse usuário restrito.
- [ ] `CONNECT` no banco, `USAGE` no schema, `SELECT` só nas tabelas e views permitidas
- [ ] Nenhuma permissão de criação, alteração, exclusão ou administrativa
- [ ] **[perfis]** Perfis nativos (`perfil_diretor`, `perfil_atendente` etc.) com `GRANT` só nas views de cada perfil, e o usuário do agente autorizado a assumir esses perfis

**Pronto quando:** um `INSERT` ou `DELETE` pelo usuário do agente retorna `permission denied`, e o atendente não consegue ler a view do diretor.

### 9. Tabelas de controle
Revisar `criar_tabelas_ia.py` contra o schema aprovado:
- [ ] `amostra_resultado_json` e `passos_execucao` como **JSONB** (hoje estão como TEXT)
- [ ] Extensão `pgvector` instalada e `gen_random_uuid()` disponível
- [ ] Índices, constraints e índices únicos
- [ ] Tipos dos campos de auditoria

### 10. Confirmar o modelo de embeddings
Hoje: `paraphrase-multilingual-MiniLM-L12-v2` e `vector(384)`.
- [ ] Confirmar que a dimensão real é 384 e que o modelo estará disponível no ambiente
- [ ] Criar o índice IVFFlat só depois de ter carga suficiente
- [ ] Se o modelo mudar, atualizar `indexador_conhecimento.py`, `buscador_vetorial.py` e `criar_tabelas_ia.py`

### 11. Contexto de schema por perfil e views para dados restritos
- [ ] O `no_escreve_sql.py` passa ao gerador só as tabelas e colunas do perfil do usuário. Se o gerador não sabe que a coluna existe, ele não tenta usá-la.
- [ ] Para um dado restrito de que o perfil precisa só do efeito (ex.: "pode parcelar?"), uma view derivada calcula o resultado reduzido dentro do banco. O dado restrito nunca chega ao LLM.
- [ ] Se a pergunta exige dado fora do perfil, o agente responde "não tenho permissão para essa informação" pela `recusa_honesta`.
- [ ] O sintetizador recebe só o campo reduzido e não explica o motivo quando o motivo é restrito.

**Pronto quando:** diretor e atendente fazem a mesma pergunta e o atendente recebe a versão reduzida ou a recusa, sem o dado restrito no resultado.

---

## Prioridade 3: integrar, testar e fechar

### 12. Trocar o stub pelo validador oficial
- [ ] Em `construtor_grafo.py`, trocar `_validador = validador or StubValidadorSQL()` pela implementação oficial
- [ ] Manter `ValidadorSQLInterface` como contrato entre as duas frentes
- [ ] Se o contrato mudar, atualizar `no_valida_sql.py`

### 13. Indexar o conhecimento real
- [ ] Glossário oficial, dicionário real da camada Gold, regras regulatórias aprovadas
- [ ] Templates SQL homologados e nomes reais de views e tabelas
- [ ] Fontes oficiais e versões dos documentos
- [ ] **[ perfis]** Cada trecho indexado guarda os perfis que podem vê-lo, e a busca filtra por esse metadado

### 14. Completar o cache parametrizado
- [ ] Revisar os templates contra o schema real e a whitelist final (`no_cache_parametrizado.py`)
- [ ] Cache hit sem chamada desnecessária ao LLM
- [ ] **[ perfis]** A chave do cache inclui o perfil, para um perfil não receber o SQL aprovado de outro

### 15. Validar a auditoria no banco real
- [ ] Grava todos os campos esperados, com os tipos corretos
- [ ] Mascara dados pessoais adequadamente
- [ ] Registra falhas de segurança, retries, erro de validação e feedback
- [ ] Não bloqueia a resposta quando a auditoria está indisponível
- [ ] Política de retenção e acesso
- [ ] **[perfis]** Registra `user_id` e perfil em cada execução

### 16. Completar os insights
O case exige insights de IA em **pelo menos uma tela**. Fazer essa(s) tela(s) bem feita(s) antes de ampliar.
- [ ] Revisar as consultas em `extrator_metricas_fixas.py`: métricas oficiais, campos corretos, variação mensal, ausência de mês anterior, status de faturas, filtro por UC
- [ ] Atualização periódica e expiração dos registros em `tb_insights_tela`
- [ ] **[ perfis]** O cache de insights por tela considera o perfil

### 17. Executar o Golden Set e os testes por nó
Feito principalmente pela frente de Testes. Eu garanto que o agente é testável.
- [ ] Testes de cada nó (`no_filtro_seguranca`, `no_completa_followup`, `no_checa_escopo`, `no_roteador_consulta`, `no_recupera_contexto`, `no_cache_parametrizado`, `no_escreve_sql`, `no_valida_sql`, `no_executa_sql`, `no_sintetiza_resposta`, `no_recusa_honesta`, `no_finaliza_auditoria`)
- [ ] Golden Set: rota esperada (sql, rag, ambos ou recusa), correspondência do SQL, tabelas e colunas usadas, recusa correta, resposta no formato `RespostaAgente`
- [ ] Mocks e respostas determinísticas (`FakeLLM`, fixtures, parametrização por cenário)
- [ ] Metas: limite de chamadas LLM, máximo de retries, timeout de SQL, limite de linhas, latência de insights, média de tokens
- [ ] **[ perfis]** Casos com a mesma pergunta em perfis diferentes: o diretor recebe a resposta e o atendente recebe a versão reduzida ou a recusa. Incluir a pergunta direta pelo dado restrito, cujo esperado é a recusa.

### 18. Corrigir o que os testes apontarem e ajustar parâmetros
- [ ] Propagação de `user_id` e do contexto da tela, cálculo do tempo de execução, formato dos passos de auditoria
- [ ] Selo de confiança em respostas RAG sem dados SQL
- [ ] Resposta vazia do LLM e PostgreSQL indisponível
- [ ] Revisar o fluxo de retry (hoje distribuído entre `no_valida_sql.py`, `no_escreve_sql.py`, `no_executa_sql.py` e `construtor_grafo.py`)
- [ ] Ajustar retries, selos, auditoria e limites conforme os resultados

### 19. Documentação e README
Começar cedo, fechar por último. O case exige o README.
- [ ] `README.md`, `guia_banco_e_portal.md`, `decisoes_arquitetura_agente.md`
- [ ] Qual validador está ativo, como configurar o banco, como executar o indexador, como configurar a memória, como rodar o Golden Set
- [ ] Quais telas têm insights e quais tabelas são efetivamente permitidas
- [ ] **[ perfis]** Perfis, o que cada um enxerga e as suposições feitas

---

## Prioridade 4: só se sobrar tempo

### 20. Memória persistente (`PostgresSaver`)
É a história 7 (follow-up), marcada como diferencial no case. Só vale priorizar se o follow-up atual não funcionar.
- [ ] Configurar o checkpointer do LangGraph e o gerenciador de memória (`memoria/gerenciador_memoria.py`)
- [ ] Associar ao `sessao_id` e limitar a janela aos últimos três turnos
- [ ] Persistir e recuperar o histórico, com isolamento entre sessões
- [ ] Não gravar conversas no índice vetorial global
- [ ] **[perfis]** O histórico guarda `user_id` e perfil, e não aparece para outro usuário

### 21. Extras de perfis
Não são necessários para o básico.
- [ ] Tabela `catalogo_acesso` (tabela, coluna, perfis permitidos), como documentação e fonte para filtrar schema, RAG e cache
- [ ] Tamanho mínimo de grupo nos agregados, para evitar descobrir um dado individual por perguntas muito específicas
- [ ] Row-Level Security, só se o case exigir restrição por município
- [ ] Função `SECURITY DEFINER`, só se uma view não resolver o caso

---

## Resumo em uma linha por bloco

1. **Prioridade 1 (itens 1 a 4):** configurar o ambiente, propagar usuário e perfil, alinhar contratos com Segurança e decidir os perfis.
2. **Prioridade 2 (itens 5 a 11):** encaixar no schema real do Banco, no executor e nas permissões.
3. **Prioridade 3 (itens 12 a 19):** trocar o validador, indexar, cache, auditoria, insights, testes e documentação.
4. **Prioridade 4 (itens 20 e 21):** memória persistente e extras de perfis.
