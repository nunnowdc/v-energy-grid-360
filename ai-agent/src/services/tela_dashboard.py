"""
Tela do portal que mostra os dados de uma resposta do agente.

Lê o SQL executado: as tabelas decidem a tela e as igualdades do WHERE viram os
filtros. Quando o resultado tem uma linha só ("qual alimentador teve o maior DEC?"),
os valores dessa linha completam os filtros que o WHERE não trouxe.
"""
from __future__ import annotations

import logging
import unicodedata
from typing import Any, Dict, Iterator, List, Optional

import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError

from ..contratos.resposta_agente import FiltrosDashboard, TelaDashboard

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
    filtros = {**_filtros_da_linha(dados), **_filtros_do_where(arvore)}

    if filtros.get("id_uc"):
        return TelaDashboard(tela="visao_360", filtros=FiltrosDashboard(id_uc=filtros["id_uc"]))

    tabelas = {tabela.name.lower() for tabela in arvore.find_all(exp.Table)}
    for tela, da_tela in _TELAS_POR_TABELA:
        if tabelas & da_tela:
            return TelaDashboard(tela=tela, filtros=FiltrosDashboard(**filtros))
    return None
