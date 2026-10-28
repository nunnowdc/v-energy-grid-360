"""
Nó 3: Verificação de Escopo — restringe o agente à concessão e dados da V-Energy Grid 360.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict

from ..contratos.estado_agente import EstadoAgente
from ..provedores.cliente_llm import ClienteLLM, ErroLLMIndisponivel

logger = logging.getLogger("venergy.no_checa_escopo")

# ────────────────────────────────────────────────────────────────────────────────
# Entidades dentro do escopo (heurística rápida — zero custo de LLM)
# ────────────────────────────────────────────────────────────────────────────────
MUNICIPIOS_CONCESSAO = {
    "recife", "olinda", "jaboatão", "jaboatao", "paulista", "camaragibe",
    "caruaru", "cabo de santo agostinho", "cabo", "moreno", "igarassu",
    "itamaracá", "itamaraca", "araçoiaba", "aracoiaba", "são lourenço",
    "sao lourenco", "paudalho", "abreu e lima",
}

TERMOS_NEGOCIO_VENERGY = {
    # Faturamento e consumo
    "faturamento", "receita", "consumo", "kwh", "tarifa", "bandeira",
    "conta de luz", "conta", "fatura", "pagamento", "inadimplência", "inadimplencia",
    # Rede e continuidade
    "uc", "ucs", "unidade consumidora", "alimentador", "subestação", "subestacao",
    "dec", "fec", "ocorrência", "ocorrencia", "ocorrências", "ocorrencias",
    "interrupção", "interrupcao", "interrupções", "interrupcoes",
    "falta de luz", "queda de energia", "corte", "religação", "religacao",
    # Regulação
    "aneel", "prodist", "bandeira tarifária", "bandeira tarifaria",
    "geração distribuída", "geracao distribuida", "gd", "minigeração",
    "perda", "desvio", "gato", "fraude", "inspeção", "inspecao",
    # Operacional
    "atendimento", "chamado", "reclamação", "reclamacao", "classe residencial",
    "classe comercial", "classe industrial", "subgrupo", "b1", "b3", "a4",
    "v-energy", "venergy", "distribuidora",
}

# Termos que indicam fora de escopo (sem qualquer relação com energia elétrica da concessão)
_TERMOS_FORA_ESCOPO_IMEDIATO = re.compile(
    r"""
    \b(
        futebol | jogo | copa | partida | resultado\s+d[oa]\s+jogo |
        rentabilidade\s+d[oa]\s+(bolsa|ação|açao) | stock\s+market |
        enel | cpfl | celpe\s+(fora) | cemig | coelba | energisa |
        receita\s+federal | imposto\s+de\s+renda | declaração\s+de\s+ir |
        presidente | governo | eleição | eleicao | congresso |
        salário\s+mínimo | salario\s+minimo |
        (rio\s+de\s+janeiro|são\s+paulo|salvador|fortaleza|maceió|natal)\s+(?!.*(v.energy|venergy|alimentador))
    )\b
    """,
    re.IGNORECASE | re.VERBOSE,
)
_TERMOS_FORA_ESCOPO_CLIMA = re.compile(
    r"\b(clima|temperatura|previsão\s+do\s+tempo|chuva|seca)\b",
    re.IGNORECASE,
)


def _contem_termo(texto: str, termo: str) -> bool:
    """Verifica um termo completo, sem casar apenas parte de outra palavra."""
    return re.search(rf"\b{re.escape(termo)}\b", texto, re.IGNORECASE) is not None

SYSTEM_PROMPT_ESCOPO = """
Você é um classificador de escopo para a distribuidora de energia V-Energy Grid 360.

TAREFA: Determine se a pergunta é sobre os dados operacionais, regulatórios ou comerciais
da distribuidora V-Energy na concessão da Região Metropolitana do Recife (14 municípios de PE).

Responda EXCLUSIVAMENTE com um dos dois textos abaixo:
- DENTRO_ESCOPO
- FORA_ESCOPO: <motivo em até 10 palavras>

EXEMPLOS:
- "Qual o consumo em Olinda em 2024?" → DENTRO_ESCOPO
- "Quantas UCs têm geração solar?" → DENTRO_ESCOPO
- "Qual a previsão do tempo para Recife?" → FORA_ESCOPO: Informação meteorológica não operacional
- "Qual a receita da Enel no Rio de Janeiro?" → FORA_ESCOPO: Empresa e local fora da concessão
""".strip()


def no_checa_escopo(
    state: EstadoAgente,
    llm: ClienteLLM,
) -> Dict[str, Any]:
    """
    Verifica se a pergunta autônoma está dentro do escopo da V-Energy.
    Usa heurística rápida antes de acionar o LLM para economizar chamadas.
    """
    pergunta = state.get("pergunta_autonoma") or state.get("pergunta_original", "")
    pergunta_lower = pergunta.lower()

    # ── 1. Rejeição heurística rápida: zero custo de LLM ──
    if _TERMOS_FORA_ESCOPO_IMEDIATO.search(pergunta_lower):
        logger.info("Nó 3 — Fora de escopo (heurística): %s", pergunta[:80])
        return {
            "dentro_escopo": False,
            "rota": "fora_escopo",
            "motivo_fora_escopo": "Pergunta detectada como fora do escopo operacional da V-Energy (heurística local).",
            "passos_executados": ["Nó 3 — Escopo: reprovado por heurística rápida (sem custo de LLM)."],
        }

    # ── 2. Aprovação heurística rápida: termos-chave de negócio da V-Energy ──
    encontrou_termo = any(_contem_termo(pergunta_lower, t) for t in TERMOS_NEGOCIO_VENERGY)
    encontrou_municipio = any(_contem_termo(pergunta_lower, m) for m in MUNICIPIOS_CONCESSAO)

    if _TERMOS_FORA_ESCOPO_CLIMA.search(pergunta_lower) and not encontrou_termo:
        logger.info("Nó 3 — Fora de escopo (clima sem termo de negócio): %s", pergunta[:80])
        return {
            "dentro_escopo": False,
            "rota": "fora_escopo",
            "motivo_fora_escopo": "Pergunta meteorológica sem relação com operação da V-Energy.",
            "passos_executados": ["Nó 3 — Escopo: clima sem termo de negócio (sem custo de LLM)."],
        }

    if encontrou_termo or encontrou_municipio:
        logger.debug("Nó 3 — Dentro do escopo (heurística positiva).")
        return {
            "dentro_escopo": True,
            "passos_executados": ["Nó 3 — Escopo: aprovado por heurística rápida (sem custo de LLM)."],
        }

    # ── 3. Classificação via LLM para casos ambíguos ──
    try:
        resposta = llm.invoke(
            prompt=f"Pergunta: {pergunta}",
            system_prompt=SYSTEM_PROMPT_ESCOPO,
            temperatura=0.0,
            resposta_mock="DENTRO_ESCOPO",
        )
    except ErroLLMIndisponivel:
        logger.warning("Nó 3 — LLM indisponível na checagem de escopo. Falha fechada (recusa).")
        return {
            "dentro_escopo": False,
            "rota": "recusa",
            "motivo_fora_escopo": "Serviço de IA temporariamente indisponível.",
            "motivo_recusa": "llm_indisponivel",
            "passos_executados": [
                "Nó 3 — Escopo: LLM indisponível; falha fechada com recusa honesta."
            ],
        }

    chamadas_llm = state.get("chamadas_llm", 0) + 1
    tokens_prompt = state.get("tokens_prompt", 0) + resposta.tokens_prompt
    tokens_resposta = state.get("tokens_resposta", 0) + resposta.tokens_resposta

    texto = resposta.texto.strip().upper()
    dentro = texto.startswith("DENTRO_ESCOPO")

    motivo = None
    if not dentro:
        partes = resposta.texto.strip().split(":", 1)
        motivo = partes[1].strip() if len(partes) > 1 else "Fora do escopo da concessão V-Energy."

    logger.info("Nó 3 — Escopo LLM: %s | Motivo: %s", "DENTRO" if dentro else "FORA", motivo)

    return {
        "dentro_escopo": dentro,
        "rota": "fora_escopo" if not dentro else state.get("rota", "sql"),
        "motivo_fora_escopo": motivo,
        "chamadas_llm": chamadas_llm,
        "tokens_prompt": tokens_prompt,
        "tokens_resposta": tokens_resposta,
        "passos_executados": [
            f"Nó 3 — Escopo LLM: {'dentro' if dentro else f'fora ({motivo})'}"
        ],
    }


def rota_pos_escopo(state: EstadoAgente) -> str:
    """Roteamento condicional após a verificação de escopo."""
    if not state.get("dentro_escopo", True):
        return "fora_escopo"
    return "dentro_escopo"
