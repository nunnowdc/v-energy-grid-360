#!/usr/bin/env python
"""
Migração idempotente para corrigir os templates do cache de perguntas certificadas.

Problema: os templates usavam igualdade direta em colunas de texto (municipio, bairro, classe,
alimentador, etc.), o que falhava quando a grafia no banco diferia da grafia da pergunta
(ex.: "Olinda" vs "olinda").

Solução: aplicar unaccent(lower(...)) em ambos os lados da comparação para todas as colunas
de texto filtradas por slots. Colunas numéricas, de data ou de ID (ano, mes, competencia, id_uc)
não são alteradas.

A migração é idempotente: pode ser executada múltiplas vezes sem erro.
"""
from __future__ import annotations

import os
import sys
import logging

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Templates corrigidos com unaccent(lower(...)) nas colunas de texto
TEMPLATES_CORRIGIDOS = {
    "faturamento_por_municipio_ano": (
        "SELECT r.municipio, r.ano, SUM(r.receita_faturada) AS receita_total "
        "FROM agg_receita_mensal r "
        "WHERE unaccent(lower(r.municipio)) = unaccent(lower(:municipio)) AND r.ano = :ano "
        "GROUP BY r.municipio, r.ano"
    ),
    # Adicione aqui outros templates conforme forem criados, mantendo o mesmo padrão:
    # - Colunas de texto (municipio, bairro, classe, alimentador, regiao, bandeira_tarifaria,
    #   causa, tipo, status, modalidade, subgrupo_tarifario, etc.): unaccent(lower(col)) = unaccent(lower(:slot))
    # - Colunas numéricas/data/ID (ano, mes, competencia, id_uc, total_ucs, receita_faturada, etc.): col = :slot
}


def executar_migracao(db_url: str) -> None:
    """Executa a migração idempotente nos templates do cache."""
    import psycopg2
    from psycopg2.extras import RealDictCursor

    logger.info("Conectando ao banco: %s", db_url.split("@")[-1] if "@" in db_url else db_url)

    with psycopg2.connect(db_url) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 1. Verifica templates existentes
            cur.execute(
                "SELECT template_id, esqueleto, sql_template FROM tb_cache_perguntas_certificadas WHERE ativo = TRUE;"
            )
            existentes = {row["esqueleto"]: row for row in cur.fetchall()}
            logger.info("Templates ativos encontrados no banco: %d", len(existentes))

            # 2. Para cada template corrigido, faz upsert (INSERT ... ON CONFLICT DO UPDATE)
            for esqueleto, sql_template in TEMPLATES_CORRIGIDOS.items():
                template_id = esqueleto  # usamos o esqueleto como template_id

                if esqueleto in existentes:
                    # Verifica se já está correto
                    atual = existentes[esqueleto]["sql_template"]
                    if atual.strip() == sql_template.strip():
                        logger.info("  ✓ [%s] já está correto (id=%s)", esqueleto, template_id)
                        continue
                    logger.info("  ↻ [%s] atualizando template (id=%s)", esqueleto, template_id)
                else:
                    logger.info("  + [%s] inserindo novo template (id=%s)", esqueleto, template_id)

                # Upsert idempotente
                cur.execute(
                    """
                    INSERT INTO tb_cache_perguntas_certificadas (template_id, esqueleto, sql_template, descricao, ativo)
                    VALUES (%s, %s, %s, %s, TRUE)
                    ON CONFLICT (template_id) DO UPDATE SET
                        sql_template = EXCLUDED.sql_template,
                        descricao = EXCLUDED.descricao,
                        ativo = TRUE
                    """,
                    (
                        template_id,
                        esqueleto,
                        sql_template,
                        f"Template corrigido com unaccent(lower(...)) para filtro de texto sem acento/case",
                    ),
                )

            conn.commit()
            logger.info("Migração concluída com sucesso.")

            # 3. Mostra resultado final
            cur.execute(
                "SELECT template_id, esqueleto, sql_template FROM tb_cache_perguntas_certificadas WHERE ativo = TRUE ORDER BY esqueleto;"
            )
            logger.info("\n=== Templates após migração ===")
            for row in cur.fetchall():
                logger.info("template_id: %s", row["template_id"])
                logger.info("esqueleto: %s", row["esqueleto"])
                logger.info("sql_template: %s", row["sql_template"])
                logger.info("---")


def main() -> None:
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL não definida no ambiente.")
        sys.exit(1)

    try:
        executar_migracao(db_url)
    except Exception as exc:
        logger.exception("Falha na migração: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()