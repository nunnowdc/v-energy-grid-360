"""
Testes unitários para o cliente LLM robusto, roteador semântico tolerante e conferente numérico.
Usa httpx.MockTransport para simular respostas da rede sem latência real.
"""
import json
import httpx
import pytest

from src.provedores.cliente_llm import (
    ClienteLLM,
    ErroHTTPProvedor,
    ErroLLMIndisponivel,
    remover_raciocinio,
    _ler_resposta,
)
from src.nos.no_roteador_consulta import _parsear_resposta_roteador
from src.insights.conferente_numerico import conferir, numeros_nao_encontrados


# ── 1. Testes de remover_raciocinio ──

def test_remover_raciocinio_sem_tags():
    assert remover_raciocinio("Texto normal") == "Texto normal"


def test_remover_raciocinio_com_think():
    bruto = "<think>Raciocínio interno aqui\ncom várias linhas</think>Resposta limpa."
    assert remover_raciocinio(bruto) == "Resposta limpa."


def test_remover_raciocinio_texto_vazio():
    assert remover_raciocinio("") == ""
    assert remover_raciocinio("<think>tudo em think</think>") == ""


# ── 2. Testes de _ler_resposta ──

def test_ler_resposta_sucesso():
    payload = {
        "choices": [{"message": {"content": "Olá mundo"}, "finish_reason": "stop"}]
    }
    assert _ler_resposta(payload) == "Olá mundo"


def test_ler_resposta_com_erro_no_corpo():
    payload = {"error": {"message": "Rate limit exceeded", "type": "rate_limit"}}
    with pytest.raises(RuntimeError, match="Erro da API do provedor"):
        _ler_resposta(payload)


def test_ler_resposta_sem_choices():
    with pytest.raises(RuntimeError, match="Resposta sem 'choices'"):
        _ler_resposta({})
    with pytest.raises(RuntimeError, match="Resposta sem 'choices'"):
        _ler_resposta({"choices": []})


def test_ler_resposta_content_null():
    payload = {
        "choices": [{"message": {"content": None}, "finish_reason": "content_filter"}]
    }
    with pytest.raises(RuntimeError, match=r"resposta sem texto \(finish_reason=content_filter\)"):
        _ler_resposta(payload)


def test_ler_resposta_content_espacos():
    payload = {
        "choices": [{"message": {"content": "   "}, "finish_reason": "stop"}]
    }
    with pytest.raises(RuntimeError, match="resposta sem texto"):
        _ler_resposta(payload)


def test_ler_resposta_limpa_think():
    payload = {
        "choices": [
            {
                "message": {"content": "<think>pensando...</think>SELECT * FROM gold;"},
                "finish_reason": "stop",
            }
        ]
    }
    assert _ler_resposta(payload) == "SELECT * FROM gold;"


# ── 3. Testes de Retentativas e MockTransport no ClienteLLM ──

def test_retry_em_429_com_sucesso():
    tentativas = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal tentativas
        tentativas += 1
        if tentativas == 1:
            return httpx.Response(429, headers={"Retry-After": "0.01"}, json={"error": "rate limit"})
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "sucesso após 429"}}], "usage": {}},
        )

    transport = httpx.MockTransport(handler)
    cliente = ClienteLLM(
        modelo_primario="mock-model",
        transport=transport,
    )
    cliente.openrouter_key = "test-key"

    resp = cliente.invoke("teste")
    assert resp.texto == "sucesso após 429"
    assert tentativas == 2


def test_retry_em_500_502_503_504():
    status_codes = [502, 503]
    chamadas = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal chamadas
        chamadas += 1
        if status_codes:
            return httpx.Response(status_codes.pop(0), text="Bad Gateway")
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "recuperado"}}]},
        )

    transport = httpx.MockTransport(handler)
    cliente = ClienteLLM(modelo_primario="mock-model", transport=transport)
    cliente.openrouter_key = "test-key"

    resp = cliente.invoke("teste")
    assert resp.texto == "recuperado"
    assert chamadas == 3


def test_nao_repete_em_400_401_404():
    chamadas = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal chamadas
        chamadas += 1
        return httpx.Response(404, json={"error": "model not found"})

    transport = httpx.MockTransport(handler)
    cliente = ClienteLLM(modelo_primario="mock-model", transport=transport)
    cliente.openrouter_key = "test-key"

    with pytest.raises(ErroLLMIndisponivel):
        cliente.invoke("teste")
    # Não deve ter retentado no mesmo provedor
    assert chamadas == 1


def test_nao_repete_timeout_de_leitura():
    chamadas = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal chamadas
        chamadas += 1
        raise httpx.ReadTimeout("Timeout de leitura")

    transport = httpx.MockTransport(handler)
    cliente = ClienteLLM(modelo_primario="mock-model", transport=transport)
    cliente.openrouter_key = "test-key"

    with pytest.raises(ErroLLMIndisponivel):
        cliente.invoke("teste")
    assert chamadas == 1


def test_fallback_para_segundo_provedor():
    chamadas_url = []

    def handler(request: httpx.Request) -> httpx.Response:
        chamadas_url.append(str(request.url))
        if "openrouter" in str(request.url):
            return httpx.Response(401, json={"error": "Unauthorized"})
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "resposta do 9router"}}]},
        )

    transport = httpx.MockTransport(handler)
    cliente = ClienteLLM(
        modelo_primario="model-primary",
        modelo_fallback="model-fallback",
        transport=transport,
    )
    cliente.openrouter_key = "or-key"
    cliente.ninerouter_key = "nine-key"

    resp = cliente.invoke("teste")
    assert resp.provedor_utilizado == "9router"
    assert resp.texto == "resposta do 9router"
    assert any("openrouter" in u for u in chamadas_url)
    assert any("9router" in u for u in chamadas_url)


def test_provedor_com_chave_mas_sem_modelo_ignorado():
    cliente = ClienteLLM()
    cliente.openrouter_key = "or-key"
    cliente.modelo_primario = None
    cliente.ninerouter_key = ""

    with pytest.raises(ErroLLMIndisponivel, match="sem modelo"):
        cliente.invoke("teste")


# ── 4. Testes do Roteador Semântico Tolerante ──

def test_parsear_resposta_roteador_json_puro():
    texto = '{"rota": "sql", "confianca": 0.95, "motivo": "Consulta ao banco"}'
    decisao = _parsear_resposta_roteador(texto)
    assert decisao.rota == "sql"
    assert decisao.confianca == 0.95
    assert decisao.motivo == "Consulta ao banco"


def test_parsear_resposta_roteador_maiusculo_e_espacos():
    texto = '{"rota": " SQL ", "confianca": 0.92, "motivo": "Dados"}'
    decisao = _parsear_resposta_roteador(texto)
    assert decisao.rota == "sql"
    assert decisao.confianca == 0.92


def test_parsear_resposta_roteador_porcentagem():
    texto = '{"rota": "rag", "confianca": "95%", "motivo": "Conceito aneel"}'
    decisao = _parsear_resposta_roteador(texto)
    assert decisao.rota == "rag"
    assert decisao.confianca == 0.95


def test_parsear_resposta_roteador_decimal_virgula():
    texto = '{"rota": "ambos", "confianca": "0,88", "motivo": "Dados e normas"}'
    decisao = _parsear_resposta_roteador(texto)
    assert decisao.rota == "ambos"
    assert decisao.confianca == 0.88


def test_parsear_resposta_roteador_com_think():
    texto = '<think>Eu acho que {"rota": "interna"}</think>```json\n{"rota": "sql", "confianca": 0.99, "motivo": "OK"}\n```'
    decisao = _parsear_resposta_roteador(texto)
    assert decisao.rota == "sql"
    assert decisao.confianca == 0.99


def test_parsear_resposta_roteador_invalido_vira_recusa():
    texto = "Não sei a rota"
    decisao = _parsear_resposta_roteador(texto)
    assert decisao.rota == "recusa"
    assert decisao.confianca == 0.0


# ── 5. Testes do Conferente Numérico com 'Grid 360' ──

def test_conferente_ignora_360_do_grid_360():
    fatos = [{"receita_total": 50000.0}]
    # O texto cita "V-Energy Grid 360", cujo 360 NÃO deve ser cobrado nos fatos
    texto = "Segundo os dados da V-Energy Grid 360, a receita foi de 50.000."
    assert conferir(fatos, texto) is True
    assert numeros_nao_encontrados(fatos, texto) == []


def test_conferente_barra_360_fora_do_nome():
    fatos = [{"receita_total": 50000.0}]
    texto = "Foram inspecionadas 360 unidades e a receita foi de 50.000."
    assert conferir(fatos, texto) is False
    assert "360" in numeros_nao_encontrados(fatos, texto)
