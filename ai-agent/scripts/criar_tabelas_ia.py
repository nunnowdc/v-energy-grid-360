"""
Script de criação das tabelas de controle do módulo de IA no PostgreSQL.
Execute uma vez no banco de desenvolvimento antes de iniciar o agente.
"""
from __future__ import annotations

import os
import sys


DDL_TABELAS = """
-- Extensão vetorial para o RAG
CREATE EXTENSION IF NOT EXISTS vector;

-- Base de conhecimento vetorial (RAG regulatório e de esquemas Gold)
CREATE TABLE IF NOT EXISTS tb_conhecimento_vetorial (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    categoria   VARCHAR(50)  NOT NULL,  -- 'glossario' | 'esquema' | 'prodist' | 'templates'
    titulo      VARCHAR(255) NOT NULL,
    conteudo    TEXT         NOT NULL,
    fonte       VARCHAR(150),
    metadados   JSONB        DEFAULT '{}'::JSONB,
    embedding   vector(384)            -- dimensão do modelo multilíngue paraphrase-MiniLM-L12-v2
);

CREATE INDEX IF NOT EXISTS idx_conhecimento_categoria
    ON tb_conhecimento_vetorial (categoria);

CREATE INDEX IF NOT EXISTS idx_conhecimento_embedding
    ON tb_conhecimento_vetorial USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 50);

-- Log de auditoria ponta a ponta
CREATE TABLE IF NOT EXISTS tb_auditoria_agente (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sessao_id             VARCHAR(100) NOT NULL,
    data_hora             TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    pergunta_original     TEXT         NOT NULL,
    pergunta_autonoma     TEXT,
    rota_escolhida        VARCHAR(50)  NOT NULL,
    hit_cache             BOOLEAN      DEFAULT FALSE,
    sql_gerado            TEXT,
    linhas_retornadas     INTEGER      DEFAULT 0,
    amostra_resultado_json TEXT,
    selo_confianca        VARCHAR(50)  NOT NULL,
    passos_execucao       TEXT,
    tempo_execucao_ms     FLOAT        NOT NULL DEFAULT 0,
    tokens_prompt         INTEGER      DEFAULT 0,
    tokens_resposta       INTEGER      DEFAULT 0,
    erro_mensagem         TEXT,
    feedback_usuario      SMALLINT     -- NULL | 1 (útil) | -1 (inútil)
);

CREATE INDEX IF NOT EXISTS idx_auditoria_sessao
    ON tb_auditoria_agente (sessao_id, data_hora DESC);

-- Cache de perguntas certificadas (templates parametrizados homologados)
CREATE TABLE IF NOT EXISTS tb_cache_perguntas_certificadas (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id     VARCHAR(100) UNIQUE NOT NULL,
    esqueleto       TEXT         NOT NULL,  -- ex: 'faturamento_por_municipio_ano'
    sql_template    TEXT         NOT NULL,  -- SQL com placeholders :municipio, :ano
    descricao       TEXT,
    entidades_slots JSONB        DEFAULT '{}'::JSONB,
    ativo           BOOLEAN      DEFAULT TRUE,
    criado_em       TIMESTAMPTZ  DEFAULT CURRENT_TIMESTAMP
);

-- Cache de insights proativos por tela
CREATE TABLE IF NOT EXISTS tb_insights_tela (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tela                  VARCHAR(50)  NOT NULL,
    entidade_id           VARCHAR(100) NOT NULL,
    fatos_calculados_json JSONB        NOT NULL,
    texto_insight         TEXT         NOT NULL,
    selo_validacao        VARCHAR(50)  NOT NULL,
    gerado_em             TIMESTAMPTZ  DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_insights_tela_entidade
    ON tb_insights_tela (tela, entidade_id);
"""


def criar_tabelas(db_url: str) -> None:
    print("Criando tabelas de controle do módulo de IA no PostgreSQL...")
    try:
        import psycopg2
        with psycopg2.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(DDL_TABELAS)
            conn.commit()
        print("✅  Tabelas criadas com sucesso.")
    except ImportError:
        print("❌  psycopg2 não encontrado. Instale com: pip install psycopg2-binary")
        sys.exit(1)
    except Exception as e:
        print(f"❌  Erro ao criar tabelas: {e}")
        sys.exit(1)


if __name__ == "__main__":
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌  Variável de ambiente DATABASE_URL não definida.")
        sys.exit(1)
    criar_tabelas(db_url)
