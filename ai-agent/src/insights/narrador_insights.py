"""Narração executiva dos fatos extraídos, sem cálculo livre pelo LLM."""
from __future__ import annotations

import json
from typing import Any, Dict

from ..provedores.cliente_llm import ClienteLLM


def gerar_texto_modelo(tela: str, fatos: list[Dict[str, Any]]) -> str:
    if not fatos:
        return "Não há dados disponíveis para este insight no momento."
    primeiro = fatos[0]
    if tela == "visao_360_uc":
        comp = primeiro.get("competencia", "")
        kwh = primeiro.get("consumo_kwh", 0)
        try:
            kwh_str = f"{int(float(kwh)):,}".replace(",", ".")
        except Exception:
            kwh_str = str(kwh)
        rec = primeiro.get("receita_faturada", 0)
        try:
            rec_str = f"{float(rec):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except Exception:
            rec_str = str(rec)
        return f"Em {comp} a UC consumiu {kwh_str} kWh e a conta foi de R$ {rec_str}."
    else:
        resumo = ", ".join(f"{k}: {v}" for k, v in list(primeiro.items())[:3])
        return f"Dados recentes da tela: {resumo}."


def narrar_insight(
    tela: str,
    fatos: list[Dict[str, Any]],
    llm: ClienteLLM,
) -> str:
    prompt = (
        f"Tela: {tela}\nFATOS_JSON:\n{json.dumps(fatos, ensure_ascii=False, default=str)}\n"
        "Escreva uma frase executiva em português. Preserve os mesmos valores, no formato brasileiro (ex.: 'R$ 388,85', '427 kWh', '1,6%'), use 'valor da conta' em vez de 'receita faturada' e não invente nenhum número. Se houver campos de variação percentual, use o sinal do valor para dizer se foi alta ou queda, e escreva o percentual sem sinal (ex.: 'queda de 4%')."
    )
    resposta = llm.invoke(
        prompt=prompt,
        system_prompt=(
            "Você narra métricas de uma distribuidora. Não faça cálculos nem crie números. "
            "Se não houver fatos, informe que não há dados disponíveis."
        ),
        temperatura=0.2,
        resposta_mock=gerar_texto_modelo(tela, fatos),
    )
    return resposta.texto.strip() or gerar_texto_modelo(tela, fatos)


def _fallback(fatos: list[Dict[str, Any]]) -> str:
    return gerar_texto_modelo("visao_360_uc", fatos)
