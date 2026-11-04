"""
Fixtures e configurações compartilhadas para os testes do agente V-Energy Grid 360.
Fornece banco SQLite sintético com schema da camada Gold, mocks de LLM e validador SQL.
"""
from __future__ import annotations

import os
import logging
import re
import sqlite3
import sys
import types
import uuid
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

from src.provedores.cliente_llm import ClienteLLM, RespostaLLM
from src.services.sql_executor import SQLExecutor
from src.interfaces.stub_validador_sql import StubValidadorSQL
from security.sql_validator import SQLValidator

logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def isolar_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """Impede que testes herdem uma URL genérica de banco do ambiente local."""
    monkeypatch.delenv("DATABASE_URL", raising=False)


# ── 2. DDL e Carga de Dados Sintéticos (Camada Gold) ─────────────────────────
DDL_GOLD = """
CREATE TABLE IF NOT EXISTS dim_unidade_consumidora (
    id_uc VARCHAR(30) PRIMARY KEY,
    classe VARCHAR(50) NOT NULL,
    municipio VARCHAR(100) NOT NULL,
    bairro VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_faturamento (
    id_fatura VARCHAR(50) PRIMARY KEY,
    id_uc VARCHAR(30) NOT NULL REFERENCES dim_unidade_consumidora(id_uc),
    ano INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    receita_faturada NUMERIC NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_leituras (
    id_leitura VARCHAR(50) PRIMARY KEY,
    id_uc VARCHAR(30) NOT NULL REFERENCES dim_unidade_consumidora(id_uc),
    ano INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    consumo_kwh NUMERIC NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_ocorrencias (
    id_ocorrencia VARCHAR(50) PRIMARY KEY,
    id_uc VARCHAR(30) NOT NULL REFERENCES dim_unidade_consumidora(id_uc),
    tipo VARCHAR(50) NOT NULL,
    causa VARCHAR(100) NOT NULL,
    competencia DATE NOT NULL,
    duracao_h NUMERIC NOT NULL
);
"""

DADOS_SINTETICOS_UCS = [
    ("UC-00101", "COMERCIAL", "Recife", "Boa Viagem", "ATIVA"),
    ("UC-00102", "COMERCIAL", "Olinda", "Bairro Novo", "ATIVA"),
    ("UC-00103", "INDUSTRIAL", "Jaboatão dos Guararapes", "Prazeres", "ATIVA"),
    ("UC-00104", "RESIDENCIAL", "Recife", "Boa Viagem", "ATIVA"),
    ("UC-00105", "RESIDENCIAL", "Olinda", "Casa Caiada", "ATIVA"),
    ("UC-00106", "PODER_PUBLICO", "Recife", "Santo Antônio", "ATIVA"),
]

DADOS_SINTETICOS_FATURAMENTO = [
    # id_fatura, id_uc, ano, mes, receita_faturada
    ("FAT-001", "UC-00101", 2023, 1, 1080.0),
    ("FAT-002", "UC-00101", 2023, 2, 1170.0),
    ("FAT-003", "UC-00101", 2024, 1, 1260.0),
    ("FAT-004", "UC-00102", 2023, 1, 765.0),
    ("FAT-005", "UC-00102", 2023, 2, 810.0),
    ("FAT-006", "UC-00102", 2024, 1, 855.0),
    ("FAT-007", "UC-00103", 2023, 1, 12000.0),
    ("FAT-008", "UC-00103", 2024, 1, 12800.0),
    ("FAT-009", "UC-00104", 2023, 1, 200.0),
    ("FAT-010", "UC-00104", 2024, 1, 224.0),
    ("FAT-011", "UC-00105", 2023, 1, 248.0),
    ("FAT-012", "UC-00106", 2023, 1, 4500.0),
]

DADOS_SINTETICOS_LEITURAS = [
    # id_leitura, id_uc, ano, mes, consumo_kwh
    ("LEI-001", "UC-00101", 2023, 1, 1200.0),
    ("LEI-002", "UC-00101", 2023, 2, 1300.0),
    ("LEI-003", "UC-00102", 2023, 1, 850.0),
    ("LEI-004", "UC-00102", 2023, 2, 900.0),
    ("LEI-005", "UC-00103", 2023, 1, 15000.0),
    ("LEI-006", "UC-00104", 2023, 1, 250.0),
]

DADOS_SINTETICOS_OCORRENCIAS = [
    # id_ocorrencia, id_uc, tipo, causa, competencia, duracao_h
    ("OCO-001", "UC-00101", "FALTA DE ENERGIA", "CLIMATICA", "2023-03-01", 0.75),
    ("OCO-002", "UC-00101", "FALTA DE ENERGIA", "VEGETACAO", "2023-08-01", 2.0),
    ("OCO-003", "UC-00102", "FALTA DE ENERGIA", "CLIMATICA", "2023-05-01", 1.5),
    ("OCO-004", "UC-00104", "FALTA DE ENERGIA", "CLIMATICA", "2024-02-01", 0.5),
]


def _testar_conexao_postgres(db_url: str) -> bool:
    """Verifica rapidamente se o PostgreSQL está acessível."""
    conn = None
    try:
        import psycopg2
        conn = psycopg2.connect(db_url, connect_timeout=2)
        return True
    except Exception as exc:
        logger.warning("PostgreSQL indisponível; usando SQLite nos testes: %s", exc)
        return False
    finally:
        if conn is not None:
            conn.close()


@pytest.fixture(scope="session")
def postgres_test_info():
    """
    Sessão de testes com PostgreSQL real:
    Cria e popula um schema temporário exclusivo desta execução.
    O nome usa TEST_POSTGRES_SCHEMA como prefixo, nunca apaga schema preexistente.
    Retorna dicionário indicando disponibilidade, db_url e schema.
    """
    db_url = os.getenv("TEST_DATABASE_URL")
    schema_prefix = os.getenv("TEST_POSTGRES_SCHEMA", "venergy_test_gold")

    if not db_url or not db_url.startswith("postgres"):
        logger.warning("TEST_DATABASE_URL não configurada para PostgreSQL; usando SQLite nos testes.")
        yield {"disponivel": False, "db_url": None, "schema": None}
        return

    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", schema_prefix):
        raise ValueError("TEST_POSTGRES_SCHEMA deve conter apenas letras, números e underscore, começando por letra ou underscore.")

    schema = f"{schema_prefix[:48]}_{uuid.uuid4().hex[:12]}"
    if not _testar_conexao_postgres(db_url):
        yield {"disponivel": False, "db_url": None, "schema": None}
        return

    import psycopg2
    from psycopg2 import sql

    schema_criado = False
    conn = None
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
            schema_criado = True
            cur.execute(
                sql.SQL("SET search_path TO {}, public").format(sql.Identifier(schema))
            )
            cur.execute(DDL_GOLD)

            cur.executemany(
                "INSERT INTO dim_unidade_consumidora VALUES (%s, %s, %s, %s, %s)",
                DADOS_SINTETICOS_UCS,
            )
            cur.executemany(
                "INSERT INTO fact_faturamento VALUES (%s, %s, %s, %s, %s)",
                DADOS_SINTETICOS_FATURAMENTO,
            )
            cur.executemany(
                "INSERT INTO fact_leituras VALUES (%s, %s, %s, %s, %s)",
                DADOS_SINTETICOS_LEITURAS,
            )
            cur.executemany(
                "INSERT INTO fact_ocorrencias VALUES (%s, %s, %s, %s, %s, %s)",
                DADOS_SINTETICOS_OCORRENCIAS,
            )
    except Exception as exc:
        if conn is not None:
            conn.close()
        if schema_criado:
            cleanup_conn = psycopg2.connect(db_url)
            try:
                cleanup_conn.autocommit = True
                with cleanup_conn.cursor() as cur:
                    cur.execute(
                        sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema))
                    )
            finally:
                cleanup_conn.close()
        raise RuntimeError(
            f"Falha ao preparar schema PostgreSQL para os testes: {exc}"
        ) from exc

    finally:
        if conn is not None and not conn.closed:
            conn.close()

    try:
        yield {"disponivel": True, "db_url": db_url, "schema": schema}
    finally:
        cleanup_conn = psycopg2.connect(db_url)
        try:
            cleanup_conn.autocommit = True
            with cleanup_conn.cursor() as cur:
                cur.execute(
                    sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema))
                )
        finally:
            cleanup_conn.close()


@pytest.fixture
def sqlite_gold_path(tmp_path: Path) -> str:
    """
    Fallback: Cria e popula arquivo SQLite temporário com o schema Gold e dados sintéticos.
    """
    db_file = tmp_path / "v_energy_gold_test.db"
    conn = sqlite3.connect(str(db_file))
    cur = conn.cursor()
    cur.executescript(DDL_GOLD)

    cur.executemany(
        "INSERT INTO dim_unidade_consumidora VALUES (?, ?, ?, ?, ?)",
        DADOS_SINTETICOS_UCS,
    )
    cur.executemany(
        "INSERT INTO fact_faturamento VALUES (?, ?, ?, ?, ?)",
        DADOS_SINTETICOS_FATURAMENTO,
    )
    cur.executemany(
        "INSERT INTO fact_leituras VALUES (?, ?, ?, ?, ?)",
        DADOS_SINTETICOS_LEITURAS,
    )
    cur.executemany(
        "INSERT INTO fact_ocorrencias VALUES (?, ?, ?, ?, ?, ?)",
        DADOS_SINTETICOS_OCORRENCIAS,
    )
    conn.commit()
    conn.close()
    return str(db_file)


@pytest.fixture
def sql_executor_teste(postgres_test_info, sqlite_gold_path: str) -> SQLExecutor:
    """
    Instância de SQLExecutor conectada ao PostgreSQL real (se disponível)
    ou com fallback transparente para SQLite sintético.
    """
    if postgres_test_info.get("disponivel"):
        return SQLExecutor(
            db_url=postgres_test_info["db_url"],
            schema=postgres_test_info["schema"],
        )
    return SQLExecutor(sqlite_path=sqlite_gold_path)


@pytest.fixture
def usando_postgres(postgres_test_info) -> bool:
    """Indica se a execução atual dos testes está usando PostgreSQL real."""
    return postgres_test_info["disponivel"]


@pytest.fixture
def validador_sql_padrao() -> SQLValidator:
    """Instância do SQLValidator (AST sqlglot) padronizada no dialeto postgres para testes."""
    return SQLValidator(dialect="postgres")


# ── 3. Fakes e Mocks de LLM ──────────────────────────────────────────────────
class FakeClienteLLM(ClienteLLM):
    """
    Dublê de teste para ClienteLLM que retorna respostas pré-programadas
    ou roteadas por palavras-chave, sem chamadas de rede.
    """

    def __init__(self, mapa_respostas: Optional[Dict[str, str]] = None, resposta_padrao: str = ""):
        # Não chamar super().__init__() pois ele valida chaves de API
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

        # 3. Fallback do nó (apenas se não forçar mock ou se resposta_mock for fornecida explicitamente)
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
