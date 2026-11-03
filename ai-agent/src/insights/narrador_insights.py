"""Narração executiva dos fatos extraídos, sem cálculo livre pelo LLM."""
from __future__ import annotations

import json
from typing import Any, Dict

from ..provedores.cliente_llm import ClienteLLM


def narrar_insight(
    tela: str,
    fatos: list[Dict[str, Any]],
    llm: ClienteLLM,
) -> str:
    prompt = (
        f"Tela: {tela}\nFATOS_JSON:\n{json.dumps(fatos, ensure_ascii=False, default=str)}\n"
        "Escreva uma frase executiva em português. Preserve exatamente todos os números presentes nos fatos e não invente nenhum. Se houver campos de variação percentual, use o sinal do valor para dizer se foi alta ou queda, e escreva o percentual sem sinal (ex.: 'queda de 4%')."
    )
    resposta = llm.invoke(
        prompt=prompt,
        system_prompt=(
            "Você narra métricas de uma distribuidora. Não faça cálculos nem crie números. "
            "Se não houver fatos, informe que não há dados disponíveis."
        ),
        temperatura=0.2,
        resposta_mock=_fallback(fatos),
    )
    return resposta.texto.strip() or _fallback(fatos)


def _fallback(fatos: list[Dict[str, Any]]) -> str:
    if not fatos:
        return "Não há dados disponíveis para este insight no momento."
    primeiro = fatos[0]
    resumo = ", ".join(f"{chave}: {valor}" for chave, valor in list(primeiro.items())[:3])
    return f"Dados recentes da tela: {resumo}."
