# Período da consulta no dashboard: o que mudou no agente

Branch `feature/periodos-indicadores-receita`. O `/api/ai/ask` já devolvia `dashboard {tela, filtros}`, deduzido do SQL executado (`ai-agent/src/services/tela_dashboard.py`). Agora ele também devolve **o período consultado**, para o portal abrir a tela com os KPIs batendo com a resposta.

**Problema que resolve:** em "Qual o faturamento em Recife no ano de 2024?", a resposta era R$ 68.560.067,39, mas o dashboard abria no período padrão (jul/2025–jun/2026) e mostrava outro número.

## Contrato (`ai-agent/src/contratos/resposta_agente.py`)

Dois campos novos e opcionais em `FiltrosDashboard`, com o novo modelo `PeriodoDashboard {de, ate}` (`yyyy-MM`):

| Campo | Quando vem |
|---|---|
| `periodo` | Meses consultados. O portal põe esse período no **"Comparado com"**, que é o que os KPIs mostram |
| `periodo_base` | Só quando a consulta compara dois períodos (ex.: 2023 e 2024): o mais antigo |

```json
"dashboard": {
  "tela": "indicadores",
  "filtros": { "municipio": "recife", "periodo": { "de": "2024-01", "ate": "2024-12" }, "periodo_base": null }
}
```

Os campos antigos não mudaram. Na `visao_360` não vem período.

## Como o período é lido do SQL

Colunas de tempo: `ano`, `mes`, `competencia` e `mes_referencia`, também dentro de `EXTRACT(YEAR|MONTH FROM …)`/`date_part` e com cast (`r.ano::int`).

| No WHERE | Período |
|---|---|
| `ano = 2024`, `EXTRACT(YEAR FROM competencia) = 2024`, `mes_referencia LIKE '2024-%'` | jan–dez/2024 |
| `ano = 2025 AND mes BETWEEN 1 AND 3` | jan–mar/2025 |
| `competencia >= '2024-01-01' AND competencia < '2025-01-01'` | jan–dez/2024 |
| `ano IN (2023, 2024)`, `ano = 2023 OR ano = 2024`, um `FILTER (WHERE ano = …)` ou uma CTE para cada ano | base 2023, comparado 2024 |
| `mes_referencia = '2025-03'` | mar/2025 |

Como funciona por dentro:
- **Partes.** Cada valor de um `IN`, cada lado de um `OR` e cada `WHERE` (incluindo `FILTER` e subconsultas) é uma parte. Assim, `ano IN (2023, 2024)` vira uma comparação e não um bloco de 24 meses. Condições com `AND` são interseção.
- **Período.** Uma parte de meses seguidos vira `periodo`. Duas partes do mesmo tamanho, sem meses em comum, viram `periodo_base` + `periodo`. Uma parte que contém outra sai (por exemplo, `WHERE ano BETWEEN 2023 AND 2024` com um `FILTER` por ano).
- **Sem período.** Fica sem período quando:
  - o filtro não tem fim (`ano >= 2024`);
  - há três partes ou mais, ou duas de tamanhos diferentes;
  - só o mês é filtrado (`mes = 3`, de todos os anos);
  - um `OR` mistura tempo com outro filtro;
  - nenhum mês passa.
- **Filtro que só o banco resolve.** Por exemplo, `competencia >= (SELECT MAX(competencia) …) - INTERVAL '11 months'`. Nesse caso o período vem da **linha única** do resultado, se houver uma: `mes_referencia`, `competencia` (date ou texto), ou `ano` (+ `mes`). Com várias linhas, não há período.
- **Junção.** `f.competencia = r.competencia` (coluna com coluna) é junção e é ignorada.

## Testes (`ai-agent/tests/test_tela_dashboard.py`)

- Quatro testes antigos filtram `ano` e passaram a esperar também o `periodo`.
- Casos novos para cada forma da tabela acima, para as comparações, para o que fica sem período e para a linha única.
- `pytest tests` (sem o golden set): **138 passando**.

## Conferido com o agente de verdade (backend + 9router)

| Pergunta | `dashboard.filtros` |
|---|---|
| Qual o faturamento em Recife no ano de 2024? | `municipio: recife`, `periodo: 2024-01..2024-12` |
| Qual foi o consumo total entre janeiro e março de 2025? | `periodo: 2025-01..2025-03` |
| Compare o faturamento de 2023 com o de 2024 | `periodo_base: 2023`, `periodo: 2024` |
| Qual alimentador teve o maior DEC em 2025? | `alimentador: ALM-JAB-016`, `periodo: 2025` |
| Qual o faturamento total de Olinda? | `municipio: olinda`, sem período (a tela fica no padrão) |

No portal, "Recife em 2024" abre os Indicadores com base jan–dez/2023, comparado jan–dez/2024, e o card de Receita faturada mostra **R$ 68,6 mi**, igual à resposta.

## Para o time de IA olhar

1. **Pergunta de seguimento virando recusa.** No painel, com o histórico de uma pergunta sobre Recife, "Compare o faturamento de 2023 com o de 2024" foi reescrita como "…de Recife em 2023 com o de 2024" e terminou em `recusa_honesta`, sem SQL. Em conversa nova, a mesma comparação funciona.
2. **Texto cru na resposta.** Ainda vem "receita_total: 68560067.39000009" quando a conferência numérica reprova e cai na resposta determinística.
