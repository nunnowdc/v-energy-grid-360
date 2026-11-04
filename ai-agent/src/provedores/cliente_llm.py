"""
Cliente unificado de LLM com suporte a OpenRouter (primário), 9router (fallback) e modo Mock.
Inclui retentativas automáticas, tolerância a falhas transitórias e limpeza de raciocínio.
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import httpx
from pydantic import BaseModel

logger = logging.getLogger("venergy.cliente_llm")


def remover_raciocinio(texto: str) -> str:
    """Remove blocos <think>...</think> gerados por modelos de raciocínio."""
    if not texto:
        return ""
    return re.sub(r"<think>.*?</think>", "", texto, flags=re.DOTALL).strip()


class ErroLLMIndisponivel(RuntimeError):
    """Exceção levantada quando os provedores de LLM estão indisponíveis ou não configurados."""
    pass


class ErroHTTPProvedor(RuntimeError):
    """Exceção levantada quando uma chamada HTTP a provedor falha."""
    def __init__(self, status_code: int, texto: str, retry_after: Optional[float] = None):
        self.status_code = status_code
        self.retry_after = retry_after
        super().__init__(f"HTTP {status_code}: {texto[:300]}")


class RespostaLLM(BaseModel):
    texto: str
    tokens_prompt: int = 0
    tokens_resposta: int = 0
    provedor_utilizado: str = "mock"
    latencia_ms: float = 0.0


def _ler_resposta(data: Dict[str, Any]) -> str:
    """Extrai o texto da resposta do payload JSON com validação segura de campos."""
    if "error" in data:
        raise RuntimeError(f"Erro da API do provedor: {data['error']}")
    choices = data.get("choices")
    if not choices or not isinstance(choices, list) or len(choices) == 0:
        raise RuntimeError("Resposta sem 'choices'")
    primeira = choices[0]
    finish_reason = primeira.get("finish_reason")
    msg = primeira.get("message") or {}
    content = msg.get("content")
    if content is None or not str(content).strip():
        motivo = f" (finish_reason={finish_reason})" if finish_reason else ""
        raise RuntimeError(f"resposta sem texto{motivo}")
    return remover_raciocinio(str(content))


class ClienteLLM:
    """
    Gerencia chamadas aos provedores com fallback automático, retry com backoff e circuit breaker.
    """

    def __init__(
        self,
        modelo_primario: Optional[str] = None,
        modelo_fallback: Optional[str] = None,
        timeout_segundos: Optional[float] = None,
        transport: Optional[httpx.BaseTransport] = None,
    ):
        env_timeout = os.getenv("LLM_TIMEOUT_SEGUNDOS")
        if timeout_segundos is not None:
            self.timeout = float(timeout_segundos)
        elif env_timeout is not None and env_timeout.strip():
            try:
                self.timeout = float(env_timeout)
            except ValueError:
                self.timeout = 90.0
        else:
            self.timeout = 90.0

        # Número de tentativas por provedor (padrão 3; 1 desliga retry)
        env_tentativas = os.getenv("LLM_TENTATIVAS")
        if env_tentativas is not None and env_tentativas.strip():
            try:
                self.tentativas = max(1, int(env_tentativas))
            except ValueError:
                self.tentativas = 3
        else:
            self.tentativas = 3

        self._transport = transport

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

        # Modelos configuráveis
        self.modelo_primario = (
            modelo_primario
            or os.getenv("MODELO_LLM_PRIMARIO")
        )
        self.modelo_fallback = (
            modelo_fallback
            or os.getenv("MODELO_LLM_FALLBACK")
            or self.modelo_primario
        )

        # Checagens e avisos sobre modelos e fallback
        if self.openrouter_key and not self.modelo_primario:
            logger.warning("OPENROUTER_API_KEY configurada, mas MODELO_LLM_PRIMARIO está vazio.")

        if self.ninerouter_key and not self.modelo_fallback:
            logger.warning("NINEROUTER_API_KEY configurada, mas nenhum modelo disponível.")

        if self.openrouter_key and self.ninerouter_key and not os.getenv("MODELO_LLM_FALLBACK"):
            logger.warning(
                "Aviso: OPENROUTER_API_KEY e NINEROUTER_API_KEY configuradas, mas MODELO_LLM_FALLBACK "
                "está vazio. O 9router usará MODELO_LLM_PRIMARIO, o que pode falhar se os nomes divergirem."
            )

        # Modo Mock (ativado exclusivamente quando LLM_MOCK_MODE=true)
        self.forcar_mock = os.getenv("LLM_MOCK_MODE", "false").lower() in ("true", "1")

    def invoke(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperatura: float = 0.0,
        resposta_mock: Optional[str] = None,
    ) -> RespostaLLM:
        """
        Executa chamada ao LLM tentando OpenRouter -> 9router com retentativas.
        Mock é utilizado exclusivamente quando LLM_MOCK_MODE=true.
        """
        inicio = time.time()

        if self.forcar_mock:
            texto = resposta_mock or "RESPOSTA MOCK DO AGENTE (Modo Mock ativo)."
            return RespostaLLM(
                texto=texto,
                tokens_prompt=len(prompt.split()),
                tokens_resposta=len(texto.split()),
                provedor_utilizado="mock_local",
                latencia_ms=(time.time() - inicio) * 1000,
            )

        if not self.openrouter_key and not self.ninerouter_key:
            raise ErroLLMIndisponivel("nenhuma chave de provedor configurada")

        mensagens = []
        if system_prompt:
            mensagens.append({"role": "system", "content": system_prompt})
        mensagens.append({"role": "user", "content": prompt})

        ultimo_erro: Optional[Exception] = None

        # 1. Tentativa Primária: OpenRouter
        if self.openrouter_key:
            if not self.modelo_primario:
                ultimo_erro = RuntimeError("OpenRouter ignorado: chave configurada, mas sem modelo definido.")
            else:
                try:
                    resp = self._chamar_com_novas_tentativas(
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
                    ultimo_erro = e
                    logger.warning("Falha na chamada ao OpenRouter: %s. Tentando 9router...", e)

        # 2. Tentativa Fallback: 9router
        if self.ninerouter_key:
            if not self.modelo_fallback:
                ultimo_erro = RuntimeError("9router ignorado: chave configurada, mas sem modelo definido.")
            else:
                try:
                    resp = self._chamar_com_novas_tentativas(
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
                    ultimo_erro = e
                    logger.error("Falha na chamada ao 9router (fallback): %s", e)

        erro_detalhe = f": {ultimo_erro}" if ultimo_erro else ""
        raise ErroLLMIndisponivel(f"Todos os provedores de LLM falharam{erro_detalhe}")

    def _chamar_com_novas_tentativas(
        self,
        url: str,
        api_key: str,
        modelo: str,
        mensagens: List[Dict[str, str]],
        temperatura: float,
    ) -> RespostaLLM:
        """Executa chamadas com retry e backoff exponencial em erros transitórios."""
        for tentativa in range(1, self.tentativas + 1):
            try:
                return self._chamar_api(
                    url=url,
                    api_key=api_key,
                    modelo=modelo,
                    mensagens=mensagens,
                    temperatura=temperatura,
                )
            except Exception as e:
                if tentativa >= self.tentativas:
                    raise

                # Não repete timeout de leitura
                if isinstance(e, httpx.ReadTimeout):
                    raise

                deve_repetir = False
                tempo_espera = min(float(2 ** (tentativa - 1)), 5.0)

                if isinstance(e, (httpx.ConnectError, httpx.RemoteProtocolError, httpx.ConnectTimeout)):
                    deve_repetir = True
                elif isinstance(e, ErroHTTPProvedor):
                    if e.status_code in (429, 500, 502, 503, 504):
                        deve_repetir = True
                        if e.retry_after is not None and e.retry_after > 0:
                            tempo_espera = min(e.retry_after, 5.0)
                elif isinstance(e, RuntimeError):
                    m = re.search(r"HTTP (\d{3})", str(e))
                    if m and int(m.group(1)) in (429, 500, 502, 503, 504):
                        deve_repetir = True

                if not deve_repetir:
                    raise

                logger.warning(
                    "Tentativa %d de %d falhou (%s). Aguardando %.1fs antes de tentar novamente...",
                    tentativa, self.tentativas, e, tempo_espera,
                )
                time.sleep(tempo_espera)

        raise RuntimeError("Número máximo de tentativas excedido.")

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

        with httpx.Client(timeout=self.timeout, transport=self._transport) as client:
            res = client.post(url, json=payload, headers=headers)
            if res.is_error:
                retry_header = res.headers.get("Retry-After")
                retry_after = None
                if retry_header:
                    try:
                        retry_after = float(retry_header)
                    except ValueError:
                        pass
                raise ErroHTTPProvedor(res.status_code, res.text, retry_after=retry_after)

            tipo = res.headers.get("content-type", "")
            if "text/event-stream" in tipo:
                return self._parse_sse(res.text)

            data = res.json()
            texto = _ler_resposta(data)
            usage = data.get("usage") or {}
            return RespostaLLM(
                texto=texto,
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

            try:
                pedaco = json.loads(bruto)
            except Exception:
                continue

            if pedaco.get("usage"):
                usage = pedaco["usage"]

            for escolha in pedaco.get("choices", []):
                trecho = escolha.get("delta", {}).get("content")
                if trecho:
                    partes.append(trecho)

        texto_completo = "".join(partes).strip()
        texto_limpo = remover_raciocinio(texto_completo)
        if not texto_limpo:
            raise RuntimeError("resposta sem texto (stream vazio)")

        return RespostaLLM(
            texto=texto_limpo,
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
