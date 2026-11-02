"""
Tabelas das avaliações do golden set: uma linha por execução e uma por caso.

O script de avaliação cria as tabelas na primeira vez (idempotente), então o setup
não ganha passo novo. A tela do Admin TI só lê; sem execução gravada, mostra o vazio.
"""

from __future__ import annotations

from typing import Any

DDL_AVALIACOES = """
CREATE TABLE IF NOT EXISTS tb_avaliacoes_agente (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    executada_em          TIMESTAMPTZ      NOT NULL DEFAULT now(),
    modelo                TEXT,
    total_casos           INTEGER          NOT NULL,
    casos_aprovados       INTEGER          NOT NULL,
    -- Nulas quando a execução não tem caso daquele tipo
    taxa_execucao         DOUBLE PRECISION,
    taxa_component_match  DOUBLE PRECISION,
    taxa_abstencao        DOUBLE PRECISION,
    tokens_medio          DOUBLE PRECISION,
    duracao_ms            DOUBLE PRECISION NOT NULL
);

CREATE TABLE IF NOT EXISTS tb_avaliacoes_agente_casos (
    avaliacao_id  UUID             NOT NULL REFERENCES tb_avaliacoes_agente (id) ON DELETE CASCADE,
    caso_id       VARCHAR(20)      NOT NULL,
    -- sql, rag ou recusa (rota_esperada do golden set)
    tipo          VARCHAR(20)      NOT NULL,
    pergunta      TEXT             NOT NULL,
    selo          VARCHAR(50)      NOT NULL,
    passou        BOOLEAN          NOT NULL,
    motivo        TEXT             NOT NULL,
    sql_gerado    TEXT,
    tokens        INTEGER          NOT NULL,
    tempo_ms      DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (avaliacao_id, caso_id)
);
"""

_COLUNAS_EXECUCAO = (
    "modelo",
    "total_casos",
    "casos_aprovados",
    "taxa_execucao",
    "taxa_component_match",
    "taxa_abstencao",
    "tokens_medio",
    "duracao_ms",
)
_COLUNAS_CASO = (
    "caso_id",
    "tipo",
    "pergunta",
    "selo",
    "passou",
    "motivo",
    "sql_gerado",
    "tokens",
    "tempo_ms",
)


def criar_tabelas(cursor) -> None:
    cursor.execute(DDL_AVALIACOES)


def gravar_execucao(conexao, execucao: dict[str, Any], modelo: str | None) -> str:
    """Grava a execução e os casos numa transação só; devolve o id da execução."""
    with conexao.cursor() as cur:
        criar_tabelas(cur)
        valores = {**execucao, "modelo": modelo}
        cur.execute(
            f"INSERT INTO tb_avaliacoes_agente ({', '.join(_COLUNAS_EXECUCAO)}) "
            f"VALUES ({', '.join(['%s'] * len(_COLUNAS_EXECUCAO))}) RETURNING id",
            [valores[coluna] for coluna in _COLUNAS_EXECUCAO],
        )
        avaliacao_id = cur.fetchone()[0]
        for caso in execucao["casos"]:
            cur.execute(
                f"INSERT INTO tb_avaliacoes_agente_casos (avaliacao_id, {', '.join(_COLUNAS_CASO)}) "
                f"VALUES (%s, {', '.join(['%s'] * len(_COLUNAS_CASO))})",
                [avaliacao_id, *(caso[coluna] for coluna in _COLUNAS_CASO)],
            )
    conexao.commit()
    return str(avaliacao_id)
