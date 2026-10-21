"""
Cliente unificado de LLM com suporte a OpenRouter (primário), 9router (fallback) e modo Mock.
"""
from __future__ import annotations

import logging
import os
import time
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
        self.openrouter_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1/chat/completions").strip()
        
        self.ninerouter_key = os.getenv("NINEROUTER_API_KEY", "").strip()
        self.ninerouter_url = os.getenv("NINEROUTER_BASE_URL", "https://api.9router.com/v1/chat/completions").strip()

        # Modelos configuráveis (default para o melhor Gemini Flash disponível)
        self.modelo_primario = (
            modelo_primario
            or os.getenv("MODELO_LLM_PRIMARIO", "google/gemini-2.5-flash-lite")
        )
        self.modelo_fallback = (
            modelo_fallback
            or os.getenv("MODELO_LLM_FALLBACK", "google/gemini-2.5-flash-lite")
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
        }

        with httpx.Client(timeout=self.timeout) as client:
            res = client.post(url, json=payload, headers=headers)
            res.raise_for_status()
            data = res.json()

            escolha = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            return RespostaLLM(
                texto=escolha.strip(),
                tokens_prompt=usage.get("prompt_tokens", 0),
                tokens_resposta=usage.get("completion_tokens", 0),
            )
