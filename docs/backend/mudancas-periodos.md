# Períodos escolhíveis: o que mudou no backend

Branch `feature/periodos-indicadores-receita`. Indicadores, Receita e Continuidade agora comparam dois períodos escolhidos na tela: **Período base** × **Comparado com**. Os KPIs mostram sempre o **comparado**; o base é a referência da variação.

Regra comum às duas rotas: os dois períodos têm **o mesmo tamanho (1 a 24 meses)**, ficam **dentro da base** e o comparado **começa depois do fim do base**.

## `GET /api/metrics/general`

| | Antes | Agora |
|---|---|---|
| `inicio`, `fim` | 3, 6 ou 12 meses, terminando no último mês da base | De 1 a 24 meses, terminando em qualquer mês da base (`fim` depois do último mês → 422) |
| Período anterior | Sempre o imediatamente anterior | **Novos** `inicio_anterior` e `fim_anterior` (opcionais). Sem eles, continua o imediatamente anterior |

Regras dos novos parâmetros (violou → **422** `"Período inválido"`):
- vêm juntos (só um deles → 422);
- exigem `inicio` e `fim`;
- mesmo tamanho do período atual;
- `fim_anterior` antes de `inicio`.

Mantido do seu código: anterior fora do calendário → **503**; parâmetro desconhecido ou repetido → 422. A validação roda antes de abrir a conexão.

Exemplo (Recife, 2024 comparado com 2023):
```
/api/metrics/general?inicio=2024-01&fim=2024-12&inicio_anterior=2023-01&fim_anterior=2023-12&municipio=Recife
```

Arquivos: `backend/app/controllers/metrics.py`, `backend/app/services/metrics.py` (`validate_metrics_period` aceita 1–24; nova `validate_previous_period`; `get_general_metrics` recebe `inicio_anterior`/`fim_anterior` e busca só os meses das duas janelas).

## `GET /api/metrics/revenue-variance`

| | Antes | Agora |
|---|---|---|
| Períodos | Fixos: P0 = 2022-07 a 2023-06, P1 = 2025-07 a 2026-06 | **Novos** `inicio_p0`, `fim_p0`, `inicio_p1`, `fim_p1`: os quatro ou nenhum |
| Sem parâmetros | P0 × P1 fixos | Primeiros 12 meses × últimos 12 meses da base (dá o mesmo P0 × P1 de antes) |
| Fonte | `agg_receita_preco_volume` | `agg_receita_mensal`, com a mesma conta da Gold |

Regras (violou → **422** `"Período inválido"`; só parte dos quatro → 422 pedindo os quatro juntos): formato `yyyy-MM`, mesmo tamanho dos dois lados, de 1 a 24 meses, P0 começa na base, P1 começa depois do fim de P0 e termina até o último mês. Calendário ausente ou com menos de 24 meses → **503**.

O contrato da resposta **não mudou**; `periodo_p0` e `periodo_p1` passam a trazer os períodos usados.

**Como calcula:** CTE por célula município × bairro × classe × `possui_gd` sobre `agg_receita_mensal` (`_CELLS` em `backend/app/repositories/revenue.py`), com a fórmula do `05_gold_receita.py`:
- `efeito_volume = (kwh_p1 − kwh_p0) × receita_p0 / kwh_p0`, ou `receita_p1 − receita_p0` quando `kwh_p0 = 0`;
- `efeito_preco` = o resto da variação;
- UCs = `ucs_faturadas` do **último mês** de cada período (na base, toda UC ativa é faturada todo mês, então é igual às UCs distintas do período).

**Conferido no banco real:** com os períodos padrão, o resultado é idêntico ao de `agg_receita_preco_volume` nas **1.525 células**.

Mudanças internas:
- `RevenueRepository.get_periods()` saiu; entrou `get_calendar()`, que devolve o primeiro e o último `mes_referencia`;
- `get_total`, `get_by_gd`, `get_by_municipio` e `get_detail` recebem `RevenuePeriods`;
- `_periods()` em `backend/app/services/revenue.py` valida e monta os períodos.

## Testes

- `backend/tests/test_metrics_http.py`: casos novos para `inicio_anterior`/`fim_anterior` e tamanhos de 1 a 24.
  - O teste do OpenAPI passou a listar os parâmetros novos.
  - Três testes usavam janelas de 2 meses como inválidas, mas 2 meses agora vale; passaram a usar 25 meses.
- `backend/tests/test_revenue_http.py`: os quatro parâmetros, combinações inválidas e o padrão sem parâmetros.
- `backend/tests/test_revenue_integration.py`: dois testes novos no banco real, pulados sem banco:
  - outros períodos batem com a série mensal;
  - trimestres de anos diferentes fecham `efeito_volume + efeito_preco = variação`.
- Suíte de metrics + revenue: 154 testes passando. A única falha da suíte, `test_uc.py::test_consumo_imputado_real_preserva_valor_gold_e_sinalizador`, **já falhava no `dev`** antes desta branch.

## O que fica com você, Pedro

1. **`GET /api/network/continuity`** (ainda no MSW). O front já manda `inicio`, `fim`, `inicio_anterior`, `fim_anterior`, `municipio`, `alimentador` e `causa`, com as mesmas regras do `/metrics/general`. O contrato proposto está em `frontend/src/hooks/use-continuidade.ts`.
2. **`docs/backend/impl_filtros.md`** ainda fala em "últimos 3/6/12 meses" e em períodos fixos na Receita. Vale atualizar com as regras acima.
3. A rota da Receita não lê mais `agg_receita_preco_volume`, mas a tabela continua sendo usada pelo agente de IA, então ela fica.
