from __future__ import annotations

import pytest

from src.insights.extrator_metricas_fixas import (
    adicionar_variacao_percentual_diagnostico_receita,
    extrair_metricas,
)
from src.insights.conferente_numerico import conferir


class FakeResult:
    def __init__(self, sucesso=True, linhas=None, erro=None):
        self.sucesso = sucesso
        self.linhas = linhas or []
        self.erro = erro


class FakeExecutor:
    def __init__(self, linhas):
        self.linhas = linhas

    def executar(self, sql):
        return FakeResult(sucesso=True, linhas=self.linhas)


def test_variacao_positiva():
    linhas = [
        {"ano": 2025, "receita_total": 108.0, "volume_total": 216.0},
        {"ano": 2024, "receita_total": 100.0, "volume_total": 200.0},
    ]
    adicionar_variacao_percentual_diagnostico_receita(linhas)
    assert linhas[0]["variacao_receita_pct"] == 8.0
    assert linhas[0]["variacao_volume_pct"] == 8.0


def test_variacao_negativa_e_conferente():
    linhas = [
        {"ano": 2025, "receita_total": 96.0, "volume_total": 190.0},
        {"ano": 2024, "receita_total": 100.0, "volume_total": 200.0},
    ]
    adicionar_variacao_percentual_diagnostico_receita(linhas)
    assert linhas[0]["variacao_receita_pct"] == -4.0
    assert linhas[0]["variacao_volume_pct"] == -5.0

    # Texto com número correto (absoluto) correspondente à variação negativa (-4.0 -> 4)
    texto_correto = "A receita teve queda de 4% em 2025."
    assert conferir(linhas, texto_correto) is True


def test_texto_com_numero_errado_reprova():
    linhas = [
        {"ano": 2025, "receita_total": 96.0, "volume_total": 190.0},
        {"ano": 2024, "receita_total": 100.0, "volume_total": 200.0},
    ]
    adicionar_variacao_percentual_diagnostico_receita(linhas)
    texto_errado = "A receita teve queda de 7% em 2025."
    assert conferir(linhas, texto_errado) is False


def test_menos_de_duas_linhas_ou_anterior_zero():
    # Menos de 2 linhas
    linhas_uma = [{"ano": 2025, "receita_total": 100.0, "volume_total": 200.0}]
    adicionar_variacao_percentual_diagnostico_receita(linhas_uma)
    assert "variacao_receita_pct" not in linhas_uma[0]

    # Anterior zero
    linhas_zero = [
        {"ano": 2025, "receita_total": 100.0, "volume_total": 200.0},
        {"ano": 2024, "receita_total": 0.0, "volume_total": 0.0},
    ]
    adicionar_variacao_percentual_diagnostico_receita(linhas_zero)
    assert linhas_zero[0].get("variacao_receita_pct") is None
    assert linhas_zero[0].get("variacao_volume_pct") is None


def test_visao_360_uc_nao_muda():
    fatos_originais = [
        {"competencia": "2025-02-01", "consumo_kwh": 150.0, "receita_faturada": 75.0, "status_pagamento": "PAGO"},
        {"competencia": "2025-01-01", "consumo_kwh": 140.0, "receita_faturada": 70.0, "status_pagamento": "PAGO"},
    ]
    executor = FakeExecutor(fatos_originais)
    resultado = extrair_metricas("visao_360_uc", "UC12345", executor)
    assert resultado == fatos_originais
    assert all("variacao_receita_pct" not in r for r in resultado)
