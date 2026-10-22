"""
Fixtures e configurações compartilhadas para os testes do agente V-Energy Grid 360.
Fornece banco SQLite sintético com schema da camada Gold, mocks de LLM e validador SQL.
"""
from __future__ import annotations

import os
import sqlite3
import sys
import types
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import pytest

# ── 1. Resolução do módulo ai_agent e paths de importação ────────────────────
root_dir = Path(__file__).resolve().parent.parent.parent
ai_agent_dir = Path(__file__).resolve().parent.parent

for p in [str(root_dir), str(ai_agent_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

if "ai_agent" not in sys.modules:
    ai_agent_mod = types.ModuleType("ai_agent")
    ai_agent_mod.__path__ = [str(ai_agent_dir)]
    ai_agent_mod.__file__ = str(ai_agent_dir / "__init__.py")
    sys.modules["ai_agent"] = ai_agent_mod

from ai_agent.src.provedores.cliente_llm import ClienteLLM, RespostaLLM
from ai_agent.src.services.sql_executor import SQLExecutor
from ai_agent.src.interfaces.stub_validador_sql import StubValidadorSQL
from security.sql_validator import SQLValidator


# ── 2. DDL e Carga de Dados Sintéticos (Camada Gold) ─────────────────────────
DDL_GOLD = """
CREATE TABLE IF NOT EXISTS dim_unidade_consumidora (
    uc_id INTEGER PRIMARY KEY,
    codigo_uc TEXT UNIQUE NOT NULL,
    nome_cliente TEXT NOT NULL,
    classe TEXT NOT NULL,
    municipio TEXT NOT NULL,
    bairro TEXT NOT NULL,
    fase TEXT NOT NULL,
    status_ligacao TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_faturamento (
    id_fatura INTEGER PRIMARY KEY,
    uc_id INTEGER NOT NULL,
    ano INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    volume_faturado REAL NOT NULL,
    receita_faturada REAL NOT NULL,
    status_pagamento TEXT NOT NULL,
    FOREIGN KEY (uc_id) REFERENCES dim_unidade_consumidora(uc_id)
);

CREATE TABLE IF NOT EXISTS fact_ocorrencias (
    id_ocorrencia INTEGER PRIMARY KEY,
    uc_id INTEGER NOT NULL,
    tipo_interrupcao TEXT NOT NULL,
    duracao_minutos REAL NOT NULL,
    data_inicio TEXT NOT NULL,
    ano INTEGER NOT NULL,
    FOREIGN KEY (uc_id) REFERENCES dim_unidade_consumidora(uc_id)
);
"""

DADOS_SINTETICOS_UCS = [
    (1, "UC-00101", "Empresa Alfa LTDA", "Comercial", "Recife", "Boa Viagem", "Trifásico", "Ativo"),
    (2, "UC-00102", "Restaurante Beta", "Comercial", "Olinda", "Bairro Novo", "Bifásico", "Ativo"),
    (3, "UC-00103", "Indústria Gama S/A", "Industrial", "Jaboatão dos Guararapes", "Prazeres", "Trifásico", "Ativo"),
    (4, "UC-00104", "João da Silva", "Residencial", "Recife", "Boa Viagem", "Monofásico", "Ativo"),
    (5, "UC-00105", "Maria Fernandes", "Residencial", "Olinda", "Casa Caiada", "Monofásico", "Ativo"),
    (6, "UC-00106", "Prefeitura Municipal", "Poder Público", "Recife", "Santo Antônio", "Trifásico", "Ativo"),
]

DADOS_SINTETICOS_FATURAMENTO = [
    # uc_id, ano, mes, volume_faturado, receita_faturada, status_pagamento
    (1, 1, 2023, 1, 1200.0, 1080.0, "Pago"),
    (2, 1, 2023, 2, 1300.0, 1170.0, "Pago"),
    (3, 1, 2024, 1, 1400.0, 1260.0, "Pago"),
    (4, 2, 2023, 1, 850.0, 765.0, "Pago"),
    (5, 2, 2023, 2, 900.0, 810.0, "Pago"),
    (6, 2, 2024, 1, 950.0, 855.0, "Pago"),
    (7, 3, 2023, 1, 15000.0, 12000.0, "Pago"),
    (8, 3, 2024, 1, 16000.0, 12800.0, "Pago"),
    (9, 4, 2023, 1, 250.0, 200.0, "Pago"),
    (10, 4, 2024, 1, 280.0, 224.0, "Pago"),
    (11, 5, 2023, 1, 310.0, 248.0, "Pago"),
    (12, 6, 2023, 1, 5000.0, 4500.0, "Pago"),
]

DADOS_SINTETICOS_OCORRENCIAS = [
    # id, uc_id, tipo, duracao, data_inicio, ano
    (1, 1, "Acidental", 45.0, "2023-03-12 14:00:00", 2023),
    (2, 1, "Programada", 120.0, "2023-08-05 08:00:00", 2023),
    (3, 2, "Acidental", 90.0, "2023-05-18 10:30:00", 2023),
    (4, 4, "Acidental", 30.0, "2024-02-10 16:15:00", 2024),
]


@pytest.fixture
def sqlite_gold_path(tmp_path: Path) -> str:
    """
    Cria e popula um arquivo SQLite temporário com o schema Gold e dados sintéticos.
    Retorna o caminho em string para ser consumido pelo SQLExecutor.
    """
    db_file = tmp_path / "v_energy_gold_test.db"
    conn = sqlite3.connect(str(db_file))
    cur = conn.cursor()
    cur.executescript(DDL_GOLD)

    cur.executemany(
        "INSERT INTO dim_unidade_consumidora VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        DADOS_SINTETICOS_UCS,
    )
    cur.executemany(
        "INSERT INTO fact_faturamento VALUES (?, ?, ?, ?, ?, ?, ?)",
        DADOS_SINTETICOS_FATURAMENTO,
    )
    cur.executemany(
        "INSERT INTO fact_ocorrencias VALUES (?, ?, ?, ?, ?, ?)",
        DADOS_SINTETICOS_OCORRENCIAS,
    )
    conn.commit()
    conn.close()
    return str(db_file)


@pytest.fixture
def sql_executor_teste(sqlite_gold_path: str) -> SQLExecutor:
    """Instância de SQLExecutor apontando para o banco SQLite sintético."""
    return SQLExecutor(sqlite_path=sqlite_gold_path)


@pytest.fixture
def validador_sql_padrao() -> SQLValidator:
    """Instância do SQLValidator (AST sqlglot) em dialeto sqlite para testes."""
    return SQLValidator(dialect="sqlite")


# ── 3. Fakes e Mocks de LLM ──────────────────────────────────────────────────
class FakeClienteLLM(ClienteLLM):
    """
    Dublê de teste para ClienteLLM que retorna respostas pré-programadas
    ou roteadas por palavras-chave, sem chamadas de rede.
    """

    def __init__(self, mapa_respostas: Optional[Dict[str, str]] = None, resposta_padrao: str = ""):
        super().__init__()
        self.forcar_mock = True
        self.mapa_respostas = mapa_respostas or {}
        self.resposta_padrao = resposta_padrao
        self.historico_chamadas: List[Dict[str, Any]] = []

    def invoke(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperatura: float = 0.0,
        resposta_mock: Optional[str] = None,
    ) -> RespostaLLM:
        self.historico_chamadas.append({
            "prompt": prompt,
            "system_prompt": system_prompt,
            "temperatura": temperatura,
        })

        # 1. Procura match em mapa_respostas por substring do prompt ou system_prompt
        texto = None
        for chave, resp in self.mapa_respostas.items():
            if chave.lower() in prompt.lower() or (system_prompt and chave.lower() in system_prompt.lower()):
                texto = resp
                break

        # 2. Resposta padrão do teste
        if texto is None and self.resposta_padrao:
            texto = self.resposta_padrao

        # 3. Fallback do nó
        if texto is None and resposta_mock:
            texto = resposta_mock

        if not texto:
            texto = "Mock FakeLLM: resposta automática de teste."

        return RespostaLLM(
            texto=texto,
            tokens_prompt=len(prompt.split()),
            tokens_resposta=len(texto.split()),
            provedor_utilizado="fake_llm_teste",
            latencia_ms=1.5,
        )


@pytest.fixture
def fake_llm_factory() -> Callable[..., FakeClienteLLM]:
    """Fábrica para instanciar FakeClienteLLM configurado sob demanda."""
    def _criar(mapa_respostas: Optional[Dict[str, str]] = None, resposta_padrao: str = "") -> FakeClienteLLM:
        return FakeClienteLLM(mapa_respostas=mapa_respostas, resposta_padrao=resposta_padrao)
    return _criar
