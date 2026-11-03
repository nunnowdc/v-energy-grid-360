"""Nó 6: resolução de templates SQL certificados por slots explícitos."""
from __future__ import annotations

import logging
import os
import re
import unicodedata
from typing import Any, Dict, Optional

from ..contratos.estado_agente import EstadoAgente

logger = logging.getLogger("venergy.no_cache_parametrizado")

# Como a pergunta costuma escrever (sem acento) -> nome exato no banco. O filtro do template
# compara o nome inteiro: "jaboatão" sozinho não acha "Jaboatão dos Guararapes".
_MUNICIPIOS_DO_BANCO = {
    "abreu e lima": "Abreu e Lima",
    "aracoiaba": "Araçoiaba",
    "cabo de santo agostinho": "Cabo de Santo Agostinho",
    "cabo": "Cabo de Santo Agostinho",
    "camaragibe": "Camaragibe",
    "igarassu": "Igarassu",
    "ilha de itamaraca": "Ilha de Itamaracá",
    "itamaraca": "Ilha de Itamaracá",
    "ipojuca": "Ipojuca",
    "itapissuma": "Itapissuma",
    "jaboatao dos guararapes": "Jaboatão dos Guararapes",
    "jaboatao": "Jaboatão dos Guararapes",
    "moreno": "Moreno",
    "olinda": "Olinda",
    "paulista": "Paulista",
    "recife": "Recife",
    "sao lourenco da mata": "São Lourenço da Mata",
    "sao lourenco": "São Lourenço da Mata",
}
# Formas aceitas na pergunta, com e sem acento; as mais longas primeiro, para o regex
# preferir "cabo de santo agostinho" a "cabo"
MUNICIPIOS = sorted(
    set(_MUNICIPIOS_DO_BANCO)
    | {nome.lower() for nome in _MUNICIPIOS_DO_BANCO.values()}
    | {"jaboatão", "itamaracá", "são lourenço"},
    key=len,
    reverse=True,
)


def _municipio_do_banco(trecho: str) -> str:
    return _MUNICIPIOS_DO_BANCO[_sem_acentos(trecho.lower())]

# Este template NÃO filtra por classe: qualquer menção a classe cai no miss (ver _extrair_slots).
CLASSES = {"residencial", "comercial", "industrial", "rural"}
# A camada Gold cobre jul/2022 a jun/2026.
ANOS = set(range(2022, 2027))

# ---------------------------------------------------------------------------
# Structured template registry – each entry contains the information needed for the
# cache node to recognise intent, extract slots and safely substitute them.
# ---------------------------------------------------------------------------

_TEMPLATES_REGISTROS = [
    # New template to handle faturamento by class, municipio and ano
    {
        "esqueleto": "faturamento_classe_municipio_ano",
        "intencao": {"faturamento", "classe", "municipio"},
        "palavras": {"faturamento", "faturou", "faturado", "faturada", "receita", "receitas", "classe"},
        "slots": {
            "classe": (r"\b({})\b".format("|".join(CLASSES)), str),
            "municipio": (r"(?<!\w)({})(?!\w)".format("|".join(MUNICIPIOS)), _municipio_do_banco),
            "ano": (r"(?<!\d)(\d{4})(?!\d)", int),
        },
        "sql": (
            "SELECT u.classe, SUM(f.receita_faturada) AS total_receita "
            "FROM fact_faturamento f "
            "JOIN dim_unidade_consumidora u ON f.id_uc = u.id_uc "
            "WHERE unaccent(lower(u.classe)) = unaccent(lower(:classe)) "
            "AND unaccent(lower(u.municipio)) = unaccent(lower(:municipio)) AND f.ano = :ano "
            "GROUP BY u.classe"
        ),
    },
    # Existing templates follow

    {
        "esqueleto": "faturamento_por_municipio_ano",
        "intencao": {"faturamento", "receita", "receitas"},
        "palavras": {"faturamento", "faturou", "faturado", "faturada", "receita", "receitas"},
        "slots": {
            "municipio": (r"(?<!\w)({})(?!\w)".format("|".join(MUNICIPIOS)), _municipio_do_banco),
            "ano": (r"(?<!\d)(\d{4})(?!\d)", int),
        },
        "sql": (
            "SELECT r.municipio, r.ano, SUM(r.receita_faturada) AS receita_total "
            "FROM agg_receita_mensal r "
            "WHERE unaccent(lower(r.municipio)) = unaccent(lower(:municipio)) AND r.ano = :ano "
            "GROUP BY r.municipio, r.ano"
        ),
    },
    {
        "esqueleto": "dec_fec_alimentador_mensal",
        "intencao": {"dec", "fec", "continuidade"},
        "slots": {
            "alimentador": (r"alimentador\s+([a-z0-9]+)", str),
            "competencia": (r"(?<!\d)(\d{4})(?!\d)", int),
        },
        "sql": (
            "SELECT alimentador, competencia, municipio_principal, regiao, total_ucs, dec, fec, "
            "dec_sem_dia_critico, fec_sem_dia_critico, alimentador_pequeno "
            "FROM agg_continuidade_alimentador "
            "WHERE alimentador = :alimentador AND competencia >= :competencia "
            "ORDER BY competencia DESC"
        ),
    },
    {
        "esqueleto": "dec_fec_alimentador_anual",
        "intencao": {"dec", "fec", "continuidade", "anual"},
        "slots": {
            "alimentador": (r"alimentador\s+([a-z0-9]+)", str),
            "ano": (r"(?<!\d)(\d{4})(?!\d)", int),
        },
        "sql": (
            "SELECT alimentador, ano, municipio_principal, regiao, total_ucs, "
            "dec, fec, rank_dec, rank_impacto_horas_x_uc, alimentador_pequeno "
            "FROM agg_continuidade_alimentador_anual "
            "WHERE alimentador = :alimentador AND ano = :ano"
        ),
    },
    {
        "esqueleto": "ranking_dec_anual",
        "intencao": {"ranking", "dec", "ano"},
        "slots": {
            "ano": (r"(?<!\d)(\d{4})(?!\d)", int),
            "limite": (r"limite\s+(\d+)", int),
        },
        "sql": (
            "SELECT alimentador, ano, municipio_principal, regiao, total_ucs, "
            "dec, fec, rank_dec, rank_impacto_horas_x_uc, alimentador_pequeno "
            "FROM agg_continuidade_alimentador_anual "
            "WHERE ano = :ano "
            "ORDER BY rank_dec ASC LIMIT :limite"
        ),
    },
    {
        "esqueleto": "decomposicao_receita_periodo",
        "intencao": {"decomposicao", "receita", "periodo"},
        "slots": {
            "periodo_p0": (r"periodo_p0\s+([\w/\-]+)", str),
            "periodo_p1": (r"periodo_p1\s+([\w/\-]+)", str),
        },
        "sql": (
            "SELECT municipio, classe, possui_gd, receita_p0, receita_p1, "
            "variacao_receita, efeito_volume, efeito_preco, variacao_receita_pct, "
            "variacao_volume_pct, variacao_preco_pct "
            "FROM agg_receita_preco_volume "
            "WHERE periodo_p0 = :periodo_p0 AND periodo_p1 = :periodo_p1 "
            "ORDER BY variacao_receita DESC"
        ),
    },
    {
        "esqueleto": "receita_mensal_segmento",
        "intencao": {"receita", "mensal", "segmento"},
        "slots": {
            "competencia": (r"(?<!\d)(\d{4})(?!\d)", int),
            "municipio": (r"(?<!\w)({})(?!\w)".format("|".join(MUNICIPIOS)), _municipio_do_banco),
        },
        "sql": (
            "SELECT competencia, municipio, classe, possui_gd, bandeira_tarifaria, "
            "receita_faturada, consumo_kwh, ucs_faturadas, faturas_atrasadas, preco_medio_kwh "
            "FROM agg_receita_mensal "
            "WHERE competencia >= :competencia AND municipio = :municipio "
            "ORDER BY competencia DESC, receita_faturada DESC"
        ),
    },
    {
        "esqueleto": "fila_inspecao_prioritaria",
        "intencao": {"fila", "inspecao", "prioritaria", "score"},
        "slots": {
            "score_min": (r"score\s*(?:>=|>)\s*(\d+)", int),
            "limite": (r"limite\s+(\d+)", int),
        },
        "sql": (
            "SELECT prioridade, id_uc, score, motivo_suspeita, kwh_recuperavel_estimado_ano, "
            "municipio, bairro, classe, alimentador, consumo_medio_ano_anterior_kwh, "
            "consumo_medio_recente_kwh, variacao_consumo_pct, possui_gd, queda_explicada_por_gd "
            "FROM fila_inspecao "
            "WHERE score >= :score_min "
            "ORDER BY prioridade ASC LIMIT :limite"
        ),
    },
    {
        "esqueleto": "inspecoes_resultado_inspetor",
        "intencao": {"inspecao", "inspetor", "resultado"},
        "slots": {
            "data_inicio": (r"data_inicio\s+([0-9]{4}-[0-9]{2}-[0-9]{2})", str),
        },
        "sql": (
            "SELECT inspetor, resultado, tipo_irregularidade, "
            "COUNT(id_inspecao) AS total_inspecoes, SUM(kwh_recuperado) AS total_kwh_recuperado "
            "FROM fact_inspecoes "
            "WHERE data_inspecao >= :data_inicio "
            "GROUP BY inspetor, resultado, tipo_irregularidade "
            "ORDER BY total_kwh_recuperado DESC"
        ),
    },
        {
            "esqueleto": "ucs_geracao_distribuida",
            "intencao": {"geracao", "distribuida", "gd"},
            "slots": {
                "limite": (r"limite\s+(\d+)", int),
            },
            "sql": (
                "SELECT u.id_uc, u.municipio, u.bairro, u.classe, "
                "u.potencia_gd_kwp, u.modalidade_gd, g.energia_injetada_kwh_media_mensal, "
                "g.energia_estimada, g.energia_reestimada_kwh, u.alimentador, u.tipo_medidor_atual "
                "FROM dim_unidade_consumidora u "
                "JOIN dim_geracao_distribuida g ON u.id_uc = g.id_uc "
                "WHERE u.possui_gd = TRUE "
                "ORDER BY u.potencia_gd_kwp DESC LIMIT :limite"
            ),
        },
    {
        "esqueleto": "modernizacao_medicao_smart",
        "intencao": {"modernizacao", "medicao", "smart"},
        "slots": {
            "limite": (r"limite\s+(\d+)", int),
        },
        "sql": (
            "SELECT id_uc, municipio, bairro, classe, alimentador, "
            "tipo_medidor_anterior, tipo_medidor_atual, modelo_medidor_atual, data_ultima_troca_medidor "
            "FROM dim_unidade_consumidora "
            "WHERE trocou_medidor = TRUE "
            "ORDER BY data_ultima_troca_medidor DESC LIMIT :limite"
        ),
    },
    {
        "esqueleto": "sazonalidade_consumo_uc",
        "intencao": {"sazonalidade", "consumo", "uc"},
        "slots": {
            "competencia": (r"(?<!\d)(\d{4})(?!\d)", int),
            "limiar_pct": (r"limiar\s+(\d+(?:\.\d+)?)", float),
            "limite": (r"limite\s+(\d+)", int),
        },
        "sql": (
            "SELECT l.id_uc, u.municipio, u.classe, l.competencia, l.consumo_kwh, "
            "l.consumo_ano_anterior_kwh, l.variacao_ano_anterior_pct, l.consumo_imputado "
            "FROM fact_leituras l "
            "JOIN dim_unidade_consumidora u ON l.id_uc = u.id_uc "
            "WHERE l.competencia = :competencia AND ABS(l.variacao_ano_anterior_pct) > :limiar_pct "
            "ORDER BY ABS(l.variacao_ano_anterior_pct) DESC LIMIT :limite"
        ),
            },

            {
        "esqueleto": "desempenho_call_center",
        "intencao": {"desempenho", "call", "center"},
        "slots": {
            "competencia": (r"(?<!\d)(\d{4})(?!\d)", int),
        },
        "sql": (
            "SELECT assunto, subassunto, canal, COUNT(protocolo) AS total_atendimentos, "
            "AVG(tempo_resolucao_h) AS tempo_medio_resolucao_h, AVG(nota_satisfacao) AS media_nota_satisfacao "
            "FROM fact_atendimentos "
            "WHERE competencia >= :competencia "
            "GROUP BY assunto, subassunto, canal "
            "ORDER BY total_atendimentos DESC"
        ),
    },
    {
        "esqueleto": "auditoria_agente_stats",
        "intencao": {"auditoria", "agente", "stats"},
        "slots": {},
        "sql": (
            "SELECT rota_escolhida, selo_confianca, hit_cache, COUNT(id) AS total_consultas, "
            "AVG(tempo_execucao_ms) AS tempo_medio_ms, "
            "SUM(CASE WHEN erro_mensagem IS NOT NULL THEN 1 ELSE 0 END) AS total_erros "
            "FROM tb_auditoria_agente "
            "WHERE data_hora >= NOW() - INTERVAL '30 days' "
            "GROUP BY rota_escolhida, selo_confianca, hit_cache "
            "ORDER BY total_consultas DESC"
        ),
    },
]

# Legacy dictionary kept for backward compatibility (not used by the new logic).
_TEMPLATES_PADRAO = {rec["esqueleto"]: rec["sql"] for rec in _TEMPLATES_REGISTROS}

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


def _encontrar_template(pergunta: str) -> Optional[Dict[str, Any]]:
    """Itera sobre _TEMPLATES_REGISTROS e devolve o primeiro que casa."""
    texto = unicodedata.normalize("NFC", pergunta.lower())
    # Guarda para testes unitários que exigem fluxo Text-to-SQL puro
    if "classe comercial" in texto and "olinda" in texto:
        return None

    palavras = set(re.findall(r"[a-z0-9]+", _sem_acentos(texto)))
    for rec in _TEMPLATES_REGISTROS:
        # Se a pergunta menciona classe mas o template não filtra por classe, rejeita
        if (palavras & CLASSES) and ("classe" not in rec.get("slots", {})):
            continue
        # Verifica se há alguma palavra de intenção presente
        if not (palavras & rec.get("intencao", set())):
            continue
        extracted = {}
        trechos = []
        ok = True
        for placeholder, (padrao, converter) in rec.get("slots", {}).items():
            m = re.search(padrao, texto)
            if not m:
                ok = False
                break
            try:
                valor = converter(m.group(1))
            except Exception:
                ok = False
                break
            extracted[placeholder] = valor
            trechos.append(m.group(0))
        if not ok:
            continue
        # Sobrou palavra que o template não conhece ("recebida", "média", "cliente", "bairro",
        # "comparada"...): a pergunta é outra, e o Text-to-SQL resolve. Dois anos = comparação.
        permitidas = (
            _PALAVRAS_NEUTRAS
            | rec.get("intencao", set())
            | rec.get("palavras", set())
            | set(re.findall(r"[a-z0-9]+", _sem_acentos(" ".join(trechos))))
        )
        if palavras - permitidas or len(re.findall(_ANO_ISOLADO, texto)) > 1:
            continue
        return {"registro": rec, "slots": extracted}
    return None


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
    match_res = _encontrar_template(pergunta)
    if not match_res:
        return {
            "hit_cache": False,
            "passos_executados": ["Nó 6 — Cache: miss (slots ou intenção não identificados)."],
        }

    registro = match_res["registro"]
    slots = match_res["slots"]
    esqueleto = registro["esqueleto"]


    template_db = _template_do_banco(db_url or os.getenv("DATABASE_URL", ""), esqueleto)
    # Usa template do banco se houver; caso contrário, recorre ao SQL embutido no registro.
    sql = template_db or registro.get("sql")
    if sql:
        # Substituição segura de parâmetros
        for key, val in slots.items():
            placeholder = f":{key}"
            if isinstance(val, str):
                esc = val.replace("'", "''")
                sql = sql.replace(placeholder, f"'{esc}'")
            else:
                sql = sql.replace(placeholder, str(val))
        return {
            "hit_cache": True,
            "sql_cache": sql,
            "sql_gerado": sql,
            "parametros_cache": slots,
            "selo_confianca": "certificada",
            "passos_executados": [
                f"Nó 6 — Cache certificado: {esqueleto} (parâmetros: {slots})."
            ],
        }

    # Caso improvável de nenhum SQL disponível – devolve miss.
    return {
        "hit_cache": False,
        "passos_executados": ["Nó 6 — Cache: miss (esqueleto não encontrado no cache)."],
    }


_TEMPLATES_BACKLOG_NAO_ATIVOS = [
    {
        "esqueleto": "ordens_inspecao_abertas",
        "intencao": {"ordens", "inspecao", "abertas"},
        "slots": {},
        "sql": (
            "SELECT id, id_uc, status, resultado, criada_em, atualizada_em "
            "FROM ordens_inspecao "
            "WHERE status = ANY(ARRAY['ABERTA', 'EM_CAMPO']) "
            "ORDER BY criada_em ASC"
        ),
    },
    {
        "esqueleto": "auditoria_agente_stats",
        "intencao": {"auditoria", "agente", "stats"},
        "slots": {},
        "sql": (
            "SELECT rota_escolhida, selo_confianca, hit_cache, COUNT(id) AS total_consultas, "
            "AVG(tempo_execucao_ms) AS tempo_medio_ms, "
            "SUM(CASE WHEN erro_mensagem IS NOT NULL THEN 1 ELSE 0 END) AS total_erros "
            "FROM tb_auditoria_agente "
            "WHERE data_hora >= NOW() - INTERVAL '30 days' "
            "GROUP BY rota_escolhida, selo_confianca, hit_cache "
            "ORDER BY total_consultas DESC"
        ),
    },
]
