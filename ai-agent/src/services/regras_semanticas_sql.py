"""Regras de negócio que o SQL precisa respeitar além de ser válido (cada problema vira feedback de nova tentativa)."""
from __future__ import annotations

import re

import sqlglot
from sqlglot import exp

# Colunas que são razões ou médias: somar ou tirar média delas dá número sem sentido.
# DEC e FEC ficam de fora: somar o DEC mensal de um alimentador dá o DEC do ano (regra C16)
_RAZAO = re.compile(r"(_pct$|^pct_|^preco_|ticket|_medio|_media|^taxa_|^score|^prioridade)")
# Contagem mensal de UCs da agg_receita_mensal: somada entre meses conta a mesma UC várias vezes.
# total_ucs fica de fora: somar entre alimentadores do mesmo mês é o certo no DEC/FEC (regra C16)
_ESTOQUE = {"ucs_faturadas"}
# Colunas que deixam a soma num mês só: agrupar por elas ou filtrar uma delas com "="
_MES = {"competencia", "mes_referencia", "mes"}


def _colunas(no: exp.Expression | None) -> set[str]:
    return {c.name.lower() for c in no.find_all(exp.Column)} if no else set()


def _filtra_igual(select: exp.Select, colunas: set[str]) -> bool:
    """Se o WHERE fixa uma dessas colunas com '=' ou IN (ex.: municipio = 'Recife')."""
    where = select.args.get("where")
    if not where:
        return False
    return any(_colunas(comparacao) & colunas for comparacao in where.find_all(exp.EQ, exp.In))


def problemas_semanticos(sql: str) -> list[str]:
    try:
        arvore = sqlglot.parse_one(sql, read="postgres")
    except sqlglot.errors.ParseError:
        return []  # sintaxe é com o validador
    problemas: list[str] = []

    for agregado in arvore.find_all(exp.Sum, exp.Avg):
        alvo = agregado.this
        # SUM(coluna) direto, sem conta dentro: é aí que mora a soma de percentuais
        if isinstance(alvo, exp.Column) and _RAZAO.search(alvo.name.lower()):
            problemas.append(
                f"{agregado.key.upper()}({alvo.name}) agrega uma razão. Recalcule a partir do numerador e do "
                "denominador somados (regra C1)."
            )

    for soma in arvore.find_all(exp.Sum):
        if not _colunas(soma) & _ESTOQUE:
            continue
        select = soma.find_ancestor(exp.Select)
        um_mes_por_vez = select is not None and (
            _colunas(select.args.get("group")) & _MES or _filtra_igual(select, _MES)
        )
        if not um_mes_por_vez:
            problemas.append(
                "SUM(ucs_faturadas) soma a contagem de UCs de cada mês: a mesma UC entra uma vez por mês. "
                "Para quantidade de UCs ou 'por cliente', use COUNT(DISTINCT id_uc) em fact_faturamento, "
                "ou agrupe por competencia e registre a premissa (regra C4)."
            )

    for select in arvore.find_all(exp.Select):
        grupo = _colunas(select.args.get("group"))
        if "bairro" in grupo and "municipio" not in grupo and not _filtra_igual(select, {"municipio"}):
            problemas.append("Agrupou por bairro sem município (regra R1).")
        # A agg_receita_preco_volume tem uma linha por possui_gd: ler a linha crua de um bairro
        # dá só as UCs com ou sem GD (Iputinga −15,72% no lugar de −22,2%)
        tabelas = {t.name.lower() for t in select.find_all(exp.Table)}
        mostra_gd = "possui_gd" in _colunas(select.args.get("where")) | {
            c.name.lower() for coluna in select.expressions for c in coluna.find_all(exp.Column)
        }
        if (
            "agg_receita_preco_volume" in tabelas
            and not grupo
            and not select.find(exp.AggFunc)
            and not mostra_gd
            and {"bairro", "municipio"} & {c.name.lower() for c in select.find_all(exp.Column)}
        ):
            problemas.append(
                "agg_receita_preco_volume tem uma linha com GD e outra sem GD para cada bairro. Some kwh_p0, "
                "kwh_p1, receita_p0 e receita_p1 com GROUP BY municipio, bairro e recalcule a variação (regra C6)."
            )
    return list(dict.fromkeys(problemas))
