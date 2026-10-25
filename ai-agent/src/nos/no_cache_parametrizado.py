"""Nó 6: resolução de templates SQL certificados por slots explícitos."""
from __future__ import annotations

import logging
import os
import re
import unicodedata
from typing import Any, Dict, Optional

from ..contratos.estado_agente import EstadoAgente

logger = logging.getLogger("venergy.no_cache_parametrizado")

MUNICIPIOS = {
    "recife", "olinda", "jaboatão", "jaboatao", "paulista", "camaragibe",
    "caruaru", "cabo de santo agostinho", "cabo", "moreno", "igarassu",
    "itamaracá", "itamaraca", "araçoiaba", "aracoiaba", "são lourenço",
    "sao lourenco", "paudalho", "abreu e lima",
}
# Este template NÃO filtra por classe: qualquer menção a classe cai no miss (ver _extrair_slots).
CLASSES = {"residencial", "comercial", "industrial", "rural"}
# A camada Gold cobre jul/2022 a jun/2026.
ANOS = set(range(2022, 2027))

_TEMPLATES_PADRAO = {
    "faturamento_por_municipio_ano": (
        "SELECT r.municipio, r.ano, SUM(r.receita_faturada) AS receita_total "
        "FROM agg_receita_mensal r "
        "WHERE r.municipio = '{municipio}' AND r.ano = {ano} "
        "GROUP BY r.municipio, r.ano"
    ),
}

# Palavras que indicam a intenção do template (receita/faturamento).
_TERMOS_DE_INTENCAO = {
    "faturamento", "faturou", "faturado", "faturada", "receita", "receitas",
}
# Palavras neutras que não mudam o significado da pergunta.
# Qualquer palavra fora destas listas (classe, bairro, mês, comparação, volume...)
# faz o cache dar miss e deixa o Text-to-SQL resolver. Errar para o lado do miss custa
# uma chamada ao LLM; errar para o lado do hit entrega resposta errada com selo "certificada".
_PALAVRAS_NEUTRAS = {
    "qual", "quanto", "foi", "a", "o", "as", "os", "de", "do", "da", "dos", "das",
    "em", "no", "na", "nos", "nas", "ano", "total", "me", "mostre", "mostra",
    "diga", "informe", "municipio", "cidade", "teve",
}
_ANO_ISOLADO = r"(?<!\d)\d{4}(?!\d)"


def _sem_acentos(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    )


def _extrair_slots(pergunta: str) -> Optional[Dict[str, Any]]:
    """Devolve município e ano só se a pergunta for EXATAMENTE receita por município e ano.

    Retorna None (miss) quando há: mais de um município, mais de um ano, ano fora de ANOS,
    ou qualquer palavra além da intenção e das palavras neutras (classe, bairro, mês...).
    """
    texto = unicodedata.normalize("NFC", pergunta.lower())

    municipios_encontrados: list[str] = []
    restante = texto
    for municipio in sorted(MUNICIPIOS, key=len, reverse=True):
        padrao = rf"(?<!\w){re.escape(municipio)}(?!\w)"
        if re.search(padrao, restante):
            municipios_encontrados.append(municipio)
            restante = re.sub(padrao, " ", restante)
    if len(municipios_encontrados) != 1:
        return None

    anos = re.findall(_ANO_ISOLADO, restante)
    if len(anos) != 1 or int(anos[0]) not in ANOS:
        return None
    restante = re.sub(_ANO_ISOLADO, " ", restante)

    palavras = set(re.findall(r"[a-z0-9]+", _sem_acentos(restante)))
    if not palavras & _TERMOS_DE_INTENCAO:
        return None
    if not palavras <= (_TERMOS_DE_INTENCAO | _PALAVRAS_NEUTRAS):
        return None

    return {"municipio": municipios_encontrados[0], "ano": int(anos[0])}


def _template_do_banco(db_url: str, esqueleto: str) -> Optional[str]:
    try:
        import psycopg2
        with psycopg2.connect(db_url, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT sql_template FROM tb_cache_perguntas_certificadas "
                    "WHERE esqueleto = %s AND ativo = TRUE LIMIT 1;",
                    (esqueleto,),
                )
                row = cur.fetchone()
                return row[0] if row else None
    except ImportError:
        logger.warning("psycopg2 não disponível; cache certificado local será usado.")
    except Exception as exc:
        logger.warning("Não foi possível consultar o cache certificado: %s", exc)
    return None


def no_cache_parametrizado(
    state: EstadoAgente,
    db_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Resolve apenas templates conhecidos; perguntas não casadas seguem para Text-to-SQL."""
    pergunta = state.get("pergunta_autonoma") or state.get("pergunta_original", "")
    slots = _extrair_slots(pergunta)
    if not slots:
        return {
            "hit_cache": False,
            "passos_executados": ["Nó 6 — Cache: miss (slots ou intenção não identificados)."],
        }

    esqueleto = "faturamento_por_municipio_ano"
    template = _template_do_banco(db_url or os.getenv("DATABASE_URL", ""), esqueleto)
    template = template or _TEMPLATES_PADRAO[esqueleto]
    sql = template.replace(":municipio", f"'{slots['municipio']}'").replace(
        ":ano", str(slots["ano"])
    )
    sql = sql.replace("{municipio}", slots["municipio"]).replace("{ano}", str(slots["ano"]))
    return {
        "hit_cache": True,
        "sql_cache": sql,
        "sql_gerado": sql,
        "parametros_cache": slots,
        "selo_confianca": "certificada",
        "passos_executados": [
            f"Nó 6 — Cache certificado: {esqueleto} ({slots['municipio']}, {slots['ano']})."
        ],
    }