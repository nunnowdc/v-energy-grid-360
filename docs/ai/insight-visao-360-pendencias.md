# Insight da IA na Visão 360: o que falta no ai-agent e no backend

O insight de IA fica **só na Visão 360**: o case pede insights em pelo menos uma tela, e na Receita o bloco "Com e sem geração própria" já explica a variação com números calculados direto da Gold. O front está pronto na branch `feature/insights-ia`: a caixa "Insight da IA" fica abaixo do resumo da UC e chama `GET /api/ai/insights/visao_360_uc/{id_uc}`.

Este documento lista o que falta do lado do ai-agent e do backend para o insight ficar confiável e útil. Tudo foi conferido na `dev` (`fff1ae6`) em 01/11/2026.

## O que o front usa da resposta

| Campo | Uso |
|---|---|
| `insight_texto` | O texto da caixa |
| `selo` | `auditado_llm` mostra "Números conferidos"; `template_fallback` mostra "Sem conferência". Outro valor fica sem selo |
| `fontes` (novo, opcional) | Lista de tabelas. Quando vem, a caixa mostra "Fonte: fact_leituras, fact_faturamento" |

- **403:** a caixa some e o resto da tela continua.
- **Outros erros:** a caixa mostra o erro com "Tentar de novo". O front não tenta sozinho, porque cada tentativa pode chamar o modelo.
- **Tempo limite:** 60 s, para a primeira vez de cada UC, quando a IA escreve o texto na hora.

Mudanças nesses campos precisam de aviso para o front. Os demais campos (`metricas_destaque`, `tempo_ms`) não aparecem na tela.

## Como está hoje

`InsightsService.obter` (`ai-agent/src/insights/service.py`):

1. Procura o texto na `tb_insights_tela`.
2. Se não achar, pega as 2 últimas faturas da UC em `fact_faturamento`.
3. A IA narra essas faturas.
4. O conferente numérico confere o texto.
5. O resultado é gravado na `tb_insights_tela`, **mesmo quando a conferência falha**.

**Teste:** 9 textos gerados para a UC140669, sem passar pelo cache, todos pelo combo `venergy` do 9router.
- 7 passaram na conferência.
- 2 falharam porque a IA inventou uma data:

> "…enquanto na competência de **2025-05-01 (ou 2026-05-01)**, o consumo registrado foi de 664.0 kWh…"

O conferente fez o papel dele: o dado real é 2026-05-01. O problema é o que vem depois:
- O texto vira o aviso fixo "Não foi possível validar numericamente o texto gerado; consulte os dados exibidos." e esse aviso fica guardado para sempre. Aquela UC passa a mostrar "Sem conferência" toda vez.
- Os textos que passam saem com números crus: "competência de 2026-06-01", "receita faturada de 163.95".
- O conteúdo só repete as 2 últimas faturas, que já aparecem na tela.

## ai-agent

### 1. Não guardar a falha, tentar de novo e ter um texto-modelo (essencial)

Em `InsightsService.obter`:

- **Tentar até 3 vezes** quando a conferência reprovar. Com ~2 falhas em 9, três tentativas deixam a falha perto de 1%.
- **Se as 3 falharem:**
  - montar um **texto-modelo com os próprios fatos**, sem IA, em português e com os números no formato brasileiro (exemplo no item 3);
  - devolver com `selo: "template_fallback"`;
  - **não gravar** na `tb_insights_tela`, para a próxima abertura da UC tentar de novo.
- **Registrar no log** o texto reprovado e o número recusado (`logger.warning`). Hoje o texto reprovado se perde, e não dá para saber o que a IA errou.

### 2. Datas como texto e números no formato brasileiro (essencial)

O erro do teste foi a IA se confundir com a data em ISO. Nos fatos que vão para a IA:

- **Datas como texto curto:** `"mes_referencia": "jun/2026"` em vez de `date(2026, 6, 1)`.
- **Valores continuam numéricos:** `563.39`, nunca `"R$ 563,39"`. O conferente lê os dígitos de um campo de texto com ponto decimal, então `"R$ 563,39"` vira `563` e `39` e o texto certo é reprovado. Conferido no conferente atual.
- **No prompt (`narrador_insights.py`), pedir:**
  - números no formato brasileiro: "R$ 563,39", "618 kWh", "1,6%". O conferente já aceita esse formato;
  - não abreviar com "mil" nem "milhões": `_ESCALAS` está vazio no `conferente_numerico.py`, e "R$ 5,7 mil" é reprovado;
  - não calcular nada: "10 kWh a menos" é reprovado, porque 10 não está nos fatos. Toda diferença ou percentual que o texto deva citar precisa vir pronta nos fatos;
  - escrever para o atendente, que está com o cliente na linha: "valor da conta" em vez de "receita faturada".

### 3. Um conteúdo que responda ao atendente (se der tempo)

O pedido do case é: "quando alguém diz que a conta veio alta, o atendente precisa conseguir responder na hora se o consumo realmente subiu". Uma consulta que serve a isso, com as mesmas regras da tela:

| Fato | De onde vem |
|---|---|
| `mes_referencia`, `consumo_kwh` | `fact_leituras`, último mês da UC (a mesma fonte do gráfico "Consumo dos últimos 12 meses") |
| `mes_ano_anterior`, `consumo_ano_anterior_kwh`, `variacao_ano_anterior_pct` | `fact_leituras`, já calculados na Gold |
| `valor_conta` | `fact_faturamento.receita_faturada` do mesmo mês |
| `faturas_em_aberto`, `total_em_aberto` | `fact_faturamento` com `status_pagamento IN ('PENDENTE', 'ATRASADA')`, a mesma regra de `get_faturas_em_aberto` em `backend/app/repositories/uc.py` |

Exemplo com a UC140669 (dados reais da Gold local):

```json
{
  "mes_referencia": "jun/2026", "consumo_kwh": 618, "valor_conta": 563.39,
  "mes_ano_anterior": "jun/2025", "consumo_ano_anterior_kwh": 628, "variacao_ano_anterior_pct": -1.6,
  "faturas_em_aberto": 4, "total_em_aberto": 5714.34
}
```

Texto esperado, que também serve de texto-modelo do item 1:

> Em jun/2026 a UC consumiu 618 kWh, 1,6% abaixo do mesmo mês de 2025 (628 kWh). Há 4 faturas em aberto, somando R$ 5.714,34.

Esse texto passa no conferente atual. `mes_ano_anterior` precisa estar nos fatos para o "2025" ser aceito.

**Decisão de produto pendente:** a `fila_inspecao` tem a prioridade e o motivo da suspeita (a UC140669 é a 3ª da fila). Isso ajuda o perfil Perdas, mas o Atendimento também vê a Visão 360. Mostrar "suspeita de fraude" para quem está falando com o cliente precisa de decisão do time antes de entrar.

### 4. Devolver `fontes`

Exemplo: `"fontes": ["fact_leituras", "fact_faturamento"]`, com as tabelas que a consulta usou. O case pede que o insight cite o valor e a tabela de origem (`docs/context/05-inteligencia-artificial.md`, seção 3.2), e o front já mostra o campo quando ele vem.

### 5. UC sem dados: 404, sem chamar a IA nem gravar

Hoje qualquer id que passe na regex gera um texto e grava no cache: há uma linha com `entidade_id = '1'` e fatos vazios. Com fatos vazios, o certo é responder 404 sem chamar o modelo e sem gravar. Isso também evita que alguém encha a tabela chamando ids inventados.

### 6. Tirar o `diagnostico_receita`

Nenhuma tela usa mais essa consulta, e ela compara anos-calendário: 2026 tem 6 meses (R$ 87,9 mi) e 2025 tem 12 (R$ 172,0 mi). Basta tirar a chave de `QUERIES` em `extrator_metricas_fixas.py`, com `adicionar_variacao_percentual_diagnostico_receita` e `tests/test_variacao_percentual_diagnostico_receita.py`. Uma tela que não está em `QUERIES` já responde 400 na geração. Mas o `obter` lê o cache **antes** de checar a tela, e o texto errado de `diagnostico_receita/global` está guardado. Por isso, a tela também precisa ser validada antes da leitura do cache, ou as linhas `WHERE tela = 'diagnostico_receita'` precisam ser apagadas.

### 7. Limpar os textos guardados quando a Gold muda

A `scripts/carga_banco_local.py` recria as tabelas da Gold, mas não mexe na `tb_insights_tela`. Depois de uma carga, os textos antigos continuam aparecendo. A carga no PostgreSQL deveria terminar com `TRUNCATE tb_insights_tela`, se a tabela existir.

Depois que os itens 1 a 3 entrarem, cada máquina precisa limpar os textos já guardados:

```powershell
docker exec postgres-venergy psql -U postgres -d v_energy -c "DELETE FROM tb_insights_tela WHERE tela = 'visao_360_uc';"
```

### Testes

- **Item 1:**
  - conferência reprovando 1 vez e depois passando: grava e devolve `auditado_llm`;
  - reprovando 3 vezes: devolve o texto-modelo com `template_fallback` e não grava.
- **Item 2:** os fatos levam datas como `"jun/2026"` e números como números.
- **Item 5:** fatos vazios respondem 404, sem chamar o LLM e sem gravar.
- **Conferente:** casos com os textos deste documento:

| Texto | Conferência |
|---|---|
| O texto esperado do item 3 | passa |
| "10 kWh a menos" | reprova |
| "R$ 5,7 mil" | reprova |
| "2025-05-01 (ou 2026-05-01)" | reprova |

## Backend

### Permissão da rota de insights (essencial)

Em `backend/app/security/permissions.py:36`, a rota está liberada para todos:

```python
("GET", "/api/ai/insights/{tela}/{entidade_id}"): ALL_PROFILES,
```

Com isso, a Diretoria e a Operação conseguem ler dados de uma UC por essa rota, mesmo sem acesso à Visão 360 (LGPD e menor privilégio, como está no README). Como a Visão 360 é a única tela com insight, a rota deve ter a mesma permissão de `/api/uc/{uc_id}/360`:

```python
("GET", "/api/ai/insights/{tela}/{entidade_id}"): CUSTOMER_SERVICE,
```

A matriz é por padrão de rota, então não distingue telas. Se algum dia outra tela voltar a ter insight, para outros perfis, a rota precisa ser separada por tela ou checada dentro do handler.

**Teste** (`backend/tests/test_rbac_http.py`, hoje com `("GET", "/api/ai/insights/teste/entidade", ALL)`):
- `DIRETORIA` e `OPERACAO` recebem 403;
- `ATENDIMENTO`, `PERDAS` e `ADMIN_TI` passam.

O front já esconde a caixa quando recebe 403.

## Ordem até a entrega (04/11)

| Prioridade | Itens |
|---|---|
| Essencial | Backend: permissão. ai-agent: 1, 2 e 7 |
| Se der tempo | ai-agent: 3 e 4 |
| Pequenos | ai-agent: 5 e 6 |

O front não muda com nenhum desses itens: o texto, o selo e as fontes já são mostrados como vierem.

## Como conferir no portal

1. Limpe os textos guardados (comando do item 7).
2. Entre como `atendimento@example.test`.
3. Abra a Visão 360 da UC100000, da UC132549 e da UC140669. Cada uma deve mostrar:
   - "Números conferidos";
   - os números no formato brasileiro;
   - a linha "Fonte: …".
4. Repita o passo 1 e abra a UC140669 umas 5 vezes. Nenhuma vez deve aparecer o aviso "Não foi possível validar…".
5. Entre como `diretoria@example.test` e abra `http://localhost:5173/api/ai/insights/visao_360_uc/UC100000` na barra de endereço do navegador, que usa o mesmo login. Deve dar 403.
