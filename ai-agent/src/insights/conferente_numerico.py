"""Conferência determinística dos valores numéricos narrados pelo LLM.

Regra: TODO número que aparece no texto precisa existir nos fatos extraídos do banco.
Um número do texto é aceito quando é um arredondamento correto de algum valor dos fatos
(ex.: fato 289,6 aceita "289,60" e "R$ 290", mas não "R$ 291").
"""
from __future__ import annotations

import math
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict

# Número escrito no texto: "1.250,50", "289.60", "12,5", "2025", seguido ou não de "mil/milhão".
_NUMERO_NO_TEXTO = re.compile(
    r"(?<!\w)(\d+(?:\.\d+)*)(?:,(\d+))?"
    r"(?:\s*(mil|milhao|milhão|milhoes|milhões|bilhao|bilhão|bilhoes|bilhões)\b)?",
    re.IGNORECASE,
)
_MILHAR_BR = re.compile(r"\d{1,3}(?:\.\d{3})+")
_NUMERO_EM_TEXTO_DE_FATO = re.compile(r"\d+(?:\.\d+)?")

_ESCALAS = {}


def _numeros_dos_fatos(fatos: list[Dict[str, Any]]) -> list[float]:
    """Todos os números permitidos: valores numéricos, partes de datas e dígitos de textos.

    Além dos valores originais, aceita também o valor absoluto de números (ex.: -3.9 aceita 3.9)."""
    permitidos: list[float] = []
    for fato in fatos:
        for valor in fato.values():
            if valor is None or isinstance(valor, bool):
                continue
            if isinstance(valor, (int, float, Decimal)):
                numero = float(valor)
                if math.isfinite(numero):
                    permitidos.append(numero)
                    if numero != 0:
                        permitidos.append(abs(numero))
            elif isinstance(valor, (date, datetime)):
                permitidos.extend([float(valor.year), float(valor.month), float(valor.day)])
            else:
                permitidos.extend(float(t) for t in _NUMERO_EM_TEXTO_DE_FATO.findall(str(valor)))
    return permitidos



def _leituras_possiveis(inteiro: str, decimais: str | None) -> list[tuple[float, int]]:
    """Valores possíveis (valor, casas decimais) de um número escrito no texto.

    "1.250,50" -> padrão brasileiro. "289.60" -> ponto como decimal.
    "1.250" é ambíguo (1250 ou 1,25), então as duas leituras são testadas.
    Lista vazia = número malformado.
    """
    if decimais is not None:
        if "." in inteiro and not _MILHAR_BR.fullmatch(inteiro):
            return []
        return [(float(inteiro.replace(".", "") + "." + decimais), len(decimais))]
    if "." not in inteiro:
        return [(float(inteiro), 0)]
    leituras: list[tuple[float, int]] = []
    if inteiro.count(".") == 1:
        leituras.append((float(inteiro), len(inteiro.split(".")[1])))
    if _MILHAR_BR.fullmatch(inteiro):
        leituras.append((float(inteiro.replace(".", "")), 0))
    return leituras


def _bate(
    valor: float, casas: int, multiplicador: int, permitido: float, tolerancia: float
) -> bool:
    """O valor do texto é um arredondamento correto do valor permitido?"""
    meia_unidade = 0.5 * (10 ** -casas) * multiplicador
    folga_float = 1e-9 * max(1.0, abs(permitido))
    return abs(valor * multiplicador - permitido) <= meia_unidade + tolerancia + folga_float


def conferir(fatos: list[Dict[str, Any]], texto: str, tolerancia: float = 0.0) -> bool:
    """True se todo número do texto existir nos fatos (dentro do arredondamento).

    `tolerancia` é uma folga absoluta EXTRA, além do arredondamento (padrão: nenhuma).
    """
    permitidos = _numeros_dos_fatos(fatos)
    for achado in _NUMERO_NO_TEXTO.finditer(texto):
        inteiro, decimais, escala = achado.groups()
        multiplicador = _ESCALAS.get(escala.lower(), 1) if escala else 1
        leituras = _leituras_possiveis(inteiro, decimais)
        aceito = any(
            _bate(valor, casas, multiplicador, permitido, tolerancia)
            for valor, casas in leituras
            for permitido in permitidos
        )
        if not aceito:
            return False
    return True