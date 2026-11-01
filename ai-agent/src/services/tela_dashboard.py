"""
Tela do portal que mostra os dados de uma resposta do agente.

Lê o SQL executado: as tabelas decidem a tela e as igualdades do WHERE viram os
filtros. Quando o resultado tem uma linha só ("qual alimentador teve o maior DEC?"),
os valores dessa linha completam os filtros que o WHERE não trouxe.

Os filtros de tempo do WHERE (ano = 2024, competencia entre dois meses...) viram o
período consultado, que o portal mostra nos KPIs.
"""
from __future__ import annotations

import logging
import operator
import re
import unicodedata
from datetime import date
from typing import Any, Callable, Dict, Iterator, List, Optional, Set, Tuple

import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError

from ..contratos.resposta_agente import FiltrosDashboard, PeriodoDashboard, TelaDashboard

logger = logging.getLogger("venergy.tela_dashboard")

# Na ordem de prioridade: consulta que junta ocorrências e cadastro de UCs é Continuidade.
# Tabelas sem tela no portal (atendimentos, medidores, GD) só abrem a Visão 360 de uma UC
_TELAS_POR_TABELA = (
    ("continuidade", {
        "agg_continuidade_alimentador", "agg_continuidade_alimentador_anual",
        "fact_ocorrencias", "dim_alimentador",
    }),
    ("inspecoes", {"fila_inspecao", "fact_inspecoes"}),
    # Receita mostra a variação (efeito preço e volume); receita do mês está nos Indicadores
    ("receita", {"agg_receita_preco_volume"}),
    ("indicadores", {
        "agg_receita_mensal", "fact_faturamento", "fact_leituras", "dim_unidade_consumidora",
    }),
)

# Coluna da Gold → filtro do portal
_FILTRO_DA_COLUNA = {
    "municipio": "municipio",
    "municipio_principal": "municipio",
    "bairro": "bairro",
    "classe": "classe",
    "alimentador": "alimentador",
    "causa": "causa",
    "id_uc": "id_uc",
}

# Funções que só normalizam o texto: unaccent(lower(municipio)) ainda é municipio
_FUNCOES_DE_TEXTO = {"unaccent", "lower", "upper", "trim"}


def _normalizar(texto: str) -> str:
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    )
    return sem_acento.strip().lower()


def _sem_funcoes_de_texto(no: exp.Expression) -> exp.Expression:
    while True:
        if isinstance(no, (exp.Lower, exp.Upper, exp.Trim, exp.Paren)):
            no = no.this
        elif isinstance(no, exp.Anonymous) and no.name.lower() in _FUNCOES_DE_TEXTO and len(no.expressions) == 1:
            no = no.expressions[0]
        else:
            return no


def _filtro_da_coluna(no: exp.Expression) -> Optional[str]:
    no = _sem_funcoes_de_texto(no)
    return _FILTRO_DA_COLUNA.get(no.name.lower()) if isinstance(no, exp.Column) else None


def _texto_literal(no: exp.Expression) -> Optional[str]:
    no = _sem_funcoes_de_texto(no)
    return no.this if isinstance(no, exp.Literal) and no.is_string else None


def _condicoes_com_and(no: exp.Expression) -> Iterator[exp.Expression]:
    """Partes de 'a AND (b AND c)'. Um OR fica inteiro e não vira filtro."""
    if isinstance(no, exp.Paren):
        yield from _condicoes_com_and(no.this)
    elif isinstance(no, exp.And):
        yield from _condicoes_com_and(no.left)
        yield from _condicoes_com_and(no.right)
    else:
        yield no


def _filtros_do_where(arvore: exp.Expression) -> Dict[str, str]:
    """
    Igualdades 'coluna = texto' (ou IN com um valor só) ligadas por AND, em qualquer
    WHERE da consulta. Coluna filtrada com dois valores diferentes fica de fora.
    """
    valores: Dict[str, List[str]] = {}
    for where in arvore.find_all(exp.Where):
        for condicao in _condicoes_com_and(where.this):
            pares = []
            if isinstance(condicao, exp.EQ):
                pares = [(condicao.left, condicao.right), (condicao.right, condicao.left)]
            elif isinstance(condicao, exp.In) and len(condicao.expressions) == 1:
                pares = [(condicao.this, condicao.expressions[0])]
            for coluna, valor in pares:
                filtro, texto = _filtro_da_coluna(coluna), _texto_literal(valor)
                if filtro and texto:
                    valores.setdefault(filtro, []).append(texto)

    return {
        filtro: textos[0]
        for filtro, textos in valores.items()
        if len({_normalizar(texto) for texto in textos}) == 1
    }


def _filtros_da_linha(dados: Optional[List[Dict[str, Any]]]) -> Dict[str, str]:
    """Valores de uma linha única do resultado. Com várias linhas, nenhum vale mais que os outros."""
    if not dados or len(dados) != 1:
        return {}
    filtros: Dict[str, str] = {}
    for coluna, valor in dados[0].items():
        filtro = _FILTRO_DA_COLUNA.get(str(coluna).lower())
        if filtro and isinstance(valor, str) and valor.strip():
            filtros.setdefault(filtro, valor)
    return filtros


# Colunas da Gold em que cada valor é um mês: competencia (1º dia) e mes_referencia (yyyy-MM)
_COLUNAS_DE_MES = {"competencia", "mes_referencia"}

# Os meses são contados como ano × 12 + (mês − 1). Um filtro que chega na borda
# desse intervalo não tem fim (ex.: ano >= 2024) e não vira período
_PRIMEIRO_ANO, _ULTIMO_ANO = 2000, 2099
_MESES = range(_PRIMEIRO_ANO * 12, (_ULTIMO_ANO + 1) * 12)

_OPERADORES = {exp.EQ: "=", exp.GTE: ">=", exp.GT: ">", exp.LTE: "<=", exp.LT: "<"}
# Para ler '2024 = ano' como 'ano = 2024'
_INVERSO = {"=": "=", ">=": "<=", ">": "<", "<=": ">=", "<": ">"}
_COMPARAR: Dict[str, Callable[[int, int], bool]] = {
    "=": operator.eq, ">=": operator.ge, ">": operator.gt, "<=": operator.le, "<": operator.lt,
}
# Parte de cada mês contado: o ano, o mês do ano (1–12) ou o próprio mês
_PARTE_DO_MES: Dict[str, Callable[[int], int]] = {
    "ano": lambda mes: mes // 12,
    "mes": lambda mes: mes % 12 + 1,
    "mes_inteiro": lambda mes: mes,
}


class _TempoNaoLido(Exception):
    """Filtro de tempo que só o banco resolve (ex.: competencia >= max(competencia) - 11 meses)."""


def _mes_do_texto(texto: str) -> Optional[Tuple[int, int]]:
    """'2024-03' ou '2024-03-15' → (mês contado, dia)."""
    achado = re.match(r"^(\d{4})-(\d{2})(?:-(\d{2}))?", texto.strip())
    if not achado or not 1 <= int(achado.group(2)) <= 12:
        return None
    return int(achado.group(1)) * 12 + int(achado.group(2)) - 1, int(achado.group(3) or 1)


def _texto_do_mes(mes: int) -> str:
    return f"{mes // 12:04d}-{mes % 12 + 1:02d}"


def _sem_conversao(no: exp.Expression) -> exp.Expression:
    while isinstance(no, (exp.Cast, exp.Paren)):
        no = no.this
    return no


def _parte_do_tempo(no: exp.Expression) -> Optional[str]:
    """'ano', 'mes' ou 'mes_inteiro' (competencia, mes_referencia) da coluna ou do EXTRACT."""
    no = _sem_conversao(no)
    if isinstance(no, exp.Extract):
        return {"year": "ano", "month": "mes"}.get(no.this.name.lower())
    if isinstance(no, exp.Column):
        nome = no.name.lower()
        if nome in ("ano", "mes"):
            return nome
        if nome in _COLUNAS_DE_MES:
            return "mes_inteiro"
    return None


def _fala_de_tempo(no: exp.Expression) -> bool:
    return any(_parte_do_tempo(filho) for filho in no.walk())


def _meses_da_comparacao(parte: str, simbolo: str, valor: exp.Expression) -> Set[int]:
    literal = _sem_conversao(valor)
    if not isinstance(literal, exp.Literal):
        raise _TempoNaoLido(valor.sql())
    if parte == "mes_inteiro":
        mes_e_dia = _mes_do_texto(literal.this) if literal.is_string else None
        if not mes_e_dia:
            raise _TempoNaoLido(valor.sql())
        numero, dia = mes_e_dia
        # A competência é sempre o dia 1: '>= 2024-03-15' já começa em abril e
        # '< 2024-03-15' ainda inclui março
        if dia != 1:
            if simbolo == "=":
                return set()
            simbolo = ">" if simbolo in (">=", ">") else "<="
    else:
        try:
            numero = int(literal.this)
        except ValueError:
            raise _TempoNaoLido(valor.sql()) from None
    da_parte, comparar = _PARTE_DO_MES[parte], _COMPARAR[simbolo]
    return {mes for mes in _MESES if comparar(da_parte(mes), numero)}


def _meses_da_condicao(condicao: exp.Expression) -> Optional[List[Set[int]]]:
    """
    Meses que a condição deixa passar, em partes: cada valor do IN e cada lado do OR
    é uma parte ('ano IN (2023, 2024)' compara dois anos, não junta 24 meses).
    None quando a condição não fala de tempo.
    """
    if isinstance(condicao, exp.Paren):
        return _meses_da_condicao(condicao.this)
    if isinstance(condicao, (exp.And, exp.Or)):
        lados = [_meses_da_condicao(condicao.left), _meses_da_condicao(condicao.right)]
        if isinstance(condicao, exp.And):
            com_tempo = [lado for lado in lados if lado is not None]
            if len(com_tempo) < 2:
                return com_tempo[0] if com_tempo else None
            return [a & b for a in com_tempo[0] for b in com_tempo[1]]
        if lados == [None, None]:
            return None
        # 'ano = 2024 OR municipio = ...' não diz quais meses entram
        if None in lados:
            raise _TempoNaoLido(condicao.sql())
        return lados[0] + lados[1]

    simbolo = _OPERADORES.get(type(condicao))
    if simbolo:
        esquerda, direita = condicao.left, condicao.right
        # Coluna com coluna é junção (f.competencia = d.competencia), não filtro
        if isinstance(_sem_conversao(esquerda), exp.Column) and isinstance(_sem_conversao(direita), exp.Column):
            return None
        for coluna, valor, lido in ((esquerda, direita, simbolo), (direita, esquerda, _INVERSO[simbolo])):
            parte = _parte_do_tempo(coluna)
            if parte:
                return [_meses_da_comparacao(parte, lido, valor)]
    elif isinstance(condicao, exp.Between) and (parte := _parte_do_tempo(condicao.this)):
        return [
            _meses_da_comparacao(parte, ">=", condicao.args["low"])
            & _meses_da_comparacao(parte, "<=", condicao.args["high"])
        ]
    elif isinstance(condicao, exp.In) and condicao.expressions and (parte := _parte_do_tempo(condicao.this)):
        return [_meses_da_comparacao(parte, "=", valor) for valor in condicao.expressions]
    elif isinstance(condicao, exp.Like) and _parte_do_tempo(condicao.this) == "mes_inteiro":
        # mes_referencia LIKE '2024-%'
        padrao = _sem_conversao(condicao.expression)
        if isinstance(padrao, exp.Literal) and re.fullmatch(r"\d{4}(-\d{0,2})?%", padrao.this):
            return [{mes for mes in _MESES if _texto_do_mes(mes).startswith(padrao.this[:-1])}]

    if _fala_de_tempo(condicao):
        raise _TempoNaoLido(condicao.sql())
    return None


def _meses_do_where(arvore: exp.Expression) -> Optional[List[Set[int]]]:
    """
    Partes de meses de todos os WHEREs. Uma comparação de 2023 com 2024 costuma ter
    um WHERE (ou FILTER) para cada ano, então as partes de cada um se somam.
    """
    partes: Optional[List[Set[int]]] = None
    for where in arvore.find_all(exp.Where):
        do_where = _meses_da_condicao(where.this)
        if do_where is not None:
            partes = (partes or []) + do_where
    return partes


def _meses_da_linha(dados: Optional[List[Dict[str, Any]]]) -> Optional[List[Set[int]]]:
    """O mês ou o ano de uma linha única do resultado ("qual mês teve a maior receita?")."""
    if not dados or len(dados) != 1:
        return None
    linha = {str(coluna).lower(): valor for coluna, valor in dados[0].items()}
    for coluna in ("mes_referencia", "competencia"):
        valor = linha.get(coluna)
        texto = valor.isoformat() if isinstance(valor, date) else valor
        mes_e_dia = _mes_do_texto(texto) if isinstance(texto, str) else None
        if mes_e_dia:
            return [{mes_e_dia[0]}]
    ano, mes = linha.get("ano"), linha.get("mes")
    if not isinstance(ano, int) or not _PRIMEIRO_ANO <= ano <= _ULTIMO_ANO:
        return None
    if isinstance(mes, int) and 1 <= mes <= 12:
        return [{ano * 12 + mes - 1}]
    return [set(range(ano * 12, ano * 12 + 12))]


def _periodos(partes: List[Set[int]]) -> Dict[str, PeriodoDashboard]:
    """
    Uma parte de meses seguidos é o período consultado; duas do mesmo tamanho, sem
    meses em comum, são uma comparação (a mais antiga é o base). Parte que contém
    outra sai: 'WHERE ano IN (2023, 2024)' com um FILTER para cada ano compara os
    dois anos. Qualquer outra forma fica de fora.
    """
    distintas = [parte for indice, parte in enumerate(partes) if parte and parte not in partes[:indice]]
    menores = [parte for parte in distintas if not any(outra < parte for outra in distintas)]
    if not menores or len(menores) > 2:
        return {}
    for parte in menores:
        seguidos = max(parte) - min(parte) + 1 == len(parte)
        if not seguidos or min(parte) == _MESES[0] or max(parte) == _MESES[-1]:
            return {}
    periodos = sorted(
        (PeriodoDashboard(de=_texto_do_mes(min(parte)), ate=_texto_do_mes(max(parte))) for parte in menores),
        key=lambda periodo: periodo.de,
    )
    if len(periodos) == 1:
        return {"periodo": periodos[0]}
    if len(menores[0]) == len(menores[1]) and not menores[0] & menores[1]:
        return {"periodo_base": periodos[0], "periodo": periodos[1]}
    return {}


def _periodos_da_consulta(
    arvore: exp.Expression, dados: Optional[List[Dict[str, Any]]]
) -> Dict[str, PeriodoDashboard]:
    """Período do WHERE ou, sem filtro de tempo que dê para ler, da linha única do resultado."""
    try:
        partes = _meses_do_where(arvore)
    except _TempoNaoLido as exc:
        logger.info("Filtro de tempo sem valor fixo; o período vem da linha, se houver uma só: %s", exc)
        partes = None
    if partes is None:
        partes = _meses_da_linha(dados)
    return _periodos(partes) if partes is not None else {}


def tela_do_dashboard(
    sql: Optional[str],
    dados: Optional[List[Dict[str, Any]]] = None,
) -> Optional[TelaDashboard]:
    """
    Decide a tela e os filtros do portal a partir do SQL executado e do resultado.
    Sem SQL, com SQL que não dá para ler ou sem tabela com tela no portal, devolve None.
    """
    if not sql:
        return None
    try:
        arvore = sqlglot.parse_one(sql, read="postgres")
    except SqlglotError as exc:
        logger.warning("SQL não lido para escolher a tela do dashboard: %s", exc)
        return None

    # O WHERE vale mais que a linha: "Recife" filtrado não é trocado pelo valor do resultado
    filtros_brutos = {**_filtros_da_linha(dados), **_filtros_do_where(arvore)}
    filtros: Dict[str, Any] = {}
    for chave, valor in filtros_brutos.items():
        if isinstance(valor, str):
            filtros[chave] = valor.lower()
        else:
            filtros[chave] = valor

    if filtros.get("id_uc"):
        return TelaDashboard(tela="visao_360", filtros=FiltrosDashboard(id_uc=filtros["id_uc"]))

    tabelas = {tabela.name.lower() for tabela in arvore.find_all(exp.Table)}
    for tela, da_tela in _TELAS_POR_TABELA:
        if tabelas & da_tela:
            periodos = _periodos_da_consulta(arvore, dados)
            return TelaDashboard(tela=tela, filtros=FiltrosDashboard(**filtros, **periodos))
    return None
