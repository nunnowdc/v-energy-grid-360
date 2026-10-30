"""
Nó 11: Síntese da resposta final — narrativa clara a partir dos dados SQL e/ou contexto RAG.
"""
from __future__ import annotations

import json
import logging
from decimal import Decimal
from typing import Any, Dict

from ..contratos.estado_agente import EstadoAgente
from ..insights.conferente_numerico import conferir
from ..provedores.cliente_llm import ClienteLLM, ErroLLMIndisponivel
from .no_recusa_honesta import MENSAGENS_RECUSA

logger = logging.getLogger("venergy.no_sintetiza_resposta")

SYSTEM_PROMPT_SINTESE = """
Você é o assistente de dados da V‑Energy Grid 360, responsável por transformar dados tabulares em respostas claras, objetivas e executivas em português.

REGRAS ABSOLUTAS:
1. NÃO invente nem estime números que não estejam em <DADOS_SQL>.
2. Se <DADOS_SQL> estiver vazio, informe que não há dados disponíveis.
3. Formate números no padrão brasileiro (vírgula decimal, ponto milhar). Ex.: R$ 1.250.430,00.
4. Cite fontes do <CONTEXTO_RAG> no rodapé, se utilizadas.
5. MANTENHA a resposta curta (máx. 4‑6 linhas), porém deixe‑a **conversacional**:
   • Comece com um breve preâmbulo (“Conforme a base de dados,…”).
   • Use conectores (“Além disso”, “Portanto”).
   • Termine com um encerramento amigável (“Qualquer outra informação, estou à disposição.”).
6. NUNCA misture dados do <CONTEXTO_RAG> com números de <DADOS_SQL>.
""".strip()

SYSTEM_PROMPT_SINTESE_RAG = """
Você é o assistente de conhecimento regulatório da V-Energy Grid 360.
Responda SOMENTE com informações presentes em <CONTEXTO_RAG>.
Não invente números nem informações que não estejam no contexto.
Não mencione dados do banco.
Inclua a fonte utilizada em um rodapé.
Seja conciso e responda em português.
""".strip()


def _formatar_dados_sql(dados: list[dict]) -> str:
    if not dados:
        return "(Nenhum dado retornado pelo banco)"
    try:
        limite = 10
        texto = json.dumps(dados[:limite], ensure_ascii=False, indent=2, default=str)
        if len(dados) > limite:
            texto += f"\n(Exibindo {limite} de {len(dados)} linhas; não há outras linhas disponíveis no contexto.)"
        return texto
    except Exception:
        return str(dados[:5])


def _formatar_contexto_rag(chunks: list[dict]) -> str:
    if not chunks:
        return "(Nenhum contexto regulatório recuperado)"
    limite = 4
    texto = "\n".join(
        f"- [{c.get('fonte', '?')}] {c.get('titulo', '')}: {c.get('conteudo', '')[:300]}"
        for c in chunks[:limite]
    )
    if len(chunks) > limite:
        texto += f"\n(Exibindo {limite} de {len(chunks)} trechos recuperados.)"
    return texto

# ---------------------------------------------------------------------------
# Helper para formatação de valores quando usamos o plano B (fallback)
# ---------------------------------------------------------------------------
_NOMES_COLUNAS = {
    "municipio": "Município",
    "bairro": "Bairro",
    "classe": "Classe",
    "ano": "Ano",
    "mes": "Mês",
    "alimentador": "Alimentador",
    # outros nomes podem ser adicionados conforme necessidade
}

_COLUNAS_SEM_SEPARADOR = {"ano", "mes", "mês", "competencia"}

def _numero_br(valor: float, casas: int) -> str:
    """Formata número no padrão brasileiro (ponto milhar, vírgula decimal)."""
    return f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")

def _formatar_valor(chave: str, valor: Any) -> str:
    c = chave.lower()
    if valor is None:
        return "sem valor"
    # valores booleanos ou não numéricos são devolvidos como string simples
    if isinstance(valor, bool) or not isinstance(valor, (int, float, Decimal)):
        return str(valor)
    # colunas que não precisam de separador de milhar
    if c in _COLUNAS_SEM_SEPARADOR or c.startswith(("id_", "cod")):
        return str(int(valor)) if float(valor) == int(valor) else str(valor)
    # valores monetários ou de faturamento
    if any(p in c for p in ("receita", "faturamento", "fatura", "valor", "preco", "preço")):
        return f"R$ {_numero_br(float(valor), 2)}"
    # kilowatt‑hour
    if "kwh" in c:
        return f"{_numero_br(float(valor), 0)} kWh"
    # percentuais
    if "pct" in c or "percentual" in c:
        return f"{_numero_br(float(valor), 1)}%"
    # demais números – se for inteiro, sem casas decimais; caso contrário, duas casas
    inteiro = isinstance(valor, int) or float(valor) == int(valor)
    return _numero_br(float(valor), 0 if inteiro else 2)


def _gerar_resposta_mock(dados: list[dict], pergunta: str) -> str:
    """Fallback legível quando o modo mock está ativo.
    Usa nomes de coluna amigáveis e formatação brasileira para valores monetários.
    Também inclui um pequeno preâmbulo que referencia a pergunta original,
    para deixar a resposta mais natural.
    """
    if not dados:
        return "Não há dados disponíveis para responder a esta pergunta no momento."
    # Preâmbulo: reutiliza a própria pergunta (sem o ponto final) como introdução.
    preambulo = f"Conforme solicitado, {pergunta.rstrip('?').capitalize()}: "
    primeiros = dados[0]
    partes = [
        f"{_NOMES_COLUNAS.get(k.lower(), k.replace('_', ' ').capitalize())}: {_formatar_valor(k, v)}"
        for k, v in list(primeiros.items())[:6]
    ]
    corpo = "; ".join(partes) + "."
    if len(dados) > 1:
        corpo += f" (primeira de {len(dados)} linhas retornadas)"
    return preambulo + corpo


def _gerar_resposta_rag_mock(chunks: list[dict]) -> str:
    """Fallback determinístico baseado exclusivamente no primeiro trecho recuperado."""
    if not chunks:
        return MENSAGENS_RECUSA["sem_dados"]
    chunk = chunks[0]
    fonte = chunk.get("fonte", "fonte não informada")
    return f"{chunk.get('conteudo', '')}\n\nFonte: {fonte}"


def no_sintetiza_resposta(
    state: EstadoAgente,
    llm: ClienteLLM,
) -> Dict[str, Any]:
    """
    Narra os dados do SQL em linguagem executiva clara.
    Controla estritamente a separação entre dados numéricos (SQL) e conhecimento textual (RAG).
    """
    dados_sql = state.get("dados_sql") or []
    contexto_rag = state.get("contexto_rag") or []
    pergunta = state.get("pergunta_autonoma") or state.get("pergunta_original", "")
    rota = state.get("rota") or ("sql" if dados_sql else "rag")

    if rota == "rag" and not contexto_rag:
        return {
            "texto_resposta": MENSAGENS_RECUSA["sem_dados"],
            "fontes_citadas": [],
            "selo_confianca": "recusa_honesta",
            "motivo_recusa": "sem_dados",
            "passos_executados": [
                "Nó 11 — RAG sem contexto; recusa honesta emitida sem chamar o LLM."
            ],
        }

    dados_texto = _formatar_dados_sql(dados_sql)
    rag_texto = _formatar_contexto_rag(contexto_rag)

    prompt = (
        f"Pergunta do usuário: {pergunta}\n\n"
        f"<DADOS_SQL>\n{dados_texto}\n</DADOS_SQL>\n\n"
        f"<CONTEXTO_RAG>\n{rag_texto}\n</CONTEXTO_RAG>\n\n"
        "Escreva a resposta para a diretoria:"
    )

    resposta_mock = _gerar_resposta_mock(dados_sql, pergunta)

    system_prompt = (
        SYSTEM_PROMPT_SINTESE_RAG if rota == "rag" else SYSTEM_PROMPT_SINTESE
    )

    fatos = (
        dados_sql + [{"pergunta": pergunta}]
        if rota in ("sql", "ambos")
        else contexto_rag + [{"pergunta": pergunta}]
    )

    try:
        resposta = llm.invoke(
            prompt=prompt,
            system_prompt=system_prompt,
            temperatura=0.3,
            resposta_mock=resposta_mock,
        )
        chamadas_llm = state.get("chamadas_llm", 0) + 1
        tokens_prompt = state.get("tokens_prompt", 0) + resposta.tokens_prompt
        tokens_resposta_acc = state.get("tokens_resposta", 0) + resposta.tokens_resposta
        resposta_texto = resposta.texto
        passo_conferencia = "Nó 11 — Conferência numérica aprovada."
        if not conferir(fatos, resposta_texto):
            resposta_texto = (
                _gerar_resposta_mock(dados_sql, pergunta)
                if rota in ("sql", "ambos")
                else _gerar_resposta_rag_mock(contexto_rag)
            )
            passo_conferencia = (
                "Nó 11 — Conferência numérica reprovada; resposta determinística utilizada."
            )
    except ErroLLMIndisponivel:
        logger.warning("Nó 11 — LLM indisponível; resposta determinística utilizada.")
        chamadas_llm = state.get("chamadas_llm", 0)
        tokens_prompt = state.get("tokens_prompt", 0)
        tokens_resposta_acc = state.get("tokens_resposta", 0)
        resposta_texto = (
            _gerar_resposta_mock(dados_sql, pergunta)
            if rota in ("sql", "ambos")
            else _gerar_resposta_rag_mock(contexto_rag)
        )
        passo_conferencia = "Nó 11 — LLM indisponível; resposta determinística."

    motivo_recusa = None
    if rota in ("sql", "ambos") and not dados_sql:
        resposta_texto = MENSAGENS_RECUSA["sem_dados"]
        passo_conferencia = "Nó 11 — SQL sem linhas; resposta de ausência de dados emitida."
        selo = "recusa_honesta"
        motivo_recusa = "sem_dados"
    else:
        hit_cache = state.get("hit_cache", False)
        if hit_cache:
            selo = "certificada"
        elif rota in ("sql", "ambos"):
            selo = "gerada_confiavel"
        else:
            selo = "documental_rag"

    fontes = list({c.get("fonte", "") for c in contexto_rag if c.get("fonte")})

    logger.info("Nó 11 — Síntese concluída. Selo: %s | Fontes: %s", selo, fontes)

    resultado = {
        "texto_resposta": resposta_texto,
        "fontes_citadas": fontes,
        "selo_confianca": selo,
        "chamadas_llm": chamadas_llm,
        "tokens_prompt": tokens_prompt,
        "tokens_resposta": tokens_resposta_acc,
        "passos_executados": [
            f"Nó 11 — Síntese gerada. Selo: {selo}. {len(dados_sql)} linha(s) de dados utilizadas.",
            passo_conferencia,
        ],
    }
    if motivo_recusa:
        resultado["motivo_recusa"] = motivo_recusa

    return resultado
