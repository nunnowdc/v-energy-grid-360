"""
Cliente unificado de LLM com suporte a OpenRouter (primário), 9router (fallback) e modo Mock.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import httpx
from pydantic import BaseModel

logger = logging.getLogger("venergy.cliente_llm")


class RespostaLLM(BaseModel):
    texto: str
    tokens_prompt: int = 0
    tokens_resposta: int = 0
    provedor_utilizado: str = "mock"
    latencia_ms: float = 0.0


class ClienteLLM:
    """
    Gerencia chamadas aos provedores com fallback automático e circuit breaker.
    """

    def __init__(
        self,
        modelo_primario: Optional[str] = None,
        modelo_fallback: Optional[str] = None,
        timeout_segundos: float = 12.0,
    ):
        self.timeout = timeout_segundos
        
        # Chaves de API e URLs base
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        self.openrouter_url = os.getenv(
            "OPENROUTER_BASE_URL",
            "https://openrouter.ai/api/v1/chat/completions",
        ).strip()
        
        self.ninerouter_key = os.getenv("NINEROUTER_API_KEY", "").strip()
        self.ninerouter_url = os.getenv(
            "NINEROUTER_BASE_URL",
            "https://api.9router.com/v1/chat/completions",
        ).strip()

        # Modelos configuráveis (default para o melhor Gemini Flash disponível)
        self.modelo_primario = (
            modelo_primario
            or os.getenv("MODELO_LLM_PRIMARIO")
        )
        self.modelo_fallback = (
            modelo_fallback
            or os.getenv("MODELO_LLM_FALLBACK")
            or self.modelo_primario
        )

        # Modo Mock (ativado se explicitamente pedido ou se não houver chaves válidas)
        self.forcar_mock = os.getenv("LLM_MOCK_MODE", "false").lower() in ("true", "1")

    def invoke(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperatura: float = 0.0,
        resposta_mock: Optional[str] = None,
    ) -> RespostaLLM:
        """
        Executa chamada ao LLM tentando OpenRouter -> 9router -> Mock.
        """
        inicio = time.time()

        if self.forcar_mock or (not self.openrouter_key and not self.ninerouter_key):
            texto = resposta_mock or "RESPOSTA MOCK DO AGENTE (Sem chaves de API configuradas)."
            return RespostaLLM(
                texto=texto,
                tokens_prompt=len(prompt.split()),
                tokens_resposta=len(texto.split()),
                provedor_utilizado="mock_local",
                latencia_ms=(time.time() - inicio) * 1000,
            )

        mensagens = []
        if system_prompt:
            mensagens.append({"role": "system", "content": system_prompt})
        mensagens.append({"role": "user", "content": prompt})

        # 1. Tentativa Primária: OpenRouter
        if self.openrouter_key:
            try:
                resp = self._chamar_api(
                    url=self.openrouter_url,
                    api_key=self.openrouter_key,
                    modelo=self.modelo_primario,
                    mensagens=mensagens,
                    temperatura=temperatura,
                )
                resp.provedor_utilizado = "openrouter"
                resp.latencia_ms = (time.time() - inicio) * 1000
                return resp
            except Exception as e:
                logger.warning("Falha na chamada ao OpenRouter: %s. Tentando 9router...", e)

        # 2. Tentativa Fallback: 9router
        if self.ninerouter_key:
            try:
                resp = self._chamar_api(
                    url=self.ninerouter_url,
                    api_key=self.ninerouter_key,
                    modelo=self.modelo_fallback,
                    mensagens=mensagens,
                    temperatura=temperatura,
                )
                resp.provedor_utilizado = "9router"
                resp.latencia_ms = (time.time() - inicio) * 1000
                return resp
            except Exception as e:
                logger.error("Falha na chamada ao 9router (fallback): %s", e)

        # 3. Fallback de Emergência
        if resposta_mock:
            return RespostaLLM(
                texto=resposta_mock,
                tokens_prompt=len(prompt.split()),
                tokens_resposta=len(resposta_mock.split()),
                provedor_utilizado="mock_fallback_emergencia",
                latencia_ms=(time.time() - inicio) * 1000,
            )

        raise RuntimeError("Todos os provedores de LLM falharam e nenhuma resposta mock foi fornecida.")

    def _chamar_api(
        self,
        url: str,
        api_key: str,
        modelo: str,
        mensagens: List[Dict[str, str]],
        temperatura: float,
    ) -> RespostaLLM:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://v-energy-grid-360.internal",
            "X-Title": "V-Energy Grid 360 Agent",
        }
        payload = {
            "model": modelo,
            "messages": mensagens,
            "temperature": temperatura,
            "stream": False,
        }

        with httpx.Client(timeout=self.timeout) as client:
            res = client.post(url, json=payload, headers=headers)
            if res.is_error:
                raise RuntimeError(f"HTTP {res.status_code}: {res.text[:300]}")

            tipo = res.headers.get("content-type", "")
            if "text/event-stream" in tipo:
                return self._parse_sse(res.text)

            data = res.json()

            escolha = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            return RespostaLLM(
                texto=escolha.strip(),
                tokens_prompt=usage.get("prompt_tokens", 0),
                tokens_resposta=usage.get("completion_tokens", 0),
            )

    @staticmethod
    def _parse_sse(corpo: str) -> RespostaLLM:
        partes: List[str] = []
        usage: Dict[str, Any] = {}

        for linha in corpo.splitlines():
            if not linha.startswith("data:"):
                continue

            bruto = linha[5:].strip()
            if not bruto or bruto == "[DONE]":
                continue

            pedaco = json.loads(bruto)
            if pedaco.get("usage"):
                usage = pedaco["usage"]

            for escolha in pedaco.get("choices", []):
                trecho = escolha.get("delta", {}).get("content")
                if trecho:
                    partes.append(trecho)

        return RespostaLLM(
            texto="".join(partes).strip(),
            tokens_prompt=usage.get("prompt_tokens", 0),
            tokens_resposta=usage.get("completion_tokens", 0),
        )


def _testar_conexao_llm() -> int:
    """Executa uma chamada real para validar provedor, chave e modelo configurados."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        print("Erro: instale a dependência python-dotenv.")
        return 1

    raiz_projeto = Path(__file__).resolve().parents[3]
    arquivo_env = raiz_projeto / ".env"
    load_dotenv(arquivo_env)

    cliente = ClienteLLM(timeout_segundos=30.0)
    print(f"Arquivo .env: {arquivo_env}")
    print(f"Modelo primário: {cliente.modelo_primario}")
    print(f"Modelo fallback: {cliente.modelo_fallback}")
    print(f"OpenRouter configurado: {bool(cliente.openrouter_key)}")
    print(f"9router configurado: {bool(cliente.ninerouter_key)}")

    if not cliente.openrouter_key and not cliente.ninerouter_key:
        print("Erro: nenhuma chave de provedor foi configurada.")
        return 1

    try:
        resposta = cliente.invoke(
            prompt="Responda apenas com: conexão funcionando.",
            system_prompt="Você está sendo usado em um teste de conectividade.",
            temperatura=0.0,
        )
    except Exception as erro:
        print(f"Falha na chamada ao provedor: {erro}")
        return 1

    print("\nConexão com o provedor realizada com sucesso.")
    print(f"Provedor utilizado: {resposta.provedor_utilizado}")
    print(f"Resposta: {resposta.texto}")
    print(f"Tokens: {resposta.tokens_prompt + resposta.tokens_resposta}")
    print(f"Latência: {resposta.latencia_ms:.1f} ms")
    return 0


if __name__ == "__main__":
    sys.exit(_testar_conexao_llm())
