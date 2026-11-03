"""
Testes unitários para o nó 11 — Síntese da resposta final.

Valida:
- Fallback (_gerar_resposta_mock) produz texto natural com formatação brasileira.
- no_sintetiza_resposta devolve estrutura esperada quando LLM indisponível (mock).
"""
from __future__ import annotations

import pytest

from src.nos.no_sintetiza_resposta import _gerar_resposta_mock, no_sintetiza_resposta


# ---------------------------------------------------------------------------
# Helpers de mock para o LLM
# ---------------------------------------------------------------------------
class FakeLLM:
    """Implementação mínima de ClienteLLM que retorna resposta mock."""

    def __init__(self, resposta_texto: str = "Resposta do LLM", deve_falhar: bool = False):
        self.resposta_texto = resposta_texto
        self.deve_falhar = deve_falhar
        self.historico_chamadas = []

    def invoke(self, *, prompt: str, system_prompt: str, temperatura: float, resposta_mock: str):
        self.historico_chamadas.append(
            {
                "prompt": prompt,
                "system_prompt": system_prompt,
                "temperatura": temperatura,
                "resposta_mock": resposta_mock,
            }
        )
        if self.deve_falhar:
            from src.provedores.cliente_llm import ErroLLMIndisponivel

            raise ErroLLMIndisponivel("LLM simulado indisponível")
        # Objeto simples com os atributos esperados pelo nó
        class _Resp:
            def __init__(self, texto: str):
                self.texto = texto
                self.tokens_prompt = 10
                self.tokens_resposta = 20

        return _Resp(self.resposta_texto)


# ---------------------------------------------------------------------------
# Testes do fallback (_gerar_resposta_mock)
# ---------------------------------------------------------------------------
def test_gerar_resposta_mock_formata_valores_monetarios():
    """O fallback deve formatar números no padrão BR e usar nomes amigáveis."""
    dados = [
        {
            "municipio": "Recife",
            "ano": 2024,
            "receita_total": 68560067.39000009,
        }
    ]
    pergunta = "Qual o faturamento em Recife no ano de 2024?"
    resp = _gerar_resposta_mock(dados, pergunta)

    # Preâmbulo baseado na pergunta original
    assert resp.startswith("Conforme solicitado, Qual o faturamento em Recife no ano de 2024:")
    # Nomes de coluna amigáveis
    assert "Município: Recife" in resp
    assert "Ano: 2024" in resp
    # Formatação monetária brasileira (ponto milhar, vírgula decimal, símbolo R$)
    assert "R$ 68.560.067,39" in resp


def test_gerar_resposta_mock_varias_linhas():
    """Quando há mais de uma linha, o texto indica a quantidade."""
    dados = [
        {"municipio": "Recife", "ano": 2024, "receita_total": 1000},
        {"municipio": "Olinda", "ano": 2024, "receita_total": 2000},
    ]
    pergunta = "Faturamento 2024?"
    resp = _gerar_resposta_mock(dados, pergunta)
    assert "(2 linhas)" in resp


def test_gerar_resposta_mock_sem_dados():
    """Sem dados deve retornar mensagem padrão."""
    resp = _gerar_resposta_mock([], "Qualquer coisa?")
    assert resp == "Não há dados disponíveis para responder a esta pergunta no momento."


# ---------------------------------------------------------------------------
# Testes do nó completo (no_sintetiza_resposta) em modo mock / LLM indisponível
# ---------------------------------------------------------------------------
def test_no_sintetiza_resposta_llm_indisponivel_usa_fallback():
    """Se o LLM lançar ErroLLMIndisponivel, o nó deve usar o fallback determinístico."""
    fake_llm = FakeLLM(deve_falhar=True)
    estado = {
        "dados_sql": [
            {"municipio": "Olinda", "ano": 2024, "receita_total": 16679081.66}
        ],
        "contexto_rag": [],
        "pergunta_autonoma": "Faturamento Olinda 2024?",
        "rota": "sql",
        "chamadas_llm": 0,
        "tokens_prompt": 0,
        "tokens_resposta": 0,
    }
    resultado = no_sintetiza_resposta(estado, fake_llm)

    # Deve conter a resposta formatada pelo fallback
    assert "Município: Olinda" in resultado["texto_resposta"]
    assert "R$ 16.679.081,66" in resultado["texto_resposta"]
    # Selo de confiança para rota SQL sem cache
    assert resultado["selo_confianca"] == "gerada_confiavel"
    # Passo de conferência indica uso do plano B
    assert any("LLM indisponível" in p for p in resultado["passos_executados"])


def test_no_sintetiza_resposta_conferencia_reprovada_usa_fallback():
    """Se a conferência numérica reprovar, o nó troca a resposta do LLM pelo fallback."""
    # LLM responde algo que a conferência vai recusar (ex.: abreviação "R$ 16,7 mi")
    fake_llm = FakeLLM(resposta_texto="O faturamento foi de R$ 16,7 milhões.")
    estado = {
        "dados_sql": [
            {"municipio": "Olinda", "ano": 2024, "receita_total": 16679081.66}
        ],
        "contexto_rag": [],
        "pergunta_autonoma": "Faturamento Olinda 2024?",
        "rota": "sql",
        "chamadas_llm": 0,
        "tokens_prompt": 0,
        "tokens_resposta": 0,
    }
    resultado = no_sintetiza_resposta(estado, fake_llm)

    # A resposta final deve ser a do fallback (formatada corretamente)
    assert "R$ 16.679.081,66" in resultado["texto_resposta"]
    assert "Município: Olinda" in resultado["texto_resposta"]
    # Passo indica que a conferência reprovou
    assert any("Conferência numérica reprovada" in p for p in resultado["passos_executados"])


def test_no_sintetiza_resposta_rota_rag_sem_contexto_retorna_recusa():
    """Rota RAG sem chunks deve emitir recusa honesta sem chamar LLM."""
    fake_llm = FakeLLM()
    estado = {
        "dados_sql": [],
        "contexto_rag": [],
        "pergunta_autonoma": "O que diz a resolução 414?",
        "rota": "rag",
        "chamadas_llm": 0,
        "tokens_prompt": 0,
        "tokens_resposta": 0,
    }
    resultado = no_sintetiza_resposta(estado, fake_llm)

    assert resultado["selo_confianca"] == "recusa_honesta"
    assert resultado["motivo_recusa"] == "sem_dados"
    assert "não há dados" in resultado["texto_resposta"].lower()
    # LLM não deve ter sido chamado
    assert len(fake_llm.historico_chamadas) == 0